import urllib.parse
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from utils import bot, get_time_string
from database import channels_col, users_col
import config
import time
from plugins.start import USER_STATES
from plugins.store import get_items_by_category_markup, get_categories_markup, get_store_text

# ===================================================
# --- EXTRA CONFIG: FRESH START MENU RE-LOAD ---
# ===================================================
def send_home_menu(chat_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))

    bot.send_message(
        chat_id, 
        "❌ <b>ᴘᴀʏᴍᴇɴᴛ ᴄᴀɴᴄᴇʟʟᴇᴅ!</b>\n\nAapka current payment process rok diya gaya hai. Aap niche diye gaye menu se fir se shuru kar sakte hain:", 
        reply_markup=markup, 
        parse_mode="HTML"
    )


# --- 1. PAYMENT SELECTION ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('select_'))
def confirm_step(call):
    parts = call.data.split('_')
    mins = parts[-1]               
    item_id = "_".join(parts[1:-1]) 
    
    data = channels_col.find_one({"item_id": item_id}) or \
           channels_col.find_one({"channel_id": int(item_id) if item_id.replace('-','').isdigit() else 0})
    
    if not data: 
        return bot.answer_callback_query(call.id, f"❌ Data not found! (ID: {item_id})", show_alert=True)

    if data.get('is_combo'):
        price = data['price']
        display_name = data.get('combo_name', 'Premium Combo')
    elif 'story_name' in data:
        price = data['price']
        display_name = data.get('story_name')
    else:
        price = data['plans'].get(mins, "0") if isinstance(data.get('plans'), dict) else data.get('price', '0')
        display_name = data.get('name', 'Premium Channel')
    
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("💳 ᴘᴀʏ ᴠɪᴀ ǫʀ sᴄᴀɴ", callback_data=f"man_{item_id}_{mins}_qr"),
        InlineKeyboardButton("📲 ᴘᴀʏ ᴠɪ VIA ᴜᴘɪ ɪᴅ", callback_data=f"man_{item_id}_{mins}_upi"),
        InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ ᴘᴀʏᴍᴇɴᴛ", callback_data="cancel_payment")
    )
    
    text = (
        f"<b>🛒 ᴄᴏɴғɪʀᴍ sᴇʟᴇᴄᴛɪᴏɴ</b>\n"
        f"────────────────────\n"
        f"📦 ɪᴛᴇᴍ: <b>{display_name}</b>\n"
        f"💰 ᴀᴍᴏᴜɴᴛ: <b>₹{price}</b>\n\n"
        f"➔ Payment method select karein:"
    )
    
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

    bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="HTML")


# --- 2. MANUAL PAYMENT SYSTEM ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('man_'))
def manual_pay(call):
    parts = call.data.split('_')
    mode = parts[-1]                
    mins = parts[-2]                
    item_id = "_".join(parts[1:-2]) 
    
    data = channels_col.find_one({"item_id": item_id}) or \
           channels_col.find_one({"channel_id": int(item_id) if item_id.replace('-','').isdigit() else 0})
    
    if not data:
        return bot.answer_callback_query(call.id, "❌ Data Error on Payment!", show_alert=True)

    if data.get('is_combo') or 'story_name' in data:
        price = data['price']
    else:
        price = data['plans'].get(mins, "0") if isinstance(data.get('plans'), dict) else data.get('price', '0')
        
    upi_string = f"upi://pay?pa={config.UPI_ID}&am={price}&cu=INR&tn=Pay_{item_id}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=350x350&data={urllib.parse.quote(upi_string)}"
    
    markup = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("✅ sᴜʙᴍɪᴛ sᴄʀᴇᴇɴsʜᴏᴛ", callback_data=f"paid_{item_id}_{mins}"),
        InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ ᴘᴀʏᴍᴇɴᴛ", callback_data="cancel_payment")
    )

    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

    if mode == "qr":
        bot.send_photo(call.message.chat.id, qr_url, caption=f"📥 <b>ǫʀ sᴄᴀɴɴᴇʀ</b>\n\nAmount: <b>₹{price}</b>\n\n➔ Pay karke niche wala button dabayein.", reply_markup=markup, parse_mode="HTML")
    else:
        bot.send_message(call.message.chat.id, f"📲 <b>ᴜᴘɪ ɪᴅ:</b> <code>{config.UPI_ID}</code>\nAmount: <b>₹{price}</b>\n\n➔ Pay karne ke baad niche button dabayein.", reply_markup=markup, parse_mode="HTML")


