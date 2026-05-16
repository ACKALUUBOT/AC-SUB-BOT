from telebot import types
from database import channels_col
import config

# ─── 1. UPDATED CATEGORIES MENU (WITH COMBO) ───
def get_categories_markup():
    """User ko categories ke sath Combo Pack ka option dikhane ke liye"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    markup.add(
        types.InlineKeyboardButton("🔥 sɪɴɢʟᴇ sᴛᴏʀɪᴇs (ʟᴀᴛᴇsᴛ)", callback_data="view_cat_story"),
        types.InlineKeyboardButton("👑 ᴠɪᴘ ᴄʜᴀɴɴᴇʟ ᴀᴄᴄᴇss", callback_data="view_cat_channel"),
        types.InlineKeyboardButton("🎁 sᴘᴇᴄɪᴀʟ ᴄᴏᴍʙᴏ ᴘᴀᴄᴋs (ʙɪɢ sᴀᴠᴇ)", callback_data="view_cat_combo") # NEW
    )
    
    markup.add(types.InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_to_start"))
    return markup


# ─── 2. FILTERED ITEMS MENU BY CATEGORY ───
def get_items_by_category_markup(category_type, bot_username):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Database filter logic for 3 categories
    if category_type == "story":
        all_items = list(channels_col.find({"story_name": {"$exists": True}, "is_combo": {"$exists": False}}))
    elif category_type == "channel":
        all_items = list(channels_col.find({"name": {"$exists": True}, "is_combo": {"$exists": False}}))
    elif category_type == "combo":
        # NEW: Combo items filter
        all_items = list(channels_col.find({"is_combo": True}))
        
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
            elif category_type == "channel":
                name = item['name']
                plans = item.get('plans', {})
                price = f"Starts @ ₹{min([int(p) for p in plans.values()])}" if plans else "Check Plans"
                param = item.get('channel_id')
                icon = "👑"
                badge = " [<b>ᴄʜᴀɴɴᴇʟ</b>]"
            elif category_type == "combo":
                # NEW: Combo pack rendering
                name = item['combo_name']
                price = f"₹{item['price']}"
                param = item['item_id'] # Combo ke liye bhi unique item_id use karenge
                icon = "🎁"
                badge = " [ᴄᴏᴍʙᴏ]"

            btn_text = f"{icon} {name}{badge} ➔ {price}"
            url = f"https://t.me/{bot_username}?start={param}"
            markup.add(types.InlineKeyboardButton(text=btn_text, url=url))
            
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
        "🎁 <b>ᴄᴏᴍʙᴏ ᴘᴀᴄᴋs:</b> Multi-stories ka bundle ek sath saste price me!\n"
        "──────────────────────────"
    )
