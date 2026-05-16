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
    if message.from_user.id != config.ADMIN_ID: return
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
            try: bot.send_message(u_id, "⚠️ <b>Access Revoked:</b> Aapka subscription khatam kar diya gaya hai.")
            except: pass
        else:
            bot.send_message(message.chat.id, "❓ Is ID ka koi active subscription nahi mila.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid ID! Sirf numbers bhejein.")


# ==========================================
# --- 2. MANAGE CHANNELS & STORIES ---
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
    if not ch_data: return bot.answer_callback_query(call.id, "Data not found!")

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
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

    photo_id = ch_data.get('file_id')
    if photo_id:
        bot.send_photo(call.message.chat.id, photo=photo_id, caption=text, parse_mode="HTML")
    else:
        bot.send_message(call.message.chat.id, text=text, parse_mode="HTML")


# ==========================================
# --- 3. SEPARATE LOGIC CHANNELS & STORIES ---
# ==========================================
@bot.message_handler(commands=['add'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def add_start(message):
    chat_id = message.chat.id if hasattr(message, 'chat') else message.message.chat.id
    msg = bot.send_message(
        chat_id, 
        "📢 <b>ᴀ_ᴅ_ᴅ  ɪ_ᴛ_ᴇ_ᴍ:</b>\n\n"
        "➔ <b>Channel Setup:</b> Kisi channel ka koi post <b>Forward</b> karein.\n"
        "➔ <b>Direct Photo Setup:</b> Ek <b>Photo</b> bhejein jiska <b>Caption</b> Story ka naam ho:", 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, route_setup_type)

def route_setup_type(message):
    if message.text and message.text == "/cancel":
        return bot.send_message(message.chat.id, "❌ Action cancelled.")

    # ──────────────────────────────────────────
    # [FLOW 1] CHANNEL FORWARD MODE (Automated Link Method)
    # ──────────────────────────────────────────
    if message.forward_from_chat:
        ch_id = message.forward_from_chat.id
        ch_name = message.forward_from_chat.title
        
        msg = bot.send_message(
            message.chat.id, 
            f"✅ <b>Channel Detected:</b> {ch_name}\n\n"
            f"Plans likhein (Format - Min:Price):\nExample: <code>1440:30, 10080:150</code>", 
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, channel_ask_photo, ch_id, ch_name)

    # ──────────────────────────────────────────
    # [FLOW 2] DIRECT PHOTO UPLOAD MODE (Manual Link Method)
    # ──────────────────────────────────────────
    elif message.photo:
        file_id = message.photo[-1].file_id
        story_name = message.caption.split("\n")[0] if message.caption else "Untitled Story"
        
        msg = bot.send_message(
            message.chat.id, 
            f"🎬 <b>Story Detected:</b> {story_name}\n\n"
            f"Is Story ka Price/Plan likhein (Example: 49):", 
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, story_ask_main_link, story_name, file_id)
        
    else:
        msg = bot.send_message(message.chat.id, "❌ Galat input! Kripya post forward karein ya direct photo bhejein:")
        bot.register_next_step_handler(msg, route_setup_type)

# ─── FLOW 1: CHANNEL SETUP HANDLERS ───
def channel_ask_photo(message, ch_id, ch_name):
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    plans_data = message.text.strip()
    
    # EXTRA FEATURE ASK PHOTO: Bot aapse poochega ki channel ke liye photo chahiye ya nahi
    msg = bot.send_message(
        message.chat.id, 
        "🖼️ <b>ᴄʜᴀɴɴᴇʟ ᴘʜᴏᴛᴏ:</b>\n"
        "Aap is channel ke liye koi custom photo lagana chahte hain?\n\n"
        "➔ Ek <b>Photo</b> bhejein.\n"
        "➔ Ya bina photo ke save karne ke liye <code>skip</code> likhein:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, channel_ask_demo, ch_id, ch_name, plans_data)

def channel_ask_demo(message, ch_id, ch_name, plans_data):
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    
    msg = bot.send_message(message.chat.id, "🔗 Demo Link bhejein (Ya 'skip' ya 'none' likhein):")
    bot.register_next_step_handler(msg, finalize_channel_setup, ch_id, ch_name, plans_data, file_id)

def finalize_channel_setup(message, ch_id, ch_name, plans_data, file_id):
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    demo = None if message.text.lower() in ['none', 'skip'] else message.text.strip()
    
    try:
        plans = {p.split(':')[0].strip(): p.split(':')[1].strip() for p in plans_data.split(',')}
    except:
        return bot.send_message(message.chat.id, "❌ Plans ka format galat tha. Dubara /add karein.")
        
    item_id = str(uuid.uuid4())[:10]
    channels_col.update_one(
        {"channel_id": ch_id}, 
        {"$set": {
            "item_id": item_id,
            "name": ch_name, 
            "plans": plans, 
            "demo_link": demo, 
            "file_id": file_id, # Agar photo di toh saved, warna None
            "type": "channel"
        }}, 
        upsert=True
    )
    link = f"https://t.me/{bot.get_me().username}?start={item_id}"
    bot.send_message(message.chat.id, f"✅ <b>ᴄʜᴀɴɴᴇʟ sᴇᴛᴜᴘ ғɪɴɪsʜᴇᴅ!</b>\n\nLink: <code>{link}</code>", parse_mode="HTML")


# ─── FLOW 2: DIRECT PHOTO STORY HANDLERS ───
def story_ask_main_link(message, story_name, file_id):
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    price = message.text.strip()
    
    # Is step par bot aapse main manual link mangega
    msg = bot.send_message(
        message.chat.id, 
        "🤖 <b>ғɪɴᴀʟ ᴀᴄᴄᴇss ʟɪɴᴋ:</b>\n"
        "User ke payment approve hone par jo main link (Video ya Group) milna chahiye, woh link bhejein:"
    )
    bot.register_next_step_handler(msg, story_ask_demo, story_name, price, file_id)

def story_ask_demo(message, story_name, price, file_id):
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    final_link = message.text.strip()
    
    msg = bot.send_message(message.chat.id, "🔗 Demo Link bhejein (Ya 'skip' ya 'none' likhein):")
    bot.register_next_step_handler(msg, finalize_story_setup, story_name, price, final_link, file_id)

def finalize_story_setup(message, story_name, price, final_link, file_id):
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    demo = None if message.text.lower() in ['none', 'skip'] else message.text.strip()
    
    item_id = str(uuid.uuid4())[:10]
    fake_channel_id = int(f"-100{str(uuid.uuid4().int)[:9]}") # Bot link bypass ke liye dummy reference id
    
    channels_col.insert_one({
        "item_id": item_id,
        "channel_id": fake_channel_id,
        "story_name": story_name,
        "price": price,
        "bot_link": final_link, # Aapka diya hua custom link yahan save ho gaya
        "demo_link": demo,
        "file_id": file_id,
        "type": "channel"
    })
    link = f"https://t.me/{bot.get_me().username}?start={item_id}"
    bot.send_message(message.chat.id, f"✅ <b>sᴛᴏʀʏ sᴇᴛᴜᴘ ғɪɴɪsʜᴇᴅ!</b>\n\nLink: <code>{link}</code>", parse_mode="HTML")