# --- 3. DIRECT SCREENSHOT SUBMISSION ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('paid_'))
def handle_paid(call):
    parts = call.data.split('_')
    mins = parts[-1]
    item_id = "_".join(parts[1:-1])
    bot.answer_callback_query(call.id)
    
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ ᴘᴀʏᴍᴇɴᴛ", callback_data="cancel_payment"))
        
    msg = bot.send_message(
        call.message.chat.id, 
        "📸 Payment ka <b>Screenshot</b> bhejein:\n\n"
        "➔ <i>Agar cancel karna chahte hain toh niche button par click karein ya chat me <code>/cancel</code> likhein.</i>", 
        reply_markup=markup, 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, send_request_to_admin, item_id, mins)

def send_request_to_admin(message, item_id, mins):
    if message.text and message.text.lower() in ['/cancel', 'cancel']:
        return send_home_menu(message.chat.id)

    if message.content_type != 'photo':
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ ᴘᴀʏᴍᴇɴᴛ", callback_data="cancel_payment"))
        msg = bot.send_message(
            message.chat.id, 
            "❌ Please sirf Photo (Screenshot) bhejein!\n"
            "Cancel karne ke liye <code>/cancel</code> likhein ya neeche click karein:", 
            reply_markup=markup, 
            parse_mode="HTML"
        )
        bot.register_next_step_handler(msg, send_request_to_admin, item_id, mins)
        return
    
    photo_id = message.photo[-1].file_id
    data = channels_col.find_one({"item_id": item_id}) or \
           channels_col.find_one({"channel_id": int(item_id) if item_id.replace('-','').isdigit() else 0})
    
    if not data:
        return bot.send_message(message.chat.id, "❌ Something went wrong, item not found!")

    display_name = data.get('combo_name') or data.get('story_name') or data.get('name')
    bot.send_message(message.chat.id, "⏳ <b><b>ʀᴇǫᴜᴇsᴛ sᴇɴᴛ!</b></b>\nAdmin check karke aapka access on kar dega.")
    
    markup = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("✅ Approve", callback_data=f"app_{message.from_user.id}_{item_id}_{mins}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"rej_{message.from_user.id}"),
        InlineKeyboardButton("💬 Support", url=f"tg://openmessage?user_id={message.from_user.id}")
    )
    
    admin_text = f"📥 <b>ɴᴇᴡ ᴘᴀʏᴍᴇɴᴛ ʀᴇǫᴜᴇsᴛ</b>\n────────────────────\n👤 User ID: <code>{message.from_user.id}</code>\n📦 Item: <b>{display_name}</b>\n⏳ Plan: {mins if mins != 'manual' else 'Lifetime'}"
    bot.send_photo(config.ADMIN_ID, photo_id, caption=admin_text, reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data == "cancel_payment")
def process_inline_cancel(call):
    bot.answer_callback_query(call.id, "Process Cancelled!")
    bot.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    return send_home_menu(call.message.chat.id)


