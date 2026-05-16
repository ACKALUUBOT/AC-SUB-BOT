import uuid
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot, get_time_string
from database import channels_col, users_col
from datetime import datetime
import config

from plugins.store import get_categories_markup, get_items_by_category_markup, get_store_text

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    text = message.text.split() if message.text else []

    # ─── 1. DEEP LINK ENTRY (STORY, CHANNEL & COMBO) ───
    if len(text) > 1:
        param = text[1]
        data = channels_col.find_one({"item_id": param}) or \
               channels_col.find_one({"channel_id": int(param) if param.replace('-','').isdigit() else 0})

        if data:
            markup = InlineKeyboardMarkup(row_width=1)
            db_id = data.get('item_id') or data.get('channel_id')
            
            # CONDITION 1: COMBO PACK BUYING
            if data.get('is_combo'):
                markup.add(InlineKeyboardButton(f"💳 🎁 ᴜɴʟᴏᴄᴋ ᴄᴏᴍʙᴏ - ₹{data['price']}", callback_data=f"select_{db_id}_manual"))
                display_name = data['combo_name']
                header = "🎁 <b>ᴘʀᴇᴍɪᴜᴍ sᴘᴇᴄɪᴀʟ ᴄᴏᴍʙᴏ ʙᴜɴᴅʟᴇ</b>"
                desc_text = f"📝 <b>ɪɴᴄʟᴜᴅᴇᴅ sᴛᴏʀɪᴇs:</b>\n<i>{data.get('description', 'Multiple premium stories inside!')}</i>"
            
            # CONDITION 2: SINGLE STORY
            elif 'story_name' in data:
                markup.add(InlineKeyboardButton(f"💳 ⚡ ᴜɴʟᴏᴄᴋ sᴛᴏʀʏ - ₹{data['price']}", callback_data=f"select_{db_id}_manual"))
                display_name = data['story_name']
                header = "🔥 <b>ᴘʀᴇᴍɪᴜᴍ ᴇxᴄʟᴜsɪᴠᴇ sᴛᴏʀʏ</b>"
                desc_text = "⚡ <i>Instant access paane ke liye niche se payment karein.</i>"
            
            # CONDITION 3: VIP CHANNEL
            else:
                for p_time, p_price in data['plans'].items():
                    markup.add(InlineKeyboardButton(f"👑 {get_time_string(p_time)} Access ➔ ₹{p_price}", callback_data=f"select_{db_id}_{p_time}"))
                display_name = data.get('name', 'Premium Access')
                header = "👑 <b>ᴠɪᴘ ᴄʜᴀɴɴᴇʟ sᴜʙsᴄʀɪᴘᴛɪᴏɴ</b>"
                desc_text = "⚡ <i>Instant access paane ke liye niche se apna plan select karke payment karein.</i>"

            if data.get('demo_link'):
                markup.add(InlineKeyboardButton("📺 ᴠɪᴇᴡ ǫᴜᴀʟɪᴛʏ ᴅᴇᴍᴏ (ᴛᴇᴀsᴇʀ)", url=data['demo_link']))
            
            markup.add(InlineKeyboardButton("🏠 ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))

            premium_text = (
                f"{header}\n"
                f"──────────────────────────\n"
                f"📦 <b>ᴘᴀᴄᴋ ɴᴀᴍᴇ:</b> <code>{display_name}</code>\n\n"
                f"{desc_text}\n"
                f"──────────────────────────"
            )
            
            photo_id = data.get('file_id')
            if photo_id:
                return bot.send_photo(message.chat.id, photo=photo_id, caption=premium_text, reply_markup=markup, parse_mode="HTML")
            else:
                return bot.send_message(message.chat.id, premium_text, reply_markup=markup, parse_mode="HTML")

    # ─── 2. MAIN DASHBOARD ───
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("🛍️ ᴇxᴄʟᴜsɪᴠᴇ sᴛᴏʀʏ sᴛᴏʀｅ 🛍️", callback_data="open_store"))
    
    markup.add(
        InlineKeyboardButton("👤 ᴍʏ ᴅᴀsʜʙᴏᴀʀᴅ", callback_data="my_plan"),
        InlineKeyboardButton("📞 🌟 ʟɪᴠᴇ sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{config.CONTACT_USERNAME}")
    )

    if user_id == config.ADMIN_ID:
        markup.add(
            InlineKeyboardButton("➕ ᴀᴅᴅ sᴛᴏʀʏ", callback_data="admin_story"),
            InlineKeyboardButton("📺 ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", callback_data="admin_add"),
            InlineKeyboardButton("🎁 ᴄʀᴇᴀᴛᴇ ᴄᴏᴍʙᴏ", callback_data="admin_combo") # NEW ADMIN BUTTON
        )
        markup.add(
            InlineKeyboardButton("⚙️ ᴍᴀɴᴀɢᴇ ᴀʟʟ", callback_data="admin_channels"),
            InlineKeyboardButton("❌ ʀᴇᴍᴏᴠᴇ sᴜʙ", callback_data="admin_remove")
        )

    title = "⚡ <b>ᴀᴅᴍɪɴ ᴍᴀsᴛᴇʀ ᴘᴀɴᴇʟ</b>" if user_id == config.ADMIN_ID else "✨ <b>ᴍᴇᴍʙᴇʀ ᴍᴀɪɴ ᴍᴇɴᴜ</b>"
    desc = "Welcome Back, Boss! Complete system controls niche diye gaye hain." if user_id == config.ADMIN_ID else "👋 ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ᴏғғɪᴄɪᴀʟ sᴛᴏʀʏ sᴇʟʟᴇʀ ʙᴏᴛ! ᴛʜɪs ʙᴏᴛ sᴇʟʟs ᴀʟʟ ᴛʜᴇ ᴘʀᴇᴍɪᴜᴍ ᴀɴᴅ ʟᴀᴛᴇsᴛ sᴛᴏʀɪᴇs ᴏғ ᴘᴏᴄᴋᴇᴛ ғᴍ ᴀɴᴅ ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ. ʏᴏᴜ ᴄᴀɴ ᴄʜᴇᴄᴋ ᴛʜᴇ ᴅᴇᴍᴏ ғɪʟᴇs ʜᴇʀᴇ ʙᴇғᴏʀᴇ ᴍᴀᴋɪɴɢ ᴀ ᴘᴜʀᴄʜᴀsᴇ!  👑 ʜᴏᴡ ᴛᴏ ʙᴜʏ:
ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʙᴜʏ ᴀɴʏ ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ, ᴘʟᴇᴀsᴇ ᴄʜᴇᴄᴋ ᴏᴜʀ sᴛᴏʀᴇ ʙʏ ᴄʟɪᴄᴋɪɴɢ ᴛʜᴇ ᴏᴘᴇɴ ᴇxᴄʟᴜsɪᴠᴇ sᴛᴏʀᴇ ʙᴜᴛᴛᴏɴ ɢɪᴠᴇɴ ʙᴇʟᴏᴡ. ⚡ ɪɴsᴛᴀɴᴛ ᴅᴇᴍᴏ | ᴀᴜᴛᴏ ᴘᴀʏᴍᴇɴᴛ | ᴀᴜᴛᴏ ᴅᴇʟɪᴠᴇʀʏ. 👨‍💻 ᴅᴇᴠᴇʟᴏᴘᴇʀ: @HDFILM0900_BOT"

    final_text = (
        f"{title}\n"
        f"──────────────────────────\n"
        f"👋 Hello, <b>{message.from_user.first_name}</b>!\n\n"
        f"➔ {desc}\n"
        f"──────────────────────────"
    )
    bot.send_message(message.chat.id, final_text, reply_markup=markup, parse_mode="HTML")


# ─── 3. CALLBACK HANDLERS ───

@bot.callback_query_handler(func=lambda call: call.data == "open_store")
def open_store_callback(call):
    bot.answer_callback_query(call.id)
    markup = get_categories_markup()
    store_text = get_store_text()
    
    if call.message.content_type == 'photo':
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, store_text, reply_markup=markup, parse_mode="HTML")
    else:
        bot.edit_message_text(store_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data.startswith("view_cat_"))
