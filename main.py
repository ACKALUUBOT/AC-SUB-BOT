import os
from threading import Thread
import config
from utils import bot
from server import app
from scheduler import start_scheduler

# Plugins folder ke handlers register karne ke liye explicitly import karein
import plugins.start
import plugins.story
import plugins.admin
import plugins.custom_combo
import plugins.payment
import plugins.broadcast
try:
    import plugins.callback_handlers
except Exception as e:
    print(f"Callback handlers import warning: {e}")

if __name__ == '__main__':
    try:
        print("Cleaning up old connections...")
        bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print(f"Cleanup error: {e}")
    
    # 1. Flask Web Server running thread
    port = int(os.environ.get("PORT", 5000))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port, use_reloader=False)).start()
    
    # 2. Start Background Scheduler for Expiries
    start_scheduler()
    
    # 3. Start Telegram Bot Polling (With Anti-Conflict Protection)
    print("Bot setup separated successfully! Starting polling...")
    
    # skip_pending=True se purani bachi hui updates clear ho jayengi aur 409 Conflict nahi aayega
    bot.infinity_polling(
        allowed_updates=["message", "callback_query", "chat_member"],
        skip_pending=True,
        timeout=20,
        long_polling_timeout=10
    )
