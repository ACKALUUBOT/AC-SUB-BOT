import config
from utils import bot
from telebot import types

# यूज़र के सेलेक्ट किए गए स्टोरी IDs को स्टोर करने के लिए डिक्शनरी
# Format: { user_id: set(selected_story_ids) }
COMBO_SELECTIONS = {}

# -------------------------------------------------------------
# 📌 हेल्पर्स फ़ंक्शन (Helpers)
# -------------------------------------------------------------
def get_discount_percentage(count):
    """चुनी गई स्टोरीज़ की संख्या के हिसाब से डिस्काउंट % तय करता है"""
    if 1 <= count <= 4:
        return 10  # 1 से 4 पर 10% डिस्काउंट
    elif 5 <= count <= 10:
        return 30  # 5 से 10 पर 30% डिस्काउंट
    elif count > 10:
        return 50  # 10 से ज्यादा पर 50% डिस्काउंट
    return 0

def get_all_stories_from_db():
    """
    नोट: यहाँ अपने MongoDB या डेटाबेस से स्टोरीज़ लाने वाला फ़ंक्शन कॉल करें।
    उदाहरण के लिए: return list(db.stories.find())
    """
    # डेमो डेटा (इसे अपने Database Call से बदलें):
    return [
        {"_id": "st1", "title": "Story 1", "price": 50},
        {"_id": "st2", "title": "Story 2", "price": 50},
        {"_id": "st3", "title": "Story 3", "price": 50},
        {"_id": "st4", "title": "Story 4", "price": 50},
        {"_id": "st5", "title": "Story 5", "price": 50},
        {"_id": "st6", "title": "Story 6", "price": 50},
    ]

def calculate_combo_total(user_id, all_stories):
    """मूल कीमत, डिस्काउंट और फ़ाइनल कीमत की गणना करता है"""
    user_selected = COMBO_SELECTIONS.get(user_id, set())
    if not user_selected:
        return 0, 0, 0, 0

    selected_stories = [s for s in all_stories if str(s['_id']) in user_selected]
    total_price = sum(s.get('price', 0) for s in selected_stories)
    count = len(selected_stories)
    discount_pct = get_discount_percentage(count)
    
    discount_amount = (total_price * discount_pct) / 100
    final_price = round(total_price - discount_amount, 2)
    
    return count, total_price, discount_pct, final_price

