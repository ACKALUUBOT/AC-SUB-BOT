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
    user_id = message.from_user.id
    text = message.text.split() if message.text else []

    USER_STATES[user_id] = {"category": "home", "page": 1}

    # Deep Link Handle
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
                desc_text = "🤖 <b>ᴅᴇʟɪᴠᴇʀʏ:</b> <code>ʙᴏᴛ ʟɪɴᴋ ᴀᴄᴄᴇss</code>"
            else:
                for p_time, p_price in data['plans'].items():
                    markup.add(InlineKeyboardButton(f"👑 {get_time_string(p_time)} Access ➔ ₹{p_price}", callback_data=f"select_{db_id}_{p_time}"))
                display_name = data.get('name', 'Premium Access')
                header = "👑 <b>ᴠɪᴘ ᴄʜᴀɴɴᴇʟ sᴜʙsᴄʀɪᴘᴛɪᴏɴ</b>"
                desc_text = "📢 <b>ᴅᴇʟɪᴠᴇʀʏ:</b> <code>ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ ᴀᴄᴄᴇss</code>"

            if data.get('demo_link'):
                markup.add(InlineKeyboardButton("📺 ᴠɪᴇᴡ ǫᴜᴀʟɪᴛʏ ᴅᴇᴍᴏ (ᴛᴇᴀsᴇʀ)", url=data['demo_link']))
            
            markup.add(InlineKeyboardButton("🏠 ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))
            premium_text = f"{header}\n──────────────────────────\n📦 <b>ᴘᴀᴄᴋ ɴᴀᴍᴇ:</b> <code>{display_name}</code>\n\n{desc_text}\n──────────────────────────"
            
            photo_id = data.get('file_id')
            if photo_id:
                return bot.send_photo(message.chat.id, photo=photo_id, caption=premium_text, reply_markup=markup, parse_mode="HTML")
            else:
                return bot.send_message(message.chat.id, premium_text, reply_markup=markup, parse_mode="HTML")

    # MAIN DASHBOARD INLINE
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("🛍️ ᴏᴘᴇɴ ᴇxᴄʟᴜsɪᴠᴇ sᴛᴏʀᴇ 🛍️", callback_data="open_store"))
    markup.add(
        InlineKeyboardButton("👤 ᴍʏ ᴅᴀsʜʙᴏᴀʀᴅ", callback_data="my_plan"),
        InlineKeyboardButton("📞 🌟 ʟɪᴠᴇ sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{config.CONTACT_USERNAME}")
    )

    title = "╔════════════════════════════╗\n       **✨ sᴛᴏʀʏ x ᴅᴇᴍᴏ ✨**\n╚════════════════════════════╝"
    desc = "ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ᴏғғɪᴄɪᴀʟ sᴛᴏʀʏ sᴇʟʟᴇʀ ʙᴏᴛ!\n\n⚡ ɪɴsᴛᴀɴᴛ ᴅᴇᴍᴏ | ᴀᴜᴛᴏ ᴘᴀʏᴍᴇɴᴛ | ᴀᴜᴛᴏ ᴅᴇʟɪᴠᴇʀʏ"
    bot.send_message(message.chat.id, f"{title}\n\n{desc}", reply_markup=markup, parse_mode="HTML")


# ─── 3. TEXT NAVIGATION HANDLERS ───
@bot.message_handler(func=lambda msg: msg.text in [
    "✨ ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ sᴛᴏʀɪᴇs (ʙᴏᴛ ʟɪɴᴋ)", 
    "📢 ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ ᴄʜᴀɴɴᴇʟ (ᴠɪᴘ)", 
    "🎁 SPECIAL COMBO PACKS (BIG SAVE)",
    "🔙 BACK TO CATEGORIES",
    "« BACK TO MENU",
    "❌ CLOSE STORE",
    "🚫 STORE IS EMPTY"
])
def store_navigation_text_handler(message):
    user_id = message.from_user.id
    text = message.text

    # Empty store button handling
    if text == "🚫 STORE IS EMPTY":
        return bot.send_message(message.chat.id, "⚠️ **Is category mein abhi koi stories nahi hain.** Kripya dusri category check karein.")

    # Close button clicks: Niche ka keyboard remove karke normal standard keyboard active karega
    if text == "❌ CLOSE STORE":
        return bot.send_message(
            message.chat.id, 
            "✖️ **sᴛᴏʀᴇ ᴄʟᴏsᴇᴅ!**\n\nNormal keyboard active ho gaya hai.", 
            reply_markup=ReplyKeyboardRemove(), 
            parse_mode="HTML"
        )

    if text == "« BACK TO MENU":
        bot.send_message(message.chat.id, "⬅️ _Returning to Main Dashboard..._", reply_markup=ReplyKeyboardRemove())
        return start_handler(message)

    if text == "🔙 BACK TO CATEGORIES":
        USER_STATES[user_id] = {"category": "home", "page": 1}
        return bot.send_message(message.chat.id, get_store_text(), reply_markup=get_categories_markup(), parse_mode="HTML")

    # Set categories based on user choice
    if text == "✨ ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ sᴛᴏʀɪᴇs (ʙᴏᴛ ʟɪɴᴋ)":
        USER_STATES[user_id] = {"category": "story", "page": 1}
        cat_title, c_type = "🎬 **sɪɴɢʟᴇ sᴛᴏʀɪᴇs ʟɪsᴛ**", "story"
    elif text == "📢 ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ ᴄʜᴀɴɴᴇʟ (ᴠɪᴘ)":
        USER_STATES[user_id] = {"category": "channel", "page": 1}
        cat_title, c_type = "💎 **ᴠɪᴘ ᴄʜᴀɴɴᴇʟs ʟɪsᴛ**", "channel"
    elif text == "🎁 SPECIAL COMBO PACKS (BIG SAVE)":
        USER_STATES[user_id] = {"category": "combo", "page": 1}
        cat_title, c_type = "🎁 **✨ ᴘʀᴇᴍɪᴜᴍ ᴄᴏᴍʙᴏ ᴘᴀᴄᴋs ✨**", "combo"

    # 🌟 MAIN FIX: Niche hamesha BADA KEYBOARD bhejega!
    markup = get_items_by_category_markup(c_type, bot.get_me().username, page=1)
    bot.send_message(message.chat.id, f"{cat_title}\n──────────────────────────\n👇 _apni pasand ka item select karke full access lein:_", reply_markup=markup, parse_mode="HTML")


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
    cat_mapping = {"story": "sɪɴɢʟᴇ sᴛᴏʀɪᴇs", "channel": "ᴠɪᴘ ᴄʜᴀɴɴᴇʟs", "combo": "ᴘʀᴇᴍɪᴜᴍ ᴄᴏᴍʙᴏs"}
    bot.send_message(message.chat.id, f"**AVAILABLE STORIES — {cat_mapping.get(state['category'], 'Store')}**\n`PAGE {state['page']}`\n──────────────────────────", reply_markup=markup, parse_mode="HTML")


# ─── 5. STORY CLICK ROUTER ───
@bot.message_handler(func=lambda msg: any(char in msg.text for char in ['[ ₹', '➔ [']))
def item_selection_handler(message):
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
        return bot.send_message(message.chat.id, "❌ Is item ki details load nahi ho payi.")

    load_msg = bot.send_message(message.chat.id, "⌛ _Loading Details..._", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    inline_markup = InlineKeyboardMarkup(row_width=1)
    db_id = data.get('item_id') or data.get('channel_id')

    if data.get('is_combo'):
        inline_markup.add(InlineKeyboardButton(f"✅ CONFIRM & PAY - ₹{data['price']}", callback_data=f"select_{db_id}_manual"))
        header, desc_text = "🎁 <b>ᴘʀᴇᴍɪᴜᴍ sᴘᴇᴄɪᴀʟ ᴄᴏᴍʙᴏ ʙᴜɴᴅʟᴇ</b>", f"📝 <b>ɪɴᴄʟᴜᴅᴇᴅ sᴛᴏʀɪᴇs:</b>\n<i>{data.get('description', 'Multiple bundles inside!')}</i>"
    elif 'story_name' in data:
        inline_markup.add(InlineKeyboardButton(f"✅ CONFIRM & PAY - ₹{data['price']}", callback_data=f"select_{db_id}_manual"))
        header, desc_text = "🔥 <b>ᴘʀᴇᴍɪᴜᴍ ᴇxᴄʟᴜsɪᴠᴇ sᴛᴏʀʏ</b>", "🤖 <b>ᴅᴇʟɪᴠᴇʀʏ:</b> <code>ʙᴏᴛ ʟɪɴᴋ ᴀᴄᴄᴇss</code>"
    else:
        for p_time, p_price in data['plans'].items():
            inline_markup.add(InlineKeyboardButton(f"✅ CONFIRM & PAY: {get_time_string(p_time)} - ₹{p_price}", callback_data=f"select_{db_id}_{p_time}"))
        header, desc_text = "👑 <b>ᴠɪᴘ ᴄʜᴀɴɴᴇʟ sᴜʙsᴄʀɪᴘᴛɪᴏɴ</b>", "📢 <b>ᴅᴇʟɪᴠᴇʀʏ:</b> <code>ᴄʜᴀɴɴᴇʟ ʟɪɴᴋ ᴀᴄᴄᴇss</code>"

    if data.get('demo_link'):
        inline_markup.add(InlineKeyboardButton("📺 ᴠɪᴇᴡ ǫᴜᴀʟɪᴛʏ ᴅᴇᴍᴏ (ᴛᴇᴀsᴇʀ)", url=data['demo_link']))
    inline_markup.add(InlineKeyboardButton("⬅️ BACK TO LIST", callback_data=f"return_to_list_{data.get('is_combo', False) or 'story' in data}"))

    details_text = f"{header}\n──────────────────────────\n📦 <b>ɪᴛᴇᴍ:</b> <code>{data.get('story_name') or data.get('name') or data.get('combo_name')}</code>\n\n{desc_text}\n──────────────────────────"
    
    photo_id = data.get('file_id')
    if photo_id:
        bot.send_photo(message.chat.id, photo=photo_id, caption=details_text, reply_markup=inline_markup, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, details_text, reply_markup=inline_markup, parse_mode="HTML")

    try: bot.delete_message(message.chat.id, load_msg.message_id)
    except: pass


# ─── CALLBACK HANDLERS ───
@bot.callback_query_handler(func=lambda call: call.data.startswith("return_to_list_"))
def return_to_list_callback(call):
    bot.answer_callback_query(call.id)
    state = USER_STATES.get(call.from_user.id, {"category": "story", "page": 1})
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    markup = get_items_by_category_markup(state["category"], bot.get_me().username, page=state["page"])
    bot.send_message(call.message.chat.id, "👇 _apni pasand ka item select karke full access lein:_", reply_markup=markup, parse_mode="HTML")

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
    load_title_msg = bot.send_message(u_id, "⌛ _Opening Dashboard..._", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    
    back_markup = InlineKeyboardMarkup(row_width=2)
    back_markup.add(InlineKeyboardButton("🛍️ Open Store", callback_data="open_store"), InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))

    subs = list(users_col.find({"user_id": u_id}))
    try: bot.delete_message(u_id, load_title_msg.message_id)
    except: pass

    if not subs:
        return bot.send_message(u_id, "❌ **ɴᴏ ᴀᴄᴛɪᴠᴇ ᴘʟᴀɴ**\n\nAapka koi bhi plan active nahi hai.", reply_markup=back_markup, parse_mode="HTML")

    res = "👤 **ᴍʏ ᴘᴇʀsᴏɴᴀʟ ᴅᴀsʜʙᴏᴀʀᴅ**\n──────────────────────────\n\n"
    for s in subs:
        ch = channels_col.find_one({"channel_id": s['channel_id']})
        name = ch.get('story_name') or ch.get('name') or ch.get('combo_name', 'Premium Combo') if ch else "Premium Item"
        expiry = datetime.fromtimestamp(s['expiry']).strftime('%d %b %Y | %I:%M %p')
        res += f"🎬 **ɪᴛᴇᴍ:** {name}\n⌛ **<b>ᴇxᴘɪʀʏ ᴅᴀᴛᴇ:</b>** `{expiry}`\n──────────────────────────\n"
    bot.send_message(u_id, res, reply_markup=back_markup, parse_mode="HTML")
