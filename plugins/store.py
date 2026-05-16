from telebot import types
from database import channels_col
import config

# ─── 1. BOTTOM KEYBOARD CATEGORIES MENU (WITH COMBO PACKS) ───
def get_categories_markup():
    """User ko niche keyboard me 3 categories dikhane ke liye"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(
        types.KeyboardButton("✨ ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ sᴛᴏʀɪᴇs"),
        types.KeyboardButton("🔥 ᴘᴏᴄᴋᴇᴛ ғᴍ sᴛᴏʀɪᴇs"),
        types.KeyboardButton("🎁 SPECIAL COMBO PACKS (BIG SAVE)"), # Combo button wapas add ho gaya
        types.KeyboardButton("« BACK TO MENU")
    )
    return markup


# ─── 2. PAGINATED ITEMS MENU BY CATEGORY (DYNAMIC FILTER) ───
def get_items_by_category_markup(category_type, bot_username=None, page=1):
    """Source aur combo ke hisab se database se items filter karega (8 items per page)"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    
    # 🌟 DATABASE DATABASE FETCH FILTER
    if category_type == "pratilipi":
        all_items = list(channels_col.find({"story_name": {"$exists": True}, "source": "pratilipi", "is_combo": {"$exists": False}}))
    elif category_type == "pocket":
        all_items = list(channels_col.find({"story_name": {"$exists": True}, "source": "pocket", "is_combo": {"$exists": False}}))
    elif category_type == "combo":
        all_items = list(channels_col.find({"is_combo": True})) # Combo packs ka alag query filter
    else:
        all_items = []
        
    # Agar data nahi hai toh direct ye button show hoga
    if not all_items:
        markup.add(types.KeyboardButton("🚫 STORE IS EMPTY"))
        markup.add(types.KeyboardButton("🔙 BACK TO CATEGORIES"))
        return markup

    per_page = 8
    total_items = len(all_items)
    total_pages = (total_items + per_page - 1) // per_page
    
    if page < 1: page = 1
    if page > total_pages: page = total_pages
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    sliced_items = all_items[start_idx:end_idx]

    # Buttons display generation loop
    for index, item in enumerate(sliced_items, start=start_idx + 1):
        if category_type == "combo":
            btn_text = f"🎁 {item['combo_name']} ➔ [ ₹{item['price']} ]"
        else:
            btn_text = f"{index}. {item['story_name']} [ ₹{item['price']} ]"
            
        markup.add(types.KeyboardButton(btn_text))
            
    # Navigation Row (Next/Prev)
    nav_buttons = []
    if page > 1:
        nav_buttons.append(types.KeyboardButton("‹ PREV"))
    if page < total_pages:
        nav_buttons.append(types.KeyboardButton("NEXT ›"))
        
    if nav_buttons:
        markup.row(*nav_buttons)
        
    markup.add(types.KeyboardButton("🔙 BACK TO CATEGORIES"))
    markup.add(types.KeyboardButton("❌ CLOSE STORE"))
    return markup


# ─── 3. TEXT FOR CATEGORIES PAGE ───
def get_store_text():
    return (
        "🛍️ <b>ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ ᴄᴀᴛᴇɢᴏʀɪᴇs</b> 🛍️\n"
        "──────────────────────────\n"
        "ᴀᴀᴘ ᴋɪs ᴘʟᴀᴛғᴏʀᴍ ᴋɪ sᴛᴏʀɪᴇs ᴅᴇᴋʜɴᴀ ᴄʜᴀʜᴛᴇ ʜᴀɪɴ? ɴɪᴄʜᴇ sᴇ sᴇʟᴇᴄᴛ ᴋᴀʀᴇɪɴ:\n\n"
        "✨ <b>ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ sᴛᴏʀɪᴇs:</b> sᴇʟᴇᴄᴛ ᴛᴏ ᴠɪᴇᴡ ᴀʟʟ ᴘʀᴀᴛɪʟɪᴘɪ sᴛᴏʀɪᴇs.\n"
        "🔥 <b>ᴘᴏᴄᴋᴇᴛ ғᴍ sᴛᴏʀɪᴇs:</b> sᴇʟᴇᴄᴛ ᴛᴏ ᴠɪᴇᴡ ᴀʟʟ ᴘᴏᴄᴋᴇᴛ ғᴍ sᴛᴏʀɪᴇs.\n"
        "🎁 <b>sᴘᴇᴄɪᴀʟ ᴄᴏᴍʙᴏ ᴘᴀᴄᴋs:</b> ᴍᴜʟᴛɪ-sᴛᴏʀɪᴇs ʙᴜɴᴅʟᴇ ᴀᴛ ᴀ ᴄʜᴇᴀᴘ ᴘʀɪᴄᴇ!\n"
        "──────────────────────────"
    )
