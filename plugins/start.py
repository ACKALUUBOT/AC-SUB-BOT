import uuid
from datetime import datetime
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, WebAppInfo # <-- WebAppInfo import kiya
import config
from utils import bot, get_time_string
from database import channels_col, users_col
from plugins.store import get_categories_markup, get_items_by_category_markup, get_store_text
from main import USER_STATES

@bot.message_handler(commands=['start'])
def start_handler(message):
    if hasattr(message, 'from_user') and message.from_user:
        user_id = message.from_user.id
    else:
        user_id = message.chat.id

    if hasattr(message, 'chat'):
        chat_id = message.chat.id
    else:
        chat_id = user_id

    USER_STATES[user_id] = {"category": "home", "page": 1}

    # ─── 1. DEEP LINK PARAMETER CHECK (3 SEPARATE FLOWS) ───
    text = message.text.split() if hasattr(message, 'text') and message.text else []
    if len(text) > 1:
        param = text[1]
        data = channels_col.find_one({"item_id": param}) or \
               channels_col.find_one({"channel_id": int(param) if param.replace('-','').isdigit() else 0})

        if data:
            markup = InlineKeyboardMarkup(row_width=1)
            db_id = data.get('item_id') or data.get('channel_id')
            
            # [FLOW A] Combo Pack
            if data.get('is_combo'):
                markup.add(InlineKeyboardButton(f"💳 🎁 ᴜɴʟᴏᴄᴋ ᴄᴏᴍʙᴏ - ₹{data['price']}", callback_data=f"select_{db_id}_manual"))
                display_name = data['combo_name']
                header = "🎁 <b>ᴘʀᴇᴍɪᴜᴍ sᴘᴇᴄɪᴀʟ ᴄᴏᴍʙᴏ ʙᴜɴᴅʟᴇ</b>"
                desc_text = f"📝 <b>ɪɴᴄʟᴜᴅᴇᴅ sᴛᴏʀɪᴇs:</b>\n<i>{data.get('description', 'Multiple premium stories inside!')}</i>"
            
            # [FLOW B] Forwarded Channel (/add flow)
            elif 'channel_id' in data and not data.get('story_name'):
                if data.get('plans') and isinstance(data['plans'], dict):
                    for p_time, p_price in data['plans'].items():
                        markup.add(InlineKeyboardButton(f"💳 {get_time_string(p_time)} - ₹{p_price}", callback_data=f"select_{db_id}_{p_time}"))
                else:
                    markup.add(InlineKeyboardButton(f"✅ CONFIRM & PAY - ₹{data.get('price', '49')}", callback_data=f"select_{db_id}_manual"))
                display_name = data.get('name', 'Premium Access')
                header = "💎 <b>ᴘʀᴇᴍɪᴜᴍ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀɴɴᴇʟ</b>"
                desc_text = "🤖 <b>ᴅᴇʟɪᴠᴇʀʏ:</b> <code><b>ᴄʜᴀɴɴᴇʟ ɪɴᴠɪᴛᴇ ʟɪɴᴋ (𝟷-ᴛɪᴍᴇ ᴜsᴇ)</b></code>\nℹ️ <i>Isme join hone ke liye direct temporary invite link milega.</i>"
            
            # [FLOW C] Direct Story (/add_story flow)
            else:
                markup.add(InlineKeyboardButton(f"💳 🎧 ᴜɴʟᴏᴄᴋ sᴛᴏʀʏ - ₹{data.get('price', '49')}", callback_data=f"select_{db_id}_manual"))
                display_name = data.get('story_name')
                header = f"🔥 <b>ᴘʀᴇᴍɪᴜᴍ ᴇxᴄʟᴜsɪᴠᴇ sᴛᴏʀʏ ({data.get('source', 'audio')})</b>"
                desc_text = "🤖 <b>ᴅᴇʟɪᴠᴇʀʏ:</b> <code><b>ɪsᴛᴀɴᴛ ʙᴏᴛ ʟɪɴᴋ ᴀᴄᴄᴇss</b></code>\nℹ️ <i>Isme payment ke baad direct external link ya redirection button milega.</i>"

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
    
    # 🌟 MINI APP BUTTON (Apna Mini app URL config.py me set karein ya direct string pass karein)
    miniapp_url = getattr(config, 'MINIAPP_URL', 'https://your-miniapp-url.com')
    markup.add(InlineKeyboardButton("🚀 ᴏᴘᴇɴ ᴍɪɴɪ ᴀᴘᴘ 🚀", web_app=WebAppInfo(url=miniapp_url)))
    
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

    title = "╔════════════════════════════╗\n       ✨ sᴛᴏʀʏ x ᴅᴇᴍᴏ ✨\n╚════════════════════════════╝"
    desc = """ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ᴏғғɪᴄɪᴀʟ sᴛᴏʀʏ sᴇʟʟᴇʀ ʙᴏᴛ!

ᴛʜɪs ʙᴏᴛ sᴇʟʟs ᴀʟʟ ᴛʜᴇ ᴘʀᴇᴍɪᴜᴍ ᴀɴᴅ ʟᴀᴛᴇsᴛ sᴛᴏʀɪᴇs ᴏғ ᴘᴏᴄᴋᴇᴛ ғᴍ ᴀɴᴅ ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ. ʏᴏᴜ ᴄʜᴇᴄᴋ ᴛʜᴇ ᴅᴇᴍᴏ ғɪʟᴇs ʜᴇʀᴇ ʙᴇғᴏʀᴇ ᴍᴀᴋɪɴɢ ᴀ ᴘᴜʀᴄʜᴀsᴇ!

⚡ ɪɴsᴛᴀɴᴛ ᴅᴇᴍᴏ | ᴀᴜᴛᴏ ᴘᴀʏᴍᴇɴᴛ | ᴀᴜᴛᴏ ᴅᴇʟɪᴠᴇʀʏ"""

    bot.send_message(chat_id, f"{title}\n\n{desc}", reply_markup=markup, parse_mode="HTML")


