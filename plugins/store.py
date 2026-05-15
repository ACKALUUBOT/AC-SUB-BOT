from telebot import types
from database import channels_col
import config

def get_premium_store_markup(bot_username):
    # Sabhi data uthao database se
    all_items = list(channels_col.find({}))
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not all_items:
        markup.add(types.InlineKeyboardButton("🚫 ɴᴏ sᴛᴏʀɪᴇs ᴀᴠᴀɪʟᴀʙʟᴇ", callback_data="none"))
    else:
        for item in all_items:
            # ─── CASE 1: MANUAL ADD STORY (item_id based) ───
            if 'story_name' in item:
                name = item['story_name']
                price = f"₹{item['price']}"
                param = item['item_id']
                icon = "🎬"

            # ─── CASE 2: CHANNEL FORWARD STORY (channel_id based) ───
            elif 'name' in item:
                name = item['name']
                # Isme plans hote hain, toh sabse sasta plan dikhao
                plans = item.get('plans', {})
                if plans:
                    prices = [int(p) for p in plans.values()]
                    price = f"Starts @ ₹{min(prices)}"
                else:
                    price = "Check Plans"
                param = item.get('channel_id')
                icon = "💎"
            
            else:
                # Agar koi aisa data hai jo dono nahi hai toh skip karo
                continue

            # Button Text format
            btn_text = f"{icon} {name} — {price}"
            
            # Deep Link: Manual ke liye item_id aur Forwarded ke liye channel_id
            url = f"https://t.me/{bot_username}?start={param}"
            
            markup.add(types.InlineKeyboardButton(text=btn_text, url=url))
            
    markup.add(types.InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))
    return markup

def get_store_text():
    return (
        "✨ <b>ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ sᴛᴏʀᴇ</b> ✨\n"
        "────────────────────\n"
        "Niche hamari sabhi exclusive stories ki list hai.\n\n"
        "➔ 🎬 = ꜱɪɴɢʟᴇ ꜱᴛᴏʀʏ\n"
        "➔ 💎 = ᴄʜᴀɴɴᴇʟ ᴀᴄᴄᴇꜱꜱ\n\n"
        "Select karke apna access activate karein."
    )
