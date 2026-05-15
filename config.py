import os

BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
UPI_ID = os.getenv('UPI_ID')
CONTACT_USERNAME = os.getenv('CONTACT_USERNAME')

# Razorpay Configs
RZP_KEY_ID = os.getenv('RZP_KEY_ID', '')
RZP_KEY_SECRET = os.getenv('RZP_KEY_SECRET', '')
RZP_WEBHOOK_SECRET = os.getenv('RZP_WEBHOOK_SECRET', '')