# ─── 3. TEXT NAVIGATION HANDLERS (FIXED & REAL-TIME) ───
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
        return bot.send_message(message.chat.id, "<blockquote>⚠️ ❌ NO STORY AVAILABLE RIGHT NOW.</blockquote>", parse_mode="HTML")

    if text == "❌ CLOSE STORE" or text == "« BACK TO MENU":
        USER_STATES[user_id] = {"category": "home", "page": 1}
        bot.send_message(message.chat.id, "⬅️ <i>Returning to Dashboard Panel...</i>", reply_markup=ReplyKeyboardRemove())
        return start_handler(message)

    if text == "🔙 BACK TO CATEGORIES":
        USER_STATES[user_id] = {"category": "home", "page": 1}
        return bot.send_message(message.chat.id, get_store_text(), reply_markup=get_categories_markup(), parse_mode="HTML")

    # Dynamic Routing strictly matching with database and store file layout
    if text == "✨ ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ sᴛᴏʀɪᴇs":
        USER_STATES[user_id] = {"category": "pratilipi", "page": 1}
        cat_title, c_type = "🎬 <b>ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ sᴛᴏʀɪᴇs</b>", "pratilipi"
    elif text == "🔥 ᴘᴏᴄᴋᴇᴛ ғᴍ sᴛᴏʀɪᴇs":
        USER_STATES[user_id] = {"category": "pocket", "page": 1}
        cat_title, c_type = "🎧 <b>ᴘᴏᴄᴋᴇᴛ ғᴍ sᴛᴏʀɪᴇs</b>", "pocket"
    elif text == "🎁 SPECIAL COMBO PACKS (BIG SAVE)":
        USER_STATES[user_id] = {"category": "combo", "page": 1}
        cat_title, c_type = "🎁 <b>✨ ᴘʀᴇᴍɪᴜᴍ ᴄᴏᴍʙᴏ ᴘᴀᴄᴋs ✨</b>", "combo"

    # Real-time database items rendering
    markup = get_items_by_category_markup(c_type, bot.get_me().username, page=1)
    bot.send_message(
        message.chat.id, 
        f"{cat_title}\n──────────────────────────\n👇 <i>apni pasand ka item select karke full access lein:</i>", 
        reply_markup=markup, 
        parse_mode="HTML"
    )


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
    bot.send_message(
        message.chat.id, 
        f"<b>AVAILABLE STORIES — {state['category'].upper()}</b>\n`PAGE {state['page']}`\n──────────────────────────", 
        reply_markup=markup, 
        parse_mode="HTML"
    )


