import uuid
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot
from database import channels_col
import config

# --- 1. START ADD STORY ---
@bot.message_handler(commands=['add_story'])
def start_add_story(message):
    if message.from_user.id != config.ADMIN_ID: return
    
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "🎬 <b>sᴛᴏʀʏ sᴇᴛᴜᴘ:</b>\n\nStory ka naam kya hai? (User ko yahi dikhega)", parse_mode="HTML")
    bot.register_next_step_handler(msg, get_story_name)

def get_story_name(message):
    if message.text == "/cancel": return bot.send_message(message.chat.id, "❌ Setup cancelled.")
    story_name = message.text
    msg = bot.send_message(chat_id, "🎞️ <b>ᴇᴘɪsᴏᴅᴇs:</b>\nKitne episodes hain? (Example: Full Story):")
    bot.register_next_step_handler(msg, get_episodes, story_name)

def get_episodes(message, story_name):
    episodes = message.text
    msg = bot.send_message(message.chat.id, "🖼️ <b>ᴘᴏsᴛᴇʀ ʟɪɴᴋ:</b>\nPoster/Photo ka direct link dein:")
    bot.register_next_step_handler(msg, get_poster, story_name, episodes)

def get_poster(message, story_name, episodes):
    poster = message.text
    msg = bot.send_message(message.chat.id, "📺 <b>ᴅᴇᴍᴏ ʟɪɴᴋ:</b>\nTrailer ya Demo link dein (Ya 'skip' likhein):")
    bot.register_next_step_handler(msg, get_demo_link, story_name, episodes, poster)

def get_demo_link(message, story_name, episodes, poster):
    demo = None if message.text.lower() == 'skip' else message.text
    msg = bot.send_message(message.chat.id, "🤖 <b>ғɪɴᴀʟ ʙᴏᴛ ʟɪɴᴋ:</b>\nPayment ke baad milne wala main link dein:")
    bot.register_next_step_handler(msg, get_final_link, story_name, episodes, poster, demo)

def get_final_link(message, story_name, episodes, poster, demo):
    final_link = message.text
    msg = bot.send_message(message.chat.id, "💰 <b>ᴘʀɪᴄᴇ:</b>\nSirf number likhein (Example: 10):")
    bot.register_next_step_handler(msg, save_story, story_name, episodes, poster, demo, final_link)

def save_story(message, story_name, episodes, poster, demo, final_link):
    if not message.text.isdigit():
        msg = bot.send_message(message.chat.id, "❌ Price sirf number mein likhein:")
        bot.register_next_step_handler(msg, save_story, story_name, episodes, poster, demo, final_link)
        return

    price = message.text
    story_id = str(uuid.uuid4())[:10] 
    
    # DATABASE ENTRY - Yahan dhyan dein!
    channels_col.insert_one({
        "item_id": story_id,
        "story_name": story_name,
        "episodes": episodes,
        "poster": poster,      # Naya Poster field
        "demo_link": demo,     # Demo field alag
        "bot_link": final_link,
        "price": price,
        "type": "story"
    })
    
    bot_username = bot.get_me().username
    share_link = f"https://t.me/{bot_username}?start={story_id}"
    
    res = (
        f"✅ <b>sᴛᴏʀʏ ᴀᴅᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!</b>\n"
        f"────────────────────\n"
        f"📖 Name: <b>{story_name}</b>\n"
        f"💰 Price: <b>₹{price}</b>\n\n"
        f"🔗 <b>sʜᴀʀᴇ ʟɪɴᴋ:</b>\n<code>{share_link}</code>"
    )
    bot.send_message(message.chat.id, res, parse_mode="HTML")
