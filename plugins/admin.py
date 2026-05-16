import uuid
import re
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot
from database import channels_col, users_col
import config

# 🌟 GLOBAL MEMORY ROUTER: Long data aur Photo IDs ko safety se temporary hold karne ke liye
admin_setup_session = {}

# ==========================================
# --- 1. REMOVE USER (SECURE DELETE) ---
# ==========================================
@bot.message_handler(commands=['remove'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def remove_user_start(message):
    chat_id = message.chat.id
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
            try: bot.send_message(u_id, "⚠️ <b>Access Revoked:</b> Aapka subscription khatam kar diya gaya hai.")
            except: pass
        else:
            bot.send_message(message.chat.id, "❓ Is ID ka koi active subscription nahi mila.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid ID! Sirf numbers bhejein.")


# ==========================================
# --- 2. MANAGE CHANNELS & STORIES ---
# ==========================================
@bot.message_handler(commands=['channels'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def list_channels(message):
    chat_id = message.chat.id
    cursor = channels_col.find()
    markup = InlineKeyboardMarkup()
    for ch in cursor:
        name = ch.get('story_name') or ch.get('name') or ch.get('combo_name')
        markup.add(InlineKeyboardButton(f"⚙️ Manage: {name}", callback_data=f"manage_{ch['item_id']}"))
    if markup.keyboard:
        bot.send_message(chat_id, "📑 <b>ʏᴏᴜʀ ɪɴᴠᴇɴᴛᴏʀʏ:</b>\nNiche kisi bhi item ko manage karein:", reply_markup=markup, parse_mode="HTML")
    else:
        bot.send_message(chat_id, "❌ Abhi koi item add nahi hai.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('manage_'))
def manage_ch(call):
    item_id = call.data.split('_')[1]
    ch_data = channels_col.find_one({"item_id": item_id})
    if not ch_data: return bot.answer_callback_query(call.id, "Data not found!")

    bot_user = bot.get_me().username
    link = f"https://t.me/{bot_user}?start={item_id}"
    name = ch_data.get('story_name') or ch_data.get('name') or ch_data.get('combo_name')
    price_info = f"₹{ch_data['price']}" if 'price' in ch_data else ch_data.get('plans', 'N/A')
    
    text = (
        f"⚙️ <b>sᴇᴛᴛɪɴɢs:</b> {name}\n"
        f"────────────────────\n"
        f"🔗 <b>sʜᴀʀᴇ ʟɪɴᴋ:</b>\n<code>{link}</code>\n\n"
        f"📺 <b>ᴅᴇᴍᴏ:</b> {ch_data.get('demo_link', 'None')}\n"
        f"💰 <b>ᴘʟᴀɴs / ᴘʀɪᴄᴇ:</b> {price_info}\n"
        f"📌 <b>ᴘʟᴀᴛғᴏʀᴍ / sᴏᴜʀᴄᴇ:</b> <code>{ch_data.get('source', 'None/Combo')}</code>\n"
        f"────────────────────"
    )
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

    photo_id = ch_data.get('file_id')
    if photo_id and photo_id != "None":
        bot.send_photo(call.message.chat.id, photo=photo_id, caption=text, parse_mode="HTML")
    else:
        bot.send_message(call.message.chat.id, text=text, parse_mode="HTML")


# ==========================================
# --- 3. SEPARATE LOGIC CHANNELS & STORIES ---
# ==========================================
@bot.message_handler(commands=['add'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def add_start(message):
    chat_id = message.chat.id
    admin_setup_session[message.from_user.id] = {} # User session initialization
    
    msg = bot.send_message(
        chat_id, 
        "📢 <b>ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ sʏsᴛᴇᴍ:</b>\n\n"
        "➔ <b>Way 1 (Forward):</b> Channel ka koi post <b>Forward</b> karein.\n"
        "➔ <b>Way 2 (Direct Photo):</b> Ek <b>Photo</b> bhejein jiska <b>Caption</b> Channel/Story ka naam ho:", 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, route_setup_type)

def route_setup_type(message):
    user_id = message.from_user.id
    if message.text and message.text == "/cancel":
        return bot.send_message(message.chat.id, "❌ Action cancelled.")

    # ──────────────────────────────────────────
    # [FLOW 1] CHANNEL FORWARD MODE
    # ──────────────────────────────────────────
    if message.forward_from_chat:
        ch_id = message.forward_from_chat.id
        ch_name = message.forward_from_chat.title
        
        admin_setup_session[user_id] = {
            "type": "channel",
            "channel_id": ch_id,
            "story_name": ch_name
        }
        
        msg = bot.send_message(
            message.chat.id, 
            f"✅ <b>Channel Detected (Forward):</b> {ch_name}\n\n"
            f"Plans likhein (Format - Min:Price):\nExample: <code>1440:30, 10080:150</code>", 
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, channel_ask_photo)

    # ──────────────────────────────────────────
    # [FLOW 2] DIRECT PHOTO UPLOAD MODE (NOW CREATING CHANNEL)
    # ──────────────────────────────────────────
    elif message.photo:
        file_id = message.photo[-1].file_id
        # Single line save command apply kiya caption par
        ch_name = message.caption.split("\n")[0].strip() if message.caption else "Untitled Channel"
        
        # Unique mock channel hash create karna backend process bypass ke liye
        fake_ch_id = int(f"-100{str(uuid.uuid4().int)[:9]}")
        
        admin_setup_session[user_id] = {
            "type": "channel",
            "channel_id": fake_ch_id,
            "story_name": ch_name,
            "file_id": file_id
        }
        
        msg = bot.send_message(
            message.chat.id, 
            f"🖼️ <b>Channel Detected (Photo Mode):</b> {ch_name}\n\n"
            f"Plans likhein (Format - Min:Price):\nExample: <code>1440:30, 10080:150</code>", 
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, photo_channel_get_plans)
        
    else:
        msg = bot.send_message(message.chat.id, "❌ Galat input! Kripya post forward karein ya direct photo bhejein:")
        bot.register_next_step_handler(msg, route_setup_type)


# ─── FLOW 1: FORWARD CHANNEL HANDLERS ───
def channel_ask_photo(message):
    user_id = message.from_user.id
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    
    admin_setup_session[user_id]["plans_data"] = message.text.strip()
    
    msg = bot.send_message(
        message.chat.id, 
        "🖼️ <b>ᴄʜᴀɴɴᴇʟ ᴘʜᴏᴛᴏ:</b>\n"
        "Aap is forward channel ke liye koi custom photo lagana chahte hain?\n\n"
        "➔ Ek <b>Photo</b> bhejein.\n"
        "➔ Ya bina photo ke save karne ke liye <code>skip</code> likhein:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, channel_ask_demo)

def channel_ask_demo(message):
    user_id = message.from_user.id
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    
    file_id = "None"
    if message.photo:
        file_id = message.photo[-1].file_id
    
    admin_setup_session[user_id]["file_id"] = file_id
    
    msg = bot.send_message(message.chat.id, "🔗 Demo Link bhejein (Ya 'skip' ya 'none' likhein):")
    bot.register_next_step_handler(msg, channel_ask_platform)


# ─── FLOW 2: DIRECT PHOTO CHANNEL HANDLERS ───
def photo_channel_get_plans(message):
    user_id = message.from_user.id
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    
    admin_setup_session[user_id]["plans_data"] = message.text.strip()
    
    msg = bot.send_message(message.chat.id, "🔗 Demo Link bhejein (Ya 'skip' ya 'none' likhein):")
    bot.register_next_step_handler(msg, channel_ask_platform)


# ─── COMMON PLATFORM SELECTOR FOR CHANNELS ───
def channel_ask_platform(message):
    user_id = message.from_user.id
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    demo = "None" if message.text.lower() in ['none', 'skip'] else message.text.strip()
    
    admin_setup_session[user_id]["demo_link"] = demo
    session = admin_setup_session[user_id]
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✨ PRATILIPI FM", callback_data="src_pratilipi"),
        InlineKeyboardButton("🔥 POCKET FM", callback_data="src_pocket")
    )
    
    bot.send_message(
        message.chat.id, 
        f"🎯 <b>Choose Channel Platform:</b>\n"
        f"──────────────────────────\n"
        f"👑 Channel: <code>{session['story_name']}</code>\n"
        f"📊 Plans: <code>{session['plans_data']}</code>\n"
        f"🔗 Demo: <code>{demo}</code>\n"
        f"🖼️ Photo: <code>{'Attached ✅' if session['file_id'] != 'None' else 'None ❌'}</code>\n"
        f"──────────────────────────\n"
        f"Is channel ko kis category me dalna hai?",
        reply_markup=markup,
        parse_mode="HTML"
    )


# ==========================================
# --- 4. EXCLUSIVE CALLBACK SOURCE ROUTER ---
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('src_'))
def handle_universal_source_selection(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    
    source = call.data.split('_')[1]
    session = admin_setup_session.get(user_id)
    
    if not session:
        return bot.send_message(call.message.chat.id, "❌ Session Expired! Please use /add again.")
    
    try:
        plans_data = session["plans_data"]
        try:
            plans = {p.split(':')[0].strip(): p.split(':')[1].strip() for p in plans_data.split(',')}
        except:
            return bot.send_message(call.message.chat.id, "❌ Plans format syntax error! Kripya sahi format use karein.")
        
        item_id = str(uuid.uuid4())[:10]
        demo = None if session["demo_link"] == "None" else session["demo_link"]
        
        # Database document save logic
        channels_col.insert_one({
            "item_id": item_id,
            "channel_id": session["channel_id"],
            "story_name": session["story_name"], 
            "plans_options": plans,
            "price": min([int(p) for p in plans.values()]) if plans else 0, 
            "demo_link": demo,
            "file_id": session["file_id"], # Photo string safely synced here
            "type": "channel",
            "source": source
        })
        
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        
        link = f"https://t.me/{bot.get_me().username}?start={item_id}"
        admin_setup_session.pop(user_id, None) # Clear volatile user cache memory
        return bot.send_message(call.message.chat.id, f"✅ <b>ᴄʜᴀɴɴᴇʟ sᴇᴛᴜᴘ ғɪɴɪsʜᴇᴅ!</b>\n\nPlatform: <code>{source.upper()}</code>\nLink: <code>{link}</code>", parse_mode="HTML")
    except Exception as e:
        return bot.send_message(call.message.chat.id, f"❌ Channel save execution error: {str(e)}")


# ==========================================
# --- 5. MANUAL COMBO SYSTEM ---
# ==========================================
@bot.message_handler(commands=['add_combo'])
def add_combo_manual_handler(message):
    if message.from_user.id != config.ADMIN_ID:
        return bot.reply_to(message, "❌ Aapke paas is command ka access nahi hai.")

    command_text = message.text.replace("/add_combo", "").strip()
    
    if not command_text or "|" not in command_text:
        error_msg = (
            "💡 <b>ʜᴏᴡ ᴛᴏ ᴀDᴅ ᴄᴏᴍʙᴏ ᴍᴀɴᴜᴀʟʟʏ:</b>\n\n"
            "Format mein <code>|</code> (pipe symbol) ka use karein:\n"
            "<code>/add_combo Price | Name | Description | IDs</code>\n\n"
            "📝 <b>Example:</b>\n"
            "<code>/add_combo 99 | Mega 3-in-1 Pack | 1. Hot Story\n2. VIP Video\n3. Backup Link | -1001111111, -1002222222</code>\n\n"
            "⚠️ <i>Note: Channel IDs ke beech mein comma (,) lagayein.</i>"
        )
        return bot.reply_to(message, error_msg, parse_mode="HTML")

    try:
        parts = [p.strip() for p in command_text.split("|")]
        if len(parts) < 4:
            return bot.reply_to(message, "❌ <b>Format Error!</b> Kripya saari fields sahi se bharein.")

        price = parts[0]
        combo_name = parts[1]
        description = parts[2]
        
        raw_ids = parts[3].split(",")
        channels_list = []
        for cid in raw_ids:
            cid = cid.strip()
            if cid.replace('-', '').isdigit():
                channels_list.append(int(cid))

        if not channels_list:
            return bot.reply_to(message, "❌ Kripya valid Channel IDs daalein.")

        unique_item_id = f"combo_{uuid.uuid4().hex[:6]}"

        combo_data = {
            "item_id": unique_item_id,
            "combo_name": combo_name,
            "price": int(price) if price.isdigit() else price,
            "description": description,
            "channels_list": channels_list,
            "is_combo": True
        }

        channels_col.insert_one(combo_data)

        success_text = (
            "✅ <b>ᴄᴏᴍʙᴏ ᴘᴀᴄᴋ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n"
            "──────────────────────────\n"
            "📦 <b>Name:</b> <code>{name}</code>\n"
            "💰 <b>Price:</b> ₹{price}\n"
            "🆔 <b>Item ID:</b> <code>{item_id}</code>\n"
            "📺 <b>Linked Channels:</b> <code>{ch_count} Channels</code>\n"
            "──────────────────────────\n"
            "🔗 <b>Direct Link:</b> <code>https://t.me/{bot_link}?start={item_id}</code>"
        ).format(
            name=combo_name,
            price=price,
            item_id=unique_item_id,
            ch_count=len(channels_list),
            bot_link=bot.get_me().username
        )
        bot.reply_to(message, success_text, parse_mode="HTML")

    except Exception as e:
        bot.reply_to(message, f"❌ <b>Error Occurred:</b> <code>{str(e)}</code>")