def view_category_updates(call):
    bot.answer_callback_query(call.id)
    category_type = call.data.split("_")[2] # 'story', 'channel' ya 'combo'
    
    bot_username = bot.get_me().username
    markup = get_items_by_category_markup(category_type, bot_username)
    
    if category_type == "story": cat_title = "🎬 <b>sɪɴɢʟᴇ sᴛᴏʀɪᴇs ʟɪsᴛ</b>"
    elif category_type == "channel": cat_title = "💎 <b>ᴠɪᴘ ᴄʜᴀɴɴᴇʟs ʟɪsᴛ</b>"
    else: cat_title = "🎁 <b>✨ ᴘʀᴇᴍɪᴜᴍ ᴄᴏᴍʙᴏ ᴘᴀᴄᴋs ✨</b>"
    
    text = (
        f"{cat_title}\n"
        f"──────────────────────────\n"
        f"👇 <i>Apni pasand ka item select karke full access lein:</i>"
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data == "back_to_start")
def back_to_start_callback(call):
    bot.answer_callback_query(call.id)
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    start_handler(call.message)


@bot.callback_query_handler(func=lambda call: call.data == "my_plan")
def my_plan_callback(call):
    u_id = call.from_user.id
    bot.answer_callback_query(call.id)
    
    back_markup = InlineKeyboardMarkup().add(InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))

    if u_id == config.ADMIN_ID:
        all_subs = list(users_col.find().sort("expiry", 1))
        if not all_subs:
            return bot.send_message(u_id, "📋 Abhi database mein koi active user nahi hai.", reply_markup=back_markup)

        report = "📋 <b>ᴀʟʟ ᴀᴄᴛɪᴠᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴs</b>\n──────────────────────────\n\n"
        for s in all_subs:
            ch = channels_col.find_one({"channel_id": s['channel_id']})
            ch_name = ch.get('story_name') or ch.get('name') or ch.get('combo_name', 'Unknown') if ch else "Unknown Item"
            days_left = (datetime.fromtimestamp(s['expiry']) - datetime.now()).days
            report += f"👤 <code>{s['user_id']}</code>\n➔ 📺 {ch_name}\n➔ ⏳ Time left: <b>{max(0, days_left)} Days</b>\n─────────────────\n"
        bot.send_message(u_id, report, reply_markup=back_markup, parse_mode="HTML")
    else:
        subs = list(users_col.find({"user_id": u_id}))
        if not subs:
            return bot.send_message(u_id, "❌ <b>ɴᴏ ᴀᴄᴛɪᴠᴇ ᴘʟᴀɴ</b>\n\nAapka koi bhi plan active nahi hai. Kripya premium store se subscription khareedein.", reply_markup=back_markup, parse_mode="HTML")

        res = "👤 <b>ᴍʏ ᴘᴇʀsᴏɴᴀʟ ᴅᴀsʜʙᴏᴀʀᴅ</b>\n──────────────────────────\n\n"
        for s in subs:
            ch = channels_col.find_one({"channel_id": s['channel_id']})
            name = ch.get('story_name') or ch.get('name') or ch.get('combo_name', 'Premium Combo') if ch else "Premium Item"
            expiry = datetime.fromtimestamp(s['expiry']).strftime('%d %b %Y | %I:%M %p')
            res += f"🎬 <b>ɪᴛᴇᴍ:</b> {name}\n⌛ <b>ᴇxᴘɪʀʏ ᴅᴀᴛᴇ:</b> <code>{expiry}</code>\n──────────────────────────\n"
        bot.send_message(u_id, res, reply_markup=back_markup, parse_mode="HTML")


@bot.message_handler(commands=['delete'])
def delete_item_handler(message):
    if message.from_user.id != config.ADMIN_ID:
        return bot.reply_to(message, "❌ Aapke paas is command ka access nahi hai.")

    text = message.text.split()
    if len(text) < 2:
        return bot.reply_to(message, "💡 <b>Usage:</b> <code>/delete ID</code>\n\n(ID aapko store link ya manage list mein mil jayegi)")

    target_id = text[1]

    result = channels_col.delete_one({
        "$or": [
            {"item_id": target_id},
            {"channel_id": int(target_id) if target_id.replace('-', '').isdigit() else 0}
        ]
    })

    if result.deleted_count > 0:
        bot.reply_to(message, f"✅ <b>sᴜᴄᴄᴇss:</b> Item <code>{target_id}</code> database se permanently delete kar diya gaya hai.")
    else:
        bot.reply_to(message, f"❌ <b>ᴇʀʀᴏʀ:</b> Database mein <code>{target_id}</code> naam ki koi entry nahi mili.")