def build_combo_keyboard(user_id, all_stories):
    """स्टोरीज़ चुनने के लिए इनलाइन कीबोर्ड बनाता है"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    user_selected = COMBO_SELECTIONS.get(user_id, set())

    # सभी उपलब्ध स्टोरीज़ को बटन के रूप में जोड़ना
    for story in all_stories:
        story_id = str(story['_id'])
        title = story.get('title', 'Untitled')
        price = story.get('price', 0)
        
        # अगर यूज़र ने यह स्टोरी चुनी है तो Tick (✅) दिखाओ
        if story_id in user_selected:
            btn_text = f"✅ {title} - ₹{price}"
        else:
            btn_text = f"▫️ {title} - ₹{price}"
            
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"toggle_combo_{story_id}"))

    # ऐक्शन बटन्स (Buy / Clear / Back)
    if user_selected:
        markup.add(types.InlineKeyboardButton("💳 खरीदें (Proceed to Pay)", callback_data="buy_custom_combo"))
        markup.add(types.InlineKeyboardButton("🔄 सब रिसेट करें (Clear All)", callback_data="clear_combo"))
    
    markup.add(types.InlineKeyboardButton("🔙 मुख्य मेनू (Back)", callback_data="back_to_start"))
    return markup


# -------------------------------------------------------------
# 📌 कॉल बैक हैंडल्स (Callback Handlers)
# -------------------------------------------------------------

# 1. जब यूज़र 'Create Combo' बटन दबाए
@bot.callback_query_handler(func=lambda call: call.data in ["create_combo", "custom_combo"])
def start_custom_combo(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    
    if user_id not in COMBO_SELECTIONS:
        COMBO_SELECTIONS[user_id] = set()
        
    all_stories = get_all_stories_from_db()
    count, total_price, discount_pct, final_price = calculate_combo_total(user_id, all_stories)

    msg_text = (
        "🎁 **अपना कस्टम कॉम्बो (Custom Combo) बनाएं!**\n\n"
        "अपनी पसंद की स्टोरीज़ पर क्लिक करके सेलेक्ट करें:\n"
        "• **1 से 4 स्टोरीज़:** 10% डिस्काउंट 🎉\n"
        "• **5 से 10 स्टोरीज़:** 30% डिस्काउंट 🔥\n"
        "• **10 से अधिक स्टोरीज़:** 50% भारी डिस्काउंट 💥\n\n"
        f"📊 **चुनी गई स्टोरीज़:** `{count}`\n"
        f"💵 **मूल कीमत:** `₹{total_price}`\n"
        f"🏷 **डिस्काउंट:** `{discount_pct}%`\n"
        f"💰 **फ़ाइनल कीमत:** `₹{final_price}`\n\n"
        "👇 *नीचे लिस्ट में से अपनी मनपसंद स्टोरीज़ चुनें:*"
    )

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=msg_text,
        parse_mode="Markdown",
        reply_markup=build_combo_keyboard(user_id, all_stories)
    )


# 2. जब यूज़र किसी स्टोरी को सेलेक्ट या अन-सेलेक्ट (Toggle) करे
@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_combo_"))
def toggle_story_selection(call):
    user_id = call.from_user.id
    story_id = call.data.split("toggle_combo_")[1]

    if user_id not in COMBO_SELECTIONS:
        COMBO_SELECTIONS[user_id] = set()

    # सेलेक्ट / डि-सेलेक्ट टॉगल
    if story_id in COMBO_SELECTIONS[user_id]:
        COMBO_SELECTIONS[user_id].remove(story_id)
        bot.answer_callback_query(call.id, "❌ स्टोरी हटाई गई")
    else:
        COMBO_SELECTIONS[user_id].add(story_id)
        bot.answer_callback_query(call.id, "✅ स्टोरी जोड़ी गई")

    all_stories = get_all_stories_from_db()
    count, total_price, discount_pct, final_price = calculate_combo_total(user_id, all_stories)

    msg_text = (
        "🎁 **अपना कस्टम कॉम्बो (Custom Combo) बनाएं!**\n\n"
        "अपनी पसंद की स्टोरीज़ पर क्लिक करके सेलेक्ट करें:\n"
        "• **1 से 4 स्टोरीज़:** 10% डिस्काउंट 🎉\n"
        "• **5 से 10 स्टोरीज़:** 30% डिस्काउंट 🔥\n"
        "• **10 से अधिक स्टोरीज़:** 50% भारी डिस्काउंट 💥\n\n"
        f"📊 **चुनी गई स्टोरीज़:** `{count}`\n"
        f"💵 **मूल कीमत:** `₹{total_price}`\n"
        f"🏷 **डिस्काउंट:** `{discount_pct}%`\n"
        f"💰 **फ़ाइनल कीमत:** `₹{final_price}`\n\n"
        "👇 *नीचे लिस्ट में से अपनी मनपसंद स्टोरीज़ चुनें:*"
    )

    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=msg_text,
            parse_mode="Markdown",
            reply_markup=build_combo_keyboard(user_id, all_stories)
        )
    except Exception:
        pass


# 3. सेलेक्शन रिसेट करना (Clear All)
@bot.callback_query_handler(func=lambda call: call.data == "clear_combo")
def clear_combo_selection(call):
    user_id = call.from_user.id
    COMBO_SELECTIONS[user_id] = set()
    bot.answer_callback_query(call.id, "🔄 सभी स्टोरीज़ हटा दी गईं!")
    start_custom_combo(call)


# 4. पेमेंट (Checkout) का प्रोसेस शुरू करना
@bot.callback_query_handler(func=lambda call: call.data == "buy_custom_combo")
def process_custom_combo_checkout(call):
    user_id = call.from_user.id
    user_selected = COMBO_SELECTIONS.get(user_id, set())

    if not user_selected:
        return bot.answer_callback_query(call.id, "⚠️ आपने कोई स्टोरी नहीं चुनी है!", show_alert=True)

    all_stories = get_all_stories_from_db()
    count, total_price, discount_pct, final_price = calculate_combo_total(user_id, all_stories)

    bot.answer_callback_query(call.id)
    
    # यहाँ से अपने पेमेंट गेटवे (Razorpay/UPI) पर रीडायरेक्ट करें
    checkout_msg = (
        f"🛍 **आपका कस्टम कॉम्बो रेडी है!**\n\n"
        f"📚 कुल स्टोरीज़: `{count}`\n"
        f"💵 कुल मूल्य: `₹{total_price}`\n"
        f"🏷 डिस्काउंट लागू: `{discount_pct}%`\n"
        f"💰 **आपको भुगतान करना है:** `₹{final_price}`\n\n"
        f"👇 नीचे दिए गए बटन पर क्लिक करके पेमेंट करें:"
    )
    
    markup = types.InlineKeyboardMarkup()
    # अपने पेमेंट लिंक/फ़ंक्शन के अनुसार बटन का callback_data सेट करें
    markup.add(types.InlineKeyboardButton(f"💳 ₹{final_price} Pay Now", callback_data=f"pay_combo_{final_price}"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Combo", callback_data="create_combo"))

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=checkout_msg,
        parse_mode="Markdown",
        reply_markup=markup
    )
