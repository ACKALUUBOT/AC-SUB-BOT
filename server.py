import json
import razorpay
from flask import Flask, request, abort
import config
from utils import approve_user_logic

app = Flask('')

rzp_client = None
if config.RZP_KEY_ID and config.RZP_KEY_SECRET:
    rzp_client = razorpay.Client(auth=(config.RZP_KEY_ID, config.RZP_KEY_SECRET))

@app.route('/')
def home(): 
    return "Healthy"

@app.route('/razorpay_webhook', methods=['POST'])
def razorpay_webhook():
    if not config.RZP_WEBHOOK_SECRET or not rzp_client: 
        abort(400)
        
    webhook_signature = request.headers.get('X-Razorpay-Signature')
    payload = request.data
    try:
        rzp_client.utility.verify_webhook_signature(payload.decode('utf-8'), webhook_signature, config.RZP_WEBHOOK_SECRET)
        data = json.loads(payload)
        if data['event'] == 'payment.captured':
            notes = data['payload']['payment']['entity']['notes']
            approve_user_logic(int(notes['user_id']), int(notes['channel_id']), int(notes['mins']), "Razorpay Online")
    except: 
        abort(400)
    return 'OK', 200

