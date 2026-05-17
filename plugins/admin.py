import uuid
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import channels_col
from utils import bot, get_time_string
from datetime import datetime
import config

# Temporary state memory registration flows ke liye
ADMIN_SETUP_STATE = {}

# =====================================================================
# ─── FLOW 1: FORWARDED CHANNEL REGISTRATION (/add) ───
# =====================================================================

@bot.callback_query_handler(func=lambda call: call.data == "admin_add")
def admin_add_channel_callback(call):
    bot.answer_callback_query(call.id)
    if call.from_user.id != config.ADMIN_ID:
        return bot.send_message(call.message.chat.id, "❌ Only admin can access this.")
        
    msg = bot.send_message(
        call.message.chat.id, 
        "📺 <b>[ᴄʜᴀɴɴᴇʟ sᴇᴛᴜᴘ] sᴛᴇᴘ 𝟷:</b>\n\nJis premium private channel ko add karna hai, uski koi bhi ek post yahan <b>Forward</b> kijiye:\n\n<i>⚠️ Note: Bot us channel me Admin hona chahiye taaki invite link bana sake!</i>",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_forwarded_channel)

def process_forwarded_channel(message):
    if message.text and message.text.startswith('/'): return
    admin_id = message.from_user.id

    if not message.forward_from_chat:
        msg = bot.send_message(message.chat.id, "⚠️ Kripya post ko direct channel se hi forward karein. Dobara try karein:")
        return bot.register_next_step_handler(msg, process_forwarded_channel)

    channel_id = message.forward_from_chat.id
    channel_name = message.forward_from_chat.title

    ADMIN_SETUP_STATE[admin_id] = {
        "channel_id": int(channel_id),
        "name": channel_name,
        "is_combo": False,
        "item_id": f"chan_{str(uuid.uuid4())[:8]}"
    }

    msg = bot.send_message(
        message.chat.id, 
        f"💰 <b>[ᴄʜᴀɴɴᴇʟ sᴇᴛᴜᴘ] sᴛᴇᴘ 𝟸 (ᴘʀɪᴄɪɴɢ):</b>\n\nChannel: <b>{channel_name}</b>\n\nIs channel ka subscription price set karein.\n\n"
        "<b>Format 1 (Single Price):</b>\n<code>99</code>\n\n"
        "<b>Format 2 (Multi Plans):</b>\n<code>60:49,1440:99,10080:199</code>\n"
        "<i>(60 mins=49rs, 1 din=99rs)</i>",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, save_channel_with_price)

def save_channel_with_price(message):
    if message.text and message.text.startswith('/'): return
    admin_id = message.from_user.id
    price_input = message.text.strip()

    if admin_id not in ADMIN_SETUP_STATE:
        return bot.send_message(message.chat.id, "❌ Session expired.")

    plans_dict = {}
    final_price = "49"

    if ":" in price_input:
        try:
            pairs = price_input.split(",")
            for p in pairs:
                mins, rs = p.split(":")
                plans_dict[mins.strip()] = rs.strip()
            final_price = list(plans_dict.values())[0]
        except:
            bot.send_message(message.chat.id, "❌ Invalid multi-plan format! Default Price ₹49 set ho gaya hai.")
    else:
        final_price = price_input if price_input.isdigit() else "49"

    channel_data = ADMIN_SETUP_STATE[admin_id]
    channel_data["price"] = final_price
    channel_data["plans"] = plans_dict if plans_dict else None
    channel_data["timestamp"] = datetime.now().timestamp()

    channels_col.update_one(
        {"channel_id": channel_data["channel_id"]},
        {"$set": channel_data},
        upsert=True
    )

    bot.send_message(message.chat.id, f"✅ <b>ᴘʀᴇᴍɪᴜᴍ ᴄʜᴀɴɴᴇʟ sᴀᴠᴇᴅ!</b>\n\n📢 {channel_data['name']}\n💳 Base Price: ₹{final_price}", parse_mode="HTML")
    del ADMIN_SETUP_STATE[admin_id]


# =====================================================================
# ─── FLOW 2: MANUAL COMBO BUNDLE REGISTRATION (/admin_combo) ───
# =====================================================================

