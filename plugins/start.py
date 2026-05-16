import uuid
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from utils import bot, get_time_string
from database import channels_col, users_col
from datetime import datetime
import config

# Naye functions jo humne store.py me dale hain unhe import kiya
from plugins.store import get_categories_markup, get_items_by_category_markup, get_store_text

# Global state system ko sync kiya (main.py se connected rahega)
from main import USER_STATES

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    text = message.text.split() if message.text else []

    # Jab bhi user main command par aaye, state ko clear ya home kar do
    USER_STATES[user_id] = {"category": "home", "page": 1}

    # ─── 1. DEEP LINK ENTRY (STORY, CHANNEL & COMBO) ───
    if len(text) > 1:
        param = text[1]
        data = channels_col.find_one({"item_id": param}) or \
               channels_col.find_one({"channel_id": int(param) if param.replace('-','').isdigit() else 0})

        if data:
            markup = InlineKeyboardMarkup(row_width=1)
            db_id = data.get('item_id') or data.get('channel_id')
            
            if data.get('is_combo'):
                markup.add(InlineKeyboardButton(f"💳 🎁 ᴜɴʟᴏᴄᴋ ᴄᴏᴍʙᴏ - ₹{data['price']}", callback_data=f"select_{db_id}_manual"))
                display_name = data['combo_name']
                header = "🎁 <b>ᴘʀᴇᴍɪᴜᴍ sᴘᴇᴄɪᴀʟ ᴄᴏᴍʙᴏ ʙᴜɴᴅʟᴇ</b>"
                desc_text = f"📝 <b>ɪɴᴄʟᴜᴅᴇᴅ sᴛᴏʀɪᴇs:</b>\n<i>{data.get('description', 'Multiple premium stories inside!')}</i>"
            
            elif 'story_name' in data:
                markup.add(InlineKeyboardButton(f"💳 ⚡ ᴜɴʟᴏᴄᴋ sᴛᴏʀʏ - ₹{data['price']}", callback_data=f"select_{db_id}_manual"))
                display_name = data['story_name']
                header = "🔥 <b>ᴘʀᴇᴍɪᴜᴍ ᴇxᴄʟᴜsɪᴠᴇ sᴛᴏʀʏ</b>"
                desc_text = (
                    "🤖 <b>ᴅᴇʟɪᴠᴇʀʏ:</b> <code>ʙᴏᴛ ʟɪɴᴋ ᴀᴄᴄᴇss</code>\n"
                    "⚡ <i>ɪs sᴛᴏʀʏ ᴋᴏ ʙᴜʏ ᴋᴀʀɴᴇ ᴘᴀʀ ᴀᴀᴘᴋᴏ ᴘʀᴇᴍɪᴜᴍ ʙᴏᴛ ᴋɪ ʟɪɴᴋ ᴍɪʟᴇɢɪ.</i>"
                )
            
            else:
                for p_time, p_price in data['plans'].items():
                    markup.add(InlineKeyboardButton(f"👑 {get_time_string(p_time)} Access ➔ ₹{p_price}", callback_data=f"select_{db_id}_{p_time}"))
                display_name = data.get('name', 'Premium Access')
                header = "👑 <b>ᴠɪᴘ ᴄʜᴀɴɴᴇʟ sᴜʙsᴄʀɪᴘᴛɪᴏɴ</b>"
                desc_text = (
                    "📢 <b>ᴅᴇʟɪᴠᴇʀʏ:</b> <code><b>ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ ᴀᴄᴄᴇss</b></code>\n"
                    "⚡ <i>ɪs ᴘʟᴀɴ ᴋᴏ ʙᴜʏ ᴋᴀʀɴᴇ ᴘᴀʀ ᴀᴀᴘᴋᴏ ᴅɪʀᴇᴄᴛ ᴠɪᴘ ᴄʜᴀɴɴᴇʟ ᴋɪ ʟɪɴᴋ ᴍɪʟᴇɢɪ.</i>"
                )

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
    markup.add(InlineKeyboardButton("🛍️ ᴏᴘᴇɴ ᴇxᴄʟᴜsɪᴠᴇ sᴛᴏʀᴇ 🛍️", callback_data="open_store"))
    
    markup.add(
        InlineKeyboardButton("👤 ᴍʏ ᴅᴀsʜʙᴏᴀʀᴅ", callback_data="my_plan"),
        InlineKeyboardButton("📞 🌟 ʟɪᴠᴇ sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{config.CONTACT_USERNAME}")
    )

    if user_id == config.ADMIN_ID:
        markup.add(
            InlineKeyboardButton("➕ ᴀᴅᴅ sᴛᴏʀʏ", callback_data="admin_story"),
            InlineKeyboardButton("📺 ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", callback_data="admin_add"),
            InlineKeyboardButton("🎁 ᴄʀᴇᴀᴛᴇ ᴄᴏᴍʙᴏ", callback_data="admin_combo")
        )
        markup.add(
            InlineKeyboardButton("⚙️ ᴍᴀɴᴀɢᴇ ᴀʟʟ", callback_data="admin_channels"),
            InlineKeyboardButton("❌ ʀᴇᴍᴏᴠᴇ sᴜʙ", callback_data="admin_remove")
        )

    title = "⚡ <b>ᴀᴅᴍɪɴ ᴍᴀsᴛᴇʀ ᴘᴀɴᴇʟ</b>" if user_id == config.ADMIN_ID else "╔════════════════════════════╗\n       ✨ sᴛᴏʀʏ x ᴅᴇᴍᴏ ✨\n╚════════════════════════════╝"
    
    if user_id == config.ADMIN_ID:
        desc = "Welcome Back, Boss! Complete system controls niche diye gaye hain."
    else:
        desc = """ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ᴏғғɪᴄɪᴀʟ sᴛᴏʀʏ sᴇʟʟᴇʀ ʙᴏᴛ!

ᴛʜɪs ʙᴏᴛ sᴇʟʟs ᴀʟʟ ᴛʜᴇ ᴘʀᴇᴍɪᴜᴍ ᴀɴ ʟᴀᴛᴇsᴛ sᴛᴏʀɪᴇs ᴏғ ᴘᴏᴄᴋᴇᴛ ғᴍ ᴀɴᴅ ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ. ʏᴏᴜ ᴄᴀɴ ᴄʜᴇᴄᴋ ᴛʜᴇ ᴅᴇᴍᴏ ғɪʟᴇs ʜᴇʀᴇ ʙᴇғᴏʀᴇ ᴍᴀᴋɪɴɢ ᴀ ᴘᴜʀᴄʜᴀsᴇ!

👑 ʜᴏᴡ ᴛᴏ ʙᴜʏ:
ɪғ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ʙᴜʏ ᴀɴʏ ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ, ᴘʟᴇᴀsᴇ ᴄʜᴇᴄᴋ ᴏᴜʀ sᴛᴏʀᴇ ʙʏ ᴄʟɪᴄᴋɪɴɢ ᴛʜᴇ ᴏᴘᴇɴ ᴇxᴄʟᴜsɪᴠᴇ sᴛᴏʀᴇ ʙᴜᴛᴛᴏɴ ɢɪᴠᴇɴ ʙᴇʟᴏᴡ.

⚡ ɪɴsᴛᴀɴᴛ ᴅᴇᴍᴏ | ᴀᴜᴛᴏ ᴘᴀʏᴍᴇɴᴛ | ᴀᴜᴛᴏ ᴅᴇʟɪᴠᴇʀʏ"""

    if user_id == config.ADMIN_ID:
        final_text = (
            f"{title}\n"
            f"──────────────────────────\n"
            f"👋 Hello, <b>{message.from_user.first_name}</b>!\n\n"
            f"➔ {desc}\n"
            f"──────────────────────────"
        )
    else:
        final_text = (
            f"{title}\n\n"
            f"{desc}\n"
            f"──────────────────────────\n"
            f"👨‍💻 ᴅᴇᴠᴇʟᴏᴘᴇʀ: @HDFILM0900_BOT"
        )
        
    # FIX: Main Dashboard bhejte waqt default normal keyboard enforce karne ke liye ReplyKeyboardRemove pass kiya hai
    bot.send_message(message.chat.id, final_text, reply_markup=markup, parse_mode="HTML")


