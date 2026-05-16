import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot
from database import users_col
import config

# ==========================================
# --- ADMIN BROADCAST SYSTEM (BULK SEND) ---
# ==========================================

@bot.message_handler(commands=['broadcast'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def start_broadcast(message):
    if message.from_user.id != config.ADMIN_ID: 
        return

    msg = bot.send_message(
        message.chat.id, 
        "📢 <b>ᴀᴅᴍɪɴ ʙʀᴏᴀᴅᴄᴀsᴛ:</b>\n\n"
        "Aap jo bhi message sabhi users ko bhejna chahte hain, woh yahan <b>Forward</b> karein ya direct <b>Type/Upload</b> karein.\n\n"
        "➔ <i>Isme Text, Photo, Video, Animation sab support hoga. Cancel karne ke liye <code>/cancel</code> likhein.</i>",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_broadcast)

def process_broadcast(message):
    if message.text and message.text.lower() in ['/cancel', 'cancel']:
        return bot.send_message(message.chat.id, "❌ Broadcast cancelled.")

    all_users = users_col.distinct("user_id")
    total_users = len(all_users)

    if total_users == 0:
        return bot.send_message(message.chat.id, "❌ Database mein koi user nahi mila!")

    status_msg = bot.send_message(message.chat.id, f"🚀 <b>Broadcast Shuru Ho Gaya Hai...</b>\n\n👥 Total Targets: <code>{total_users}</code>\n⏳ Processing...", parse_mode="HTML")

    threading.Thread(target=run_broadcast_loop, args=(message, all_users, status_msg.message_id)).start()

def run_broadcast_loop(media_msg, user_list, status_message_id):
    success = 0
    failed = 0
    total = len(user_list)
    chat_id = media_msg.chat.id

    for index, u_id in enumerate(user_list):
        try:
            bot.copy_message(
                chat_id=u_id, 
                from_chat_id=chat_id, 
                message_id=media_msg.message_id
            )
            success += 1
        except Exception:
            failed += 1

        if (index + 1) % 10 == 0 or (index + 1) == total:
            try:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_message_id,
                    text=f"📢 <b>ʙʀᴏᴀᴅᴄᴀsᴛ ɪɴ ᴘʀᴏɢʀᴇss:</b>\n"
                         f"────────────────────\n"
                         f"📊 Progress: <code>{index + 1}/{total}</code>\n"
                         f"✅ Successful: <code>{success}</code>\n"
                         f"❌ Failed/Blocked: <code>{failed}</code>",
                    parse_mode="HTML"
                )
            except:
                pass

    bot.send_message(
        chat_id, 
        f"🏁 <b>ʙʀᴏᴀᴅᴄᴀsᴛ ғɪɴɪsʜᴇᴅ!</b>\n"
        f"────────────────────\n"
        f"✅ Total Delivered: <code>{success}</code>\n"
        f"❌ Total Failed: <code>{failed}</code>\n"
        f"👥 Grand Total: <code>{total}</code>", 
        parse_mode="HTML"
    )
