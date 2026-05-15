from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot, get_time_string
from database import channels_col, users_col
from datetime import datetime
import config

# ─── 1. STORE MARKUP (LIST VIEW) ───
def get_store_markup():
    all_items = list(channels_col.find({
        "$or": [{"story_name": {"$exists": True}}, {"name": {"$exists": True}}]
    }))
    
    markup = InlineKeyboardMarkup(row_width=1)
    if not all_items:
        markup.add(InlineKeyboardButton("🚫 No Items Available", callback_data="none"))
    else:
        for item in all_items:
            db_id = item.get('item_id') or item.get('channel_id')
            name = item.get('story_name') or item.get('name', 'Premium Channel')
            icon = "🎬" if 'story_name' in item else "💎"
            markup.add(InlineKeyboardButton(f"{icon} {name}", callback_data=f"view_card_{db_id}"))
            
    markup.add(InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))
    return markup

# ─── 2. CARD VIEW GENERATOR (FIXED PHOTO LOGIC) ───
def send_detail_card(chat_id, data, message_id=None, is_new=False):
    markup = InlineKeyboardMarkup(row_width=1)
    db_id = data.get('item_id') or data.get('channel_id')
    
    # Story vs Channel logic
    if 'story_name' in data:
        display_name = data['story_name']
        price_info = f"₹{data['price']}"
        episodes = data.get('episodes', 'Full Story')
        markup.add(InlineKeyboardButton(f"💳 ʙᴜʏ ɴᴏᴡ - {price_info}", callback_data=f"select_{db_id}_manual"))
        header = "🎬 <b>ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ ᴄᴀʀᴅ</b>"
    else:
        display_name = data.get('name', 'Premium Access')
        episodes = data.get('episodes', 'Full Access (All Episodes)')
        plans = data.get('plans', {})
        for p_time, p_price in plans.items():
            markup.add(InlineKeyboardButton(f"💳 {get_time_string(p_time)} - ₹{p_price}", callback_data=f"select_{db_id}_{p_time}"))
        header = "💎 <b>ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss ᴄᴀʀᴅ</b>"

    # DEMO BUTTON: Sirf tab dikhega jab database mein demo link ho aur 'skip' na ho
    if data.get('demo_link') and data['demo_link'].lower() != 'skip':
        markup.add(InlineKeyboardButton("📺 ᴠɪᴇᴡ ǫᴜᴀʟɪᴛʏ ᴅᴇᴍᴏ", url=data['demo_link']))
    
    markup.add(InlineKeyboardButton("⬅️ ʙᴀᴄᴋ ᴛᴏ sᴛᴏʀᴇ", callback_data="open_store"))

    card_text = (
        f"{header}\n"
        f"────────────────────\n"
        f"📦 ɴᴀᴍᴇ: <b>{display_name}</b>\n"
        f"🎞️ ᴇᴘɪsᴏᴅᴇs: <b>{episodes}</b>\n"
        f"📊 sᴛᴀᴛᴜs: <code>Available</code>\n\n"
        f"📝 ᴅᴇsᴄʀɪᴘᴛɪᴏɴ:\n"
        f"<i>Premium quality. Instant access after payment.</i>\n"
        f"────────────────────"
    )

    # --- PHOTO LOGIC FIX ---
    # priority: 1. poster (new field), 2. demo_link (old field), 3. placeholder
    photo = data.get('poster') or data.get('demo_link') or "https://via.placeholder.com/1024x512.png"

    try:
        if is_new:
            bot.send_photo(chat_id, photo, caption=card_text, reply_markup=markup, parse_mode="HTML")
        else:
            bot.delete_message(chat_id, message_id)
            bot.send_photo(chat_id, photo, caption=card_text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        # Fallback agar photo send na ho paye
        bot.send_message(chat_id, card_text, reply_markup=markup, parse_mode="HTML")

# ─── 3. START & DASHBOARD ───
@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    text = message.text.split()

    # Deep Link Handler
    if len(text) > 1:
        param = text[1]
        data = channels_col.find_one({"item_id": param}) or \
               channels_col.find_one({"channel_id": int(param) if param.replace('-','').isdigit() else 0})
        if data:
            return send_detail_card(message.chat.id, data, is_new=True)

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("✨ ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀᴇ ✨", callback_data="open_store"))
    markup.add(
        InlineKeyboardButton("📊 ᴍʏ ᴅᴀsʜʙᴏᴀʀᴅ", callback_data="my_plan"),
        InlineKeyboardButton("💬 sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{config.CONTACT_USERNAME}")
    )

    if user_id == config.ADMIN_ID:
        markup.add(InlineKeyboardButton("➕ ᴀᴅᴅ sᴛᴏʀʏ", callback_data="admin_story"), InlineKeyboardButton("📺 ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", callback_data="admin_add"))
        markup.add(InlineKeyboardButton("⚙️ ᴍᴀɴᴀɢᴇ ᴀʟʟ", callback_data="admin_channels"), InlineKeyboardButton("❌ ʀᴇᴍᴏᴠᴇ sᴜʙ", callback_data="admin_remove"))

    title = "⚡ <b>ᴀᴅᴍɪɴ ᴍᴀsᴛᴇʀ ᴘᴀɴᴇʟ</b>" if user_id == config.ADMIN_ID else "👋 <b>ᴡᴇʟᴄᴏᴍᴇ ᴍᴇᴍʙᴇʀ</b>"
    bot.send_message(message.chat.id, f"{title}\n\nPremium access aur content ke liye niche buttons use karein.", reply_markup=markup, parse_mode="HTML")

# ─── 4. CALLBACK HANDLERS ───
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    u_id = call.from_user.id
    
    if call.data == "open_store":
        markup = get_store_markup()
        store_text = "✨ <b>ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ sᴛᴏʀᴇ</b> ✨\n────────────────────\nList se item select karein:"
        if call.message.content_type == 'photo':
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, store_text, reply_markup=markup, parse_mode="HTML")
        else:
            bot.edit_message_text(store_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

    elif call.data.startswith('view_card_'):
        target_id = call.data.replace('view_card_', '')
        data = channels_col.find_one({"item_id": target_id}) or \
               channels_col.find_one({"channel_id": int(target_id) if target_id.replace('-','').isdigit() else 0})
        if data:
            send_detail_card(call.message.chat.id, data, call.message.message_id)

    elif call.data == "back_to_start":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start_handler(call.message)

    elif call.data == "my_plan":
        subs = list(users_col.find({"user_id": u_id}))
        if not subs:
            bot.answer_callback_query(call.id, "❌ No active plan found.")
            return
        res = "👤 <b>ᴍʏ sᴜʙsᴄʀɪᴘᴛɪᴏɴs</b>\n\n"
        for s in subs:
            ch = channels_col.find_one({"channel_id": s['channel_id']})
            name = ch.get('story_name') or ch.get('name') if ch else "Item"
            res += f"📺 <b>{name}</b>\n⌛ Valid: <code>{datetime.fromtimestamp(s['expiry']).strftime('%d %b %Y')}</code>\n\n"
        bot.send_message(u_id, res, parse_mode="HTML")

@bot.message_handler(commands=['delete'])
def delete_item_handler(message):
    if message.from_user.id != config.ADMIN_ID: return
    text = message.text.split()
    if len(text) < 2: return bot.reply_to(message, "💡 Usage: /delete ID")
    target_id = text[1]
    channels_col.delete_one({"$or": [{"item_id": target_id}, {"channel_id": int(target_id) if target_id.replace('-','').isdigit() else 0}]})
    bot.reply_to(message, "✅ Task completed.")