# ─── 3. TEXT NAVIGATION HANDLERS ───

@bot.message_handler(func=lambda msg: msg.text in [
    "✨ ᴘʀᴀᴛɪʟipi ғᴍ sᴛᴏʀɪᴇs (ʙᴏᴛ ʟɪɴᴋ)", 
    "📢 ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ ᴄʜᴀɴɴᴇʟ (ᴠɪᴘ)", 
    "🎁 SPECIAL COMBO PACKS (BIG SAVE)",
    "🔙 BACK TO CATEGORIES",
    "« BACK TO MENU"
])
def store_navigation_text_handler(message):
    user_id = message.from_user.id
    text = message.text

    # FIX: Back to Menu dabate hi Custom Custom Keyboard destroy hoga aur system normal default keyboard active hoga
    if text == "« BACK TO MENU":
        bot.send_message(message.chat.id, "⬅️ <i>Returning to Main Dashboard...</i>", reply_markup=ReplyKeyboardRemove())
        return start_handler(message)

    if text == "🔙 BACK TO CATEGORIES":
        USER_STATES[user_id] = {"category": "home", "page": 1}
        markup = get_categories_markup()
        return bot.send_message(message.chat.id, get_store_text(), reply_markup=markup, parse_mode="HTML")

    if text == "✨ ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ sᴛᴏʀɪᴇs (ʙᴏᴛ ʟɪɴᴋ)":
        USER_STATES[user_id] = {"category": "story", "page": 1}
        cat_title, c_type = "🎬 <b>sɪɴɢʟᴇ sᴛᴏʀɪᴇs ʟɪsᴛ</b>", "story"
    elif text == "📢 ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ ᴄʜᴀɴɴᴇʟ (ᴠɪᴘ)":
        USER_STATES[user_id] = {"category": "channel", "page": 1}
        cat_title, c_type = "💎 <b>ᴠɪᴘ ᴄʜᴀɴɴᴇʟs ʟɪsᴛ</b>", "channel"
    elif text == "🎁 SPECIAL COMBO PACKS (BIG SAVE)":
        USER_STATES[user_id] = {"category": "combo", "page": 1}
        cat_title, c_type = "🎁 <b>✨ ᴘʀᴇᴍɪᴜᴍ ᴄᴏᴍʙᴏ ᴘᴀᴄᴋs ✨</b>", "combo"

    bot_username = bot.get_me().username
    markup = get_items_by_category_markup(c_type, bot_username, page=1)
    
    final_text = f"{cat_title}\n──────────────────────────\n👇 <i>apni pasand ka item select karke full access lein:</i>"
    bot.send_message(message.chat.id, final_text, reply_markup=markup, parse_mode="HTML")