# --- 4. ADMIN APPROVAL CONTROL PANEL ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('app_'))
def admin_approve(call):
    parts = call.data.split('_')
    u_id = parts[1]
    mins = parts[-1]
    item_id = "_join".join(parts[2:-1]) if "_join" in call.data else "_".join(parts[2:-1])
    
    data = channels_col.find_one({"item_id": item_id}) or \
           channels_col.find_one({"channel_id": int(item_id) if item_id.replace('-','').isdigit() else 0})
    
    if not data: 
        return bot.answer_callback_query(call.id, "❌ Data not found on Approval!", show_alert=True)
    
    expiry = int(time.time()) + (int(mins) * 60) if mins != 'manual' else int(time.time()) + (365*24*60*60)
    markup = InlineKeyboardMarkup(row_width=1)

    # ─── CASE A: COMBO PACK APPROVAL ───
    if data.get('is_combo') and 'channels_list' in data:
        msg = "🎁 <b><b><b><b>ᴄᴏᴍʙᴏ ᴘᴀᴄᴋ ᴀᴘᴘʀᴏᴠᴇᴅ!</b></b></b></b>\n\nAapko sabhi linked channels ka access de diya gaya hai. Niche diye buttons se join karein:\n\n"
        for ch_id in data['channels_list']:
            users_col.update_one({"user_id": int(u_id), "channel_id": int(ch_id)}, {"$set": {"expiry": expiry}}, upsert=True)
            try:
                invite = bot.create_chat_invite_link(int(ch_id), member_limit=1)
                ch_info = channels_col.find_one({"channel_id": int(ch_id)})
                ch_title = ch_info.get('name') or ch_info.get('story_name') if ch_info else f"VIP Channel {ch_id}"
                markup.add(InlineKeyboardButton(f"📢 Join: {ch_title}", url=invite.invite_link))
            except Exception as e:
                print(f"Combo Link Error: {e}")
        msg += "⚠️ <i>Links single-use hain, ek baar join hone ke baad automatic expire ho jayengi!</i>"

    # ─── CASE B: FORWARDED CHANNEL (/add Flow) ───
    elif 'channel_id' in data and not data.get('story_name'):
        target_channel = int(data['channel_id'])
        users_col.update_one({"user_id": int(u_id), "channel_id": target_channel}, {"$set": {"expiry": expiry}}, upsert=True)
        try:
            # Strict Single-use Link generation
            invite = bot.create_chat_invite_link(chat_id=target_channel, member_limit=1, name=f"Paid_{u_id}")
            markup.add(InlineKeyboardButton("🔐 JOIN PREMIUM CHANNEL", url=invite.invite_link))
            
            validity_display = data.get('validity', mins)
            msg = (
                f"✅ <b><b>ᴀᴘᴘʀᴏᴠᴇᴅ!</b></b>\n\n"
                f"📂 <b>ᴄʜᴀɴɴᴇʟ:</b> <b>{data.get('name', 'VIP Channel')}</b>\n"
                f"⏱️ <b><b>ᴠᴀʟɪᴅɪᴛʏ:</b></b> {validity_display if validity_display != 'manual' else 'Lifetime'}\n\n"
                f"Join karne ke liye neeche button par click karein:\n\n"
                f"⚠️ <i>Yeh link single use hai, ek baar use hone ke baad automatic expire ho jayegi!</i>"
            )
        except Exception as e: 
            print(f"Error: {e}")
            msg = "✅ <b>ᴀᴘᴘʀᴏᴠᴇᴅ!</b>\n\nBot link generate nahi kar saka, admin rights setup check karein."

    # ─── CASE C: MANUAL PREMIUM STORY (/add_story Flow) ───
    else:
        users_col.update_one({"user_id": int(u_id), "channel_id": data.get('channel_id', 0)}, {"$set": {"expiry": expiry}}, upsert=True)
        target_link = data.get('bot_link') or data.get('final_link') or 'https://t.me'
        
        markup.add(InlineKeyboardButton("🚀 sᴛᴀʀᴛ sᴛᴏʀỹ", url=target_link))
        
        platform_info = f"\n📂 Platform: <code>{data.get('source')}</code>" if data.get('source') else ""
        msg = (
            f"🎉 <b>ᴘᴀʏᴍᴇɴᴛ ᴀᴘᴘʀᴏᴠᴇᴅ!</b>\n"
            f"────────────────────\n"
            f"📖 <b>sᴛᴏʀʏ:</b> {data.get('story_name', 'Premium Story')}"
            f"{platform_info}\n"
            f"💰 <b><b>ᴘʀɪᴄᴇ:</b></b> ₹{data.get('price', '49')}\n"
            f"────────────────────\n"
            f"➔ Niche diye gaye button par click karke apni full story access karein 👇"
        )

    try:
        if 'story_name' in data and data.get('file_id'):
            bot.send_photo(u_id, photo=data['file_id'], caption=msg, reply_markup=markup, parse_mode="HTML", protect_content=True)
        else:
            bot.send_message(u_id, msg, reply_markup=markup, parse_mode="HTML", protect_content=True)
    except Exception as e:
        print(f"Delivery Error: {e}")
        
    bot.edit_message_caption(f"✅ Approved for User: {u_id}", call.message.chat.id, call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('rej_'))
def admin_reject(call):
    u_id = call.data.split('_')[1]
    bot.edit_message_caption("❌ Payment Rejected!", call.message.chat.id, call.message.message_id)
    bot.send_message(u_id, "❌ Aapka payment reject ho gaya hai. Support se baat karein.")


# --- 5. AUTOMATIC LINK REVOKE ---
@bot.chat_member_handler()
def handle_chat_member_updates(update):
    if update.chat.type != "channel":
        return

    if update.new_chat_member.status == "member" and update.old_chat_member.status in ["left", "kicked", "restricted"]:
        if update.invite_link and update.invite_link.invite_link:
            used_link = update.invite_link.invite_link
            channel_id = update.chat.id
            try:
                bot.revoke_chat_invite_link(chat_id=channel_id, invite_link=used_link)
                print(f"[SUCCESS] Revoked: {used_link}")
            except Exception as e:
                print(f"[ERROR] Revoke failed: {e}")
