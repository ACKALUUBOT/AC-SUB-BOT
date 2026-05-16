import uuid
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot
from database import channels_col, users_col
import config

# ==========================================
# --- 1. REMOVE USER (SECURE DELETE) ---
# ==========================================
@bot.message_handler(commands=['remove'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def remove_user_start(message):
    if message.from_user.id != config.ADMIN_ID: 
        return
    
    chat_id = message.chat.id if hasattr(message, 'chat') else message.message.chat.id
    
    msg = bot.send_message(
        chat_id, 
        "👤 <b>User ko remove karein:</b>\n\nUs user ki <b>ID</b> bhejein jiska access khatam karna hai (ya /cancel):", 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_remove_user)

def process_remove_user(message):
    if message.text == '/cancel':
        return bot.send_message(message.chat.id, "❌ Action cancelled.")
    
    try:
        u_id = int(message.text)
        result = users_col.delete_many({"user_id": u_id})
        if result.deleted_count > 0:
            bot.send_message(message.chat.id, f"✅ <b>Success!</b>\nUser <code>{u_id}</code> ka access hata diya gaya.", parse_mode="HTML")
            try: 
                bot.send_message(u_id, "⚠️ <b>Access Revoked:</b> Aapka subscription khatam kar diya gaya hai.")
            except: 
                pass
        else:
            bot.send_message(message.chat.id, "❓ Is ID ka koi active subscription nahi mila.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid ID! Sirf numbers bhejein.")


# ==========================================
# --- 2. MANAGE CHANNELS & STORIES (With Delete & Photo Support) ---
# ==========================================
@bot.message_handler(commands=['channels'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def list_channels(message):
    chat_id = message.chat.id if hasattr(message, 'chat') else message.message.chat.id
    cursor = channels_col.find()
    markup = InlineKeyboardMarkup()
    
    for ch in cursor:
        name = ch.get('story_name') or ch.get('name')
        markup.add(InlineKeyboardButton(f"⚙️ Manage: {name}", callback_data=f"manage_{ch['item_id']}"))
    
    if markup.keyboard:
        bot.send_message(chat_id, "📑 <b>ʏᴏᴜʀ ɪɴᴠᴇɴᴛᴏʀʏ:</b>\nNiche kisi bhi item ko manage karein:", reply_markup=markup, parse_mode="HTML")
    else:
        bot.send_message(chat_id, "❌ Abhi koi item add nahi hai.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('manage_'))
def manage_ch(call):
    item_id = call.data.split('_')[1]
    ch_data = channels_col.find_one({"item_id": item_id})
    
    if not ch_data:
        return bot.answer_callback_query(call.id, "Data not found!")

    bot_user = bot.get_me().username
    link = f"https://t.me/{bot_user}?start={item_id}"
    name = ch_data.get('story_name') or ch_data.get('name')
    price_info = f"₹{ch_data['price']}" if 'story_name' in ch_data else ch_data['plans']
    
    text = (
        f"⚙️ <b>sᴇᴛᴛɪɴɢs:</b> {name}\n"
        f"────────────────────\n"
        f"🔗 <b>sʜᴀʀᴇ ʟɪɴᴋ:</b>\n<code>{link}</code>\n\n"
        f"📺 <b>ᴅᴇᴍᴏ:</b> {ch_data.get('demo_link', 'None')}\n"
        f"💰 <b>ᴘʟᴀɴs:</b> {price_info}\n"
        f"────────────────────"
    )
    
    # Jaise hi user ne button dabaya, purana text/photo message delete ho jayega
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        print(f"Delete Message Error: {e}")

    photo_id = ch_data.get('file_id')
    
    if photo_id:
        # Agar item ke paas photo hai toh photo + caption bhejega (Freeze nahi hoga)
        bot.send_photo(call.message.chat.id, photo=photo_id, caption=text, parse_mode="HTML")
    else:
        bot.send_message(call.message.chat.id, text=text, parse_mode="HTML")


# ==========================================
# --- 3. ADD CHANNEL & STORY WITH PHOTO ---
# ==========================================
@bot.message_handler(commands=['add'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def add_start(message):
    chat_id = message.chat.id if hasattr(message, 'chat') else message.message.chat.id
    
    msg = bot.send_message(
        chat_id, 
        "📢 <b>ᴀᴅᴅ ɪᴛᴇᴍ:</b>\n\n"
        "1. Kisi channel ka koi post <b>Forward</b> karein.\n"
        "2. Ya direct ek <b>Photo</b> bhejein jiska caption Story ka naam ho:", 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, get_plans)

def get_plans(message):
    # Safe guard agar admin beech mein cancel karna chahe
    if message.text and message.text == "/cancel":
        return bot.send_message(message.chat.id, "❌ Setup cancelled.")

    ch_id = None
    ch_name = None
    file_id = None

    # Case A: User ne channel se message forward kiya hai
    if message.forward_from_chat:
        ch_id = message.forward_from_chat.id
        ch_name = message.forward_from_chat.title
        if message.photo:
            file_id = message.photo[-1].file_id

    # Case B: Admin ne direct photo select karke upload ki hai
    elif message.photo:
        ch_id = str(uuid.uuid4())[:8] 
        file_id = message.photo[-1].file_id
        ch_name = message.caption.split("\n")[0] if message.caption else "Untitled Story"

    # Case C: Simple text message bheja hai bina media ke
    elif message.text:
        ch_id = str(uuid.uuid4())[:8]
        ch_name = message.text.split("\n")[0]
        
    else:
        # Agar koi invalid content type bhej de (Sticker/Document)
        msg = bot.send_message(message.chat.id, "❌ Invalid input! Please message forward karein ya photo/text bhejein:")
        bot.register_next_step_handler(msg, get_plans)
        return

    msg = bot.send_message(
        message.chat.id, 
        f"✅ <b>Found/Detected:</b> {ch_name}\n\n"
        f"Plans likhein (Format - Min:Price):\nExample: <code>1440:30, 10080:150</code>", 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, get_demo, ch_id, ch_name, file_id)

def get_demo(message, ch_id, ch_name, file_id):
    if message.text and message.text == "/cancel":
        return bot.send_message(message.chat.id, "❌ Setup cancelled.")
        
    try:
        plans = {p.split(':')[0].strip(): p.split(':')[1].strip() for p in message.text.split(',')}
        msg = bot.send_message(message.chat.id, "🔗 Demo Link bhejein (Ya 'none' ya 'skip'):")
        bot.register_next_step_handler(msg, finalize_channel, ch_id, ch_name, plans, file_id)
    except Exception:
        msg = bot.send_message(message.chat.id, "❌ Format galat hai! Example: <code>1440:30, 10080:150</code>\n\nDubara likhein:")
        bot.register_next_step_handler(msg, get_demo, ch_id, ch_name, file_id)

def finalize_channel(message, ch_id, ch_name, plans, file_id):
    if message.text and message.text == "/cancel":
        return bot.send_message(message.chat.id, "❌ Setup cancelled.")

    demo = None if message.text.lower() in ['none', 'skip'] else message.text
    item_id = str(uuid.uuid4())[:10]
    
    # Database indexing with conditional file_id field mapping
    channels_col.update_one(
        {"channel_id": ch_id}, 
        {"$set": {
            "item_id": item_id,
            "name": ch_name, 
            "plans": plans, 
            "demo_link": demo, 
            "file_id": file_id, # Agar photo nahi hai toh None save hoga automatically
            "type": "channel"
        }}, 
        upsert=True
    )
    
    link = f"https://t.me/{bot.get_me().username}?start={item_id}"
    bot.send_message(message.chat.id, f"✅ <b>sᴇᴛᴜᴘ ғɪɴɪsʜᴇᴅ!</b>\n\nLink: <code>{link}</code>", parse_mode="HTML")
