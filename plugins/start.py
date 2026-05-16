import uuid
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from utils import bot, get_time_string
from database import channels_col, users_col
from datetime import datetime
import config

# Naye functions jo humne store.py me dale hain unhe import kiya
from plugins.store import get_categories_markup, get_items_by_category_markup, get_store_text

# ─── USER STATE TRACKER (Pagination aur Category Yaad Rakhne Ke Liye) ───
USER_STATES = {}  # Format: {user_id: {"category": "story", "page": 1}}

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
            
            # Deep link se bhi main menu jaane ke liye button ko normal inline rakha
            markup.add(InlineKeyboardButton("🏠 ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))

            premium_text = (
                f"{header}\n"
                f"──────────────────────────\n"
                f"📦 <b>ᴘᴀᴄᴋ ɴᴀᴍᴇ:</b> <code>{display_name}</code>\n\n"
                f"{desc_text}\n"
                f"──────────────────────────"
            )
            
            # Agar purana keyboard screen par hai toh clear bhej sakte hain
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
        desc = """...""" # Aapka purana default text block yahan chalega

    final_text = f"{title}\n\n{desc}" if user_id != config.ADMIN_ID else f"{title}\n──────────────────────────\n👋 Hello..."
    
    # Normal start hone par default text keyboard delete karke bhejte hain taaki clash na ho
    bot.send_message(message.chat.id, final_text, reply_markup=markup, parse_mode="HTML")


# ─── 3. TEXT NAVIGATION HANDLERS (VIDEO LOGIC IMPLEMENTATION) ───

@bot.message_handler(func=lambda msg: msg.text in [
    "🔥 SINGLE STORIES (LATEST)", 
    "👑 VIP CHANNEL ACCESS", 
    "🎁 SPECIAL COMBO PACKS (BIG SAVE)",
    "🔙 BACK TO CATEGORIES",
    "« BACK TO MENU"
])
def store_navigation_text_handler(message):
    user_id = message.from_user.id
    text = message.text

    if text == "« BACK TO MENU":
        return start_handler(message)

    if text == "🔙 BACK TO CATEGORIES":
        USER_STATES[user_id] = {"category": "home", "page": 1}
        markup = get_categories_markup()
        return bot.send_message(message.chat.id, get_store_text(), reply_markup=markup, parse_mode="HTML")

    # State update and setup
    if text == "🔥 SINGLE STORIES (LATEST)":
        USER_STATES[user_id] = {"category": "story", "page": 1}
        cat_title, c_type = "🎬 <b>sɪɴɢʟᴇ sᴛᴏʀɪᴇs ʟɪsᴛ</b>", "story"
    elif text == "👑 VIP CHANNEL ACCESS":
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

    # Page counter increment/decrement
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


# ─── 5. STORY/ITEM CLICK ROUTER (KEYBOARD REMOVE + INLINE BILLING) ───
@bot.message_handler(func=lambda msg: any(char in msg.text for char in ['[ ₹', '➔ [']))
def item_selection_handler(message):
    user_id = message.from_user.id
    input_text = message.text
    
    # Button text se exact content name filter out karna
    clean_name = input_text
    if "." in input_text:
        clean_name = input_text.split(".", 1)[1].split("[")[0].strip()
    elif "💎" in input_text or "🎁" in input_text:
        clean_name = input_text.replace("💎", "").replace("🎁", "").split("➔")[0].strip()

    # Database query based on parsing
    data = channels_col.find_one({"story_name": clean_name}) or \
           channels_col.find_one({"name": clean_name}) or \
           channels_col.find_one({"combo_name": clean_name})

    if not data:
        return bot.send_message(message.chat.id, "❌ Is item ki details load nahi ho payi. Kripya list se dubara select karein.")

    # 🌟 VIDEO TRICK: Custom reply keyboard hatakar device standard default view lana
    remove_markup = ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "⌛ <i>Loading Details...</i>", reply_markup=remove_markup, parse_mode="HTML")

    # Building Dynamic Confirmation Panel
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

    # Direct return path to list view
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


# Inline confirmation parameters and back to dashboard hooks
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


# ─── PURANE CALLBACK HANDLERS (KEEPING AS IS) ───
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

@bot.callback_query_handler(func=lambda call: call.data == "my_plan")
def my_plan_callback(call):
    # ... Aapka purane plan ka logic chalega...
    pass
