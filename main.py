import os
import sys
from threading import Thread
import config
from utils import bot
from server import app
from scheduler import start_scheduler

# Plugins folder ke handlers register karein
try:
    import plugins.start
    import plugins.admin
    import plugins.payment
    print("Plugins loaded successfully.")
except ImportError as e:
    print(f"Error loading plugins: {e}")
    sys.exit(1)

def run_flask():
    """Flask server ko run karne ke liye ek wrapper function"""
    port = int(os.environ.get("PORT", 5000))
    # production me 'waitress' use kar sakte hain:
    # from waitress import serve
    # serve(app, host='0.0.0.0', port=port)
    app.run(host='0.0.0.0', port=port, use_reloader=False, threaded=True)

if __name__ == '__main__':
    # 1. Cleanup old webhook connections safely
    try:
        print("Cleaning up old connections...")
        bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print(f"Cleanup error (Non-fatal): {e}")
    
    # 2. Flask Web Server running thread (Daemon thread banaya taaki main process ke sath exit ho sake)
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("Flask web server started.")
    
    # 3. Start Background Scheduler for Expiries
    try:
        start_scheduler()
        print("Scheduler started successfully.")
    except Exception as e:
        print(f"Failed to start scheduler: {e}")
    
    # 4. Start Telegram Bot Polling (Main thread ko block karega)
    print("Bot setup separated successfully! Starting polling...")
    try:
        # skip_pending=True updates ko drop karne me help karta hai agar bot band tha
        bot.infinity_polling(skip_pending=True)
    except KeyboardInterrupt:
        print("\nStopping bot gracefully...")
    except Exception as e:
        print(f"Bot polling crashed: {e}")
