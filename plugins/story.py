import uuid
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot
from database import channels_col
import config

# --- ADMIN BUTTON SE DIRECT CALL HONE WALA FUNCTION ---
@bot.message_handler(commands=['add_story'])
def start_add_story(message):
    if message.from_user.id != config.ADMIN_ID: 
        return
    
    chat_id = message.chat.id
    
    msg = bot.send_message(
        chat_id, 
        "🎬 <b>sᴛᴏʀʏ sᴇᴛᴜᴘ:</b>\n\n"
        "Story ka naam kya hai?\n"
        "<i>(Aap direct <b>Photo</b> bhi bhej sakte hain, bas uske <b>Caption</b> mein Story ka naam likh dein)</i>", 
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, get_story_name)

def get_story_name(message):
    if message.text and message.text == "/cancel": 
        return bot.send_message(message.chat.id, "❌ Setup cancelled.")
    
    story_name = None
    file_id = None

    # CASE 1: Agar admin ne direct photo bheji hai caption ke sath
    if message.photo:
        file_id = message.photo[-1].file_id  
        # 🌟 User rule update: Title mein matlab ek line save hogi, baaki lines filter ho jayengi
        story_name = message.caption.split("\n")[0] if message.caption else "Untitled Story"
    
    # CASE 2: Agar admin ne normal text bheja hai
    elif message.text:
        story_name = message.text.split("\n")[0] # Safe side text ka bhi single line index block
    
    else:
        msg = bot.send_message(message.chat.id, "❌ Please ek valid text naam ya photo bhejein:")
        bot.register_next_step_handler(msg, get_story_name)
        return

    msg = bot.send_message(message.chat.id, "🔗 <b>ᴅᴇᴍᴏ ʟɪɴᴋ:</b>\nDemo channel ya video link dein (Ya 'skip' likhein):")
    bot.register_next_step_handler(msg, get_demo_link, story_name, file_id)

def get_demo_link(message, story_name, file_id):
    if message.text and message.text.lower() == 'skip':
        demo = None
    else:
        demo = message.text
        
    msg = bot.send_message(message.chat.id, "🤖 <b>ғɪɴᴀʟ ʙᴏᴛ ʟɪɴᴋ:</b>\nPayment ke baad milne wala main link dein:")
    bot.register_next_step_handler(msg, get_final_link, story_name, demo, file_id)

def get_final_link(message, story_name, demo, file_id):
    final_link = message.text
    msg = bot.send_message(message.chat.id, "💰 <b>ᴘʀɪᴄᴇ:</b>\nSirf number likhein (Example: 49):")
    bot.register_next_step_handler(msg, ask_platform_source, story_name, demo, final_link, file_id)

# 🌟 NEW STEP: Price ke baad source/platform poochne ke liye panel open hoga
def ask_platform_source(message, story_name, demo, final_link, file_id):
    if not message.text or not message.text.isdigit():
        msg = bot.send_message(message.chat.id, "❌ Price sirf number mein likhein:")
        bot.register_next_step_handler(msg, ask_platform_source, story_name, demo, final_link, file_id)
        return

    price = message.text
    
    # Platform dynamic selection keyboard markup
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✨ PRATILIPI FM", callback_data=f"strysrc_pratilipi"),
        InlineKeyboardButton("🔥 POCKET FM", callback_data=f"strysrc_pocket")
    )
    
    # Ek inline prompt bhejenge jiske message text mein saari details save rhengi temporary routing ke liye
    bot.send_message(
        message.chat.id, 
        f"🎯 <b>Choose Story Platform Category:</b>\n"
        f"──────────────────────────\n"
        f"📖 Story: <code>{story_name}</code>\n"
        f"💰 Price: <code>{price}</code>\n"
        f"🔗 Demo: <code>{demo or 'None'}</code>\n"
        f"🤖 Link: <code>{final_link}</code>\n"
        f"🖼️ Media ID: <code>{file_id or 'None'}</code>\n"
        f"──────────────────────────\n"
        f"Niche diye buttons se platform choose karein jahan ise store panel me show karna hai:",
        reply_markup=markup,
        parse_mode="HTML"
    )

# 🌟 NEW CALLBACK HANDLER: Buttons click hone par data trace karke final database save trigger karega
@bot.callback_query_handler(func=lambda call: call.data.startswith('strysrc_'))
def handle_story_source_callback(call):
    source = call.data.split('_')[1]
    msg_text = call.message.text
    chat_id = call.message.chat.id
    
    # Text metadata parsing mechanics to grab current values
    try:
        story_name = msg_text.split("Story: ")[1].split("\n")[0].strip()
        price = msg_text.split("Price: ")[1].split("\n")[0].strip()
        demo_raw = msg_text.split("Demo: ")[1].split("\n")[0].strip()
        final_link = msg_text.split("Link: ")[1].split("\n")[0].strip()
        file_id_raw = msg_text.split("Media ID: ")[1].split("\n")[0].strip()
