import logging
from datetime import datetime
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot, get_time_string
import config

# Setup Logger for production tracking
logger = logging.getLogger(__name__)

# Plugins se functions import safe/try block me
try:
    from plugins.story import start_add_story 
    from plugins.admin import add_start, remove_user_start, list_channels
except Exception as e:
    logger.error(f"Error importing admin execution plugins: {e}")

# ─── EXTRA UTILS FOR DATABASE (AGAR APNE IMPORT NA KIYA HO) ───
# Note: Ensure database details are imported correctly
try:
    from database import channels_col, users_col
except Exception as e:
    logger.error(f"Database import error: {e}")


# ─── STRUCTURE 1: REUSABLE MARKUP GENERATORS ───

def get_main_menu_markup(user_id):
    """Main start dashboard menu markup generates safely without circular imports"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("✨ ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ sᴛᴏʀᴇ ✨", callback_data="open_store"))
    markup.add(
        InlineKeyboardButton("📊 ᴍʏ ᴅᴀsʜʙᴏᴀʀᴅ", callback_data="my_plan"),
        InlineKeyboardButton("💬 sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{config.CONTACT_USERNAME}")
    )
    if user_id == config.ADMIN_ID:
        markup.add(
            InlineKeyboardButton("➕ ᴀᴅᴅ sᴛᴏʀʏ", callback_data="admin_story"), 
            InlineKeyboardButton("📺 ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", callback_data="admin_add")
        )
        markup.add(
            InlineKeyboardButton("⚙️ ᴍᴀɴᴀɢᴇ ᴀʟʟ", callback_data="admin_channels"), 
            InlineKeyboardButton("❌ ʀᴇᴍᴏᴠᴇ sᴜʙ", callback_data="admin_remove")
        )
    return markup


def get_store_markup():
    """Generates the premium store list directly from DB"""
    all_items = list(channels_col.find({
        "$or": [{"story_name": {"$exists": True}}, {"name": {"$exists": True}}]
    }))
    
    markup = InlineKeyboardMarkup(row_width=1)
    if not all_items:
        markup.add(InlineKeyboardButton("🚫 No Items Available", callback_data="none"))
    else:
        for item in all_items:
            db_id = item.get('item_id') or item.get('channel_id')
            name = item.get('story_name') or item.get('name', 'Premium Channel')
            icon = "🎬" if 'story_name' in item else "💎"
            
            # OPTION: Direct Popup Card View (Smooth User Experience)
            markup.add(InlineKeyboardButton(f"{icon} {name}", callback_data=f"view_card_{db_id}"))
            
    markup.add(InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))
    return markup


def send_detail_card(chat_id, data, message_id=None, is_new=False):
    """Generates and displays deep links / product descriptions inside the bot"""
    markup = InlineKeyboardMarkup(row_width=1)
    db_id = data.get('item_id') or data.get('channel_id')
    
    if 'story_name' in data:
        display_name = data['story_name']
        price_info = f"₹{data['price']}"
        episodes = data.get('episodes', 'Full Story')
        markup.add(InlineKeyboardButton(f"💳 ʙᴜʏ ɴᴏᴡ - {price_info}", callback_data=f"select_{db_id}_manual"))
        header = "🎬 <b>ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ ᴄᴀʀᴅ</b>"
    else:
        display_name = data.get('name', 'Premium Access')
        episodes = data.get('episodes', 'Full Access (All Episodes)')
        plans = data.get('plans', {})
        for p_time, p_price in plans.items():
            markup.add(InlineKeyboardButton(f"💳 {get_time_string(p_time)} - ₹{p_price}", callback_data=f"select_{db_id}_{p_time}"))
        header = "💎 <b>ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss ᴄᴀʀᴅ</b>"

    if data.get('demo_link') and data['demo_link'].lower() != 'skip':
        markup.add(InlineKeyboardButton("📺 ᴠɪᴇᴡ ǫᴜᴀʟɪᴛʏ ᴅᴇᴍᴏ", url=data['demo_link']))
    
    markup.add(InlineKeyboardButton("⬅️ ʙᴀᴄᴋ ᴛᴏ sᴛᴏʀᴇ", callback_data="open_store"))

    card_text = (
        f"{header}\n"
        f"────────────────────\n"
        f"📦 ɴᴀᴍᴇ: <b>{display_name}</b>\n"
        f"🎞️ ᴇᴘɪsᴏᴅᴇs: <b>{episodes}</b>\n"
        f"📊 sᴛᴀᴛᴜs: <code>Available</code>\n\n"
        f"📝 ᴅᴇsᴄʀɪᴘᴛɪᴏɴ:\n"
        f"<i>Premium quality. Instant access after payment.</i>\n"
        f"────────────────────"
    )

    photo = data.get('poster') or data.get('demo_link') or "https://via.placeholder.com/1024x512.png"

    try:
        if is_new:
            bot.send_photo(chat_id, photo, caption=card_text, reply_markup=markup, parse_mode="HTML")
        else:
            bot.delete_message(chat_id, message_id)
            bot.send_photo(chat_id, photo, caption=card_text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        bot.send_message(chat_id, card_text, reply_markup=markup, parse_mode="HTML")


# ─── STRUCTURE 2: COMMAND HANDLERS ───

@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    text = message.text.split()

    # Deep Linking Detection Setup
    if len(text) > 1:
        param = text[1]
        data = channels_col.find_one({"item_id": param}) or \
               channels_col.find_one({"channel_id": int(param) if param.replace('-','').isdigit() else 0})
        if data:
            return send_detail_card(message.chat.id, data, is_new=True)

    markup = get_main_menu_markup(user_id)
    title = "⚡ <b>ᴀᴅᴍɪɴ ᴍᴀsᴛᴇ r ᴘᴀɴᴇʟ</b>" if user_id == config.ADMIN_ID else "👋 <b>ᴡᴇʟᴄᴏᴍᴇ ᴍᴇᴍʙᴇʀ</b>"
    bot.send_message(message.chat.id, f"{title}\n\nPremium access aur content ke liye niche buttons use karein.", reply_markup=markup, parse_mode="HTML")


# ─── STRUCTURE 3: ALL FIXED CALLBACK HANDLERS ───

@bot.callback_query_handler(func=lambda call: True)
def global_callback_listener(call):
    u_id = call.from_user.id
    data = call.data
    
    # 1. Open Premium Store Layout
    if data == "open_store":
        bot.answer_callback_query(call.id)
        markup = get_store_markup()
        store_text = "✨ <b>ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ sᴛᴏʀᴇ</b> ✨\n────────────────────\nList se item select karein:"
        
        try:
            if call.message.content_type == 'photo':
                bot.delete_message(call.message.chat.id, call.message.message_id)
                bot.send_message(call.message.chat.id, store_text, reply_markup=markup, parse_mode="HTML")
            else:
                bot.edit_message_text(store_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to load store markup template: {e}")

    # 2. View Individual Cards
    elif data.startswith('view_card_'):
        bot.answer_callback_query(call.id)
        target_id = data.replace('view_card_', '')
        item_data = channels_col.find_one({"item_id": target_id}) or \
                    channels_col.find_one({"channel_id": int(target_id) if target_id.replace('-','').isdigit() else 0})
        if item_data:
            send_detail_card(call.message.chat.id, item_data, call.message.message_id)

    # 3. Back To Main Start Dashboard
    elif data == "back_to_start":
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        
        markup = get_main_menu_markup(u_id)
        title = "⚡ <b>ᴀᴅᴍɪɴ ᴍᴀsᴛᴇʀ ᴘᴀɴᴇʟ</b>" if u_id == config.ADMIN_ID else "👋 <b>ᴡᴇʟᴄᴏᴍᴇ ᴍᴇᴍʙᴇʀ</b>"
        bot.send_message(call.message.chat.id, f"{title}\n\nPremium access aur content ke liye niche buttons use karein.", reply_markup=markup, parse_mode="HTML")

    # 4. User Dashboard Plan Details Tracking
    elif data == "my_plan":
        bot.answer_callback_query(call.id, "📊 Fetching your active plans...")
        subs = list(users_col.find({"user_id": u_id}))
        if not subs:
            bot.send_message(call.message.chat.id, "❌ <b>No active plan found.</b>", parse_mode="HTML")
            return
            
        res = "👤 <b>ᴍʏ sᴜʙsᴄʀɪᴘᴛɪᴏɴs</b>\n\n"
        for s in subs:
            ch = channels_col.find_one({"channel_id": s['channel_id']})
            name = ch.get('story_name') or ch.get('name') if ch else "Item"
            res += f"📺 <b>{name}</b>\n⌛ Valid: <code>{datetime.fromtimestamp(s['expiry']).strftime('%d %b %Y')}</code>\n\n"
        bot.send_message(call.message.chat.id, res, parse_mode="HTML")

    # 5. Admin Prefix Dynamic Tracking (admin_story, admin_add, admin_channels, admin_remove)
    elif data.startswith('admin_'):
        if u_id != config.ADMIN_ID:
            return bot.answer_callback_query(call.id, "❌ Access Denied!", show_alert=True)
            
        bot.answer_callback_query(call.id)
        action = data.split('_')[1]
        
        try:
            if action == "story":
                start_add_story(call.message)
            elif action == "add":
                add_start(call.message)
            elif action == "channels":
                list_channels(call.message)
            elif action == "remove":
                remove_user_start(call.message)
        except NameError as e:
            bot.send_message(call.message.chat.id, f"⚠️ Backend plugin function missing or not imported correctly: {e}")


# ─── STRUCTURE 4: REQUISITE COMMANDS FOR ADMINS ───

@bot.message_handler(commands=['delete'])
def delete_item_handler(message):
    if message.from_user.id != config.ADMIN_ID: return
    text = message.text.split()
    if len(text) < 2: return bot.reply_to(message, "💡 Usage: /delete ID")
    target_id = text[1]
    channels_col.delete_one({"$or": [{"item_id": target_id}, {"channel_id": int(target_id) if target_id.replace('-','').isdigit() else 0}]})
    bot.reply_to(message, "✅ Task completed.")
