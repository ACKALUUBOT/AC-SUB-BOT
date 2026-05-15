from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot, get_time_string
from database import channels_col, users_col
from datetime import datetime
import config

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    text = message.text.split()

    # ─── 1. DEEP LINK ENTRY (STORY & CHANNEL) ───
    if len(text) > 1:
        item_id = text[1]
        # Database mein dono jagah check karega (Naya ID vs Purana ID)
        data = channels_col.find_one({"item_id": item_id})
        
        # Agar item_id nahi mila, ho sakta hai purana channel_id ho
        if not data and item_id.replace('-', '').isdigit():
            data = channels_col.find_one({"channel_id": int(item_id)})

        if data:
            markup = InlineKeyboardMarkup(row_width=1)
            
            # Agar STORY hai (Aapka naya vision)
            if 'story_name' in data:
                # Ismein mins ki jagah 'manual' bhej rahe hain
                markup.add(InlineKeyboardButton(f"💳 ʙᴜʏ ɴᴏᴡ - ₹{data['price']}", callback_data=f"select_{data['item_id']}_manual"))
                display_name = data['story_name']
                header = "🎬 <b>ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ</b>"
            
            # Agar purana CHANNEL system hai
            else:
                db_id = data.get('item_id') or data.get('channel_id')
                for p_time, p_price in data['plans'].items():
                    markup.add(InlineKeyboardButton(f"💳 {get_time_string(p_time)} - ₹{p_price}", callback_data=f"select_{db_id}_{p_time}"))
                display_name = data['name']
                header = "💎 <b>ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss</b>"

            if data.get('demo_link'):
                markup.add(InlineKeyboardButton("📺 ᴠɪᴇᴡ ǫᴜᴀʟɪᴛʏ ᴅᴇᴍᴏ", url=data['demo_link']))
            
            premium_text = (
                f"{header}\n"
                f"────────────────────\n"
                f"📦 ɴᴀᴍᴇ: <b>{display_name}</b>\n\n"
                f"➔ Please niche diye gaye plans mein se ek select karein:"
            )
            return bot.send_message(message.chat.id, premium_text, reply_markup=markup, parse_mode="HTML")

    # ─── 2. MAIN DASHBOARD (ADMIN + USER) ───
    markup = InlineKeyboardMarkup(row_width=2)
    
    # User Buttons
    btn_dashboard = InlineKeyboardButton("📊 ᴍʏ ᴅᴀsʜʙᴏᴀʀᴅ", callback_data="my_plan")
    btn_support = InlineKeyboardButton("📞 sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{config.CONTACT_USERNAME}")
    markup.add(btn_dashboard, btn_support)

    # Admin Special Buttons
    if user_id == config.ADMIN_ID:
        markup.add(
            InlineKeyboardButton("➕ ᴀᴅᴅ sᴛᴏʀʏ", callback_data="admin_story"),
            InlineKeyboardButton("⚙️ ᴍᴀɴᴀɢᴇ ᴀʟʟ", callback_data="admin_channels")
        )
        markup.add(InlineKeyboardButton("❌ ʀᴇᴍᴏᴠᴇ sᴜʙ", callback_data="admin_remove"))

    if user_id == config.ADMIN_ID:
        title = "⚡ <b>ᴀᴅᴍɪɴ ᴍᴀsᴛᴇʀ ᴘᴀɴᴇʟ</b>"
        desc = "Welcome Back, Boss! Niche diye gaye controls se stories aur channels manage karein."
    else:
        title = "👋 <b>ᴡᴇʟᴄᴏᴍᴇ ᴍᴇᴍʙᴇʀ</b>"
        desc = "Premium access aur plans ke liye dashboard check karein."

    final_text = (
        f"{title}\n"
        f"────────────────────\n"
        f"👤 ʜᴇʟʟᴏ, <b>{message.from_user.first_name}</b>!\n\n"
        f"➔ {desc}"
    )
    bot.send_message(message.chat.id, final_text, reply_markup=markup, parse_mode="HTML")


# ─── 3. CALLBACK HANDLER FOR DASHBOARD ───
@bot.callback_query_handler(func=lambda call: call.data == "my_plan")
def my_plan_callback(call):
    u_id = call.from_user.id
    
    if u_id == config.ADMIN_ID:
        all_subs = list(users_col.find().sort("expiry", 1))
        if not all_subs:
            return bot.send_message(u_id, "📋 Abhi koi active user nahi hai.")

        report = "📋 <b>ᴀʟʟ ᴀᴄᴛɪᴠᴇ sᴜʙs</b>\n────────────────────\n\n"
        for s in all_subs:
            ch = channels_col.find_one({"channel_id": s['channel_id']})
            ch_name = ch['name'] if ch else "Unknown Item"
            expiry_dt = datetime.fromtimestamp(s['expiry'])
            days_left = (expiry_dt - datetime.now()).days
            report += f"👤 <code>{s['user_id']}</code> | 📺 {ch_name} | ⏳ {max(0, days_left)} Days\n"
        bot.send_message(u_id, report, parse_mode="HTML")
    else:
        subs = list(users_col.find({"user_id": u_id}))
        if not subs:
            return bot.send_message(u_id, "❌ Aapka koi active plan nahi hai.")

        res = "👤 <b>ᴍʏ sᴜʙsᴄʀɪᴘᴛɪᴏɴs</b>\n────────────────────\n\n"
        for s in subs:
            ch = channels_col.find_one({"channel_id": s['channel_id']})
            name = ch.get('story_name') or ch.get('name') or "Premium Access"
            expiry = datetime.fromtimestamp(s['expiry']).strftime('%d %b %Y')
            res += f"📺 <b>{name}</b>\n⌛ Valid: <code>{expiry}</code>\n────────────────────\n"
        bot.send_message(u_id, res, parse_mode="HTML")
