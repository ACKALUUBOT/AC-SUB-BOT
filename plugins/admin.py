import uuid
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot
from database import channels_col, users_col
import config

# --- 1. REMOVE USER (SECURE) ---
@bot.message_handler(commands=['remove'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def remove_user_start(message):
    msg = bot.send_message(config.ADMIN_ID, "👤 <b>User ko remove karein:</b>\n\nUs user ki <b>ID</b> bhejein jiska access aap khatam karna chahte hain (ya /cancel):", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_remove_user)

def process_remove_user(message):
    if message.text == '/cancel':
        bot.send_message(config.ADMIN_ID, "❌ Action cancelled.")
        return
    try:
        u_id = int(message.text)
        result = users_col.delete_many({"user_id": u_id})
        if result.deleted_count > 0:
            bot.send_message(config.ADMIN_ID, f"✅ <b>Success!</b>\nUser <code>{u_id}</code> ke saare access hata diye gaye hain.", parse_mode="HTML")
            try: bot.send_message(u_id, "⚠️ <b>Access Revoked:</b> Aapka subscription admin dwara khatam kar diya gaya hai.", parse_mode="HTML")
            except: pass
        else:
            bot.send_message(config.ADMIN_ID, "❓ Is ID ka koi active subscription nahi mila.")
    except ValueError:
        bot.send_message(config.ADMIN_ID, "❌ Invalid ID! Sirf numbers bhejein.")

# --- 2. MANAGE CHANNELS & STORIES (LINK FIX) ---
@bot.message_handler(commands=['channels'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def list_channels(message):
    cursor = channels_col.find() # Admin check agar database mein hai to add karein
    markup = InlineKeyboardMarkup()
    for ch in cursor:
        name = ch.get('story_name') or ch.get('name')
        markup.add(InlineKeyboardButton(f"⚙️ Manage: {name}", callback_data=f"manage_{ch['item_id']}"))
    
    if markup.keyboard:
        bot.send_message(config.ADMIN_ID, "📑 <b>ʏᴏᴜʀ ᴀʟʟ ɪᴛᴇᴍs:</b>\nNiche kisi bhi item ko manage karne ke liye click karein:", reply_markup=markup, parse_mode="HTML")
    else:
        bot.send_message(config.ADMIN_ID, "❌ Abhi koi channel ya story add nahi hai.")

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
        f"────────────────────\n"
        f"➔ Is link ko copy karke aap promote kar sakte hain."
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML")

# --- 3. ADD CHANNEL (WITH ITEM_ID GENERATION) ---
@bot.message_handler(commands=['add'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def add_start(message):
    msg = bot.send_message(config.ADMIN_ID, "📢 <b>ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ:</b>\nChannel se koi bhi ek message <b>Forward</b> karein:")
    bot.register_next_step_handler(msg, get_plans)

def get_plans(message):
    if message.forward_from_chat:
        ch_id = message.forward_from_chat.id
        ch_name = message.forward_from_chat.title
        msg = bot.send_message(config.ADMIN_ID, f"✅ <b>Found:</b> {ch_name}\n\nAb Plans enter karein (Format - Min:Price):\nExample: <code>1440:30, 10080:150</code>", parse_mode="HTML")
        bot.register_next_step_handler(msg, get_demo, ch_id, ch_name)
    else:
        bot.send_message(config.ADMIN_ID, "❌ Message forward nahi kiya gaya. Dubara /add try karein.")

def get_demo(message, ch_id, ch_name):
    try:
        plans = {p.split(':')[0].strip(): p.split(':')[1].strip() for p in message.text.split(',')}
        msg = bot.send_message(config.ADMIN_ID, "🔗 Demo Link bhejein (Ya 'none' likhein):")
        bot.register_next_step_handler(msg, finalize_channel, ch_id, ch_name, plans)
    except:
        msg = bot.send_message(config.ADMIN_ID, "❌ Format galat hai! Dubara likhein (Min:Price):")
        bot.register_next_step_handler(msg, get_demo, ch_id, ch_name)

def finalize_channel(message, ch_id, ch_name, plans):
    demo = None if message.text.lower() == 'none' else message.text
    # Yahan generate hoga unique item_id purane channels ke liye bhi
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
    
    bot_user = bot.get_me().username
    final_link = f"https://t.me/{bot_user}?start={item_id}"
    
    bot.send_message(config.ADMIN_ID, f"✅ <b>sᴇᴛᴜᴘ ғɪɴɪsʜᴇᴅ!</b>\n\nChannel: {ch_name}\nLink: <code>{final_link}</code>", parse_mode="HTML")
