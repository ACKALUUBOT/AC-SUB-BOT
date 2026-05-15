import urllib.parse
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot, get_time_string, approve_user_logic
from database import channels_col, utr_col
import config

# Server se rzp_client import kar rahe hain toggle check ke liye
from server import rzp_client

# --- 1. DYNAMIC PAYMENT METHOD CHOICE ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('select_'))
def pay_choice(call):
    _, ch_id, mins = call.data.split('_')
    
    markup = InlineKeyboardMarkup()
    
    # 🌟 CONDITIONAL LOGIC: Agar aapne Razorpay API ID feed ki hai, tabhi ye button dikhega
    if config.RZP_KEY_ID and rzp_client:
        markup.add(InlineKeyboardButton("⚡ ᴏɴʟɪɴᴇ ᴘᴀʏ (ɪɴsᴛᴀɴᴛ)", callback_data=f"rzp_{ch_id}_{mins}"))
    
    # Manual payment button hamesha dikhta rahega
    markup.add(InlineKeyboardButton("💳 ᴍᴀɴᴜᴀʟ ᴘᴀʏᴍᴇɴᴛ (ᴜᴘɪ)", callback_data=f"man_{ch_id}_{mins}"))
    
    text = (
        f"╔════════════════════════╗\n"
        f"       💎 <b>ᴘʀᴇᴍɪᴜᴍ sᴜʙsᴄʀɪᴘᴛɪᴏɴ</b>\n"
        f"╚════════════════════════╝\n\n"
        f"➔ Aapne premium plan select kar liya hai.\n"
        f"➔ Niche diye gaye button par click karke secure payment details aur QR Code generate karein."
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")


# --- 2. BACKUP RAZORPAY LOGIC (AUTO-SLEEP MODE) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('rzp_'))
def rzp_pay(call):
    if not rzp_client or not config.RZP_KEY_ID:
        bot.answer_callback_query(call.id, "Online payment is currently unavailable.", show_alert=True)
        return
        
    _, ch_id, mins = call.data.split('_')
    ch_data = channels_col.find_one({"channel_id": int(ch_id)})
    price = int(ch_data['plans'][mins]) * 100 
    
    try:
        order = rzp_client.order.create(data={
            'amount': price, 'currency': 'INR', 'payment_capture': 1,
            'notes': {'user_id': str(call.from_user.id), 'channel_id': str(ch_id), 'mins': str(mins)}
        })
        pay_url = f"https://api.razorpay.com/v1/checkout/embedded?key_id={config.RZP_KEY_ID}&order_id={order['id']}"
        bot.send_message(call.message.chat.id, "⚡ <b>sᴇᴄᴜʀᴇ ᴏɴʟɪɴᴇ ɢᴀᴛᴇᴡᴀʏ:</b>", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("Pay Now", url=pay_url)), parse_mode="HTML")
    except Exception as e:
        bot.answer_callback_query(call.id, f"Gateway Error: {str(e)}", show_alert=True)


# --- 3. PREMIUM MANUAL QR GENERATOR & DETAILS ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('man_'))
def manual_pay(call):
    _, ch_id, mins = call.data.split('_')
    ch_data = channels_col.find_one({"channel_id": int(ch_id)})
    price = ch_data['plans'][mins]
    
    upi_string = f"upi://pay?pa={config.UPI_ID}&am={price}&cu=INR&tn=Premium_Sub"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=350x350&data={urllib.parse.quote(upi_string)}"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ ɪ ʜᴀᴠᴇ ᴘᴀɪᴅ (sᴜʙᴍɪᴛ)", callback_data=f"paid_{ch_id}_{mins}"))
    
    caption_text = (
        f"┏───────────────────┓\n"
        f"     💰 <b>ᴘᴀʏᴍᴇɴᴛ ɪɴᴠᴏɪᴄᴇ</b>\n"
        f"┗───────────────────┛\n\n"
        f"📺 <b><b>ᴄʜᴀɴɴᴇʟ:</b></b> {ch_data['name']}\n"
        f"⌛ <b><b>ᴠᴀʟɪᴅɪᴛʏ:</b></b> {get_time_string(mins)}\n"
        f"💵 <b><b>ᴀᴍᴏᴜɴᴛ:</b></b> ₹{price}\n\n"
        f"➔ <b><b>ᴜᴘɪ ɪᴅ:</b></b> <code>{config.UPI_ID}</code>\n\n"
        f"⚠️ <b><b>ɪɴsᴛʀᴜᴄᴛɪᴏɴs:</b></b>\n"
        f"1. Upar diye gaye QR Code ko scan karke payment karein.\n"
        f"2. Payment successfully hone ke baad <b>Screenshot</b> le lein.\n"
        f"3. Niche diye gaye button par click karke proof submit karein."
    )
    bot.send_photo(call.message.chat.id, qr_url, caption=caption_text, reply_markup=markup, parse_mode="HTML")


