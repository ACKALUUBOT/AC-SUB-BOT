import os
from threading import Thread
import config
from utils import bot
from server import app
from scheduler import start_scheduler

# Plugins folder ke handlers register karne ke liye explicitly import karein
import plugins.start
import plugins.admin
import plugins.payment
import plugins.broadcast

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
    
    # 3. Start Telegram Bot Polling (With Allowed Updates for Anti-Rejoin)
    print("Bot setup separated successfully! Starting polling...")
    
    # FIX: Yahan allowed_updates daal diya hai taaki chat_member_handler sahi se trigger ho sake
    bot.infinity_polling(allowed_updates=["message", "callback_query", "chat_member"])
