import urllib.parse
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot, get_time_string
from database import channels_col, utr_col, users_col
import config
import time

try: from server import rzp_client
except: rzp_client = None

# --- 1. PAYMENT SELECTION ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('select_'))
def confirm_step(call):
    parts = call.data.split('_')
    item_id = parts[1]
    mins = parts[2]
    
    data = channels_col.find_one({"item_id": item_id}) or \
           channels_col.find_one({"channel_id": int(item_id) if item_id.replace('-','').isdigit() else 0})
    
    if not data:
        return bot.answer_callback_query(call.id, "❌ Error: Data not found!")

    price = data['price'] if 'story_name' in data else data['plans'].get(mins, "0")
    display_name = data.get('story_name') or data.get('name')
    
    markup = InlineKeyboardMarkup(row_width=1)
    if config.RZP_KEY_ID and rzp_client:
        markup.add(InlineKeyboardButton("⚡ ɪɴsᴛᴀɴᴛ ᴏɴʟɪɴᴇ ᴘᴀʏ", callback_data=f"rzp_{item_id}_{mins}"))
    
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

# --- 2. MANUAL PAYMENT (QR & UPI ID) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('man_'))
def manual_pay(call):
    _, item_id, mins, mode = call.data.split('_')
    data = channels_col.find_one({"item_id": item_id}) or \
           channels_col.find_one({"channel_id": int(item_id) if item_id.replace('-','').isdigit() else 0})
    
    price = data['price'] if 'story_name' in data else data['plans'].get(mins, "0")
    
    upi_string = f"upi://pay?pa={config.UPI_ID}&am={price}&cu=INR&tn=Premium_{item_id}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=350x350&data={urllib.parse.quote(upi_string)}"
    
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ sᴜʙᴍɪᴛ sᴄʀᴇᴇɴsʜᴏᴛ", callback_data=f"paid_{item_id}_{mins}"))

    if mode == "qr":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_photo(call.message.chat.id, qr_url, caption=f"📥 <b>ǫʀ sᴄᴀɴɴᴇʀ</b>\n\nAmount: <b>₹{price}</b>\nUPI: <code>{config.UPI_ID}</code>\n\n➔ Pay karein aur niche button dabayein.", reply_markup=markup, parse_mode="HTML")
    else:
        bot.edit_message_text(f"📲 <b>ᴜᴘɪ ɪᴅ:</b> <code>{config.UPI_ID}</code>\nAmount: <b>₹{price}</b>\n\n➔ Pay karne ke baad niche button dabayein.", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

# --- 3. SUBMISSION PROCESS ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('paid_'))
def handle_paid(call):
    _, item_id, mins = call.data.split('_')
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📸 Payment ka <b>Screenshot</b> bhejein:")
    bot.register_next_step_handler(msg, step_utr, item_id, mins)

def step_utr(message, item_id, mins):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ Screenshot bhejein!")
        bot.register_next_step_handler(msg, step_utr, item_id, mins)
        return
    photo_id = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, "✍️ 12-digit <b>UTR Number</b> type karein:")
    bot.register_next_step_handler(msg, send_to_admin, item_id, mins, photo_id)

def send_to_admin(message, item_id, mins, photo_id):
    utr = message.text.strip() if message.text else ""
    if len(utr) != 12 or not utr.isdigit():
        msg = bot.send_message(message.chat.id, "❌ Galat UTR! Sirf 12 digits likhein:")
        bot.register_next_step_handler(msg, send_to_admin, item_id, mins, photo_id)
        return
    
    data = channels_col.find_one({"item_id": item_id}) or \
           channels_col.find_one({"channel_id": int(item_id) if item_id.replace('-','').isdigit() else 0})
    
    display_name = data.get('story_name') or data.get('name')
    bot.send_message(message.chat.id, "⏳ <b>ʀᴇǫᴜᴇsᴛ sᴜʙᴍɪᴛᴛᴇᴅ!</b>\nAdmin ke approval ka wait karein.")
    
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("✅ Approve", callback_data=f"app_{message.from_user.id}_{item_id}_{utr}_{mins}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"rej_{message.from_user.id}_{utr}"),
        InlineKeyboardButton("💬 Support", url=f"tg://openmessage?user_id={message.from_user.id}")
    )
    
    admin_text = f"📥 <b>ɴᴇᴡ ʀᴇǫᴜᴇsᴛ</b>\nUser: <code>{message.from_user.id}</code>\nUTR: <code>{utr}</code>\nItem: {display_name}"
    bot.send_photo(config.ADMIN_ID, photo_id, caption=admin_text, reply_markup=markup, parse_mode="HTML")

# --- 4. ADMIN APPROVAL & DELIVERY ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('app_'))
def admin_approve_action(call):
    # app_userid_itemid_utr_mins
    _, u_id, item_id, utr, mins = call.data.split('_')
    
    if utr_col.find_one({"utr": utr}): 
        return bot.answer_callback_query(call.id, "Already Processed!", show_alert=True)
    
    data = channels_col.find_one({"item_id": item_id}) or \
           channels_col.find_one({"channel_id": int(item_id) if item_id.replace('-','').isdigit() else 0})
    
    if not data: return
    
    # Save to Database
    utr_col.insert_one({"utr": utr, "user_id": int(u_id)})
    
    # Subscription Logic (expiry calculate karein)
    expiry = int(time.time()) + (int(mins) * 60) if mins != 'manual' else int(time.time()) + (365*24*60*60)
    users_col.update_one({"user_id": int(u_id), "channel_id": data.get('channel_id', 0)}, {"$set": {"expiry": expiry}}, upsert=True)

    markup = InlineKeyboardMarkup()
    
    # --- CHANNEL DELIVERY ---
    if 'story_name' not in data and 'channel_id' in data:
        try:
            invite = bot.create_chat_invite_link(data['channel_id'], member_limit=1)
            markup.add(InlineKeyboardButton("📢 Join Channel", url=invite.invite_link))
            success_text = f"✅ <b>ᴘᴀʏᴍᴇɴᴛ ᴀᴘᴘʀᴏᴠᴇᴅ!</b>\n\nAapka access activate ho gaya hai. Join karne ke liye niche click karein:"
        except:
            success_text = "✅ <b>ᴀᴘᴘʀᴏᴠᴇᴅ!</b>\nPar link generate nahi ho paya. Admin se link maangein."
    
    # --- STORY DELIVERY ---
    else:
        markup.add(InlineKeyboardButton("🚀 sᴛᴀʀᴛ sᴛᴏʀʏ", url=data['bot_link']))
        success_text = f"✅ <b>ᴘᴀʏᴍᴇɴᴛ ᴀᴘᴘʀᴏᴠᴇᴅ!</b>\n\nStory: <b>{data['story_name']}</b>\nNiche button se access karein (Protected Content):"

    bot.send_message(u_id, success_text, reply_markup=markup, parse_mode="HTML", protect_content=True)
    bot.edit_message_caption(f"✅ Approved: {utr}", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('rej_'))
def admin_reject_action(call):
    _, u_id, utr = call.data.split('_')
    bot.edit_message_caption(f"❌ Rejected: {utr}", call.message.chat.id, call.message.message_id)
    bot.send_message(u_id, "❌ <b>ᴘᴀʏᴍᴇɴᴛ ʀᴇᴊᴇᴄᴛᴇᴅ!</b>\nAdmin ne aapka payment reject kar diya hai. Support se contact karein.")
