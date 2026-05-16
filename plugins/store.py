from telebot import types
from database import channels_col
import config

# ─── 1. MAIN CATEGORIES MENU ───
def get_categories_markup():
    """User ko clean categories dikhane ke liye"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    markup.add(
        types.InlineKeyboardButton("🔥 sɪɴɢʟᴇ sᴛᴏʀɪᴇs (ʟᴀᴛᴇsᴛ)", callback_data="view_cat_story"),
        types.InlineKeyboardButton("👑 ᴠɪᴘ ᴄʜᴀɴɴᴇʟ ᴀᴄᴄᴇss", callback_data="view_cat_channel")
    )
    
    markup.add(types.InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))
    return markup


# ─── 2. FILTERED ITEMS MENU BY CATEGORY ───
def get_items_by_category_markup(category_type, bot_username):
    """Selected category ke items database se nikal kar button banane ke liye"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Database filter logic
    if category_type == "story":
        # Sirf single stories jisme 'story_name' exist karta ho
        all_items = list(channels_col.find({"story_name": {"$exists": True}}))
    else:
        # Sirf full channels jisme 'name' exist karta ho
        all_items = list(channels_col.find({"name": {"$exists": True}}))
        
    if not all_items:
        markup.add(types.InlineKeyboardButton("🚫 sᴛᴏʀᴇ ɪs ᴇᴍᴘᴛʏ", callback_data="none"))
    else:
        for item in all_items:
            if category_type == "story":
                name = item['story_name']
                price = f"₹{item['price']}"
                param = item['item_id']
                icon = "🔥"
                badge = " [sᴛᴏʀʏ]"
            else:
                name = item['name']
                plans = item.get('plans', {})
                price = f"Starts @ ₹{min([int(p) for p in plans.values()])}" if plans else "Check Plans"
                param = item.get('channel_id')
                icon = "👑"
                badge = " [ᴄʜᴀɴɴᴇʟ]"

            # Premium button alignment with smooth arrow
            btn_text = f"{icon} {name}{badge} ➔ {price}"
            url = f"https://t.me/{bot_username}?start={param}"
            markup.add(types.InlineKeyboardButton(text=btn_text, url=url))
            
    # Back to Category main menu
    markup.add(types.InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴄᴀᴛᴇɢᴏʀɪᴇs", callback_data="open_store"))
    return markup


# ─── 3. TEXT FOR CATEGORIES PAGE ───
def get_store_text():
    return (
        "🛍️ <b>ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ ᴄᴀᴛᴇɢᴏʀɪᴇs</b> 🛍️\n"
        "──────────────────────────\n"
        "Aap kis tarah ka content dekhna chahte hain? Niche se category select karein:\n\n"
        "🔥 <b>sɪɴɢʟᴇ sᴛᴏʀɪᴇs:</b> Quick romantic/adult hot stories.\n"
        "👑 <b>ᴠɪᴘ ᴄʜᴀɴɴᴇʟs:</b> Daily updates aur backup VIP links ka access.\n"
        "──────────────────────────"
    )
