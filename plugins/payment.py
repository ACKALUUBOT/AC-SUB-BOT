import urllib.parse
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot, get_time_string
from database import channels_col, users_col
import config
import time

# --- 1. PAYMENT SELECTION ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('select_'))
def confirm_step(call):
    parts = call.data.split('_')
    item_id, mins = parts[1], parts[2]
    
    data = channels_col.find_one({"item_id": item_id}) or \
           channels_col.find_one({"channel_id": int(item_id) if item_id.replace('-','').isdigit() else 0})
    
    if not data: return bot.answer_callback_query(call.id, "❌ Data not found!")

    price = data['price'] if 'story_name' in data else data['plans'].get(mins, "0")
    display_name = data.get('story_name') or data.get('name')
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("💳 ᴘᴀʏ ᴠɪᴀ ǫʀ sᴄᴀɴ", callback_data=f"man_{item_id}_{mins}_qr"),
        InlineKeyboardButton("📲 ᴘᴀʏ ᴠɪᴀ ᴜᴘɪ ɪᴅ", callback_data=f"man_{item_id}_{mins}_upi")
    )
    
    text = (
        f"<b>🛒 ᴄᴏɴғɪʀᴍ sᴇʟᴇᴄᴛɪᴏɴ</b>\n"
        f"────────────────────\n"
        f"📦 ɪᴛᴇᴍ: <b>{display_name}</b>\n"
        f"💰 ᴀᴍᴏᴜɴᴛ: <b>₹{price}</b>\n\n"
        f"➔ Payment method select karein:"
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

# --- 2. MANUAL PAYMENT (QR & UPI) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('man_'))
def manual_pay(call):
    _, item_id, mins, mode = call.data.split('_')
    data = channels_col.find_one({"item_id": item_id}) or \
           channels_col.find_one({"channel_id": int(item_id) if item_id.replace('-','').isdigit() else 0})
    
    price = data['price'] if 'story_name' in data else data['plans'].get(mins, "0")
    upi_string = f"upi://pay?pa={config.UPI_ID}&am={price}&cu=INR&tn=Pay_{item_id}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=350x350&data={urllib.parse.quote(upi_string)}"
    
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ sᴜʙᴍɪᴛ sᴄʀᴇᴇɴsʜᴏᴛ", callback_data=f"paid_{item_id}_{mins}"))

    if mode == "qr":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_photo(call.message.chat.id, qr_url, caption=f"📥 <b>ǫʀ sᴄᴀɴɴᴇʀ</b>\n\nAmount: <b>₹{price}</b>\n\n➔ Pay karke niche wala button dabayein.", reply_markup=markup, parse_mode="HTML")
    else:
        bot.edit_message_text(f"📲 <b>ᴜᴘɪ ɪᴅ:</b> <code>{config.UPI_ID}</code>\nAmount: <b>₹{price}</b>\n\n➔ Pay karne ke baad niche button dabayein.", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

# --- 3. DIRECT SCREENSHOT SUBMISSION ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('paid_'))
def handle_paid(call):
    _, item_id, mins = call.data.split('_')
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📸 Payment ka <b>Screenshot</b> bhejein:")
    bot.register_next_step_handler(msg, send_request_to_admin, item_id, mins)

def send_request_to_admin(message, item_id, mins):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ Please sirf Photo (Screenshot) bhejein!")
        bot.register_next_step_handler(msg, send_request_to_admin, item_id, mins)
        return
    
    photo_id = message.photo[-1].file_id
    data = channels_col.find_one({"item_id": item_id}) or \
           channels_col.find_one({"channel_id": int(item_id) if item_id.replace('-','').isdigit() else 0})
    
    display_name = data.get('story_name') or data.get('name')
    bot.send_message(message.chat.id, "⏳ <b>ʀᴇǫᴜᴇsᴛ sᴇɴᴛ!</b>\nAdmin check karke aapka access on kar dega.")
    
    # --- ADMIN BUTTONS (Added Contact User button for Direct Chat) ---
    markup = InlineKeyboardMarkup(row_width=2)
    btn_app = InlineKeyboardButton("✅ Approve", callback_data=f"app_{message.from_user.id}_{item_id}_{mins}")
    btn_rej = InlineKeyboardButton("❌ Reject", callback_data=f"rej_{message.from_user.id}")
    btn_chat = InlineKeyboardButton("💬 ᴄᴏɴᴛᴀᴄᴛ ᴜsᴇʀ (ᴅɪʀᴇᴄᴛ ᴄʜᴀᴛ)", url=f"tg://user?id={message.from_user.id}")
    
    markup.add(btn_app, btn_rej)
    markup.add(btn_chat) # Direct Chat button added here
    
    admin_text = (
        f"📥 <b>ɴᴇᴡ ᴘᴀʏᴍᴇɴᴛ ʀᴇǫᴜᴇsᴛ</b>\n"
        f"────────────────────\n"
        f"👤 User: {message.from_user.first_name} (<code>{message.from_user.id}</code>)\n"
        f"📦 Item: <b>{display_name}</b>\n"
        f"⏳ Plan: {mins if mins != 'manual' else 'Lifetime'}"
    )
    bot.send_photo(config.ADMIN_ID, photo_id, caption=admin_text, reply_markup=markup, parse_mode="HTML")

# --- 4. ADMIN APPROVAL & REJECT ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('app_'))
def admin_approve(call):
    _, u_id, item_id, mins = call.data.split('_')
    data = channels_col.find_one({"item_id": item_id}) or \
           channels_col.find_one({"channel_id": int(item_id) if item_id.replace('-','').isdigit() else 0})
    
    if not data: return
    
    expiry = int(time.time()) + (int(mins) * 60) if mins != 'manual' else int(time.time()) + (3650*24*60*60)
    users_col.update_one({"user_id": int(u_id), "channel_id": data.get('channel_id', item_id)}, {"$set": {"expiry": expiry}}, upsert=True)

    markup = InlineKeyboardMarkup()
    if 'story_name' not in data and 'channel_id' in data:
        try:
            invite = bot.create_chat_invite_link(data['channel_id'], member_limit=1)
            markup.add(InlineKeyboardButton("📢 Join Channel", url=invite.invite_link))
            msg = "✅ <b>ᴀᴘᴘʀᴏᴠᴇᴅ!</b>\nChannel join karne ke liye niche click karein:"
        except: msg = "✅ <b>ᴀᴘᴘʀᴏᴠᴇᴅ!</b>\nAdmin se link maangein."
    else:
        markup.add(InlineKeyboardButton("🚀 sᴛᴀʀᴛ sᴛᴏʀʏ", url=data['bot_link']))
        msg = f"✅ <b>ᴀᴘᴘʀᴏᴠᴇᴅ!</b>\n\nStory: <b>{data['story_name']}</b>\nNiche button se access karein:"

    bot.send_message(u_id, msg, reply_markup=markup, parse_mode="HTML", protect_content=True)
    bot.edit_message_caption(f"✅ Approved for User: {u_id}", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('rej_'))
def admin_reject(call):
    u_id = call.data.split('_')[1]
    bot.edit_message_caption(f"❌ Payment Rejected! (User: {u_id})", call.message.chat.id, call.message.message_id)
    bot.send_message(u_id, "❌ Aapka payment reject ho gaya hai. Support se baat karein.")
