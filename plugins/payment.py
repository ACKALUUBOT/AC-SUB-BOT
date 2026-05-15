import urllib.parse
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot, get_time_string, approve_user_logic
from database import channels_col, utr_col
import config

try: from server import rzp_client
except: rzp_client = None

# --- 1. PAYMENT SELECTION ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('select_'))
def confirm_step(call):
    _, item_id, mins = call.data.split('_')
    # Hum 'item_id' se check karenge ki ye Story hai ya Channel
    data = channels_col.find_one({"item_id": item_id}) or channels_col.find_one({"channel_id": int(item_id)})
    
    if not data:
        return bot.answer_callback_query(call.id, "Data not found!")

    # Check if it's a Story (price is direct) or Channel (plans dict)
    price = data['price'] if 'story_name' in data else data['plans'][mins]
    display_name = data.get('story_name') or data.get('name')
    
    markup = InlineKeyboardMarkup(row_width=1)
    if config.RZP_KEY_ID and rzp_client:
        markup.add(InlineKeyboardButton("⚡ ɪɴsᴛᴀɴᴛ ᴏɴʟɪɴᴇ ᴘᴀʏ", callback_data=f"rzp_{item_id}_{mins}"))
    
    markup.add(InlineKeyboardButton("💳 ᴘᴀʏ ᴠɪᴀ ǫʀ sᴄᴀɴ", callback_data=f"man_{item_id}_{mins}_qr"),
               InlineKeyboardButton("📲 ᴘᴀʏ ᴠɪᴀ ᴜᴘɪ ɪᴅ", callback_data=f"man_{item_id}_{mins}_upi"))
    
    text = (
        f"<b>🛒 ᴄᴏɴғɪʀᴍ sᴇʟᴇᴄᴛɪᴏɴ</b>\n"
        f"────────────────────\n"
        f"📦 ɪᴛᴇᴍ: {display_name}\n"
        f"💰 ᴀᴍᴏᴜɴᴛ: <b>₹{price}</b>\n\n"
        f"➔ Payment method select karein:"
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

# --- 2. MANUAL (QR & UPI ID) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('man_'))
def manual_pay(call):
    _, item_id, mins, mode = call.data.split('_')
    data = channels_col.find_one({"item_id": item_id}) or channels_col.find_one({"channel_id": int(item_id)})
    price = data['price'] if 'story_name' in data else data['plans'][mins]
    
    upi_string = f"upi://pay?pa={config.UPI_ID}&am={price}&cu=INR&tn=Premium"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=350x350&data={urllib.parse.quote(upi_string)}"
    
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ sᴜʙᴍɪᴛ sᴄʀᴇᴇɴsʜᴏᴛ", callback_data=f"paid_{item_id}_{mins}"))

    if mode == "qr":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_photo(call.message.chat.id, qr_url, caption=f"📥 <b>ǫʀ sᴄᴀɴɴᴇʀ</b>\n\nAmount: <b>₹{price}</b>\nUPI: <code>{config.UPI_ID}</code>\n\n➔ Screenshot bhejein.", reply_markup=markup, parse_mode="HTML")
    else:
        bot.edit_message_text(f"📲 <b>ᴜᴘɪ ɪᴅ:</b> <code>{config.UPI_ID}</code>\nAmount: <b>₹{price}</b>\n\n➔ Pay karke screenshot bhejein.", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

# --- 3. ADMIN REQUEST ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('paid_'))
def step1(call):
    _, item_id, mins = call.data.split('_')
    msg = bot.send_message(call.message.chat.id, "📸 Payment ka <b>Screenshot</b> bhejein:")
    bot.register_next_step_handler(msg, step2, item_id, mins)

def step2(message, item_id, mins):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ Screenshot bhejein!")
        bot.register_next_step_handler(msg, step2, item_id, mins)
        return
    photo_id = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, "✍️ 12-digit <b>UTR Number</b> type karein:")
    bot.register_next_step_handler(msg, final_admin_req, item_id, mins, photo_id)

def final_admin_req(message, item_id, mins, photo_id):
    utr = message.text.strip() if message.text else ""
    if len(utr) != 12 or not utr.isdigit():
        msg = bot.send_message(message.chat.id, "❌ Sahi 12-digit UTR bhejein:")
        bot.register_next_step_handler(msg, final_admin_req, item_id, mins, photo_id)
        return
    
    data = channels_col.find_one({"item_id": item_id}) or channels_col.find_one({"channel_id": int(item_id)})
    display_name = data.get('story_name') or data.get('name')

    bot.send_message(message.chat.id, "⏳ <b>ʀᴇǫᴜᴇsᴛ sᴜʙᴍɪᴛᴛᴇᴅ!</b>\nWait for approval.")
    
    # Buttons: Approve + Reject + Support Link
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("✅ Approve", callback_data=f"app_{message.from_user.id}_{item_id}_{utr}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"rej_{message.from_user.id}_{utr}"),
        InlineKeyboardButton("💬 Support", url=f"tg://openmessage?user_id={message.from_user.id}")
    )
    admin_text = f"📥 <b>ɴᴇᴡ ʀᴇǫᴜᴇsᴛ</b>\nUser: <code>{message.from_user.id}</code>\nUTR: <code>{utr}</code>\nItem: {display_name}"
    bot.send_photo(config.ADMIN_ID, photo_id, caption=admin_text, reply_markup=markup, parse_mode="HTML")

# --- 4. ADMIN ACTIONS (SECURE DELIVERY) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('app_'))
def admin_app(call):
    _, u_id, item_id, utr = call.data.split('_')
    if utr_col.find_one({"utr": utr}): return
    
    data = channels_col.find_one({"item_id": item_id}) or channels_col.find_one({"channel_id": int(item_id)})
    utr_col.insert_one({"utr": utr, "user_id": int(u_id)})

    # AGAR STORY HAI TO PROTECTED LINK BHEJEGA
    if 'story_name' in data:
        success_text = (
            f"✅ <b>ᴘᴀʏᴍᴇɴᴛ ᴀᴘᴘʀᴏᴠᴇᴅ!</b>\n"
            f"────────────────────\n"
            f"🎬 sᴛᴏʀʏ: <b>{data['story_name']}</b>\n\n"
            f"⚠️ <b>ᴘʀɪᴠᴀᴄʏ ɴᴏᴛᴇ:</b>\n"
            f"Yeh link secure hai. Aap ise forward ya copy nahi kar sakte."
        )
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🚀 sᴛᴀʀᴛ sᴛᴏʀʏ ʙᴏᴛ", url=data['bot_link']))
        bot.send_message(u_id, success_text, reply_markup=markup, parse_mode="HTML", protect_content=True)
    else:
        # AGAR NORMAL CHANNEL HAI TO OLD LOGIC
        bot.send_message(u_id, "🎉 <b>sᴜʙsᴄʀɪᴘᴛɪᴏɴ ᴀᴄᴛɪᴠᴀᴛᴇᴅ!</b>")

    bot.edit_message_caption(f"✅ Approved: {utr}", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('rej_'))
def admin_rej(call):
    _, u_id, utr = call.data.split('_')
    bot.edit_message_caption(f"❌ Rejected: {utr}", call.message.chat.id, call.message.message_id)
    bot.send_message(u_id, "❌ <b>ᴘᴀʏᴍᴇɴᴛ ʀᴇᴊᴇᴄᴛᴇᴅ!</b>\nCheck your UTR/Screenshot.")
