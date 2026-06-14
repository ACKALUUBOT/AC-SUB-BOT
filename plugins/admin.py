import uuid
import re
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot
from database import channels_col, users_col
import config

# Global storage temporary data hold karne ke liye jab tak setup complete na ho
pending_setups = {}

def get_chat_id(message):
    if hasattr(message, 'chat') and message.chat:
        return message.chat.id
    if hasattr(message, 'message') and message.message and message.message.chat:
        return message.message.chat.id
    return None

# URL validation ke liye Strict Regex
def is_valid_url(url):
    pattern = re.compile(
        r'^https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
    )
    return bool(pattern.match(url))


# ==========================================
# --- 1. REMOVE USER (SECURE DELETE) ---
# ==========================================
@bot.message_handler(commands=['remove'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def remove_user_start(message):
    chat_id = get_chat_id(message)
    if not chat_id: return
    
    msg = bot.send_message(
        chat_id, 
        "👤 <b>User ko remove karein:</b>\n\nUs user ki <b>ID</b> bhejein jiska access khatam karna hai (ya /cancel):", 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_remove_user)

def process_remove_user(message):
    if message.text == '/cancel':
        return bot.send_message(message.chat.id, "❌ Action cancelled.")
    try:
        u_id = int(message.text)
        result = users_col.delete_many({"user_id": u_id})
        if result.deleted_count > 0:
            bot.send_message(message.chat.id, f"✅ <b>Success!</b>\nUser <code>{u_id}</code> ka access hata diya gaya.", parse_mode="HTML")
            try: 
                bot.send_message(u_id, "⚠️ <b>Access Revoked:</b> Aapka subscription khatam kar diya gaya hai.")
            except Exception: 
                pass
        else:
            bot.send_message(message.chat.id, "❓ Is ID ka koi active subscription nahi mila.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid ID! Sirf numbers bhejein.")


# =====================================================================
# ─── 2. MANAGE CHANNELS & STORIES (PREMIUM INTERFACE & REMOVE) ───
# =====================================================================
@bot.message_handler(commands=['channels'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def list_channels(message):
    chat_id = get_chat_id(message)
    if not chat_id: return
    show_inventory(chat_id)

def show_inventory(chat_id):
    cursor = channels_col.find()
    markup = InlineKeyboardMarkup(row_width=1)
    for ch in cursor:
        name = ch.get('name') or "Unnamed Item"
        # Type status emoji bundle ya channel dikhane ke liye
        icon = "🎁 Combo:" if ch.get('is_combo') else "📺"
        markup.add(InlineKeyboardButton(f"{icon} {name}", callback_data=f"manage_{ch['item_id']}"))
        
    # Bottom par ek Danger Zone button pure database ko ek sath wipeout karne ke liye
    markup.add(InlineKeyboardButton("💥 DELETE ALL STORIES 💥", callback_data="conf_del_all_start"))

    if markup.keyboard and len(markup.keyboard) > 1: # 1 because of Delete All button
        bot.send_message(chat_id, "📑 <b>ʏᴏᴜʀ  ɪɴᴠᴇɴᴛᴏʀʏ:</b>\nNiche kisi bhi item ko manage ya remove karein:", reply_markup=markup, parse_mode="HTML")
    else:
        bot.send_message(chat_id, "❌ Abhi inventory khali hai. /add ya /add_combo use karein.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('manage_'))
def manage_ch(call):
    if call.from_user.id != config.ADMIN_ID:
        return bot.answer_callback_query(call.id, "Unauthorized!")
        
    item_id = call.data.split('_')[1]
    ch_data = channels_col.find_one({"item_id": item_id})
    if not ch_data: 
        return bot.answer_callback_query(call.id, "Data not found!")

    bot_user = bot.get_me().username
    link = f"https://t.me/{bot_user}?start={item_id}"
    name = ch_data.get('name') or "Unnamed Item"
    source_platform = ch_data.get('source', 'none').upper() 
    validity_info = ch_data.get('validity', 'N/A')
    price_info = ch_data.get('price', '0')
    description = ch_data.get('description', 'Koi description nahi dala gaya hai.')
    
    text = (
        f"⚙️ <b>sᴇᴛᴛɪɴɢs:</b> {name}\n"
        f"────────────────────\n"
        f"📂 <b>Source:</b> <code>{source_platform}</code>\n"
        f"⏱️ <b>Validity:</b> {validity_info} Din\n"
        f"💰 <b>Price:</b> ₹{price_info}\n"
        f"📺 <b>Demo:</b> {ch_data.get('demo_link', 'None')}\n\n"
        f"📝 <b>Description / Included Stories:</b>\n<i>{description}</i>\n\n"
        f"🔗 <b>sʜᴀʀᴇ ʟɪɴᴋ:</b>\n<code>{link}</code>\n"
        f"────────────────────"
    )
    
    # Premium Inline Control Panel Buttons
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🗑️ Remove This", callback_data=f"single_del_{item_id}"),
        InlineKeyboardButton("🔙 Back to List", callback_data="back_to_inventory")
    )

    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception: pass

    photo_id = ch_data.get('file_id')
    if photo_id:
        bot.send_photo(call.message.chat.id, photo=photo_id, caption=text, reply_markup=markup, parse_mode="HTML")
    else:
        bot.send_message(call.message.chat.id, text=text, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_inventory")
def back_inventory_callback(call):
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    show_inventory(call.message.chat.id)

# --- SINGLE ITEM REMOVE PROPER FLOW ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('single_del_'))
def single_delete_confirm(call):
    item_id = call.data.split('_')[2]
    ch_data = channels_col.find_one({"item_id": item_id})
    if not ch_data:
        return bot.answer_callback_query(call.id, "Item nahi mila!")

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Haan, Delete Karein", callback_data=f"execute_del_{item_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"manage_{item_id}")
    )
    
    bot.send_message(
        call.message.chat.id,
        f"⚠️ <b>⚠️ DOUBLE CONFIRMATION ⚠️</b>\n\n"
        f"Kya aap sach me <b>{ch_data.get('name')}</b> ko database se permanent remove karna chahte hain?",
        reply_markup=markup,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('execute_del_'))
def single_delete_execute(call):
    item_id = call.data.split('_')[2]
    result = channels_col.delete_one({"item_id": item_id})
    
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    
    if result.deleted_count > 0:
        bot.send_message(call.message.chat.id, "✅ Item database se successfully remove kar diya gaya hai.")
    else:
        bot.send_message(call.message.chat.id, "❌ Error! Item delete nahi ho paya ya pehle hi hataya ja chuka hai.")
    show_inventory(call.message.chat.id)

# --- COMPLETE WIPE OUT (DELETE ALL) FLOW WITH SECURITY CODE ---
@bot.callback_query_handler(func=lambda call: call.data == "conf_del_all_start")
def delete_all_warning(call):
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🛑 HAAN, WIPE OUT KAREIN", callback_data="prompt_security_code"),
        InlineKeyboardButton("❌ CANCEL", callback_data="back_to_inventory")
    )
    bot.send_message(
        call.message.chat.id,
        "🚨 <b>CRITICAL WARNING !!</b> 🚨\n\n"
        "Aap database ki <b>SAARI STORIES AUR COMBOS</b> ek sath udaane ja rahe hain.\n"
        "Yeh action reverse nahi kiya ja sakta. Kya aap confirm karte hain?",
        reply_markup=markup,
        parse_mode="HTML"
    )

@bot.callback_query_handler(func=lambda call: call.data == "prompt_security_code")
def delete_all_security_step(call):
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    
    msg = bot.send_message(
        call.message.chat.id,
        "🔒 <b>SECURITY VERIFICATION:</b>\n\n"
        "Puri tarah clear karne ke liye niche likha hua code capital letters me reply karein:\n"
        "<code>CONFIRM DELETE ALL</code>\n\n"
        "➔ Ya cancel karne ke liye /cancel likhein:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, execute_all_wipeout)

def execute_all_wipeout(message):
    if message.text == "/cancel":
        return bot.send_message(message.chat.id, "❌ Wipeout process cancel kar di gayi.")
    
    if message.text.strip() == "CONFIRM DELETE ALL":
        result = channels_col.delete_many({})
        bot.send_message(
            message.chat.id, 
            f"💥 <b>DATABASE WIPED OUT!</b>\n\nInventory se saari <code>{result.deleted_count}</code> items ko permanently uda diya gaya hai.",
            parse_mode="HTML"
        )
    else:
        bot.send_message(message.chat.id, "🚫 <b>Security Code Match Nahi Hua!</b> Operation block kar diya gaya hai.")


# =====================================================================
# ─── 3. FORWARD CHANNEL STORY FLOW (/add) WITH VALIDATIONS ───
# =====================================================================
@bot.message_handler(commands=['add'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def add_start(message):
    chat_id = get_chat_id(message)
    if not chat_id: return
    
    msg = bot.send_message(
        chat_id, 
        "📢 <b>ᴀ_ᴅ_ᴅ  <b>ᴄ_ʜ_ᴀ_ɴ__ɴ_ᴇ_ʟ</b>:</b>\n\n"
        "➔ Jis channel ko add karna hai, us channel ka koi bhi ek post yahan <b>Forward</b> karein:", 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, route_setup_type)

def route_setup_type(message):
    if message.text == "/cancel":
        return bot.send_message(message.chat.id, "❌ Action cancelled.")

    is_forwarded = (
        message.forward_from_chat or 
        message.forward_from or 
        message.forward_date or 
        hasattr(message, 'forward_signature')
    )

    if is_forwarded:
        if message.forward_from_chat:
            ch_id = message.forward_from_chat.id
            ch_name = message.forward_from_chat.title
        else:
            ch_id = message.forward_from_chat.id if message.forward_from_chat else message.chat.id
            ch_name = "Private/Hidden Channel"
        
        msg = bot.send_message(
            message.chat.id, 
            f"✅ <b>Channel Detected:</b> {ch_name}\n"
            f"🆔 <b>ID:</b> <code>{ch_id}</code>\n\n"
            f"⏱| <b>⏳ ᴠᴀʟɪᴅɪᴛʏ:</b>\n"
            f"Yeh data kitne din tak valid rakhna hai? (Sirf numbers likhein, jaise: 30):", 
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, channel_ask_price, ch_id, ch_name)
        
    else:
        msg = bot.send_message(message.chat.id, "❌ <b>Galat Input!</b> Kripya channel se post forward karein (ya /cancel):", parse_mode="HTML")
        bot.register_next_step_handler(msg, route_setup_type)

def channel_ask_price(message, ch_id, ch_name):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    
    # Validation: Check validity integer hai ya nahi
    validity_days = message.text.strip()
    if not validity_days.isdigit():
        msg = bot.send_message(message.chat.id, "❌ <b>Invalid Days!</b> Kripya sirf digits/numbers bhejein (Eg: 30):", parse_mode="HTML")
        return bot.register_next_step_handler(msg, channel_ask_price, ch_id, ch_name)
    
    msg = bot.send_message(
        message.chat.id,
        f"💰 <b>ᴘʀɪᴄɪɴɢ:</b>\n"
        f"Is <code>{validity_days}</code> Din ke liye kitna <b>Price (₹)</b> rakhna hai? (Jaise: 49):",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, channel_ask_desc, ch_id, ch_name, validity_days)

# STAGE ADDED: Channel Description Flow
def channel_ask_desc(message, ch_id, ch_name, validity_days):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    
    # Validation: Check price integer hai ya nahi
    price = message.text.strip()
    if not price.isdigit():
        msg = bot.send_message(message.chat.id, "❌ <b>Invalid Price!</b> Kripya sirf plain number bhejein (Eg: 49):", parse_mode="HTML")
        return bot.register_next_step_handler(msg, channel_ask_desc, ch_id, ch_name, validity_days)

    msg = bot.send_message(
        message.chat.id,
        "📝 <b>sᴛᴏʀʏ  ᴅᴇsᴄʀɪᴘᴛɪᴏɴ:</b>\n\n"
        "Is channel ke andar kaun-kaun si hot/premium stories milengi? Unki ek list ya description bhejiyen "
        "(Taaki user buy karne se pehle padh sake):",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, channel_ask_photo, ch_id, ch_name, validity_days, price)

def channel_ask_photo(message, ch_id, ch_name, validity_days, price):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    desc = message.text.strip()
    
    msg = bot.send_message(
        message.chat.id, 
        "🖼️ <b>**ᴄʜᴀɴɴᴇʟ ᴘʜᴏᴛᴏ:**</b>\n"
        "Aap is channel ke liye koi custom photo lagana chahte hain?\n\n"
        "➔ Ek <b>Photo</b> bhejein.\n"
        "➔ Ya bina photo ke aage badhne ke liye <code>skip</code> likhein:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, channel_ask_demo, ch_id, ch_name, validity_days, price, desc)

def channel_ask_demo(message, ch_id, ch_name, validity_days, price, desc):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    
    # Validation: Agar photo nahi bheja aur text bhi 'skip' nahi hai
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.text and message.text.strip().lower() != 'skip':
        msg = bot.send_message(message.chat.id, "⚠️ Kripya ya toh ek <b>Photo</b> upload karein ya fir plain text me <code>skip</code> likhein:", parse_mode="HTML")
        return bot.register_next_step_handler(msg, channel_ask_demo, ch_id, ch_name, validity_days, price, desc)
        
    msg = bot.send_message(message.chat.id, "🔗 <b>Demo Link bhejein</b> (Ya 'skip' ya 'none' likhein):")
    bot.register_next_step_handler(msg, channel_ask_category, ch_id, ch_name, validity_days, price, desc, file_id)

def channel_ask_category(message, ch_id, ch_name, validity_days, price, desc, file_id):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    
    raw_text = message.text.strip() if message.text else ""
    demo = None if raw_text.lower() in ['none', 'skip', ''] else raw_text
    
    # Validation: Demo link valid URL hai ya nahi
    if demo and not is_valid_url(demo):
        msg = bot.send_message(message.chat.id, "❌ <b>Format Error!</b> Aapne jo link bheja hai vo sahi URL format me nahi hai. Kripya valid http/https link bhejein ya <code>skip</code> karein:", parse_mode="HTML")
        return bot.register_next_step_handler(msg, channel_ask_category, ch_id, ch_name, validity_days, price, desc, file_id)
    
    state_id = str(uuid.uuid4())[:8]
    pending_setups[state_id] = {
        "ch_id": int(ch_id), 
        "ch_name": str(ch_name),
        "validity_days": str(validity_days), 
        "price": str(price),
        "description": desc,
        "file_id": file_id,
        "demo_link": demo
    }
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("Pocket", callback_data=f"newsrc_pocket_{state_id}"),
        InlineKeyboardButton("Pratilipi", callback_data=f"newsrc_pratilipi_{state_id}")
    )
    bot.send_message(
        message.chat.id, 
        "📂 <b>Select Category:</b>", 
        reply_markup=markup, 
        parse_mode="HTML"
    )


# =====================================================================
# ─── 4. CALLBACK & FINAL SAVE (WITH DESCRIPTION) ───
# =====================================================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('newsrc_'))
def handle_category_selection(call):
    if call.from_user.id != config.ADMIN_ID: return
    
    parts = call.data.split('_')
    platform = "pocket" if parts[1] == "pocket" else "pratilipi"
    state_id = parts[2]
    
    data = pending_setups.get(state_id)
    if not data:
        return bot.answer_callback_query(call.id, "Session Expired! Dubara /add karein.", show_alert=True)
    
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    
    item_id = str(uuid.uuid4())[:10]
    
    channels_col.update_one(
        {"item_id": item_id}, 
        {"$set": {
            "item_id": item_id,
            "channel_id": data["ch_id"],
            "name": data["ch_name"], 
            "story_name": data["ch_name"], 
            "validity": data["validity_days"], 
            "price": data["price"],        
            "description": data["description"], # Saved properly
            "file_id": data["file_id"],
            "demo_link": data["demo_link"],
            "source": platform,            
            "type": "channel"
        },
        "$unset": {
            "is_combo": ""                 
        }}, 
        upsert=True
    )
    
    pending_setups.pop(state_id, None)
    
    bot_user = bot.get_me().username
    bot_link = f"https://t.me/{bot_user}?start={item_id}"
    
    success_text = (
        f"✅ <b>sᴛᴏʀỹ  sᴇᴛᴜᴘ  ғɪɴɪsʜᴇᴅ!</b>\n"
        f"──────────────────────────\n"
        f"📂 <b>Source:</b> <code>{platform.upper()}</code>\n"
        f"⏱️ <b>Validity:</b> {data['validity_days']} Din\n"
        f"💰 <b>Price:</b> ₹{data['price']}\n"
        f"📝 <b>Description:</b> {data['description']}\n"
        f"📺 <b>Demo:</b> {data['demo_link'] if data['demo_link'] else 'None'}\n\n"
        f"🔗 <b>sʜᴀʀᴇ ʟɪɴᴋ (ꜰᴏʀ ᴜsᴇʀs):</b>\n<code>{bot_link}</code>\n"
        f"──────────────────────────"
    )
    
    if data["file_id"]:
        bot.send_photo(call.message.chat.id, photo=data["file_id"], caption=success_text, parse_mode="HTML")
    else:
        bot.send_message(call.message.chat.id, text=success_text, parse_mode="HTML")


# =====================================================================
# ─── 5. STANDALONE MANUAL COMBO FIXED WITH VALIDATIONS & DESC ───
# =====================================================================
@bot.message_handler(commands=['add_combo'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def add_combo_start(message):
    chat_id = get_chat_id(message)
    if not chat_id: return
    
    msg = bot.send_message(
        chat_id, 
        "🎁 <b>ᴍ_ᴀ_ɴ_ᴜ_ᴀ_ʟ  <b>ᴄ_ᴏ_ᴍ_ʙ_ᴏ</b>  s_ᴇ_ᴛ_ᴜ_ᴘ:</b>\n\n"
        "➔ Combo Pack ka Jo Naam <u>Store Board</u> par dikhana hai, wo bhejiyen:", 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, combo_ask_validity)

def combo_ask_validity(message):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    combo_name = message.text.strip()
    
    msg = bot.send_message(
        message.chat.id,
        "⏱️ <b>⏳ ᴠᴀʟɪᴅɪᴛʏ:</b>\n"
        "Yeh combo bundle kitne din tak valid rahega? (Jaise: 30):",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, combo_ask_price, combo_name)

def combo_ask_price(message, combo_name):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    
    # Validation: Validity integer check
    validity_days = message.text.strip()
    if not validity_days.isdigit():
        msg = bot.send_message(message.chat.id, "❌ <b>Invalid Days!</b> Kripya sirf numbers bhejein (Eg: 30):", parse_mode="HTML")
        return bot.register_next_step_handler(msg, combo_ask_price, combo_name)

    msg = bot.send_message(
        message.chat.id,
        "💰 <b>ᴘʀɪᴄɪɴɢ:</b>\n"
        "Is total combo package ka <b>Price (₹)</b> kitna rakhna hai? (Jaise: 149):",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, combo_ask_desc, combo_name, validity_days)

# STAGE ADDED: Combo Pack Description Flow
def combo_ask_desc(message, combo_name, validity_days):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    
    # Validation: Price integer check
    price = message.text.strip()
    if not price.isdigit():
        msg = bot.send_message(message.chat.id, "❌ <b>Invalid Price!</b> Kripya sirf number dalein (Eg: 149):", parse_mode="HTML")
        return bot.register_next_step_handler(msg, combo_ask_desc, combo_name, validity_days)

    msg = bot.send_message(
        message.chat.id,
        "📝 <b>ᴄᴏᴍʙᴏ  ᴅᴇsᴄʀɪᴘᴛɪᴏɴ:</b>\n\n"
        "Is combo bundle pack ke andar <b>kaun-kaun si stories</b> milne vali hain, details me likh kar send karein:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, combo_ask_photo, combo_name, validity_days, price)

def combo_ask_photo(message, combo_name, validity_days, price):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    desc = message.text.strip()
    
    msg = bot.send_message(
        message.chat.id,
        "🖼️ <b>ᴄᴏᴍʙᴏ ᴘʜᴏᴛᴏ:</b>\n"
        "Is bundle banner ke liye koi photo lagani hai?\n\n"
        "➔ Ek <b>Photo</b> send karein.\n"
        "➔ Ya skip karne ke liye <code>skip</code> likhein:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, combo_ask_demo, combo_name, validity_days, price, desc)

def combo_ask_demo(message, combo_name, validity_days, price, desc):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    
    # Validation: Photo filter check
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.text and message.text.strip().lower() != 'skip':
        msg = bot.send_message(message.chat.id, "⚠️ Kripya photo send karein ya <code>skip</code> text likhein:", parse_mode="HTML")
        return bot.register_next_step_handler(msg, combo_ask_demo, combo_name, validity_days, price, desc)

    msg = bot.send_message(message.chat.id, "🔗 <b>Demo Link bhejein</b> (Ya 'skip' ya 'none' likhein):")
    bot.register_next_step_handler(msg, combo_ask_channels, combo_name, validity_days, price, desc, file_id)

def combo_ask_channels(message, combo_name, validity_days, price, desc, file_id):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    
    raw_text = message.text.strip() if message.text else ""
    demo = None if raw_text.lower() in ['none', 'skip', ''] else raw_text
    
    # Validation: Demo link valid URL structure verification
    if demo and not is_valid_url(demo):
        msg = bot.send_message(message.chat.id, "❌ <b>Format Error!</b> Sahi URL structure bhejein (Eg: https://...) ya skip likhein:", parse_mode="HTML")
        return bot.register_next_step_handler(msg, combo_ask_channels, combo_name, validity_days, price, desc, file_id)

    msg = bot.send_message(
        message.chat.id,
        "🆔 <b>ᴄʜᴀɴɴᴇʟ ɪᴅs ʟɪsᴛ:</b>\n"
        "Is combo bundle ke andar aane wale saare channels ki <b>IDs</b> comma ( , ) laga kar dein:\n\n"
        "➔ <code>-100123456,-100987654</code>",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, save_manual_combo_fixed, combo_name, validity_days, price, desc, file_id, demo)

def save_manual_combo_fixed(message, combo_name, validity_days, price, desc, file_id, demo):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    raw_ids = message.text.strip().replace(" ", "")
    
    # Strict Format Validation for comma separated Integers
    try:
        channel_ids_list = [int(cid) for cid in raw_ids.split(",") if cid]
        if not channel_ids_list:
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ <b>Format Error!</b> Keval Valid Channel IDs aur comma ka use karein. Dobara valid IDs bhejein:")
        return bot.register_next_step_handler(msg, save_manual_combo_fixed, combo_name, validity_days, price, desc, file_id, demo)

    item_id = f"combo_{str(uuid.uuid4())[:10]}"
    
    channels_col.insert_one({
        "item_id": item_id,
        "name": combo_name,
        "combo_name": combo_name,       
        "is_combo": True,               
        "validity": validity_days,
        "price": price,                 
        "description": desc,            # Saved properly
        "file_id": file_id,
        "demo_link": demo,
        "channels_list": channel_ids_list,
        "source": "combo",              
        "type": "combo"
    })
    
    bot_user = bot.get_me().username
    bot_link = f"https://t.me/{bot_user}?start={item_id}"
    
    success_text = (
        f"✅ <b>🎁 sᴘᴇᴄɪᴀʟ ᴄᴏᴍʙᴏ sᴀᴠᴇᴅ ɪɴ sᴛᴏʀᴇ!</b>\n"
        f"──────────────────────────\n"
        f"🎁 <b>ᴄᴏᴍʙᴏ ɴᴀᴍᴇ:</b> <code>{combo_name}</code>\n"
        f"⏱️ <b>ᴠᴀʟɪᴅɪᴛʏ:</b> {validity_days} Din\n"
        f"💰 <b>ᴘʀɪᴄᴇ:</b> ₹{price}\n"
        f"📝 <b>ᴅᴇsᴄʀɪᴘᴛɪᴏɴ:</b> <i>{desc}</i>\n"
        f"📊 <b>ᴄʜᴀɴɴᴇʟs:</b> {len(channel_ids_list)} Linked\n\n"
        f"🔗 <b>sʜᴀʀᴇ ʟɪɴᴋ (ᴜsᴇʀs):</b>\n<code>{bot_link}</code>\n"
        f"──────────────────────────"
    )
    
    if file_id:
        bot.send_photo(message.chat.id, photo=file_id, caption=success_text, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, text=success_text, parse_mode="HTML")