# ─── 4. PAGINATION HANDLER (NEXT / PREV BUTTON LOGIC) ───
@bot.message_handler(func=lambda msg: msg.text in ["NEXT ›", "‹ PREV"])
def store_pagination_handler(message):
    user_id = message.from_user.id
    state = USER_STATES.get(user_id, {"category": "home", "page": 1})
    
    if state["category"] == "home":
        return

    if message.text == "NEXT ›":
        state["page"] += 1
    else:
        state["page"] -= 1

    USER_STATES[user_id] = state
    bot_username = bot.get_me().username
    markup = get_items_by_category_markup(state["category"], bot_username, page=state["page"])
    
    cat_mapping = {"story": "sɪɴɢʟᴇ sᴛᴏʀɪᴇs", "channel": "ᴠɪᴘ ᴄʜᴀɴɴᴇʟs", "combo": "ᴘʀᴇᴍɪᴜᴍ ᴄᴏᴍʙᴏs"}
    text = f"<b>AVAILABLE STORIES — {cat_mapping.get(state['category'], 'Store')}</b>\n<code>PAGE {state['page']}</code>\n──────────────────────────"
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="HTML")


# ─── 5. STORY/ITEM CLICK ROUTER (KEYBOARD REMOVE + AUTO-DELETE LOADING) ───
@bot.message_handler(func=lambda msg: any(char in msg.text for char in ['[ ₹', '➔ [']))
def item_selection_handler(message):
    user_id = message.from_user.id
    input_text = message.text
    
    clean_name = input_text
    if "." in input_text:
        clean_name = input_text.split(".", 1)[1].split("[")[0].strip()
    elif "💎" in input_text or "🎁" in input_text:
        clean_name = input_text.replace("💎", "").replace("🎁", "").split("➔")[0].strip()

    data = channels_col.find_one({"story_name": clean_name}) or \
           channels_col.find_one({"name": clean_name}) or \
           channels_col.find_one({"combo_name": clean_name})

    if not data:
        return bot.send_message(message.chat.id, "❌ Is item ki details load nahi ho payi. Kripya list se dubara select karein.")

    # FIX: Loading status tracker variable me save kiya taaki isko delete kar sakein
    remove_markup = ReplyKeyboardRemove()
    load_msg = bot.send_message(message.chat.id, "⌛ <i>Loading Details...</i>", reply_markup=remove_markup, parse_mode="HTML")

    inline_markup = InlineKeyboardMarkup(row_width=1)
    db_id = data.get('item_id') or data.get('channel_id')

    if data.get('is_combo'):
        inline_markup.add(InlineKeyboardButton(f"✅ CONFIRM & PAY - ₹{data['price']}", callback_data=f"select_{db_id}_manual"))
        header, desc_text = "🎁 <b>ᴘʀᴇᴍɪᴜᴍ sᴘᴇᴄɪᴀʟ ᴄᴏᴍʙᴏ ʙᴜɴᴅʟᴇ</b>", f"📝 <b>ɪɴᴄʟᴜᴅᴇᴅ sᴛᴏʀɪᴇs:</b>\n<i>{data.get('description', 'Multiple bundles inside!')}</i>"
    elif 'story_name' in data:
        inline_markup.add(InlineKeyboardButton(f"✅ CONFIRM & PAY - ₹{data['price']}", callback_data=f"select_{db_id}_manual"))
        header, desc_text = "🔥 <b>ᴘʀᴇᴍɪᴜᴍ ᴇxᴄʟᴜsɪᴠᴇ sᴛᴏʀʏ</b>", "🤖 <b>ᴅᴇʟɪᴠᴇʀʏ:</b> <code>ʙᴏᴛ ʟɪɴᴋ ᴀᴄᴄᴇss</code>\n⚡ <i>Instant automated file processing link milegi.</i>"
    else:
        for p_time, p_price in data['plans'].items():
            inline_markup.add(InlineKeyboardButton(f"👑 CONFIRM PLAN: {get_time_string(p_time)} - ₹{p_price}", callback_data=f"select_{db_id}_{p_time}"))
        header, desc_text = "👑 <b>ᴠɪᴘ ᴄʜᴀɴɴᴇʟ sᴜʙsᴄʀɪᴘᴛɪᴏɴ</b>", "📢 <b>ᴅᴇʟɪᴠᴇʀʏ:</b> <code>ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ ᴀᴄᴄᴇss</code>"

    if data.get('demo_link'):
        inline_markup.add(InlineKeyboardButton("📺 ᴠɪᴇᴡ ǫᴜᴀʟɪᴛʏ ᴅᴇᴍᴏ (ᴛᴇᴀsᴇʀ)", url=data['demo_link']))

    inline_markup.add(InlineKeyboardButton("⬅️ BACK TO LIST", callback_data=f"return_to_list_{data.get('is_combo', False) or 'story' in data}"))

    details_text = (
        f"{header}\n"
        f"──────────────────────────\n"
        f"📦 <b>ɪᴛᴇᴍ:</b> <code>{data.get('story_name') or data.get('name') or data.get('combo_name')}</code>\n\n"
        f"{desc_text}\n"
        f"──────────────────────────"
    )

    photo_id = data.get('file_id')
    if photo_id:
        bot.send_photo(message.chat.id, photo=photo_id, caption=details_text, reply_markup=inline_markup, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, details_text, reply_markup=inline_markup, parse_mode="HTML")

    # FIX: Main layout client par drop hote hi "Loading Details..." text delete ho jayega
    try: bot.delete_message(message.chat.id, load_msg.message_id)
    except: pass


