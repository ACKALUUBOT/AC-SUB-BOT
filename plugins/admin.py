import uuid
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot
from database import channels_col, users_col
import config

# Global storage temporary data hold karne ke liye jab tak category select na ho
pending_setups = {}

def get_chat_id(message):
    if hasattr(message, 'chat') and message.chat:
        return message.chat.id
    if hasattr(message, 'message') and message.message and message.message.chat:
        return message.message.chat.id
    return None

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


# ==========================================
# --- 2. MANAGE CHANNELS & STORIES ---
# ==========================================
@bot.message_handler(commands=['channels'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def list_channels(message):
    chat_id = get_chat_id(message)
    if not chat_id: return

    cursor = channels_col.find()
    markup = InlineKeyboardMarkup()
    for ch in cursor:
        name = ch.get('name') or "Unnamed Item"
        markup.add(InlineKeyboardButton(f"⚙️ Manage: {name}", callback_data=f"manage_{ch['item_id']}"))
        
    if markup.keyboard:
        bot.send_message(chat_id, "📑 <b>ʏᴏᴜʀ  ɪɴᴠᴇɴᴛᴏʀʏ:</b>\nNiche kisi bhi item ko manage karein:", reply_markup=markup, parse_mode="HTML")
    else:
        bot.send_message(chat_id, "❌ Abhi koi item add nahi hai.")

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
    source_platform = ch_data.get('source', 'none') 
    validity_info = ch_data.get('validity', 'N/A')
    price_info = ch_data.get('price', '0')
    
    text = (
        f"⚙️ <b>sᴇᴛᴛɪɴɢs:</b> {name}\n"
        f"────────────────────\n"
        f"📂 <b>source:</b> <code>{source_platform}</code>\n"
        f"⏱️ <b>validity:</b> {validity_info} Din\n"
        f"💰 <b>price:</b> ₹{price_info}\n"
        f"📺 <b>demo:</b> {ch_data.get('demo_link', 'None')}\n\n"
        f"🔗 <b>sʜᴀʀᴇ ʟɪɴᴋ:</b>\n<code>{link}</code>\n"
        f"────────────────────"
    )
    try: 
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception: 
        pass

    photo_id = ch_data.get('file_id')
    if photo_id:
        bot.send_photo(call.message.chat.id, photo=photo_id, caption=text, parse_mode="HTML")
    else:
        bot.send_message(call.message.chat.id, text=text, parse_mode="HTML")


# =====================================================================
# ─── 3. FORWARD CHANNEL STORY FLOW (/add) ───
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
            f"⏱️ <b>⏳ ᴠᴀʟɪᴅɪᴛʏ:</b>\n"
            f"Yeh data kitne din tak valid rakhna hai? (Sirf numbers likhein, jaise: 30):", 
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, channel_ask_price, ch_id, ch_name)
        
    else:
        msg = bot.send_message(message.chat.id, "❌ Galat Input! Kripya channel se post forward karein (ya /cancel):")
        bot.register_next_step_handler(msg, route_setup_type)

def channel_ask_price(message, ch_id, ch_name):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    validity_days = message.text.strip()
    
    msg = bot.send_message(
        message.chat.id,
        f"💰 <b>ᴘʀɪᴄɪɴɢ:</b>\n"
        f"Is <code>{validity_days}</code> Din ke liye kitna <b>Price (₹)</b> rakhna hai? (Jaise: 49):",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, channel_ask_photo, ch_id, ch_name, validity_days)

def channel_ask_photo(message, ch_id, ch_name, validity_days):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    price = message.text.strip()
    
    msg = bot.send_message(
        message.chat.id, 
        "🖼️ <b>ᴄʜᴀɴɴᴇʟ ᴘʜᴏᴛᴏ:</b>\n"
        "Aap is channel ke liye koi custom photo lagana chahte hain?\n\n"
        "➔ Ek <b>Photo</b> bhejein.\n"
        "➔ Ya bina photo ke aage badhne ke liye <code>skip</code> likhein:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, channel_ask_demo, ch_id, ch_name, validity_days, price)

def channel_ask_demo(message, ch_id, ch_name, validity_days, price):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    file_id = message.photo[-1].file_id if message.photo else None
    
    msg = bot.send_message(message.chat.id, "🔗 <b>Demo Link bhejein</b> (Ya 'skip' ya 'none' likhein):")
    bot.register_next_step_handler(msg, channel_ask_category, ch_id, ch_name, validity_days, price, file_id)

def channel_ask_category(message, ch_id, ch_name, validity_days, price, file_id):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    
    raw_text = message.text.strip() if message.text else ""
    demo = None if raw_text.lower() in ['none', 'skip', ''] else raw_text
    
    state_id = str(uuid.uuid4())[:8]
    pending_setups[state_id] = {
        "ch_id": int(ch_id), 
        "ch_name": str(ch_name),
        "validity_days": str(validity_days), 
        "price": str(price),
        "file_id": file_id,
        "demo_link": demo
    }
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("pocket", callback_data=f"newsrc_pocket_{state_id}"),
        InlineKeyboardButton("pratilipi", callback_data=f"newsrc_pratilipi_{state_id}")
    )
    bot.send_message(
        message.chat.id, 
        "📂 <b>Select Category:</b>", 
        reply_markup=markup, 
        parse_mode="HTML"
    )


# =====================================================================
# ─── 4. CALLBACK & FINAL SAVE (STRICT FOR FORWARDED STORIES) ───
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
    
    # 🌟 STRICT SAVE: Item_id par strict indexing ki taaki store aur payment sync perfect chale
    channels_col.update_one(
        {"item_id": item_id}, 
        {"$set": {
            "item_id": item_id,
            "channel_id": data["ch_id"],
            "name": data["ch_name"], 
            "story_name": data["ch_name"], # store.py list matching criteria
            "validity": data["validity_days"], 
            "price": data["price"],        
            "file_id": data["file_id"],
            "demo_link": data["demo_link"],
            "source": platform,            # Pocket or Pratilipi selection
            "type": "channel"
        },
        "$unset": {
            "is_combo": ""                 # Combo criteria explicitly deleted for single entries
        }}, 
        upsert=True
    )
    
    pending_setups.pop(state_id, None)
    
    bot_user = bot.get_me().username
    bot_link = f"https://t.me/{bot_user}?start={item_id}"
    
    success_text = (
        f"✅ <b>sᴛᴏʀỹ  sᴇᴛᴜᴘ  ғɪɴɪsʜᴇᴅ!</b>\n"
        f"──────────────────────────\n"
        f"📂 <b>source:</b> <code>{platform}</code>\n"
        f"⏱️ <b>validity:</b> {data['validity_days']} Din\n"
        f"💰 <b>price:</b> ₹{data['price']}\n"
        f"📺 <b>demo:</b> {data['demo_link'] if data['demo_link'] else 'None'}\n\n"
        f"🔗 <b>sʜᴀʀᴇ ʟɪɴᴋ (ꜰᴏʀ ᴜsᴇʀs):</b>\n<code>{bot_link}</code>\n"
        f"──────────────────────────"
    )
    
    if data["file_id"]:
        bot.send_photo(call.message.chat.id, photo=data["file_id"], caption=success_text, parse_mode="HTML")
    else:
        bot.send_message(call.message.chat.id, text=success_text, parse_mode="HTML")


# =====================================================================
# ─── 5. STANDALONE MANUAL COMBO FIXED (100% SYNCED WITH store.py) ───
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
    validity_days = message.text.strip()
    
    msg = bot.send_message(
        message.chat.id,
        "💰 <b>ᴘʀɪᴄɪɴɢ:</b>\n"
        "Is total combo package ka <b>Price (₹)</b> kitna rakhna hai? (Jaise: 149):",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, combo_ask_photo, combo_name, validity_days)

def combo_ask_photo(message, combo_name, validity_days):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    price = message.text.strip()
    
    msg = bot.send_message(
        message.chat.id,
        "🖼️ <b>ᴄᴏᴍʙᴏ ᴘʜᴏᴛᴏ:</b>\n"
        "Is bundle banner ke liye koi photo lagani hai?\n\n"
        "➔ Ek <b>Photo</b> send karein.\n"
        "➔ Ya skip karne ke liye <code>skip</code> likhein:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, combo_ask_demo, combo_name, validity_days, price)

def combo_ask_demo(message, combo_name, validity_days, price):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    file_id = message.photo[-1].file_id if message.photo else None
    
    msg = bot.send_message(message.chat.id, "🔗 <b>Demo Link bhejein</b> (Ya 'skip' ya 'none' likhein):")
    bot.register_next_step_handler(msg, combo_ask_channels, combo_name, validity_days, price, file_id)

def combo_ask_channels(message, combo_name, validity_days, price, file_id):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    
    raw_text = message.text.strip() if message.text else ""
    demo = None if raw_text.lower() in ['none', 'skip', ''] else raw_text
    
    msg = bot.send_message(
        message.chat.id,
        "🆔 <b>ᴄʜᴀɴɴᴇʟ ɪᴅs ʟɪsᴛ:</b>\n"
        "Is combo bundle ke andar aane wale saare channels ki <b>IDs</b> comma ( , ) laga kar dein:\n\n"
        "➔ <code>-100123456,-100987654</code>",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, save_manual_combo_fixed, combo_name, validity_days, price, file_id, demo)

def save_manual_combo_fixed(message, combo_name, validity_days, price, file_id, demo):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    raw_ids = message.text.strip().replace(" ", "")
    
    try:
        channel_ids_list = [int(cid) for cid in raw_ids.split(",") if cid]
    except ValueError:
        msg = bot.send_message(message.chat.id, "❌ <b>Format Error!</b> Keval IDs aur comma ka use karein. Dobara valid IDs bhejein:")
        return bot.register_next_step_handler(msg, save_manual_combo_fixed, combo_name, validity_days, price, file_id, demo)

    item_id = f"combo_{str(uuid.uuid4())[:10]}"
    
    # 🌟 SCHEMA ALIGNED 100% WITH store.py COMBO FILTER FIXED 
    channels_col.insert_one({
        "item_id": item_id,
        "name": combo_name,
        "combo_name": combo_name,       # Required by store.py: item['combo_name']
        "is_combo": True,               # Required by store.py: {"is_combo": True}
        "validity": validity_days,
        "price": price,                 # Aligned with [ ₹{item['price']} ] display
        "file_id": file_id,
        "demo_link": demo,
        "channels_list": channel_ids_list,
        "source": "combo",              # Clean mapping anchor
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
        f"📊 <b>ᴄʜᴀɴɴᴇʟs:</b> {len(channel_ids_list)} Linked\n\n"
        f"🔗 <b>sʜᴀʀᴇ ʟɪɴᴋ (ᴜsᴇʀs):</b>\n<code>{bot_link}</code>\n"
        f"──────────────────────────"
    )
    
    if file_id:
        bot.send_photo(message.chat.id, photo=file_id, caption=success_text, parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, text=success_text, parse_mode="HTML")
    
