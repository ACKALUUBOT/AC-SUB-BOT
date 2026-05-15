import json
import logging
import razorpay
from flask import Flask, request, abort
import config
from utils import approve_user_logic

# Setup Logging taaki production me errors trace ho sakein
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask('')

rzp_client = None
if config.RZP_KEY_ID and config.RZP_KEY_SECRET:
    rzp_client = razorpay.Client(auth=(config.RZP_KEY_ID, config.RZP_KEY_SECRET))

@app.route('/')
def home(): 
    return "Healthy", 200

@app.route('/razorpay_webhook', methods=['POST'])
def razorpay_webhook():
    if not config.RZP_WEBHOOK_SECRET or not rzp_client: 
        logger.error("Razorpay configuration missing.")
        abort(500)  # Internal Server Error kyunki config humari taraf se missing hai
        
    webhook_signature = request.headers.get('X-Razorpay-Signature')
    payload = request.data
    
    # 1. Verify Webhook Signature
    try:
        rzp_client.utility.verify_webhook_signature(
            payload.decode('utf-8'), 
            webhook_signature, 
            config.RZP_WEBHOOK_SECRET
        )
    except razorpay.errors.SignatureVerificationError as e:
        logger.warning(f"Invalid Webhook Signature: {e}")
        abort(400)  # Bad Request kyunki signature match nahi hua
    except Exception as e:
        logger.error(f"Unexpected error during verification: {e}")
        abort(400)

    # 2. Parse Data safely after successful verification
    try:
        data = json.loads(payload)
        event = data.get('event')
        
        if event == 'payment.captured':
            payment_entity = data['payload']['payment']['entity']
            notes = payment_entity.get('notes', {})
            
            # Safe data extraction
            user_id = notes.get('user_id')
            channel_id = notes.get('channel_id')
            mins = notes.get('mins')
            
            if user_id and channel_id and mins:
                # User approval logic executes here
                approve_user_logic(int(user_id), int(channel_id), int(mins), "Razorpay Online")
                logger.info(f"Successfully approved User {user_id} for Channel {channel_id}")
            else:
                logger.warning(f"Required fields missing in notes: {notes}")
                
        else:
            # Agar koi aur event hai (e.g., payment.failed), toh log karein par Razorpay ko 200 OK dein
            logger.info(f"Unhandled Razorpay event received: {event}")

    except Exception as e:
        # Yeh exception aapke logical code/database ki vajah se ho sakta hai
        logger.error(f"Error processing webhook payload: {e}", exc_info=True)
        # Yahan hum 200 return kar rahe hain taaki Razorpay baar-baar request bhej kar server loop na banaye, 
        # par logging se aapko pata chal jayega ki debug karna hai.
        return 'Internal Processing Failed But Webhook Received', 200

    return 'OK', 200