@bot.callback_query_handler(func=lambda call: call.data == "admin_combo")
def admin_combo_callback(call):
    bot.answer_callback_query(call.id)
    if call.from_user.id != config.ADMIN_ID:
        return bot.send_message(call.message.chat.id, "❌ Only admin can access this.")
        
    msg = bot.send_message(
        call.message.chat.id, 
        "🎁 <b>[ᴄᴏᴍʙᴏ sᴇᴛᴜᴘ] sᴛᴇᴘ 𝟷:</b>\n\nApne Combo Pack ka ek attractive <b>Naam (Title)</b> likh kar bhejiye:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_combo_name)

def process_combo_name(message):
    if message.text and message.text.startswith('/'): return
    admin_id = message.from_user.id
    
    ADMIN_SETUP_STATE[admin_id] = {
        "combo_name": message.text.strip(),
        "is_combo": True,
        "item_id": f"combo_{str(uuid.uuid4())[:8]}"
    }
    
    msg = bot.send_message(
        message.chat.id,
        "📝 <b>[ᴄᴏᴍʙᴏ sᴇᴛᴜᴘ] sᴛᴇᴘ 𝟸:</b>\n\nIs combo bundle ka ek acha sa <b>Description</b> likhiye:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_combo_description)

def process_combo_description(message):
    if message.text and message.text.startswith('/'): return
    admin_id = message.from_user.id
    if admin_id not in ADMIN_SETUP_STATE: return
        
    ADMIN_SETUP_STATE[admin_id]["description"] = message.text.strip()
    msg = bot.send_message(message.chat.id, "💰 <b>[ᴄᴏᴍʙᴏ sᴇᴛᴜᴘ] sᴛᴇᴘ 𝟛:</b>\n\nIs combo bundle ka <b>Price (₹)</b> bhejiye:", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_combo_price)

def process_combo_price(message):
    if message.text and message.text.startswith('/'): return
    admin_id = message.from_user.id
    price_input = message.text.strip()
    
    if not price_input.isdigit():
        msg = bot.send_message(message.chat.id, "⚠️ Kripya sirf number bhejiye. Dobara price daaliye:")
        return bot.register_next_step_handler(msg, process_combo_price)
        
    ADMIN_SETUP_STATE[admin_id]["price"] = price_input
    
    msg = bot.send_message(
        message.chat.id,
        "🆔 <b>[ᴄᴏᴍʙᴏ sᴇᴛᴜᴘ] sᴛᴇᴘ 𝟜 (ʟᴀsᴛ sᴛᴇᴘ):</b>\n\nIs combo pack ke sabhi <b>Channels ki Telegram ID</b> comma ( , ) lagakar bhejiye:\n<code>-100123456789,-100987654321</code>",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_combo_channels_and_save)

def process_combo_channels_and_save(message):
    if message.text and message.text.startswith('/'): return
    admin_id = message.from_user.id
    channels_input = message.text.strip().replace(" ", "")
    
    if admin_id not in ADMIN_SETUP_STATE: return

    try:
        channel_ids_list = [int(cid) for cid in channels_input.split(",") if cid]
    except ValueError:
        msg = bot.send_message(message.chat.id, "⚠️ Invalid IDs Format! Dobara sahi numeric IDs bhejiye:")
        return bot.register_next_step_handler(msg, process_combo_channels_and_save)

    combo_data = ADMIN_SETUP_STATE[admin_id]
    combo_data["channels_list"] = channel_ids_list
    combo_data["timestamp"] = datetime.now().timestamp()
    
    channels_col.insert_one(combo_data)
    bot.send_message(message.chat.id, f"✅ <b>ᴄᴏᴍʙᴏ sᴀᴠᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n\n🎁 Pack: {combo_data['combo_name']}\n📊 Channels: {len(channel_ids_list)} Linked.", parse_mode="HTML")
    del ADMIN_SETUP_STATE[admin_id]


# =====================================================================
# ─── FLOW 3: MANAGE & LIST ALL CHANNELS/ITEMS (`⚙️ ᴍᴀɴᴀɢᴇ ᴀʟʟ`) ───
# =====================================================================

@bot.callback_query_handler(func=lambda call: call.data == "admin_channels")
def admin_manage_channels_callback(call):
    """Admin ko total added content ki active list dikhane ke liye"""
    bot.answer_callback_query(call.id)
    if call.from_user.id != config.ADMIN_ID: return

    all_items = list(channels_col.find())
    if not all_items:
        return bot.send_message(call.message.chat.id, "📁 <b>sᴛᴏʀᴇ ᴇᴍᴘᴛʏ:</b> Database me filhal koi data nahi mila.", parse_mode="HTML")

    report = "⚙️ <b>ᴄʜᴀɴɴᴇʟ & sᴛᴏʀʏ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ᴘᴀɴᴇʟ</b>\n──────────────────────────\n\n"
    markup = InlineKeyboardMarkup(row_width=1)

    for idx, item in enumerate(all_items, start=1):
        db_id = item.get('item_id') or item.get('channel_id')
        
        if item.get('is_combo'):
            title = f"🎁 Combo: {item['combo_name']} (₹{item['price']})"
        elif 'story_name' in item:
            title = f"🎬 Story: {item['story_name']} [{item.get('source', 'audio')}] (₹{item['price']})"
        else:
            title = f"📢 Chan: {item.get('name', 'VIP Channel')} (₹{item['price']})"
            
        report += f"<b>{idx}.</b> <code>{title}</code>\n"
        # Har item ke niche direct use delete karne ka inline button
        markup.add(InlineKeyboardButton(f"🗑️ Delete: {title[:25]}...", callback_data=f"dropitem_{db_id}"))

    markup.add(InlineKeyboardButton("⬅️ CLOSE MANAGEMENT", callback_data="back_to_start"))
    bot.send_message(call.message.chat.id, report, reply_markup=markup, parse_mode="HTML")


# =====================================================================
# ─── FLOW 4: REMOVE BUTTON LOGIC (TRIGGER DETECT & DROP ACTION) ───
# =====================================================================

@bot.callback_query_handler(func=lambda call: call.data.startswith("dropitem_"))
def admin_drop_item_confirm(call):
    """List me se delete button click hone par use database se urane ke liye"""
    bot.answer_callback_query(call.id)
    if call.from_user.id != config.ADMIN_ID: return

    target_id = call.data.replace("dropitem_", "")
    
    # Mongo strict query deletion sequence
    query = {"$or": [{"item_id": target_id}, {"channel_id": int(target_id) if target_id.replace('-','').isdigit() else 0}]}
    deleted = channels_col.delete_one(query)

    if deleted.deleted_count > 0:
        bot.answer_callback_query(call.id, "✅ Item database se permanently delete ho gaya!", show_alert=True)
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        # List refresh logic auto trigger
        return admin_manage_channels_callback(call)
    else:
        bot.send_message(call.message.chat.id, "❌ Error: Item delete nahi ho paya ya nahi mila.")


@bot.callback_query_handler(func=lambda call: call.data == "admin_remove")
def admin_remove_shortcut_callback(call):
    """Direct shortcut panel handle logic redirecting to strict listing control"""
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "💡 <i>Loading item selection map... Use dynamic list to remove items safely.</i>", parse_mode="HTML")
    return admin_manage_channels_callback(call)
