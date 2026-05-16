import uuid
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from utils import bot, get_time_string
from database import channels_col, users_col
from datetime import datetime
import config

from plugins.store import get_categories_markup, get_items_by_category_markup, get_store_text
from main import USER_STATES

@bot.message_handler(commands=['start'])
def start_handler(message):
    # Callback query aur normal message dono ke liye ID extract karne ka solid system
    if hasattr(message, 'from_user') and message.from_user:
        user_id = message.from_user.id
    else:
        user_id = message.chat.id

    if hasattr(message, 'chat'):
        chat_id = message.chat.id
    else:
        chat_id = user_id

    USER_STATES[user_id] = {"category": "home", "page": 1}

    # ─── 1. DEEP LINK PARAMETER CHECK ───
    text = message.text.split() if hasattr(message, 'text') and message.text else []
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
            else:
                markup.add(InlineKeyboardButton(f"💳 ⚡ ᴜɴʟᴏᴄᴋ sᴛᴏʀʏ - ₹{data['price']}", callback_data=f"select_{db_id}_manual"))
                display_name = data.get('story_name', 'Premium Story')
                header = "🔥 <b>ᴘʀᴇᴍɪᴜᴍ ᴇxᴄʟᴜsɪᴠᴇ sᴛᴏʀʏ</b>"
                desc_text = "🤖 <b>ᴅᴇʟɪᴠᴇʀʏ:</b> <code>ʙᴏᴛ ʟɪɴᴋ ᴀᴄᴄᴇss</code>"

            if data.get('demo_link'):
                markup.add(InlineKeyboardButton("📺 ᴠɪᴇᴡ ǫᴜᴀʟɪᴛʏ ᴅᴇᴍᴏ (ᴛᴇᴀsᴇʀ)", url=data['demo_link']))
            
            markup.add(InlineKeyboardButton("🏠 ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))
            premium_text = f"{header}\n──────────────────────────\n📦 <b>ᴘᴀᴄᴋ ɴᴀᴍᴇ:</b> <code>{display_name}</code>\n\n{desc_text}\n──────────────────────────"
            
            photo_id = data.get('file_id')
            if photo_id:
                return bot.send_photo(chat_id, photo=photo_id, caption=premium_text, reply_markup=markup, parse_mode="HTML")
            else:
                return bot.send_message(chat_id, premium_text, reply_markup=markup, parse_mode="HTML")

    # ─── 2. MAIN DASHBOARD (ADMIN VS USER SPLIT) ───
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("🛍️ ᴏᴘᴇɴ ᴇxᴄʟᴜsɪᴠᴇ sᴛᴏʀェ 🛍️", callback_data="open_store"))
    
    markup.add(
        InlineKeyboardButton("👤 ᴍʏ ᴅᴀsʜʙᴏᴀʀᴅ", callback_data="my_plan"),
        InlineKeyboardButton("📞 🌟 ʟɪᴠᴇ sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{config.CONTACT_USERNAME}")
    )

    # 🔥 ADMIN EXCLUSIVE DASHBOARD PANEL 🔥
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

    title = "╔════════════════════════════╗\n       ✨ sᴛᴏʀʏ x ᴅᴇᴍᴏ ✨\n╚════════════════════════════╝"
    desc = """ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ᴏғғɪᴄɪᴀʟ sᴛᴏʀʏ sᴇʟʟᴇʀ ʙᴏᴛ!

ᴛʜɪs ʙᴏᴛ sᴇʟʟs ᴀʟʟ ᴛʜᴇ ᴘʀᴇᴍɪᴜᴍ ᴀɴ ʟᴀᴛᴇsᴛ sᴛᴏʀɪᴇs ᴏғ ᴘᴏᴄᴋᴇᴛ ғᴍ ᴀɴᴅ ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ. ʏᴏᴜ ᴄᴀɴ ᴄʜᴇᴄᴋ ᴛʜᴇ ᴅᴇᴍᴏ ғɪʟᴇs ʜᴇʀᴇ ʙᴇғᴏʀᴇ ᴍᴀᴋɪɴɢ ᴀ ᴘᴜʀᴄʜᴀsᴇ!

⚡ ɪɴsᴛᴀɴᴛ ᴅᴇᴍᴏ | ᴀᴜᴛᴏ ᴘᴀʏᴍᴇɴᴛ | ᴀᴜᴛᴏ ᴅᴇʟɪᴠᴇʀʏ"""

    bot.send_message(chat_id, f"{title}\n\n{desc}", reply_markup=markup, parse_mode="HTML")


# ─── 3. TEXT NAVIGATION HANDLERS (UPDATED ROUTES) ───
@bot.message_handler(func=lambda msg: msg.text in [
    "✨ ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ sᴛᴏʀɪᴇs", 
    "🔥 ᴘᴏᴄᴋᴇᴛ ғᴍ sᴛᴏʀɪᴇs", 
    "🎁 SPECIAL COMBO PACKS (BIG SAVE)",
    "🔙 BACK TO CATEGORIES",
    "« BACK TO MENU",
    "❌ CLOSE STORE",
    "🚫 STORE IS EMPTY"
])
def store_navigation_text_handler(message):
    user_id = message.from_user.id
    text = message.text

    if text == "🚫 STORE IS EMPTY":
        return bot.send_message(message.chat.id, "<blockquote>⚠️ ❌ NO STORY AVAILABLE.</blockquote>", parse_mode="HTML")

    if text == "❌ CLOSE STORE":
        return bot.send_message(
            message.chat.id, 
            "✖️ <b>sᴛᴏʀᴇ ᴄʟᴏsᴇᴅ!</b>", 
            reply_markup=ReplyKeyboardRemove(), 
            parse_mode="HTML"
        )

    if text == "« BACK TO MENU":
        bot.send_message(message.chat.id, "⬅️ <i>Returning to Dashboard Panel...</i>", reply_markup=ReplyKeyboardRemove())
        return start_handler(message)

    if text == "🔙 BACK TO CATEGORIES":
        USER_STATES[user_id] = {"category": "home", "page": 1}
        return bot.send_message(message.chat.id, get_store_text(), reply_markup=get_categories_markup(), parse_mode="HTML")

    # 🌟 NEW CATEGORY ROUTING LOGIC
    if text == "✨ ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ sᴛᴏʀɪᴇs":
        USER_STATES[user_id] = {"category": "pratilipi", "page": 1}
        cat_title, c_type = "🎬 <b>ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ sᴛᴏʀɪᴇs</b>", "pratilipi"
    elif text == "🔥 ᴘᴏᴄᴋᴇᴛ ғᴍ sᴛᴏʀɪᴇs":
        USER_STATES[user_id] = {"category": "pocket", "page": 1}
        cat_title, c_type = "🎧 <b>ᴘᴏᴄᴋᴇᴛ ғᴍ sᴛᴏʀɪᴇs</b>", "pocket"
    elif text == "🎁 SPECIAL COMBO PACKS (BIG SAVE)":
        USER_STATES[user_id] = {"category": "combo", "page": 1}
        cat_title, c_type = "🎁 <b>✨ ᴘʀᴇᴍɪᴜᴍ ᴄᴏᴍʙᴏ ᴘᴀᴄᴋs ✨</b>", "combo"

    markup = get_items_by_category_markup(c_type, bot.get_me().username, page=1)
    bot.send_message(message.chat.id, f"{cat_title}\n──────────────────────────\n👇 <i>apni pasand ka item select karke full access lein:</i>", reply_markup=markup, parse_mode="HTML")


# ─── 4. PAGINATION HANDLER ───
@bot.message_handler(func=lambda msg: msg.text in ["NEXT ›", "‹ PREV"])
def store_pagination_handler(message):
    user_id = message.from_user.id
    state = USER_STATES.get(user_id, {"category": "home", "page": 1})
    if state["category"] == "home": return

    if message.text == "NEXT ›": state["page"] += 1
    else: state["page"] -= 1

    USER_STATES[user_id] = state
    markup = get_items_by_category_markup(state["category"], bot.get_me().username, page=state["page"])
    bot.send_message(message.chat.id, f"<b>AVAILABLE STORIES — {state['category'].upper()}</b>\n`PAGE {state['page']}`\n──────────────────────────", reply_markup=markup, parse_mode="HTML")


# ─── 5. STORY CLICK ROUTER ───
@bot.message_handler(func=lambda msg: any(char in msg.text for char in ['[ ₹', '➔ [']))
def item_selection_handler(message):
    input_text = message.text
    clean_name = input_text
    
    # Text clean karne ka filter
    if "." in input_text:
        clean_name = input_text.split(".", 1)[1].split("[")[0].strip()
    elif "🎁" in input_text:
        clean_name = input_text.replace("🎁", "").split("➔")[0].strip()

    state = USER_STATES.get(message.from_user.id, {"category": "pratilipi"})
    
    # Current category state ke hisab se data select hoga
    if state["category"] == "combo":
        data = channels_col.find_one({"combo_name": clean_name})
    else:
        data = channels_col.find_one({"story_name": clean_name})

    if not data:
        return bot.send_message(message.chat.id, "❌ Is item ki details load nahi ho payi.")

    load_msg = bot.send_message(message.chat.id, "⌛ <i>Loading Details...</i>", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    inline_markup = InlineKeyboardMarkup(row_width=1)
    db_id = data.get('item_id') or data.get('channel_id')

    inline_markup.add(InlineKeyboardButton(f"✅ CONFIRM & PAY - ₹{data['price']}", callback_data=f"select_{db_id}_manual"))

    if data.get('demo_link'):
        inline_markup.add(InlineKeyboardButton("📺 ᴠɪᴇᴡ ǫᴜᴀʟɪᴛʏ ᴅᴇᴍᴏ (ᴛᴇᴀsᴇʀ)", url=data['demo_link']))
    
    inline_markup.add(InlineKeyboardButton("⬅️ BACK TO LIST", callback_data="return_to_list_True"))

    if data.get('is_combo'):
        header, item_label = "🎁 <b>ᴘʀᴇᴍɪᴜᴍ sᴘᴇᴄɪᴀʟ ᴄᴏᴍʙᴏ ʙᴜɴᴅʟᴇ</b>", data.get('combo_name')
        desc_text = f"📝 <b>ɪɴᴄʟᴜᴅᴇᴅ sᴛᴏʀɪᴇs:</b>\n<i>{data.get('description', 'Multiple bundles inside!')}</i>"
    else:
        header, item_label = "🔥 <b>ᴘʀᴇᴍɪᴜᴍ ᴇxᴄʟᴜsɪᴠᴇ sᴛᴏʀʏ</b>", data.get('story_name')
        desc_text = "🤖 <b>ᴅᴇʟɪᴠᴇʀʏ:</b> <code>ʙᴏᴛ ʟɪɴᴋ ᴀᴄᴄᴇss</code>"

    details_text = f"{header}\n──────────────────────────\n📦 <b>ɪᴛᴇᴍ:</b> <code>{item_label}</code>\n\n{desc_text}\n──────────────────────────"
    
    photo_id = data.get('file_id')
    if photo_id:
        bot.send_photo(message.chat.id, photo=photo_id, caption=details_text, reply_markup=inline_markup, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, details_text, reply_markup=inline_markup, parse_mode="HTML")

    try: bot.delete_message(message.chat.id, load_msg.message_id)
    except: pass


# ─── 6. CALLBACK HANDLERS ───
@bot.callback_query_handler(func=lambda call: call.data.startswith("return_to_list_"))
def return_to_list_callback(call):
    bot.answer_callback_query(call.id)
    state = USER_STATES.get(call.from_user.id, {"category": "pratilipi", "page": 1})
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    markup = get_items_by_category_markup(state["category"], bot.get_me().username, page=state["page"])
    bot.send_message(call.message.chat.id, "👇 <i>apni pasand ka item select karke full access lein:</i>", reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "open_store")
def open_store_callback(call):
    bot.answer_callback_query(call.id)
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    bot.send_message(call.message.chat.id, get_store_text(), reply_markup=get_categories_markup(), parse_mode="HTML")

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
    load_title_msg = bot.send_message(u_id, "⌛ <i>Opening Dashboard...</i>", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    
    back_markup = InlineKeyboardMarkup(row_width=2)
    back_markup.add(InlineKeyboardButton("🛍️ Open Store", callback_data="open_store"), InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))

    if u_id == config.ADMIN_ID:
        all_subs = list(users_col.find().sort("expiry", 1))
        try: bot.delete_message(u_id, load_title_msg.message_id)
        except: pass

        if not all_subs:
            return bot.send_message(u_id, "📋 **Database clear hai. Koi active premium member nahi mila.**", reply_markup=back_markup, parse_mode="HTML")

        report = "📋 <b>ᴀʟʟ ᴀᴄᴛɪᴠᴇ sᴜʙsᴄʀɪᴘᴛɪᴏɴs (ᴀᴅᴍɪɴ)</b>\n──────────────────────────\n\n"
        for s in all_subs:
            ch = channels_col.find_one({"channel_id": s['channel_id']})
            ch_name = ch.get('story_name') or ch.get('combo_name', 'Deleted Pack')
            days_left = (datetime.fromtimestamp(s['expiry']) - datetime.now()).days
            report += f"👤 <code>{s['user_id']}</code>\n➔ 📦 {ch_name}\n➔ ⏳ Left: <b>{max(0, days_left)} Days</b>\n─────────────────\n"
        bot.send_message(u_id, report, reply_markup=back_markup, parse_mode="HTML")
    else:
        subs = list(users_col.find({"user_id": u_id}))
        try: bot.delete_message(u_id, load_title_msg.message_id)
        except: pass

        if not subs:
            return bot.send_message(u_id, "❌ <b>ɴᴏ ᴀᴄᴛɪᴠᴇ ᴘʟᴀɴ</b>\n\nAapka filhal koi active plan nahi chal raha hai.", reply_markup=back_markup, parse_mode="HTML")

        res = "👤 <b>ᴍʏ ᴘᴇʀsᴏɴᴀʟ ᴅᴀsʜʙᴏᴀʀᴅ</b>\n──────────────────────────\n\n"
        for s in subs:
            ch = channels_col.find_one({"channel_id": s['channel_id']})
            name = ch.get('story_name') or ch.get('combo_name', 'Premium Bundle')
            expiry = datetime.fromtimestamp(s['expiry']).strftime('%d %b %Y | %I:%M %p')
            res += f"🎬 <b>ɪᴛᴇᴍ:</b> {name}\n⌛ <b>ᴇxᴘɪʀʏ:</b> <code>{expiry}</code>\n──────────────────────────\n"
        bot.send_message(u_id, res, reply_markup=back_markup, parse_mode="HTML")