# --- 4. PROOF SUBMISSION GATE (SCREENSHOT + UTR) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('paid_'))
def req_ss(call):
    _, ch_id, mins = call.data.split('_')
    msg = bot.send_message(call.message.chat.id, "📸 <b>ᴘʀᴏᴏғ sᴜʙᴍɪssɪᴏɴ:</b>\n\nKripya apni payment ka <b>Screenshot</b> send karein:", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_manual_ss, ch_id, mins)

def process_manual_ss(message, ch_id, mins):
    if message.content_type != 'photo':
        msg = bot.send_message(message.chat.id, "❌ Kripya sirf <b>Screenshot (Photo)</b> hi bhejein. Dobara koshish karein:")
        bot.register_next_step_handler(msg, process_manual_ss, ch_id, mins)
        return
        
    photo_file_id = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, "✍️ <b>uᴛʀ ᴠᴇʀɪғɪᴄᴀᴛɪᴏɴ:</b>\n\nAb payment ka <b>12-digit UTR / Reference Number</b> type karke bhejein:", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_manual_utr, ch_id, mins, photo_file_id)

def process_manual_utr(message, ch_id, mins, photo_file_id):
    utr_input = message.text.strip() if message.text else ""
    user_id = message.from_user.id
    
    if utr_input == '/cancel':
        bot.send_message(message.chat.id, "❌ Action cancelled.")
        return

    if not utr_input.isdigit() or len(utr_input) != 12:
        msg = bot.send_message(message.chat.id, "❌ <b>ɪɴᴠᴀʟɪᴅ ᴜᴛʀ!</b> UTR number hamesha 12 digits ka hota hai. Sahi UTR type karke bhejein (ya /cancel):", parse_mode="HTML")
        bot.register_next_step_handler(msg, process_manual_utr, ch_id, mins, photo_file_id)
        return

    existing_utr = utr_col.find_one({"utr": utr_input})
    if existing_utr:
        bot.send_message(message.chat.id, "❌ <b>ғʀᴀᴜᴅ ᴅᴇᴛᴇᴄᴛᴇᴅ!</b> Yeh UTR pehle hi use ho chuka hai.", parse_mode="HTML")
        return

    user_success_text = (
        f"⏳ <b>ʀᴇǫᴜᴇsᴛ sᴜʙᴍɪᴛᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n\n"
        f"➔ Aapka request verification ke liye Admin ke paas bhej diya gaya hai.\n"
        f"➔ Request status check hone ke baad aapko notification mil jayega."
    )
    bot.send_message(message.chat.id, user_success_text, parse_mode="HTML")
    
    ch_data = channels_col.find_one({"channel_id": int(ch_id)})
    price = ch_data['plans'][mins]
    
    # REJECT BUTTON IS HIDDEN AS REQUESTED (ONLY APPROVE WILL APPEAR)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ ᴀᴘᴘʀᴏᴠᴇ", callback_data=f"app_{user_id}_{ch_id}_{mins}_{utr_input}"))
    
    admin_caption = (
        f"📥 <b><b>ɴᴇᴡ ᴘᴀʏᴍᴇɴᴛ ʀᴇǫᴜᴇsᴛ</b></b>\n"
        f"───────────────────\n"
        f"👤 <b><b>ᴜsᴇʀ:</b></b> <code>{user_id}</code>\n"
        f"📺 <b><b>ᴄʜᴀɴɴᴇʟ:</b></b> <b>{ch_data['name']}</b>\n"
        f"💵 <b><b>ᴀᴍᴏᴜɴᴛ:</b></b> ₹{price} ({get_time_string(mins)})\n"
        f"🔢 <b><b>ᴜᴛʀ:</b></b> <code>{utr_input}</code>\n"
        f"───────────────────\n"
        f"💬 <i>Bank Me UTR Match Karke Hi Approve Karein.</i>"
    )
    bot.send_photo(config.ADMIN_ID, photo_file_id, caption=admin_caption, reply_markup=markup, parse_mode="HTML")


# --- 5. ADMIN APPROVAL FUNCTION ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('app_'))
def manual_approve(call):
    _, u_id, ch_id, mins, utr_val = call.data.split('_')
    
    if utr_col.find_one({"utr": utr_val}):
        bot.answer_callback_query(call.id, "This UTR is already processed!", show_alert=True)
        return
        
    utr_col.insert_one({"utr": utr_val, "user_id": int(u_id), "status": "approved"})
    approve_user_logic(int(u_id), int(ch_id), int(mins), f"Manual (UTR: {utr_val})")
    bot.edit_message_caption(f"✅ ᴀᴘᴘʀᴏᴠᴇᴅ & ʟᴏᴄᴋᴇᴅ\nUTR: <code>{utr_val}</code>", call.message.chat.id, call.message.message_id, parse_mode="HTML")
