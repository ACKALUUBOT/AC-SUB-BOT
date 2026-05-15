from utils import bot
import config
# Sabhi zaroori functions ko import kar rahe hain
from plugins.story import start_add_story 
from plugins.admin import add_start, remove_user_start, list_channels

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_menu_buttons(call):
    """
    Ye handler Start Menu ke Admin buttons ko handle karta hai.
    """
    # Security: Sirf aap (Admin) hi in buttons ko daba sakein
    if call.from_user.id != config.ADMIN_ID:
        return bot.answer_callback_query(call.id, "❌ Access Denied!", show_alert=True)

    action = call.data.split('_')[1]
    
    # Button ki loading hatane ke liye
    bot.answer_callback_query(call.id)

    # 1. Add Story Button
    if action == "story":
        start_add_story(call.message)
    
    # 2. Add Channel Button
    elif action == "add":
        add_start(call.message)
        
    # 3. Manage All Button
    elif action == "channels":
        list_channels(call.message)
        
    # 4. Remove User Button
    elif action == "remove":
        remove_user_start(call.message)

# ─── USER DASHBOARD HANDLER ───
@bot.callback_query_handler(func=lambda call: call.data == "my_plan")
def user_dashboard_link(call):
    """
    Dashboard button dabane par loading icon hatata hai.
    Main logic start.py mein pehle se hai.
    """
    bot.answer_callback_query(call.id, "📊 Loading your plans...")

