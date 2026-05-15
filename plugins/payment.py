import urllib.parse
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot, get_time_string, approve_user_logic
from database import channels_col
import config
from server import rzp_client

@bot.callback_query_handler(func=lambda call: call.data.startswith('select_'))
def pay_choice(call):
    _, ch_id, mins = call.data.split('_')
    markup = InlineKeyboardMarkup()
    if config.RZP_KEY_ID:
        markup.add(InlineKeyboardButton("⚡ Online Pay (Instant)", callback_data=f"rzp_{ch_id}_{mins}"))
    markup.add(InlineKeyboardButton("📸 Manual Pay (Screenshot)", callback_data=f"man_{ch_id}_{mins}"))
    bot.edit_message_text("<b>Payment Method Select Karein:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith('rzp_'))
def rzp_pay(call):
    if not rzp_client:
        bot.answer_callback_query(call.id, "Online payment currently disabled.")
        return
    _, ch_id, mins = call.data.split('_')
    ch_data = channels_col.find_one({"channel_id": int(ch_id)})
    price = int(ch_data['plans'][mins]) * 100 
    
    order = rzp_client.order.create(data={
        'amount': price, 'currency': 'INR', 'payment_capture': 1,
        'notes': {'user_id': str(call.from_user.id), 'channel_id': str(ch_id), 'mins': str(mins)}
    })
    
    pay_url = f"https://api.razorpay.com/v1/checkout/embedded?key_id={config.RZP_KEY_ID}&order_id={order['id']}"
    bot.send_message(call.message.chat.id, "💳 <b>Secure Payment:</b>", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Pay Now", url=pay_url)), parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith('man_'))
def manual_pay(call):
    _, ch_id, mins = call.data.split('_')
    ch_data = channels_col.find_one({"channel_id": int(ch_id)})
    price = ch_data['plans'][mins]
    
    upi_string = f"upi://pay?pa={config.UPI_ID}&am={price}&cu=INR&tn=Sub"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(upi_string)}"
    
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("✅ I Have Paid", callback_data=f"paid_{ch_id}_{mins}"))
    bot.send_photo(call.message.chat.id, qr_url, caption=f"💰 <b>Pay: ₹{price}</b>\nUPI: <code>{config.UPI_ID}</code>\n\nScreenshot upload karein.", reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith('paid_'))
def req_ss(call):
    msg = bot.send_message(call.message.chat.id, "📸 Payment screenshot bhejein.")
    bot.register_next_step_handler(msg, process_manual_ss, call.data.split('_')[1], call.data.split('_')[2])

def process_manual_ss(message, ch_id, mins):
    if message.content_type != 'photo': return
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Approve", callback_data=f"app_{message.from_user.id}_{ch_id}_{mins}"))
    markup.add(InlineKeyboardButton("❌ Reject", callback_data=f"rej_{message.from_user.id}"))
    bot.send_photo(config.ADMIN_ID, message.photo[-1].file_id, caption=f"📸 <b>Manual Request</b>\nUser: <code>{message.from_user.id}</code>", reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith('app_'))
def manual_approve(call):
    _, u_id, ch_id, mins = call.data.split('_')
    approve_user_logic(int(u_id), int(ch_id), int(mins), "Manual Admin Approval")
    bot.edit_message_caption("✅ Approved", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('rej_'))
def manual_reject(call):
    bot.send_message(int(call.data.split('_')[1]), "❌ <b>Payment Rejected.</b> Contact admin.", parse_mode="HTML")
    bot.edit_message_caption("❌ Rejected", call.message.chat.id, call.message.message_id)

