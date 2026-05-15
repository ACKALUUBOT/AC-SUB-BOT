from utils import bot
import config
from telebot import types
# Plugins se functions import ho rahe hain
try:
    from plugins.story import start_add_story 
    from plugins.admin import add_start, remove_user_start, list_channels
except Exception as e:
    print(f"Error importing plugins: {e}")

# ─── 1. ADMIN BUTTONS HANDLER (Fix for Add & Remove) ───
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_menu_buttons(call):
    # Security Check
    if call.from_user.id != config.ADMIN_ID:
        return bot.answer_callback_query(call.id, "❌ Access Denied!", show_alert=True)

    # Action extract karna (e.g., 'admin_story' -> 'story')
    action = call.data.split('_')[1]
    bot.answer_callback_query(call.id)

    # Add Story Fix
    if action == "story":
        start_add_story(call.message)
    
    # Add Channel
    elif action == "add":
        add_start(call.message)
        
    # Manage All
    elif action == "channels":
        list_channels(call.message)
        
    # Remove User Fix (admin_remove)
    elif action == "remove":
        remove_user_start(call.message)

# ─── 2. PREMIUM STORE HANDLER (Naya Button Fix) ───
@bot.callback_query_handler(func=lambda call: call.data == "open_store")
def open_store_logic(call):
    from database import channels_col
    bot.answer_callback_query(call.id)
    
    # Database se stories nikalna
    all_stories = list(channels_col.find({"story_name": {"$exists": True}}))
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not all_stories:
        markup.add(types.InlineKeyboardButton("🚫 No Stories Available", callback_data="none"))
    else:
        for story in all_stories:
            # Button text format: Name — Price
            btn_text = f"📖 {story['story_name']} — ₹{story['price']}"
            # Deep link redirect
            url = f"https://t.me/{bot.get_me().username}?start={story['item_id']}"
            markup.add(types.InlineKeyboardButton(btn_text, url=url))
            
    markup.add(types.InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))
    
    store_text = (
        "✨ <b>ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ sᴛᴏʀᴇ</b> ✨\n"
        "────────────────────\n"
        "Niche hamari sabhi exclusive stories ki list hai.\n\n"
        "➔ <b>Process:</b> Story select karein aur plan choose karke access payein."
    )
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=store_text,
        reply_markup=markup,
        parse_mode="HTML"
    )

# ─── 3. BACK & DASHBOARD HANDLERS ───
@bot.callback_query_handler(func=lambda call: call.data == "back_to_start")
def back_to_start_handler(call):
    from start import start_handler
    bot.answer_callback_query(call.id)
    # Message delete karke dashboard restart karna
    bot.delete_message(call.message.chat.id, call.message.message_id)
    start_handler(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "my_plan")
def user_dashboard_link(call):
    # Sirf loading hatana, main logic start.py sambhaal lega
    bot.answer_callback_query(call.id, "📊 Loading your plans...")
