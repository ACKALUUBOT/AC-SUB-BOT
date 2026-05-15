import time
import requests

if __name__ == '__main__':
    try:
        print("Cleaning up old connections...")
        bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        print(f"Cleanup error: {e}")
    
    # 1. Flask Web Server (Running on Thread)
    port = int(os.environ.get("PORT", 5000))
    # use_reloader=False zaroori hai thread mein chalane ke liye
    Thread(target=lambda: app.run(host='0.0.0.0', port=port, use_reloader=False)).start()
    
    # 2. Start Background Scheduler for Expiries
    start_scheduler()
    
    # 3. Start Telegram Bot Polling (with Auto-Restart Logic)
    print("Bot setup separated successfully! Polling started...")
    
    while True:
        try:
            # timeout=20 aur long_polling_timeout=20 se connection stable rehta hai
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
            print(f"📡 Connection Issue: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ Unexpected Error: {e}. Restarting...")
            time.sleep(10)
