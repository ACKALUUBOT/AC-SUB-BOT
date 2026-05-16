import sys
import os
from telebot import types
from utils import bot
import config

# Python path correction taaki 'start' module project me kahin se bhi successfully import ho sake
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Plugins se functions import ho rahe hain
try:
    from plugins.story import start_add_story 
    from plugins.admin import add_start, remove_user_start, list_channels
except Exception as e:
    print(f"Error importing plugins: {e}")

# ─── 1. ADMIN BUTTONS HANDLER (Fix for Add & Remove) ───
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_menu_buttons(call):
    if call.from_user.id != config.ADMIN_ID:
        return bot.answer_callback_query(call.id, "❌ Access Denied!", show_alert=True)

    action = call.data.split('_')[1]
    bot.answer_callback_query(call.id)

    if action == "story":
        start_add_story(call.message)
    elif action == "add":
        add_start(call.message)
    elif action == "channels":
        list_channels(call.message)
    elif action == "remove":
        remove_user_start(call.message)


RESOLVED) ───
@bot.callback_query_handler(func=lambda call: call.data == "back_to_start")
def back_to_start_handler(call):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
        
    # Safe Import wrapper pattern block for runtime protection
    try:
        import start
        start.start_handler(call.message)
    except ModuleNotFoundError:
        try:
            from plugins import start
            start.start_handler(call.message)
        except Exception as err:
            bot.send_message(call.message.chat.id, f"❌ System routing breakdown error: <code>{str(err)}</code>", parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data == "my_plan")
def user_dashboard_link(call):
    bot.answer_callback_query(call.id, "📊 Loading your plans...")
