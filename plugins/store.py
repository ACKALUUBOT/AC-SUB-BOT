from telebot import types
From telebot import types
from database import channels_col
import config

# ─── 1. BOTTOM KEYBOARD CATEGORIES MENU ───
def get_categories_markup():
    """User ko niche keyboard me categories aur Combo Pack ka option dikhane ke liye"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    
    markup.add(
        types.KeyboardButton("🔥 SINGLE STORIES (LATEST)"),
        types.KeyboardButton("👑 VIP CHANNEL ACCESS"),
        types.KeyboardButton("🎁 SPECIAL COMBO PACKS (BIG SAVE)"),
        types.KeyboardButton("« BACK TO MENU")
    )
    return markup


# ─── 2. PAGINATED ITEMS MENU BY CATEGORY (8 ITEMS PER PAGE) ───
def get_items_by_category_markup(category_type, bot_username=None, page=1):
    """Dynamic database retrieval with pagination (8 items per page) without search button"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    
    # Database filter logic for 3 categories
    if category_type == "story":
        all_items = list(channels_col.find({"story_name": {"$exists": True}, "is_combo": {"$exists": False}}))
    elif category_type == "channel":
        all_items = list(channels_col.find({"name": {"$exists": True}, "is_combo": {"$exists": False}}))
    elif category_type == "combo":
        all_items = list(channels_col.find({"is_combo": True}))
        
    if not all_items:
        markup.add(types.KeyboardButton("🚫 STORE IS EMPTY"))
        markup.add(types.KeyboardButton("🔙 BACK TO CATEGORIES"))
        return markup

    # ─── PAGINATION LOGIC (8 items per page) ───
    per_page = 8
    total_items = len(all_items)
    total_pages = (total_items + per_page - 1) // per_page
    
    # Boundary check for pages
    if page < 1: page = 1
    if page > total_pages: page = total_pages
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    sliced_items = all_items[start_idx:end_idx]

    # Render current page items line-by-line
    for index, item in enumerate(sliced_items, start=start_idx + 1):
        if category_type == "story":
            name = item['story_name']
            price = f"[ ₹{item['price']} ]"
            # Video style format: "1. Story Name [ ₹130 ]"
            btn_text = f"{index}. {name} {price}"
            
        elif category_type == "channel":
            name = item['name']
            plans = item.get('plans', {})
            price = f"[ Starts @ ₹{min([int(p) for p in plans.values()])} ]" if plans else "[ Check Plans ]"
            btn_text = f"💎 {name} ➔ {price}"
            
        elif category_type == "combo":
            name = item['combo_name']
            price = f"[ ₹{item['price']} ]"
            btn_text = f"🎁 {name} ➔ {price}"

        markup.add(types.KeyboardButton(btn_text))
            
    # ─── NAVIGATION BUTTONS ROW (Bina Search Ke) ───
    nav_buttons = []
    if page > 1:
        nav_buttons.append(types.KeyboardButton("‹ PREV"))
    if page < total_pages:
        nav_buttons.append(types.KeyboardButton("NEXT ›"))
        
    if nav_buttons:
        markup.row(*nav_buttons)
        
    # Main exit options at bottom
    markup.add(types.KeyboardButton("🔙 BACK TO CATEGORIES"))
    return markup



# ─── 3. TEXT FOR CATEGORIES PAGE ───
def get_store_text():
    return (
        "🛍️ <b>ᴘʀᴇᴍɪᴜᴍ sᴛᴏʀʏ ᴄᴀᴛᴇɢᴏʀɪᴇs</b> 🛍️\n"
        "──────────────────────────\n"
        "ᴀᴀᴘ ᴋɪs ᴛᴀʀᴀʜ ᴋᴀ ᴄᴏɴᴛᴇɴᴛ ᴅᴇᴋʜɴᴀ ᴄʜᴀʜᴛᴇ ʜᴀɪɴ? ɴɪᴄʜᴇ sᴇ ᴄᴀᴛᴇɢᴏʀʏ sᴇʟᴇᴄᴛ ᴋᴀʀᴇɪɴ:\n\n"
        "✨ <b>ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ sᴛᴏʀɪᴇs:</b> ɢᴇᴛ ᴛʜᴇ ʙᴇsᴛ sᴛᴏʀɪᴇs (ʙᴏᴛ ʟɪɴᴋ ᴘʀᴏᴠɪᴅᴇᴅ).\n"
        "📢 <b>ᴘʀᴀᴛɪʟɪᴘɪ ғᴍ ᴄʜᴀɴɴᴇʟ:</b> ɢᴇᴛ ᴘʀᴇᴍɪᴜᴍ ᴄʜᴀɴɴᴇʟ sᴛᴏʀɪᴇs (ᴠɪᴘ ʟɪɴᴋ ᴘʀᴏᴠɪᴅᴇᴅ).\n"
        "🎁 <b>sᴘᴇᴄɪᴀʟ ᴄᴏᴍʙᴏ ᴘᴀᴄᴋs:</b> ᴍᴜʟᴛɪ-sᴛᴏʀɪᴇs ʙᴜɴᴅʟᴇ ᴀᴛ ᴀ ᴄʜᴇᴀᴘ ᴘʀɪᴄᴇ!\n"
        "──────────────────────────"
    )