# ─── CALLBACK HANDLERS ───

@bot.callback_query_handler(func=lambda call: call.data.startswith("return_to_list_"))
def return_to_list_callback(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    state = USER_STATES.get(user_id, {"category": "story", "page": 1})
    
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    
    bot_username = bot.get_me().username
    markup = get_items_by_category_markup(state["category"], bot_username, page=state["page"])
    bot.send_message(call.message.chat.id, "👇 <i>apni pasand ka item select karke full access lein:</i>", reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data == "open_store")
def open_store_callback(call):
    bot.answer_callback_query(call.id)
    markup = get_categories_markup()
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    bot.send_message(call.message.chat.id, get_store_text(), reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data == "back_to_start")
def back_to_start_callback(call):
    bot.answer_callback_query(call.id)
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    start_handler(call.message)


# ─── MY PLAN DASHBOARD (AUTO-DELETE LOADING LOGIC FIXED) ───
@bot.callback_query_handler(func=lambda call: call.data == "my_plan")
def my_plan_callback(call):
    u_id = call.from_user.id
    bot.answer_callback_query(call.id)
    
    remove_keyboard = ReplyKeyboardRemove()
    
    # FIX: Temporary Title loading alert ko tracking object me dala
    load_title_msg = bot.send_message(u_id, "⌛ <i>Opening Dashboard...</i>", reply_markup=remove_keyboard, parse_mode="HTML")
    
    back_markup = InlineKeyboardMarkup(row_width=2)
    back_markup.add(
        InlineKeyboardButton("🛍️ Open Store", callback_data="open_store"),
        InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start")
    )

    if u_id == config.ADMIN_ID:
        all_subs = list(users_col.find().sort("expiry", 1))
        
        # FIX: Admin data processing end hote hi status title message delete hoga
        try: bot.delete_message(u_id, load_title_msg.message_id)
        except: pass

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
        
        # FIX: User subscription load hote hi loading title clear hoga
        try: bot.delete_message(u_id, load_title_msg.message_id)
        except: pass

        if not subs:
            return bot.send_message(u_id, "❌ <b>ɴᴏ ᴀᴄᴛɪᴠᴇ ᴘʟᴀɴ</b>\n\nAapka koi bhi plan active nahi hai. Kripya premium store se subscription khareedein.", reply_markup=back_markup, parse_mode="HTML")

        res = "👤 <b>ᴍʏ ᴘᴇʀsᴏɴᴀʟ ᴅᴀsʜʙᴏᴀʀᴅ</b>\n──────────────────────────\n\n"
        for s in subs:
            ch = channels_col.find_one({"channel_id": s['channel_id']})
            name = ch.get('story_name') or ch.get('name') or ch.get('combo_name', 'Premium Combo') if ch else "Premium Item"
            expiry = datetime.fromtimestamp(s['expiry']).strftime('%d %b %Y | %I:%M %p')
            res += f"🎬 <b>ɪᴛᴇᴍ:</b> {name}\n⌛ <b>ᴇxᴘɪʀʏ ᴅᴀᴛᴇ:</b> <code>{expiry}</code>\n──────────────────────────\n"
        
        bot.send_message(u_id, res, reply_markup=back_markup, parse_mode="HTML")
