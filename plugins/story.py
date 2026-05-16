import uuid
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot
from database import channels_col
import config

# --- ADMIN BUTTON SE DIRECT CALL HONE WALA FUNCTION ---
@bot.message_handler(commands=['add_story'])
def start_add_story(message):
    if message.from_user.id != config.ADMIN_ID: return
    
    chat_id = message.chat.id
    
    # Message thoda modify kiya taaki admin ko pata chale ki photo bhi support hai
    msg = bot.send_message(
        chat_id, 
        "🎬 <b>sᴛᴏʀʏ sᴇᴛᴜᴘ:</b>\n\n"
        "Story ka naam kya hai?\n"
        "<i>(Aap direct <b>Photo</b> bhi bhej sakte hain, bas uske <b>Caption</b> mein Story ka naam likh dein)</i>", 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, get_story_name)

def get_story_name(message):
    if message.text == "/cancel": 
        return bot.send_message(message.chat.id, "❌ Setup cancelled.")
    
    story_name = None
    file_id = None

    # CASE 1: Agar admin ne direct photo bheji hai caption ke sath
    if message.photo:
        file_id = message.photo[-1].file_id  # High quality photo ki file_id
        # Caption ki pehli line ko story name banaenge
        story_name = message.caption.split("\n")[0] if message.caption else "Untitled Story"
    
    # CASE 2: Agar admin ne normal text bheja hai
    elif message.text:
        story_name = message.text
    
    else:
        # Agar na text hai na photo (jaise sticker ya document)
        msg = bot.send_message(message.chat.id, "❌ Please ek valid text naam ya photo bhejein:")
        bot.register_next_step_handler(msg, get_story_name)
        return

    msg = bot.send_message(message.chat.id, "🔗 <b>ᴅᴇᴍᴏ ʟɪɴᴋ:</b>\nDemo channel ya video link dein (Ya 'skip' likhein):")
    # file_id ko pipeline mein aage pass kar rahe hain
    bot.register_next_step_handler(msg, get_demo_link, story_name, file_id)

def get_demo_link(message, story_name, file_id):
    demo = None if message.text.lower() == 'skip' else message.text
    msg = bot.send_message(message.chat.id, "🤖 <b>ғɪɴᴀʟ ʙᴏᴛ ʟɪɴᴋ:</b>\nPayment ke baad milne wala main link dein:")
    bot.register_next_step_handler(msg, get_final_link, story_name, demo, file_id)

def get_final_link(message, story_name, demo, file_id):
    final_link = message.text
    msg = bot.send_message(message.chat.id, "💰 <b>ᴘʀɪᴄᴇ:</b>\nSirf number likhein (Example: 49):")
    bot.register_next_step_handler(msg, save_story, story_name, demo, final_link, file_id)

def save_story(message, story_name, demo, final_link, file_id):
    if not message.text.isdigit():
        msg = bot.send_message(message.chat.id, "❌ Price sirf number mein likhein:")
        bot.register_next_step_handler(msg, save_story, story_name, demo, final_link, file_id)
        return

    price = message.text
    story_id = str(uuid.uuid4())[:10] 
    
    # Database Entry me 'file_id' add kiya gaya hai
    channels_col.insert_one({
        "item_id": story_id,
        "story_name": story_name,
        "demo_link": demo,
        "bot_link": final_link,
        "price": price,
        "file_id": file_id, # Agar photo nahi hogi toh automatic None save hoga
        "type": "story" 
    })
    
    bot_username = bot.get_me().username
    share_link = f"https://t.me/{bot_username}?start={story_id}"
    
    res = (
        f"✅ <b>sᴛᴏʀʏ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n"
        f"────────────────────\n"
        f"📖 Name: <b>{story_name}</b>\n"
        f"💰 Price: <b>₹{price}</b>\n"
        f"🖼️ Media: <b>{'Saved' if file_id else 'No Photo'}</b>\n\n"
        f"🔗 <b>ʏᴏᴜʀ sʜᴀʀᴇ ʟɪɴᴋ:</b>\n<code>{share_link}</code>\n"
        f"────────────────────\n"
        f"➔ Is link ko copy karke promote karein."
    )
    
    # Final confirmation mein bhi agar photo hai toh photo ke sath confirmation bhejega
    if file_id:
        bot.send_photo(message.chat.id, photo=file_id, caption=res, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, res, parse_mode="HTML")
