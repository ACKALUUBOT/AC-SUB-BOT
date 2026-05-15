from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import bot
from database import channels_col, users_col
import config

@bot.message_handler(commands=['remove'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def remove_user_start(message):
    msg = bot.send_message(config.ADMIN_ID, "👤 <b>User ko remove karein:</b>\n\nUs user ki <b>ID</b> bhejein jiska access aap khatam karna chahte hain (ya /cancel):", parse_mode="HTML")
    bot.register_next_step_handler(msg, process_remove_user)

def process_remove_user(message):
    if message.text == '/cancel':
        bot.send_message(config.ADMIN_ID, "❌ Action cancelled.")
        return
    try:
        u_id = int(message.text)
        result = users_col.delete_many({"user_id": u_id})
        if result.deleted_count > 0:
            bot.send_message(config.ADMIN_ID, f"✅ <b>Success!</b>\nUser <code>{u_id}</code> ke saare plans hata diye gaye hain.", parse_mode="HTML")
            try: bot.send_message(u_id, "⚠️ <b>Access Revoked:</b> Aapka subscription admin dwara khatam kar diya gaya hai.", parse_mode="HTML")
            except: pass
        else:
            bot.send_message(config.ADMIN_ID, "❓ Is ID ka koi active subscription nahi mila.")
    except ValueError:
        bot.send_message(config.ADMIN_ID, "❌ Invalid ID! Sirf numbers bhejein.")

@bot.message_handler(commands=['channels'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def list_channels(message):
    cursor = channels_col.find({"admin_id": config.ADMIN_ID})
    markup = InlineKeyboardMarkup()
    for ch in cursor:
        markup.add(InlineKeyboardButton(f"📺 {ch['name']}", callback_data=f"manage_{ch['channel_id']}"))
    bot.send_message(config.ADMIN_ID, "📑 <b>Managed Channels:</b>", reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith('manage_'))
def manage_ch(call):
    ch_id = int(call.data.split('_')[1])
    ch_data = channels_col.find_one({"channel_id": ch_id})
    link = f"https://t.me/{bot.get_me().username}?start={ch_id}"
    text = (f"⚙️ <b>Settings:</b> {ch_data['name']}\n\n🔗 <b>Invite Link:</b> <code>{link}</code>\n📺 <b>Demo:</b> {ch_data.get('demo_link', 'None')}\n💰 <b>Plans:</b> {ch_data['plans']}")
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="HTML")

@bot.message_handler(commands=['add'], func=lambda m: m.from_user.id == config.ADMIN_ID)
def add_start(message):
    msg = bot.send_message(config.ADMIN_ID, "Forward a message from the channel.")
    bot.register_next_step_handler(msg, get_plans)

def get_plans(message):
    if message.forward_from_chat:
        ch_id, ch_name = message.forward_from_chat.id, message.forward_from_chat.title
        msg = bot.send_message(config.ADMIN_ID, f"✅ {ch_name}\nEnter Plans: <code>Min:Price, Min:Price</code>", parse_mode="HTML")
        bot.register_next_step_handler(msg, get_demo, ch_id, ch_name)

def get_demo(message, ch_id, ch_name):
    plans = {p.split(':')[0].strip(): p.split(':')[1].strip() for p in message.text.split(',')}
    msg = bot.send_message(config.ADMIN_ID, "Enter Demo Link (or 'none')")
    bot.register_next_step_handler(msg, finalize, ch_id, ch_name, plans)

def finalize(message, ch_id, ch_name, plans):
    demo = None if message.text.lower() == 'none' else message.text
    channels_col.update_one({"channel_id": ch_id}, {"$set": {"name": ch_name, "plans": plans, "demo_link": demo, "admin_id": config.ADMIN_ID}}, upsert=True)
    bot.send_message(config.ADMIN_ID, "✅ Setup Finished!", parse_mode="HTML")

