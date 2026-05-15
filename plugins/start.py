from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot, get_time_string
from database import channels_col, users_col
from datetime import datetime
import config

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    text = message.text.split()

    # Deep Link Entry
    if len(text) > 1:
        try:
            ch_id = int(text[1])
            ch_data = channels_col.find_one({"channel_id": ch_id})
            if ch_data:
                markup = InlineKeyboardMarkup()
                for p_time, p_price in ch_data['plans'].items():
                    markup.add(InlineKeyboardButton(f"💳 {get_time_string(p_time)} - ₹{p_price}", callback_data=f"select_{ch_id}_{p_time}"))
                if ch_data.get('demo_link'):
                    markup.add(InlineKeyboardButton("📺 View Quality Demo", url=ch_data['demo_link']))
                
                bot.send_message(message.chat.id, f"💎 <b>Premium Access: {ch_data['name']}</b>\n\nNiche diye gaye plans mein se ek select karein:", reply_markup=markup, parse_mode="HTML")
                return
        except: pass

    # Normal Start
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 My Plan", callback_data="my_plan"),
        InlineKeyboardButton("📞 Support", url=f"https://t.me/{config.CONTACT_USERNAME}")
    )
    
    bot.send_message(message.chat.id, f"👋 <b>Welcome {message.from_user.first_name}!</b>\nMain aapki premium subscriptions manage karta hoon. Join karne ke liye official link use karein.", reply_markup=markup, parse_mode="HTML")

    if user_id == config.ADMIN_ID:
        bot.send_message(config.ADMIN_ID, "🛠 <b>Admin Menu:</b>\n/add - Add Channel\n/channels - Manage\n/remove - Kick User", parse_mode="HTML")

@bot.message_handler(commands=['myplan'])
@bot.callback_query_handler(func=lambda call: call.data == "my_plan")
def my_plan(message):
    u_id = message.from_user.id if hasattr(message, 'from_user') else message.message.chat.id
    subs = list(users_col.find({"user_id": u_id}))
    
    if not subs:
        bot.send_message(u_id, "❌ <b>Aapka koi active plan nahi hai.</b>", parse_mode="HTML")
        return

    res = "👤 <b>Aapka Dashboard</b>\n\n"
    for s in subs:
        ch = channels_col.find_one({"channel_id": s['channel_id']})
        name = ch['name'] if ch else "Unknown"
        expiry = datetime.fromtimestamp(s['expiry']).strftime('%d %b %Y')
        res += f"📺 <b>{name}</b>\n⌛ Valid Till: {expiry}\n\n"
    
    bot.send_message(u_id, res, parse_mode="HTML")
    
