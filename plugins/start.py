from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot, get_time_string
from database import channels_col, users_col
from datetime import datetime
import config

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    text = message.text.split()

    # ─── DEEP LINK ENTRY (WHEN USER COMES TO BUY) ───
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
                    f"➔ Please niche diye gaye active plans mein se apni choice ka ek plan select karein:"
                )
                bot.send_message(message.chat.id, premium_text, reply_markup=markup, parse_mode="HTML")
                return
        except: 
            pass

    # ─── NORMAL USER START MENU ───
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 ᴍʏ ᴅᴀsʜʙᴏᴀʀᴅ", callback_data="my_plan"),
        InlineKeyboardButton("📞 sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{config.CONTACT_USERNAME}")
    )
    
    welcome_text = (
        f"┏───────────────────┓\n"
        f"     👋 <b>ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴍᴇᴍʙᴇʀsʜɪᴘ ʙᴏᴛ</b>\n"
        f"┗───────────────────┛\n\n"
        f"👤 <b>ʜᴇʟʟᴏ,</b> {message.from_user.first_name}!\n\n"
        f"➔ Main aapki premium subscriptions aur auto-access links ko manage karta hoon.\n"
        f"➔ Apne active plans ki validity dekhne ke liye niche diye gaye <b>My Dashboard</b> button par click karein."
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="HTML")

    # ─── PREMIUM ADMIN CONTROL PANEL (WITH BUTTONS) ───
    if user_id == config.ADMIN_ID:
        admin_markup = InlineKeyboardMarkup(row_width=2)
        # Pehli row mein do bade buttons ek sath (Add aur Manage)
        admin_markup.add(
            InlineKeyboardButton("➕ ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", callback_data="admin_add"),
            InlineKeyboardButton("⚙️ ᴍᴀɴᴀɢᴇ ᴄʜᴀɴɴᴇʟs", callback_data="admin_channels")
        )
        # Doosri row mein akele Remove subscription button (Kyunki ye bada text hai)
        admin_markup.add(
            InlineKeyboardButton("❌ ʀᴇᴍᴏᴠᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ", callback_data="admin_remove")
        )
        
        admin_text = (
            f"╔════════════════════════╗\n"
            f"     🛠 <b>⚡ ᴀᴅᴍɪɴ ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ</b>\n"
            f"╚════════════════════════╝\n\n"
            f"➔ Welcome Back, Boss! Aapke administrative shortcuts niche diye gaye hain.\n"
            f"➔ Kisi bhi command ko trigger karne ke liye seedhe button par click karein:"
        )
        bot.send_message(config.ADMIN_ID, admin_text, reply_markup=admin_markup, parse_mode="HTML")


# ─── ADMIN BUTTONS CLICKS REDIRECTION (BRIDGE) ───
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_button_bridge(call):
    if call.from_user.id != config.ADMIN_ID:
        bot.answer_callback_query(call.id, "Aap is panel ke admin nahi hain!", show_alert=True)
        return
        
    action = call.data.split('_')[1]
    
    # Message delete karke clear feel dene ke liye
    bot.delete_message(call.message.chat.id, call.message.message_id)
    
    # Fake/Virtual message object generate kar rahe hain taaki purane command handlers automatic chal sakein
    fake_msg = call.message
    fake_msg.from_user = call.from_user
    
    if action == "add":
        from plugins.admin import add_channel_handler # Agar aapki file ka path alag hai toh adjust karein
        bot.send_message(call.message.chat.id, "⚡ <b>ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ ᴍᴏᴅᴇ:</b> Please use <code>/add</code> command to start.")
    elif action == "channels":
        bot.send_message(call.message.chat.id, "⚡ <b>ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ᴍᴏᴅᴇ:</b> Please use <code>/channels</code> to see list.")
    elif action == "remove":
        bot.send_message(call.message.chat.id, "⚡ <b>ʀᴇᴍᴏᴠᴇ ᴍᴏᴅᴇ:</b> Please use <code>/remove</code> to kick user.")


# ─── PREMIUM SUBSCRIPTION DASHBOARD ───
@bot.message_handler(commands=['myplan'])
@bot.callback_query_handler(func=lambda call: call.data == "my_plan")
def my_plan(message):
    u_id = message.from_user.id if hasattr(message, 'from_user') else message.message.chat.id
    subs = list(users_col.find({"user_id": u_id}))
    
    if not subs:
        no_plan_text = (
            f"❌ <b>ɴᴏ ᴀᴄᴛɪᴠᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴ!</b>\n\n"
            f"➔ Aapka koi bhi active premium plan nahi mila.\n"
            f"➔ Please join karne ke liye official channel link ka upyog karein ya support par sampark karein."
        )
        bot.send_message(u_id, no_plan_text, parse_mode="HTML")
        return

    res = (
        f"┏───────────────────┓\n"
        f"     👤 <b>ᴜsᴇʀ sᴜʙsᴄʀɪᴘᴛɪᴏ Zone</b>\n"
        f"┗───────────────────┛\n\n"
    )
    
    for s in subs:
        ch = channels_col.find_one({"channel_id": s['channel_id']})
        name = ch['name'] if ch else "Unknown Channel"
        expiry = datetime.fromtimestamp(s['expiry']).strftime('%d %b %Y ➔ %I:%M %p')
        
        res += (
            f"📺 <b><b>ᴄʜᴀɴɴᴇʟ:</b></b> {name}\n"
            f"⌛ <b><b>ᴠᴀʟɪᴅ ᴛɪʟʟ:</b></b> <code>{expiry}</code>\n"
            f"───────────────────\n"
        )
    
    bot.send_message(u_id, res, parse_mode="HTML")
