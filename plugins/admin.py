import uuid
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot
from database import channels_col, users_col
import config

# --- 1. REMOVE USER (SECURE) ---
@bot.message_handler(commands=['remove'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def remove_user_start(message):
    if message.from_user.id != config.ADMIN_ID: return
    
    # Check if message is a CallbackQuery (from button) or a Message (from command)
    chat_id = message.chat.id if hasattr(message, 'chat') else message.message.chat.id
    
    msg = bot.send_message(chat_id, "👤 <b>User ko remove karein:</b>\n\nUs user ki <b>ID</b> bhejein jiska access khatam karna hai (ya /cancel):", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_remove_user)

def process_remove_user(message):
    if message.text == '/cancel':
        return bot.send_message(message.chat.id, "❌ Action cancelled.")
    
    try:
        u_id = int(message.text)
        result = users_col.delete_many({"user_id": u_id})
        if result.deleted_count > 0:
            bot.send_message(message.chat.id, f"✅ <b>Success!</b>\nUser <code>{u_id}</code> ka access hata diya gaya.", parse_mode="HTML")
            try: bot.send_message(u_id, "⚠️ <b>Access Revoked:</b> Aapka subscription khatam kar diya gaya hai.")
            except: pass
        else:
            bot.send_message(message.chat.id, "❓ Is ID ka koi active subscription nahi mila.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid ID! Sirf numbers bhejein.")

# --- 2. MANAGE CHANNELS & STORIES ---
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
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML")

# --- 3. ADD CHANNEL ---
@bot.message_handler(commands=['add'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def add_start(message):
    chat_id = message.chat.id if hasattr(message, 'chat') else message.message.chat.id
    msg = bot.send_message(chat_id, "📢 <b>ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ:</b>\nChannel se koi ek message <b>Forward</b> karein:")
    bot.register_next_step_handler(msg, get_plans)

def get_plans(message):
    if message.forward_from_chat:
        ch_id = message.forward_from_chat.id
        ch_name = message.forward_from_chat.title
        msg = bot.send_message(message.chat.id, f"✅ <b>Found:</b> {ch_name}\n\nPlans likhein (Format - Min:Price):\nExample: <code>1440:30, 10080:150</code>", parse_mode="HTML")
        bot.register_next_step_handler(msg, get_demo, ch_id, ch_name)
    else:
        bot.send_message(message.chat.id, "❌ Message forward nahi kiya gaya. Dubara try karein.")

def get_demo(message, ch_id, ch_name):
    try:
        plans = {p.split(':')[0].strip(): p.split(':')[1].strip() for p in message.text.split(',')}
        msg = bot.send_message(message.chat.id, "🔗 Demo Link bhejein (Ya 'none'):")
        bot.register_next_step_handler(msg, finalize_channel, ch_id, ch_name, plans)
    except:
        bot.send_message(message.chat.id, "❌ Format galat hai! Example: 1440:30, 10080:150")

def finalize_channel(message, ch_id, ch_name, plans):
    demo = None if message.text.lower() == 'none' else message.text
    item_id = str(uuid.uuid4())[:10]
    
    channels_col.update_one(
        {"channel_id": ch_id}, 
        {"$set": {
            "item_id": item_id,
            "name": ch_name, 
            "plans": plans, 
            "demo_link": demo, 
            "type": "channel"
        }}, 
        upsert=True
    )
    
    link = f"https://t.me/{bot.get_me().username}?start={item_id}"
    bot.send_message(message.chat.id, f"✅ <b>sᴇᴛᴜᴘ ғɪɴɪsʜᴇᴅ!</b>\n\nLink: <code>{link}</code>", parse_mode="HTML")
