import uuid
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot
from database import channels_col
import config

# --- ADMIN BUTTON SE DIRECT CALL HONE WALA FUNCTION ---
@bot.message_handler(commands=['add_story'])
def start_add_story(message):
    if message.from_user.id != config.ADMIN_ID: 
        return
    
    chat_id = message.chat.id
    
    msg = bot.send_message(
        chat_id, 
        "🎬 <b>sᴛᴏʀʏ sᴇᴛᴜᴘ:</b>\n\n"
        "Story ka naam kya hai?\n"
        "<i>(Aap direct <b>Photo</b> bhi bhej sakte hain, bas uske <b>Caption</b> mein Story ka naam likh dein)</i>", 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, get_story_name)

def get_story_name(message):
    if message.text and message.text == "/cancel": 
        return bot.send_message(message.chat.id, "❌ Setup cancelled.")
    
    story_name = None
    file_id = None

    if message.photo:
        file_id = message.photo[-1].file_id  
        story_name = message.caption.split("\n")[0] if message.caption else "Untitled Story"
    elif message.text:
        story_name = message.text
    else:
        msg = bot.send_message(message.chat.id, "❌ Please ek valid text naam ya photo bhejein:")
        bot.register_next_step_handler(msg, get_story_name)
        return

    msg = bot.send_message(message.chat.id, "🔗 <b>ᴅᴇᴍᴏ ʟɪɴᴋ:</b>\nDemo channel ya video link dein (Ya 'skip' likhein):")
    bot.register_next_step_handler(msg, get_demo_link, story_name, file_id)

def get_demo_link(message, story_name, file_id):
    if message.text and message.text.lower() == 'skip':
        demo = None
    else:
        demo = message.text
        
    msg = bot.send_message(message.chat.id, "🤖 <b><b>ғɪɴᴀʟ ʙᴏᴛ ʟɪɴᴋ:</b></b>\nPayment ke baad milne wala main link dein:")
    bot.register_next_step_handler(msg, get_final_link, story_name, demo, file_id)

def get_final_link(message, story_name, demo, file_id):
    final_link = message.text
    msg = bot.send_message(message.chat.id, "💰 <b><b>ᴘʀɪᴄᴇ:</b></b>\nSirf number likhein (Example: 49):")
    bot.register_next_step_handler(msg, ask_category, story_name, demo, final_link, file_id)

# NAYA STEP: Price lene ke baad platform poochne ke liye inline buttons
def ask_category(message, story_name, demo, final_link, file_id):
    if not message.text or not message.text.isdigit():
        msg = bot.send_message(message.chat.id, "❌ Price sirf number mein likhein:")
        bot.register_next_step_handler(msg, ask_category, story_name, demo, final_link, file_id)
        return

    price = message.text
    story_id = str(uuid.uuid4())[:10] # Unique ID pehle hi generate kar li taaki callback me bhej sakein

    # Hum saare data ko database me temporary ('pending') flag ke sath save kar rahe hain
    # Taaki jab admin button dabaye, toh data loss na ho aur seedhe update ho jaye.
    channels_col.insert_one({
        "item_id": story_id,
        "story_name": story_name,
        "demo_link": demo,
        "bot_link": final_link,
        "price": price,
        "file_id": file_id, 
        "type": "story",
        "status": "pending" # Temporary status
    })

    # Keyboard buttons for platform selection
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🎧 Pocket FM", callback_data=f"src_pocket_{story_id}"),
        InlineKeyboardButton("📚 Pratilipi FM", callback_data=f"src_pratilipi_{story_id}")
    )

    bot.send_message(
        message.chat.id, 
        "📂 <b>ᴄᴀᴛᴇɢᴏʀʏ sᴇʟᴇᴄᴛ ᴋᴀʀᴇɪɴ:</b>\nYeh story kis platform ki hai?", 
        reply_markup=markup, 
        parse_mode="HTML"
    )

# NAYA HANDLER: Button press hone par data update karne aur link dene ke liye
@bot.callback_query_handler(func=lambda call: call.data.startswith('src_'))
def save_story_with_source(call):
    if call.from_user.id != config.ADMIN_ID:
        return bot.answer_callback_query(call.id, "Unauthorized!")

    # Callback data se platform aur story_id nikalna
    parts = call.data.split('_')
    platform = "Pocket FM" if parts[1] == "pocket" else "Pratilipi FM"
    story_id = parts[2]

    # Database me pending story ko search karke update karna
    story_data = channels_col.find_one_and_update(
        {"item_id": story_id, "status": "pending"},
        {"$set": {"source": platform}, "$unset": {"status": ""}}, # source set kiya aur pending flag hata diya
        return_document=True
    )

    if not story_data:
        return bot.answer_callback_query(call.id, "❌ Session expired ya data nahi mila!", show_alert=True)

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

    bot_username = bot.get_me().username
    share_link = f"https://t.me/{bot_username}?start={story_id}"
    
    res = (
        f"✅ <b>sᴛᴏʀʏ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n"
        f"────────────────────\n"
        f"📖 Name: <b>{story_data['story_name']}</b>\n"
        f"📂 Platform: <b>{platform}</b>\n"
        f"💰 Price: <b>₹{story_data['price']}</b>\n"
        f"🖼️ Media: <b>{'Saved' if story_data['file_id'] else 'No Photo'}</b>\n\n"
        f"🔗 <b>ʏᴏᴜʀ sʜᴀʀᴇ ʟɪɴᴋ:</b>\n<code>{share_link}</code>\n"
        f"────────────────────\n"
        f"➔ Is link ko copy karke promote karein."
    )
    
    if story_data['file_id']:
        bot.send_photo(call.message.chat.id, photo=story_data['file_id'], caption=res, parse_mode="HTML")
    else:
        bot.send_message(call.message.chat.id, res, parse_mode="HTML")
