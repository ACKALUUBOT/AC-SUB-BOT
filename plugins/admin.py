import uuid
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot
from database import channels_col, users_col
import config

# ==========================================
# --- 1. REMOVE USER (SECURE DELETE) ---
# ==========================================
@bot.message_handler(commands=['remove'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def remove_user_start(message):
    if message.from_user.id != config.ADMIN_ID: return
    chat_id = message.chat.id if hasattr(message, 'chat') else message.message.chat.id
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
    chat_id = message.chat.id if hasattr(message, 'chat') else message.message.chat.id
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
    if photo_id:
        bot.send_photo(call.message.chat.id, photo=photo_id, caption=text, parse_mode="HTML")
    else:
        bot.send_message(call.message.chat.id, text=text, parse_mode="HTML")


# ==========================================
# --- 3. SEPARATE LOGIC CHANNELS & STORIES ---
# ==========================================
@bot.message_handler(commands=['add'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def add_start(message):
    chat_id = message.chat.id if hasattr(message, 'chat') else message.message.chat.id
    msg = bot.send_message(
        chat_id, 
        "📢 <b>add  item:</b>\n\n"
        "➔ <b>Channel Setup:</b> Kisi channel ka koi post <b>Forward</b> karein.\n"
        "➔ <b>Direct Photo Setup:</b> Ek <b>Photo</b> bhejein jiska <b>Caption</b> Story ka naam ho:", 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, route_setup_type)

def route_setup_type(message):
    if message.text and message.text == "/cancel":
        return bot.send_message(message.chat.id, "❌ Action cancelled.")

    # ──────────────────────────────────────────
    # [FLOW 1] CHANNEL FORWARD MODE
    # ──────────────────────────────────────────
    if message.forward_from_chat:
        ch_id = message.forward_from_chat.id
        ch_name = message.forward_from_chat.title
        
        msg = bot.send_message(
            message.chat.id, 
            f"✅ <b>Channel Detected:</b> {ch_name}\n\n"
            f"Plans likhein (Format - Min:Price):\nExample: <code>1440:30, 10080:150</code>", 
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, channel_ask_photo, ch_id, ch_name)

    # ──────────────────────────────────────────
    # [FLOW 2] DIRECT PHOTO UPLOAD MODE (STORY SYSTEM)
    # ──────────────────────────────────────────
    elif message.photo:
        file_id = message.photo[-1].file_id
        story_name = message.caption.split("\n")[0] if message.caption else "Untitled Story"
        
        msg = bot.send_message(
            message.chat.id, 
            f"🎬 <b>Story Detected:</b> {story_name}\n\n"
            f"Is Story ka Price likhein (Example: 49):", 
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, story_ask_platform, story_name, file_id)
        
    else:
        msg = bot.send_message(message.chat.id, "❌ Galat input! Kripya post forward karein ya direct photo bhejein:")
        bot.register_next_step_handler(msg, route_setup_type)


# ─── FLOW 1: CHANNEL SETUP HANDLERS ───
def channel_ask_photo(message, ch_id, ch_name):
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    plans_data = message.text.strip()
    
    msg = bot.send_message(
        message.chat.id, 
        "🖼️ <b>ᴄʜᴀɴɴᴇʟ ᴘʜᴏᴛᴏ:</b>\n"
        "Aap is channel ke liye koi custom photo lagana chahte hain?\n\n"
        "➔ Ek <b>Photo</b> bhejein.\n"
        "➔ Ya bina photo ke save karne ke liye <code>skip</code> likhein:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, channel_ask_demo, ch_id, ch_name, plans_data)

def channel_ask_demo(message, ch_id, ch_name, plans_data):
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    
    msg = bot.send_message(message.chat.id, "🔗 Demo Link bhejein (Ya 'skip' ya 'none' likhein):")
    bot.register_next_step_handler(msg, channel_ask_platform, ch_id, ch_name, plans_data, file_id)

def channel_ask_platform(message, ch_id, ch_name, plans_data, file_id):
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    demo = None if message.text.lower() in ['none', 'skip'] else message.text.strip()
    
    # 🌟 NEW CHANNEL FLOW SOURCE SELECTOR
    markup = InlineKeyboardMarkup(row_width=2)
    # Callback data pass parameters: type_chID_plansData_demoLink_fileID
    # Content strings filtered dynamically via custom callback router
    markup.add(
        InlineKeyboardButton("✨ PRATILIPI FM", callback_data=f"src_pratilipi_chan"),
        InlineKeyboardButton("🔥 POCKET FM", callback_data=f"src_pocket_chan")
    )
    
    # Session state pass backup using temporary processing text
    bot.send_message(
        message.chat.id, 
        f"🎯 <b>Choose Channel Platform:</b>\nChannel: <code>{ch_name}</code>\nPlans: <code>{plans_data}</code>\nDemo: <code>{demo}</code>\n\nIs channel ko kis category me dalna hai?",
        reply_markup=markup,
        parse_mode="HTML"
    )
    # Temporary global payload mapping context trigger to pass long data fields safely
    bot.pin_chat_message(message.chat.id, bot.send_message(message.chat.id, f"📝 CACHE_DATA|{ch_id}|{ch_name}|{plans_data}|{demo}|{file_id}").message_id, disable_notification=True)


# ─── FLOW 2: DIRECT PHOTO STORY HANDLERS ───
def story_ask_platform(message, story_name, file_id):
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    price = message.text.strip()
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✨ PRATILIPI FM", callback_data=f"setplatform_pratilipi_{price}"),
        InlineKeyboardButton("🔥 POCKET FM", callback_data=f"setplatform_pocket_{price}")
    )
    
    bot.send_message(
        message.chat.id, 
        f"🎯 <b>Choose Story Platform:</b>\n\nStory <code>{story_name}</code> kis platform ki category mein dikhani hai?", 
        reply_markup=markup,
        parse_mode="HTML"
    )
    bot.pin_chat_message(message.chat.id, bot.send_message(message.chat.id, f"📝 STORY_FID|{file_id}").message_id, disable_notification=True)


# ==========================================
# --- 4. EXCLUSIVE CALLBACK SOURCE ROUTER ---
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('src_') or call.data.startswith('setplatform_'))
def handle_universal_source_selection(call):
    data_split = call.data.split('_')
    action_prefix = data_split[0]
    source = data_split[1]
    
    # ─── HANDLER FOR FLOW 1 (CHANNEL) ───
    if action_prefix == "src":
        try:
            # Unpin and parse dynamic system logs cached
            chat_id = call.message.chat.id
            # Safe scanning logic for extraction 
            history = list(channels_col.find({"temp_log": {"$exists": True}})) # Alternative to raw parsing text
            
            # Simple message verification parse from active chat state
            msg_text = call.message.text
            ch_name = msg_text.split("Channel: ")[1].split("\n")[0].replace("<code>", "").replace("</code>", "").strip()
            plans_data = msg_text.split("Plans: ")[1].split("\n")[0].replace("<code>", "").replace("</code>", "").strip()
            demo_data = msg_text.split("Demo: ")[1].split("\n")[0].replace("<code>", "").replace("</code>", "").strip()
            demo = None if demo_data == "None" else demo_data
            
            # Reconstruct variables dynamically from state text cleanly
            try:
                plans = {p.split(':')[0].strip(): p.split(':')[1].strip() for p in plans_data.split(',')}
            except:
                return bot.send_message(chat_id, "❌ Plans pattern calculation failure.")
            
            item_id = str(uuid.uuid4())[:10]
            fake_ch_id = int(f"-100{str(uuid.uuid4().int)[:9]}")
            
            channels_col.insert_one({
                "item_id": item_id,
                "channel_id": fake_ch_id,
                "story_name": ch_name, # Stored as story_name pattern for integrated query processing
                "plans_options": plans,
                "price": min([int(p) for p in plans.values()]) if plans else 0, # Auto Base price index setup
                "demo_link": demo,
                "file_id": None,
                "type": "story",
                "source": source
            })
            
            try: bot.delete_message(chat_id, call.message.message_id)
            except: pass
            
            link = f"https://t.me/{bot.get_me().username}?start={item_id}"
            return bot.send_message(chat_id, f"✅ <b>ᴄʜᴀɴɴᴇʟ sᴇᴛᴜᴘ ғɪɴɪsʜᴇᴅ!</b>\n\nPlatform: <code>{source.upper()}</code>\nLink: <code>{link}</code>", parse_mode="HTML")
        except Exception as e:
            return bot.send_message(call.message.chat.id, f"❌ Channel save runtime error: {str(e)}")

    # ─── HANDLER FOR FLOW 2 (DIRECT PHOTO STORY) ───
    elif action_prefix == "setplatform":
        price = data_split[2]
        story_name = call.message.text.split("Story ")[1].split(" kis")[0].replace("<code>", "").replace("</code>", "").strip()
        
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        
        msg = bot.send_message(
            call.message.chat.id, 
            f"🤖 [Platform: {source.upper()}]\n"
            f"<b>Final Access Link:</b>\n"
            f"User ke payment karne par jo main target link milna chahiye, woh bhejein:"
        )
        bot.register_next_step_handler(msg, story_ask_demo_with_source, story_name, price, source)

def story_ask_demo_with_source(message, story_name, price, source):
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    final_link = message.text.strip()
    
    msg = bot.send_message(message.chat.id, "🔗 Demo Link bhejein (Ya 'skip' ya 'none' likhein):")
    bot.register_next_step_handler(msg, finalize_story_setup_with_source, story_name, price, final_link, source)

def finalize_story_setup_with_source(message, story_name, price, final_link, source):
    if message.text and message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Cancelled.")
    demo = None if message.text.lower() in ['none', 'skip'] else message.text.strip()
    
    item_id = str(uuid.uuid4())[:10]
    fake_channel_id = int(f"-100{str(uuid.uuid4().int)[:9]}")
    
    channels_col.insert_one({
        "item_id": item_id,
        "channel_id": fake_channel_id,
        "story_name": story_name,
        "price": int(price) if price.isdigit() else price,
        "bot_link": final_link,
        "demo_link": demo,
        "file_id": None,
        "type": "story",
        "source": source
    })
    
    link = f"https://t.me/{bot.get_me().username}?start={item_id}"
    bot.send_message(message.chat.id, f"✅ <b>sᴛᴏʀʏ sᴇᴛᴜᴘ ғɪɴɪsʜᴇᴅ!</b>\n\nPlatform: <code>{source.upper()}</code>\nLink: <code>{link}</code>", parse_mode="HTML")


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
            "💡 <b>ʜᴏᴡ ᴛᴏ ᴀ提ᴅ ᴄᴏᴍʙᴏ ᴍᴀɴᴜᴀʟʟʏ:</b>\n\n"
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
