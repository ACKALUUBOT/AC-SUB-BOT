from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot, get_time_string
from database import channels_col, users_col
from datetime import datetime
import config

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    text = message.text.split()

    # ─── 1. DEEP LINK ENTRY (FOR BUYERS) ───
    if len(text) > 1:
        try:
            ch_id = int(text[1])
            ch_data = channels_col.find_one({"channel_id": ch_id})
            if ch_data:
                markup = InlineKeyboardMarkup()
                for p_time, p_price in ch_data['plans'].items():
                    markup.add(InlineKeyboardButton(f"💳 {get_time_string(p_time)} - ₹{p_price}", callback_data=f"select_{ch_id}_{p_time}"))
                if ch_data.get('demo_link'):
                    markup.add(InlineKeyboardButton("📺 ᴠɪᴇᴡ ǫᴜᴀʟɪᴛʏ ᴅᴇᴍᴏ", url=ch_data['demo_link']))
                
                premium_text = (
                    f"╔════════════════════════╗\n"
                    f"       💎 <b>ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss</b>\n"
                    f"╚════════════════════════╝\n\n"
                    f"📺 <b>ᴄʜᴀɴɴᴇʟ:</b> {ch_data['name']}\n"
                    f"➔ Please niche diye gaye active plans mein se ek select karein:"
                )
                bot.send_message(message.chat.id, premium_text, reply_markup=markup, parse_mode="HTML")
                return
        except: 
            pass

    # ─── 2. MERGED MASTER MENU (ADMIN + USER) ───
    markup = InlineKeyboardMarkup(row_width=2)
    
    # User Buttons
    btn_dashboard = InlineKeyboardButton("📊 ᴍʏ ᴅᴀsʜʙᴏᴀʀᴅ", callback_data="my_plan")
    btn_support = InlineKeyboardButton("📞 sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{config.CONTACT_USERNAME}")
    markup.add(btn_dashboard, btn_support)

    # Admin Special Buttons (Sirf Admin ko dikhenge)
    if user_id == config.ADMIN_ID:
        markup.add(
            InlineKeyboardButton("➕ ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", callback_data="admin_add"),
            InlineKeyboardButton("⚙️ ᴍᴀɴᴀɢᴇ ᴄʜᴀɴɴᴇʟs", callback_data="admin_channels")
        )
        markup.add(InlineKeyboardButton("❌ ʀᴇᴍᴏᴠᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ", callback_data="admin_remove"))

    # Custom Text Logic
    if user_id == config.ADMIN_ID:
        title = "⚡ <b>ᴀᴅᴍɪɴ ᴍᴀsᴛᴇʀ ᴘᴀɴᴇʟ</b>"
        desc = "Welcome Back, Boss! Aapka personal dashboard aur administrative controls niche diye gaye hain."
    else:
        title = "👋 <b>ᴡᴇʟᴄᴏᴍᴇ ᴍᴇᴍʙᴇʀ</b>"
        desc = "Main aapki premium subscriptions ko manage karta hoon. Dashboard check karne ke liye niche click karein."

    final_text = (
        f"┏───────────────────┓\n"
        f"     {title}\n"
        f"┗───────────────────┛\n\n"
        f"👤 <b>ʜᴇʟʟᴏ,</b> {message.from_user.first_name}!\n\n"
        f"➔ {desc}"
    )
    
    bot.send_message(message.chat.id, final_text, reply_markup=markup, parse_mode="HTML")


# ─── 3. ADMIN BUTTONS BRIDGE (CRASH-FREE) ───
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_button_bridge(call):
    if call.from_user.id != config.ADMIN_ID:
        bot.answer_callback_query(call.id, "Unauthorized Access!", show_alert=True)
        return
        
    action = call.data.split('_')[1]
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    
    if action == "add":
        bot.send_message(call.message.chat.id, "➕ <b>ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ ᴍᴏᴅᴇ:</b>\nNaya channel add karne ke liye type karein: <code>/add</code>", parse_mode="HTML")
    elif action == "channels":
        bot.send_message(call.message.chat.id, "⚙️ <b>ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ᴍᴏᴅᴇ:</b>\nChannels manage karne ke liye type karein: <code>/channels</code>", parse_mode="HTML")
    elif action == "remove":
        bot.send_message(call.message.chat.id, "❌ <b>ʀᴇᴍᴏᴠᴇ ᴍᴏᴅᴇ:</b>\nUser ko kick karne ke liye type karein: <code>/remove</code>", parse_mode="HTML")


# ─── 4. MASTER DASHBOARD (ADMIN LIST + USER PLAN) ───
@bot.message_handler(commands=['myplan'])
@bot.callback_query_handler(func=lambda call: call.data == "my_plan")
def my_plan(message):
    u_id = message.from_user.id if hasattr(message, 'from_user') else message.message.chat.id
    
    # --- ADMIN VIEW: ALL USERS LIST ---
    if u_id == config.ADMIN_ID:
        all_subs = list(users_col.find().sort("expiry", 1))
        
        if not all_subs:
            bot.send_message(u_id, "🧐 <b>ᴀᴅᴍɪɴ ʀᴇᴘᴏʀᴛ:</b> Abhi koi bhi active premium user nahi hai.", parse_mode="HTML")
            return

        report = "📋 <b>ᴀʟʟ ᴀᴄᴛɪᴠᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴs</b>\n"
        report += "───────────────────\n\n"
        
        for s in all_subs:
            ch = channels_col.find_one({"channel_id": s['channel_id']})
            ch_name = ch['name'] if ch else "Unknown"
            expiry_dt = datetime.fromtimestamp(s['expiry'])
            days_left = (expiry_dt - datetime.now()).days
            
            status_time = f"{days_left} Days" if days_left > 0 else "Expires Today"
            
            report += (
                f"👤 <b>ᴜsᴇʀ:</b> <code>{s['user_id']}</code>\n"
                f"📺 <b>ᴄʜ:</b> {ch_name}\n"
                f"⏳ <b>ʟᴇғᴛ:</b> <code>{status_time}</code>\n"
                f"📅 <b>ᴇxᴘ:</b> {expiry_dt.strftime('%d/%m/%y')}\n"
                f"───────────────────\n"
            )
        bot.send_message(u_id, report, parse_mode="HTML")
        return

    # --- USER VIEW: OWN PLAN ---
    subs = list(users_col.find({"user_id": u_id}))
    if not subs:
        bot.send_message(u_id, "❌ <b>Aapka koi active plan nahi hai.</b>", parse_mode="HTML")
        return

    res = "┏───────────────────┓\n     👤 <b>ᴜsᴇʀ sᴜʙsᴄʀɪᴘᴛɪᴏɴ</b>\n┗───────────────────┛\n\n"
    for s in subs:
        ch = channels_col.find_one({"channel_id": s['channel_id']})
        name = ch['name'] if ch else "Unknown"
        expiry = datetime.fromtimestamp(s['expiry']).strftime('%d %b %Y ➔ %I:%M %p')
        res += f"📺 <b>{name}</b>\n⌛ Valid: <code>{expiry}</code>\n───────────────────\n"
    
    bot.send_message(u_id, res, parse_mode="HTML")
