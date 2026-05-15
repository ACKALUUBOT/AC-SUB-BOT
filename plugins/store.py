from telebot import types
from database import channels_col
import config

def get_premium_store_markup(bot_username):
    """
    Database se stories fetch karke buttons generate karne ka function.
    """
    # 1. Database se sirf stories nikalna (jisme story_name available ho)
    all_stories = list(channels_col.find({"story_name": {"$exists": True}}))
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not all_stories:
        # Agar koi story nahi milti toh ye button dikhega
        markup.add(types.InlineKeyboardButton("🚫 ɴᴏ sᴛᴏʀɪᴇs ᴀᴠᴀɪʟᴀʙʟᴇ", callback_data="none"))
    else:
        for story in all_stories:
            name = story.get('story_name', 'Unknown Story')
            price = story.get('price', 'N/A')
            item_id = story.get('item_id')

            # Button Text format: 📖 Story Name — ₹Price
            btn_text = f"📖 {name} — ₹{price}"
            
            # Deep Link: Jab user click karega toh bot ke /start logic par jayega
            # start parameter me item_id pass hoga
            url = f"https://t.me/{bot_username}?start={item_id}"
            
            markup.add(types.InlineKeyboardButton(text=btn_text, url=url))
            
    # Sabse niche Back button
    markup.add(types.InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))
    
    return markup

def get_store_text():
    """
    Store menu ka caption text.
    """
    text = (
        "✨ <b>ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ sᴛᴏʀᴇ</b> ✨\n"
        "────────────────────\n"
        "Niche hamari sabhi exclusive stories ki list hai.\n\n"
        "➔ <b>ʜᴏᴡ ɪᴛ ᴡᴏʀᴋs:</b>\n"
        "1. Apni pasand ki story select karein.\n"
        "2. Payment plan choose karein.\n"
        "3. Instant access payein.\n"
        "────────────────────"
    )
    return text

