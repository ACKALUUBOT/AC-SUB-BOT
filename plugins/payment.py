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
    _, ch_id, mins = call.data.split('_')
    ch_data = channels_col.find_one({"channel_id": int(ch_id)})
    price = ch_data['plans'][mins]
    
    markup = InlineKeyboardMarkup(row_width=1)
    if config.RZP_KEY_ID and rzp_client:
        markup.add(InlineKeyboardButton("⚡ ɪɴsᴛᴀɴᴛ ᴏɴʟɪɴᴇ ᴘᴀʏ", callback_data=f"rzp_{ch_id}_{mins}"))
    markup.add(InlineKeyboardButton("💳 ᴘᴀʏ ᴠɪᴀ ǫʀ sᴄᴀɴ", callback_data=f"man_{ch_id}_{mins}_qr"),
               InlineKeyboardButton("📲 ᴘᴀʏ ᴠɪᴀ ᴜᴘɪ ɪᴅ", callback_data=f"man_{ch_id}_{mins}_upi"))
    
    text = (
        f"<b>🛒 ᴄᴏɴғɪʀᴍ sᴇʟᴇᴄᴛɪᴏɴ</b>\n"
        f"────────────────────\n"
        f"📺 ᴄʜᴀɴɴᴇʟ: {ch_data['name']}\n"
        f"⌛ ᴘʟᴀɴ: {get_time_string(mins)}\n"
        f"💰 ᴀᴍᴏᴜɴᴛ: <b>₹{price}</b>\n\n"
        f"➔ Payment method select karein:"
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

# --- 2. ONLINE PAYMENT ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('rzp_'))
def rzp_pay(call):
    _, ch_id, mins = call.data.split('_')
    ch_data = channels_col.find_one({"channel_id": int(ch_id)})
    amount = int(ch_data['plans'][mins]) * 100
    try:
        order = rzp_client.order.create(data={'amount': amount, 'currency': 'INR', 'payment_capture': 1})
        pay_url = f"https://api.razorpay.com/v1/checkout/embedded?key_id={config.RZP_KEY_ID}&order_id={order['id']}"
        bot.send_message(call.message.chat.id, "⚡ <b>ᴏɴʟɪɴᴇ ᴘᴀʏᴍᴇɴᴛ ʟɪɴᴋ:</b>\n\nNiche click karke pay karein:", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("💳 Pay Now", url=pay_url)), parse_mode="HTML")
    except Exception as e:
        bot.answer_callback_query(call.id, f"Gateway Error: {e}")

# --- 3. MANUAL (QR & UPI ID) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('man_'))
def manual_pay(call):
    _, ch_id, mins, mode = call.data.split('_')
    ch_data = channels_col.find_one({"channel_id": int(ch_id)})
    price = ch_data['plans'][mins]
    
    upi_string = f"upi://pay?pa={config.UPI_ID}&am={price}&cu=INR&tn=Premium"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=350x350&data={urllib.parse.quote(upi_string)}"
    
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ sᴜʙᴍɪᴛ sᴄʀᴇᴇɴsʜᴏᴛ", callback_data=f"paid_{ch_id}_{mins}"))

    if mode == "qr":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_photo(call.message.chat.id, qr_url, caption=f"📥 <b>ǫʀ sᴄᴀɴɴᴇʀ</b>\n\nAmount: <b>₹{price}</b>\nUPI ID: <code>{config.UPI_ID}</code>\n\n➔ Scan karke payment karein aur screenshot bhejein.", reply_markup=markup, parse_mode="HTML")
    else:
        text = (
            f"📲 <b>ᴜᴘɪ ɪᴅ ᴘᴀʏᴍᴇɴᴛ</b>\n\n"
            f"Amount: <b>₹{price}</b>\n"
            f"UPI ID: <code>{config.UPI_ID}</code>\n\n"
            f"➔ ID copy karke pay karein aur screenshot bhejein."
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

# --- 4. STEP-BY-STEP (SS -> UTR) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('paid_'))
def step1(call):
    _, ch_id, mins = call.data.split('_')
    msg = bot.send_message(call.message.chat.id, "📸 Payment ka <b>Screenshot</b> bhejein:")
    bot.register_next_step_handler(msg, step2, ch_id, mins)

def step2(message, ch_id, mins):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ Screenshot bhejein!")
        bot.register_next_step_handler(msg, step2, ch_id, mins)
        return
    photo_id = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, "✍️ 12-digit <b>UTR Number</b> type karein:")
    bot.register_next_step_handler(msg, final_admin_req, ch_id, mins, photo_id)

def final_admin_req(message, ch_id, mins, photo_id):
    utr = message.text.strip() if message.text else ""
    if len(utr) != 12 or not utr.isdigit():
        msg = bot.send_message(message.chat.id, "❌ Sahi 12-digit UTR bhejein:")
        bot.register_next_step_handler(msg, final_admin_req, ch_id, mins, photo_id)
        return
    if utr_col.find_one({"utr": utr}):
        return bot.send_message(message.chat.id, "❌ <b>Error:</b> Yeh UTR pehle hi use ho chuka hai!")

    bot.send_message(message.chat.id, "⏳ <b>ʀᴇǫᴜᴇsᴛ sᴜʙᴍɪᴛᴛᴇᴅ!</b>\nAdmin verify karke activate kar dega.")
    
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("✅ Approve", callback_data=f"app_{message.from_user.id}_{ch_id}_{mins}_{utr}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"rej_{message.from_user.id}_{utr}"),
        InlineKeyboardButton("💬 Support", url=f"tg://openmessage?user_id={message.from_user.id}")
    )
    admin_text = f"📥 <b>ɴᴇᴡ ʀᴇǫᴜᴇsᴛ</b>\nUser: <code>{message.from_user.id}</code>\nUTR: <code>{utr}</code>\nPlan: {get_time_string(mins)}"
    bot.send_photo(config.ADMIN_ID, photo_id, caption=admin_text, reply_markup=markup, parse_mode="HTML")

# --- 5. ADMIN ACTIONS ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('app_'))
def admin_app(call):
    _, u_id, ch_id, mins, utr = call.data.split('_')
    if utr_col.find_one({"utr": utr}): return
    utr_col.insert_one({"utr": utr, "user_id": int(u_id)})
    approve_user_logic(int(u_id), int(ch_id), int(mins), f"Manual({utr})")
    bot.edit_message_caption(f"✅ Approved: {utr}", call.message.chat.id, call.message.message_id)
    bot.send_message(u_id, "🎉 <b>sᴜʙsᴄʀɪᴘᴛɪᴏɴ ᴀᴄᴛɪᴠᴀᴛᴇᴅ!</b>")

@bot.callback_query_handler(func=lambda call: call.data.startswith('rej_'))
def admin_rej(call):
    _, u_id, utr = call.data.split('_')
    bot.edit_message_caption(f"❌ Rejected: {utr}", call.message.chat.id, call.message.message_id)
    bot.send_message(u_id, "❌ <b>ᴘᴀʏᴍᴇɴᴛ ʀᴇᴊᴇᴄᴛᴇᴅ!</b>\nAdmin ne aapka request reject kar diya hai.")
