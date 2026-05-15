from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot, get_time_string
from database import channels_col, users_col
from datetime import datetime
import config

# ─── HELPER FUNCTION FOR STORE ───
def get_store_markup():
    # Database se sirf wo data nikalna jisme 'story_name' hai
    all_stories = list(channels_col.find({"story_name": {"$exists": True}}))
    markup = InlineKeyboardMarkup(row_width=1)
    
    if not all_stories:
        markup.add(InlineKeyboardButton("🚫 No Stories Available", callback_data="none"))
    else:
        for story in all_stories:
            # Button text: Story ka naam aur price
            btn_text = f"📖 {story['story_name']} — ₹{story['price']}"
            # Deep link: click karte hi payment panel khulega
            url = f"https://t.me/{bot.get_me().username}?start={story['item_id']}"
            markup.add(InlineKeyboardButton(btn_text, url=url))
            
    markup.add(InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))
    return markup

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    text = message.text.split()

    # ─── 1. DEEP LINK ENTRY (STORY & CHANNEL) ───
    if len(text) > 1:
        param = text[1]
        data = channels_col.find_one({"item_id": param}) or \
               channels_col.find_one({"channel_id": int(param) if param.replace('-','').isdigit() else 0})

        if data:
            markup = InlineKeyboardMarkup(row_width=1)
            db_id = data.get('item_id') or data.get('channel_id')
            
            if 'story_name' in data:
                markup.add(InlineKeyboardButton(f"💳 ʙᴜʏ ɴᴏᴡ - ₹{data['price']}", callback_data=f"select_{db_id}_manual"))
                display_name = data['story_name']
                header = "🎬 <b>ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ</b>"
            else:
                for p_time, p_price in data['plans'].items():
                    markup.add(InlineKeyboardButton(f"💳 {get_time_string(p_time)} - ₹{p_price}", callback_data=f"select_{db_id}_{p_time}"))
                display_name = data['name']
                header = "💎 <b>ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss</b>"

            if data.get('demo_link'):
                markup.add(InlineKeyboardButton("📺 ᴠɪᴇᴡ ǫᴜᴀʟɪᴛʏ ᴅᴇᴍᴏ", url=data['demo_link']))
            
            # Back to home button
            markup.add(InlineKeyboardButton("🏠 ʙᴀᴄᴋ ᴛᴏ ʜᴏᴍᴇ", callback_data="back_to_start"))

            premium_text = (
                f"{header}\n"
                f"────────────────────\n"
                f"📦 ɴᴀᴍᴇ: <b>{display_name}</b>\n\n"
                f"➔ Please niche diye gaye plans mein se ek select karein:"
            )
            return bot.send_message(message.chat.id, premium_text, reply_markup=markup, parse_mode="HTML")

    # ─── 2. MAIN DASHBOARD ───
    markup = InlineKeyboardMarkup(row_width=2)
    
    # Store Button (Main highlight)
    markup.add(InlineKeyboardButton("✨ ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀᴇ (ᴄʜᴇᴄᴋ sᴛᴏʀɪᴇs) ✨", callback_data="open_store"))
    
    markup.add(
        InlineKeyboardButton("📊 ᴍʏ ᴅᴀsʜʙᴏᴀʀᴅ", callback_data="my_plan"),
        InlineKeyboardButton("📞 sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{config.CONTACT_USERNAME}")
    )

    if user_id == config.ADMIN_ID:
        markup.add(
            InlineKeyboardButton("➕ ᴀᴅᴅ sᴛᴏʀʏ", callback_data="admin_story"),
            InlineKeyboardButton("📺 ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", callback_data="admin_add")
        )
        markup.add(
            InlineKeyboardButton("⚙️ ᴍᴀɴᴀɢᴇ ᴀʟʟ", callback_data="admin_channels"),
            InlineKeyboardButton("❌ ʀᴇᴍᴏᴠᴇ sᴜʙ", callback_data="admin_remove")
        )

    title = "⚡ <b>ᴀᴅᴍɪɴ ᴍᴀsᴛᴇʀ ᴘᴀɴᴇʟ</b>" if user_id == config.ADMIN_ID else "👋 <b>ᴡᴇʟᴄᴏᴍᴇ ᴍᴇᴍʙᴇʀ</b>"
    desc = "Welcome Back, Boss! Controls niche hain." if user_id == config.ADMIN_ID else "Premium access aur plans ke liye dashboard check karein."

    final_text = (
        f"{title}\n"
        f"────────────────────\n"
        f"👤 ʜᴇʟʟᴏ, <b>{message.from_user.first_name}</b>!\n\n"
        f"➔ {desc}"
    )
    bot.send_message(message.chat.id, final_text, reply_markup=markup, parse_mode="HTML")

# ─── 3. CALLBACK HANDLERS ───

@bot.callback_query_handler(func=lambda call: call.data == "open_store")
def open_store_callback(call):
    bot.answer_callback_query(call.id)
    markup = get_store_markup()
    store_text = (
        "✨ <b>ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ sᴛᴏʀᴇ</b> ✨\n"
        "────────────────────\n"
        "Niche hamari sabhi exclusive stories ki list hai.\n\n"
        "➔ <b>Process:</b> Story select karein aur apna access payein."
    )
    bot.edit_message_text(store_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_start")
def back_to_start_callback(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    # Restart the dashboard
    start_handler(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "my_plan")
def my_plan_callback(call):
    u_id = call.from_user.id
    bot.answer_callback_query(call.id)
    
    if u_id == config.ADMIN_ID:
        all_subs = list(users_col.find().sort("expiry", 1))
        if not all_subs:
            return bot.send_message(u_id, "📋 Abhi koi active user nahi hai.")

        report = "📋 <b>ᴀʟʟ ᴀᴄᴛɪᴠᴇ sᴜʙs</b>\n────────────────────\n\n"
        for s in all_subs:
            ch = channels_col.find_one({"channel_id": s['channel_id']})
            ch_name = ch.get('story_name') or ch.get('name') if ch else "Unknown"
            days_left = (datetime.fromtimestamp(s['expiry']) - datetime.now()).days
            report += f"👤 <code>{s['user_id']}</code> | 📺 {ch_name} | ⏳ {max(0, days_left)} Days\n"
        bot.send_message(u_id, report, parse_mode="HTML")
    else:
        subs = list(users_col.find({"user_id": u_id}))
        if not subs:
            return bot.send_message(u_id, "❌ Aapka koi active plan nahi hai.")

        res = "👤 <b>ᴍʏ sᴜʙsᴄʀɪᴘᴛɪᴏɴs</b>\n────────────────────\n\n"
        for s in subs:
            ch = channels_col.find_one({"channel_id": s['channel_id']})
            name = ch.get('story_name') or ch.get('name') if ch else "Premium Item"
            expiry = datetime.fromtimestamp(s['expiry']).strftime('%d %b %Y')
            res += f"📺 <b>{name}</b>\n⌛ Valid: <code>{expiry}</code>\n────────────────────\n"
        bot.send_message(u_id, res, parse_mode="HTML")