# ─── 5. STORY CLICK ROUTER (3 SEPARATE STRICT FLOWS MATCHING INDEX LOGIC) ───
@bot.message_handler(func=lambda msg: any(char in msg.text for char in ['[ ₹', '➔ [']))
def item_selection_handler(message):
    input_text = message.text
    clean_name = input_text
    
    # Strictly handle serial numbers like "1. Story Name [ ₹49 ]"
    if "." in input_text:
        try:
            clean_name = input_text.split(".", 1)[1].split("[")[0].strip()
        except:
            clean_name = input_text.split("[")[0].strip()
    elif "🎁" in input_text:
        clean_name = input_text.replace("🎁", "").split("➔")[0].strip()

    state = USER_STATES.get(message.from_user.id, {"category": "pratilipi"})
    
    if state["category"] == "combo":
        data = channels_col.find_one({"combo_name": clean_name})
    elif state["category"] == "pocket":
        data = channels_col.find_one({"story_name": clean_name, "source": "pocket"})
    elif state["category"] == "pratilipi":
        data = channels_col.find_one({"story_name": clean_name, "source": "pratilipi"})
    else:
        data = channels_col.find_one({"name": clean_name}) or channels_col.find_one({"story_name": clean_name})

    if not data:
        return bot.send_message(message.chat.id, "❌ Is item ki details load nahi ho payi.")

    load_msg = bot.send_message(message.chat.id, "⌛ <i>Loading Details...</i>", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    inline_markup = InlineKeyboardMarkup(row_width=1)
    db_id = data.get('item_id') or data.get('channel_id')

    # ─── 🎁 FLOW 1: COMBO PACK ───
    if data.get('is_combo'):
        inline_markup.add(InlineKeyboardButton(f"✅ CONFIRM & PAY COMBO - ₹{data['price']}", callback_data=f"select_{db_id}_manual"))
        header = "🎁 <b>ᴘʀᴇᴍɪᴜᴍ sᴘᴇᴄɪᴀʟ ᴄᴏᴍʙᴏ ʙᴜɴᴅʟᴇ</b>"
        item_label = data.get('combo_name')
        desc_text = f"📝 <b>ɪɴᴄʟᴜᴅᴇᴅ sᴛᴏʀɪᴇs:</b>\n<i>{data.get('description', 'Multiple bundles inside!')}</i>"
        
    # ─── 📢 FLOW 2: FORWARDED CHANNEL (/add Flow) ───
    elif 'channel_id' in data and not data.get('story_name'):
        if data.get('plans') and isinstance(data['plans'], dict):
            for p_time, p_price in data['plans'].items():
                inline_markup.add(InlineKeyboardButton(f"💳 {get_time_string(p_time)} - ₹{p_price}", callback_data=f"select_{db_id}_{p_time}"))
        else:
            inline_markup.add(InlineKeyboardButton(f"✅ CONFIRM & PAY - ₹{data.get('price', '49')}", callback_data=f"select_{db_id}_manual"))
            
        header = "📢 <b>ᴘʀᴇᴍɪᴜᴍ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀɴɴᴇʟ</b>"
        item_label = data.get('name', 'VIP Channel')
        desc_text = "🤖 <b>ᴅᴇʟɪᴠᴇʀʏ:</b> <code>ᴄʜᴀɴɴᴇʟ ɪɴᴠɪᴛᴇ ʟɪɴᴋ (𝟷-ᴛɪᴍᴇ ᴜsᴇ)</code>\nℹ️ <i>Is pack me aapko private channel join karne ka temporary link milega.</i>"

    # ─── 🔥 FLOW 3: MANUAL STORY (/add_story Flow) ───
    else:
        inline_markup.add(InlineKeyboardButton(f"💳 UNLOCK PREMIUM STORY - ₹{data.get('price', '49')}", callback_data=f"select_{db_id}_manual"))
        header = f"🔥 <b>ᴘʀᴇᴍɪᴜᴍ ᴇxᴄʟᴜsɪᴠᴇ sᴛᴏʀʏ ({data.get('source', 'audio')})</b>"
        item_label = data.get('story_name')
        desc_text = "🤖 <b>ᴅᴇʟɪᴠᴇʀʏ:</b> <code>ɪɴsᴛᴀɴᴛ ʙᴏᴛ ʟɪɴᴋ ᴀᴄᴄᴇss</code>\nℹ️ <i>Is pack me aapko direct bot file redirection button milega.</i>"

    if data.get('demo_link'):
        inline_markup.add(InlineKeyboardButton("📺 ᴠɪᴇᴡ ǫᴜᴀʟɪᴛʏ ᴅᴇᴍᴏ (ᴛᴇᴀsᴇʀ)", url=data['demo_link']))
    
    inline_markup.add(InlineKeyboardButton("⬅️ BACK TO LIST", callback_data="return_to_list_True"))

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
            ch_name = ch.get('story_name') or ch.get('combo_name', 'Deleted Pack') if ch else 'Unknown Pack'
            days_left = (datetime.fromtimestamp(s['expiry']) - datetime.now()).days
            report += f"👤 <code>{s['user_id']}</code>\n➔ 📦 {ch_name}\n➔ ⏳ Left: <b>{max(0, days_left)} Days</b>\n─────────────────\n"
        bot.send_message(u_id, report, reply_markup=back_markup, parse_mode="HTML")
    else:
        subs = list(users_col.find({"user_id": u_id}))
        try: bot.delete_message(u_id, load_title_msg.message_id)
        except: pass

        if not subs:
            return bot.send_message(u_id, "❌ <b><b>ɴᴏ ᴀᴄᴛɪᴠᴇ ᴘʟᴀɴ</b></b>\n\nAapka filhal koi active plan nahi chal raha hai.", reply_markup=back_markup, parse_mode="HTML")

        res = "👤 <b>ᴍʏ ᴘᴇʀsᴏɴᴀʟ ᴅᴀsʜʙᴏᴀʀᴅ</b>\n──────────────────────────\n\n"
        for s in subs:
            ch = channels_col.find_one({"channel_id": s['channel_id']})
            name = ch.get('story_name') or ch.get('combo_name', 'Premium Bundle') if ch else 'Premium Access'
            expiry = datetime.fromtimestamp(s['expiry']).strftime('%d %b %Y | %I:%M %p')
            res += f"🎬 <b>ɪᴛᴇᴍ:</b> {name}\n⌛ <b>ᴇxᴘɪʀʏ:</b> <code>{expiry}</code>\n──────────────────────────\n"
        bot.send_message(u_id, res, reply_markup=back_markup, parse_mode="HTML")
