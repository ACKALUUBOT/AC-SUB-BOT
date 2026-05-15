import uuid
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot
from database import channels_col, users_col
import config

# --- 1. REMOVE USER (SECURE) ---
@bot.message_handler(commands=['remove'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def remove_user_start(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "👤 <b>User ko remove karein:</b>\n\nUs user ki <b>ID</b> bhejein jiska access khatam karna hai (ya /cancel):", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_remove_user)

def process_remove_user(message):
    if message.text == '/cancel':
        return bot.send_message(message.chat.id, "❌ Action cancelled.")
    
    try:
        u_id = int(message.text)
        # Sare channels/stories se access delete karna
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
    cursor = channels_col.find()
    markup = InlineKeyboardMarkup()
    
    for ch in cursor:
        name = ch.get('story_name') or ch.get('name')
        db_id = ch.get('item_id') or ch.get('channel_id')
        markup.add(InlineKeyboardButton(f"⚙️ Manage: {name}", callback_data=f"manage_{db_id}"))
    
    if markup.keyboard:
        bot.send_message(message.chat.id, "📑 <b>ʏᴏᴜʀ ɪɴᴠᴇɴᴛᴏʀʏ:</b>\nNiche kisi bhi item ko manage karein:", reply_markup=markup, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, "❌ Abhi koi item add nahi hai.")

# --- 3. ADD CHANNEL (UPDATED FOR CARD VIEW) ---
@bot.message_handler(commands=['add'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def add_start(message):
    msg = bot.send_message(message.chat.id, "📢 <b>ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ:</b>\nChannel se koi ek message <b>Forward</b> karein:")
    bot.register_next_step_handler(msg, get_plans)

def get_plans(message):
    if message.forward_from_chat:
        ch_id = message.forward_from_chat.id
        ch_name = message.forward_from_chat.title
        msg = bot.send_message(message.chat.id, f"✅ <b>Found:</b> {ch_name}\n\nPlans likhein (Format - Min:Price):\nExample: <code>1440:30, 10080:150</code>", parse_mode="HTML")
        bot.register_next_step_handler(msg, get_ep_info, ch_id, ch_name)
    else:
        bot.send_message(message.chat.id, "❌ Message forward nahi kiya gaya. /add dubara try karein.")

def get_ep_info(message, ch_id, ch_name):
    try:
        plans = {p.split(':')[0].strip(): p.split(':')[1].strip() for p in message.text.split(',')}
        msg = bot.send_message(message.chat.id, "🎞️ <b>Episodes Info:</b>\nCard par kya likhna hai? (e.g., Full Movie, 24 Episodes)")
        bot.register_next_step_handler(msg, get_poster_url, ch_id, ch_name, plans)
    except:
        bot.send_message(message.chat.id, "❌ Format galat! Example: 1440:10. /add dubara karein.")

def get_poster_url(message, ch_id, ch_name, plans):
    episodes = message.text
    msg = bot.send_message(message.chat.id, "🖼️ <b>Poster Link:</b>\nPhoto ka direct link (.jpg/.png) bhejein:")
    bot.register_next_step_handler(msg, get_demo_url, ch_id, ch_name, plans, episodes)

def get_demo_url(message, ch_id, ch_name, plans, episodes):
    poster = message.text
    msg = bot.send_message(message.chat.id, "📺 <b>Demo Link:</b>\nTrailer ya Demo channel link dein (Ya 'skip' likhein):")
    bot.register_next_step_handler(msg, finalize_add, ch_id, ch_name, plans, episodes, poster)

def finalize_add(message, ch_id, ch_name, plans, episodes, poster):
    demo = None if message.text.lower() == 'skip' else message.text
    item_id = str(uuid.uuid4())[:10]
    
    channels_col.update_one(
        {"channel_id": ch_id}, 
        {"$set": {
            "item_id": item_id,
            "name": ch_name, 
            "plans": plans, 
            "poster": poster,      # Card ki main image
            "demo_link": demo,     # Demo button link
            "episodes": episodes,  # Card text
            "type": "channel"
        }}, 
        upsert=True
    )
    
    share_link = f"https://t.me/{bot.get_me().username}?start={item_id}"
    bot.send_message(message.chat.id, f"✅ <b>ᴄʜᴀɴɴᴇʟ ᴀᴅᴅᴇᴅ!</b>\n\nLink: <code>{share_link}</code>\nAb card view check karein.", parse_mode="HTML")
