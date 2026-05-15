from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from database import users_col
from utils import bot

def check_expiries():
    expired = users_col.find({"expiry": {"$lte": datetime.now().timestamp()}})
    for user in expired:
        try:
            bot.ban_chat_member(user['channel_id'], user['user_id'])
            bot.unban_chat_member(user['channel_id'], user['user_id'])
            users_col.delete_one({"_id": user['_id']})
        except: 
            pass

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_expiries, 'interval', minutes=1)
    scheduler.start()
