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
        try:
            item_id = text[1]
            # Pehle check karte hain ki ye Story hai ya Channel
            data = channels_col.find_one({"item_id": item_id}) or channels_col.find_one({"channel_id": int(item_id) if item_id.isdigit() else 0})
            
            if data:
                markup = InlineKeyboardMarkup(row_width=1)
                
                # Agar Story hai (Aapka naya vision)
                if 'story_name' in data:
                    markup.add(InlineKeyboardButton(f"💳 ʙᴜʏ ɴᴏᴡ - ₹{data['price']}", callback_data=f"select_{item_id}_manual"))
                    display_name = data['story_name']
                    header = "🎬 <b>ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ</b>"
                # Agar purana Channel system hai
                else:
                    for p_time, p_price in data['plans'].items():
                        markup.add(InlineKeyboardButton(f"💳 {get_time_string(p_time)} - ₹{p_price}", callback_data=f"select_{item_id}_{p_time}"))
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
                bot.send_message(message.chat.id, premium_text, reply_markup=markup, parse_mode="HTML")
                return
        except Exception as e:
            print(f"Start Error: {e}")
            pass

    # ─── 2. MERGED MASTER MENU (ADMIN + USER) ───
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


# ─── 3. ADMIN BUTTONS BRIDGE ───
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_button_bridge(call):
    if call.from_user.id != config.ADMIN_ID:
        return bot.answer_callback_query(call.id, "Unauthorized!", show_alert=True)
        
    action = call.data.split('_')[1]
    
    if action == "story":
        bot.send_message(call.message.chat.id, "🎬 <b>sᴛᴏʀʏ ᴍᴏᴅᴇ:</b>\nNayi story add karne ke liye type karein: <code>/add_story</code>", parse_mode="HTML")
    elif action == "channels":
        bot.send_message(call.message.chat.id, "⚙️ <b>ᴍᴀɴᴀɢᴇᴍᴇɴᴛ:</b>\nChannels ke liye <code>/channels</code> type karein.", parse_mode="HTML")
    elif action == "remove":
        bot.send_message(call.message.chat.id, "❌ <b>ʀᴇᴍᴏᴠᴇ:</b>\nSubscription hatane ke liye <code>/remove</code> use karein.", parse_mode="HTML")
    
    bot.answer_callback_query(call.id)


# ─── 4. MASTER DASHBOARD ───
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
            ch_name = ch['name'] if ch else "Unknown"
            days_left = (datetime.fromtimestamp(s['expiry']) - datetime.now()).days
            report += f"👤 <code>{s['user_id']}</code> | 📺 {ch_name} | ⏳ {days_left} Days\n"
        bot.send_message(u_id, report, parse_mode="HTML")
    else:
        subs = list(users_col.find({"user_id": u_id}))
        if not subs:
            return bot.send_message(u_id, "❌ Aapka koi active plan nahi hai.")

        res = "👤 <b>ᴍʏ sᴜʙsᴄʀɪᴘᴛɪᴏɴs</b>\n────────────────────\n\n"
        for s in subs:
            ch = channels_col.find_one({"channel_id": s['channel_id']})
            name = ch['name'] if ch else "Premium Item"
            expiry = datetime.fromtimestamp(s['expiry']).strftime('%d %b %Y')
            res += f"📺 <b>{name}</b>\n⌛ Valid: <code>{expiry}</code>\n────────────────────\n"
        bot.send_message(u_id, res, parse_mode="HTML")
