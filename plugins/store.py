from telebot import types
from database import channels_col
import config

def get_premium_store_markup():
    """
    Database se Stories aur Channels fetch karke list buttons banana.
    """
    # Sabhi items fetch karein jinme story_name ya name (channel) ho
    all_items = list(channels_col.find({
        "$or": [
            {"story_name": {"$exists": True}},
            {"name": {"$exists": True}}
        ]
    }))
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if not all_items:
        markup.add(types.InlineKeyboardButton("🚫 ɴᴏ ɪᴛᴇᴍs ᴀᴠᴀɪʟᴀʙʟᴇ", callback_data="none"))
    else:
        for item in all_items:
            # ID aur Name pehchan-na
            db_id = item.get('item_id') or item.get('channel_id')
            
            if 'story_name' in item:
                # Case: Single Story
                name = item['story_name']
                price = f"₹{item.get('price', 'N/A')}"
                icon = "🎬"
            else:
                # Case: Forwarded Channel
                name = item.get('name', 'Premium Access')
                plans = item.get('plans', {})
                # Safe Price Logic: Sirf numbers ka minimum nikalna
                try:
                    if plans:
                        min_price = min(int(p) for p in plans.values())
                        price = f"Starts @ ₹{min_price}"
                    else:
                        price = "View Plans"
                except:
                    price = "Check Plans"
                icon = "💎"

            # Button Text
            btn_text = f"{icon} {name} — {price}"
            
            # Callback trigger card view
            markup.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"view_card_{db_id}"))
            
    markup.add(types.InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))
    return markup

def get_store_text():
    return (
        "✨ <b>ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ sᴛᴏʀᴇ</b> ✨\n"
        "────────────────────\n"
        "Niche hamari sabhi exclusive stories ki list hai.\n\n"
        "➔ 🎬 = 🎬 sɪɴɢʟᴇ sᴛᴏʀʏ\n"
        "➔ 💎 = 💎 ᴄʜᴀɴɴᴇʟ ᴀᴄᴄᴇss\n\n"
        "<b>Note:</b> Kisi bhi item par click karke uski photo aur detail check karein."
    )
