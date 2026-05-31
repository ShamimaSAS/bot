import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import json
import os
import random
import time
import threading
from flask import Flask, request

# ========== কনফিগারেশন (Environment Variable থেকে নেওয়া) ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
FORCE_CHANNEL = "@OTPness"
FORCE_GROUP = "@OTPnessCode"
SUPPORT_GROUP = "@OTPnessSupport"
ADMIN_ID = 7273011237

bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

# Flask অ্যাপ তৈরি
app = Flask(__name__)

# ডাটাবেস ফাইল
USER_DATA_FILE = "user_numbers.json"
NUMBERS_FILE = "numbers.txt"

# ========== ডাটাবেস ফাংশন ==========
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_numbers():
    if not os.path.exists(NUMBERS_FILE):
        with open(NUMBERS_FILE, 'w') as f:
            demo_numbers = {
                "facebook": {"US": ["+11234567890", "+19876543210"], "BD": ["+8801712345678"]},
                "instagram": {"US": ["+12223334444"], "BD": ["+8801812345679", "+8801912345680"]},
                "whatsapp": {"US": ["+15556667777"], "BD": ["+8801512345681", "+8801612345682"]}
            }
            json.dump(demo_numbers, f, indent=4)
    
    with open(NUMBERS_FILE, 'r') as f:
        return json.load(f)

def get_available_numbers(service, country):
    """সার্ভিস এবং কান্ট্রি অনুযায়ী অব্যবহৃত নাম্বার রিটার্ন করে"""
    all_numbers_data = load_numbers()
    used_numbers = load_user_data()
    
    if service not in all_numbers_data or country not in all_numbers_data[service]:
        return []
    
    all_numbers = all_numbers_data[service][country]
    used_number_set = set(used_numbers.values())
    available = [num for num in all_numbers if num not in used_number_set]
    return available

# ========== রিপ্লাই কিবোর্ড (মূল মেনু) ==========
def main_reply_keyboard():
    """পার্মানেন্ট রিপ্লাই কিবোর্ড"""
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = KeyboardButton("📱 Get Number")
    btn2 = KeyboardButton("👤 Profile")
    btn3 = KeyboardButton("♻️ Support")
    markup.add(btn1, btn2, btn3)
    return markup

# ========== ইনলাইন কিবোর্ড (সার্ভিস সিলেক্ট) ==========
def service_keyboard():
    """সার্ভিস সিলেক্টের জন্য ইনলাইন কিবোর্ড"""
    markup = InlineKeyboardMarkup(row_width=1)
    btn_fb = InlineKeyboardButton("📘 Facebook", callback_data="service_facebook")
    btn_insta = InlineKeyboardButton("📸 Instagram", callback_data="service_instagram")
    btn_wa = InlineKeyboardButton("💚 Whatsapp", callback_data="service_whatsapp")
    markup.add(btn_fb, btn_insta, btn_wa)
    return markup

def country_keyboard(service):
    """কান্ট্রি সিলেক্টের জন্য ইনলাইন কিবোর্ড"""
    markup = InlineKeyboardMarkup(row_width=1)
    btn_us = InlineKeyboardButton("🇺🇸 USA", callback_data=f"country_{service}_US")
    btn_bd = InlineKeyboardButton("🇧🇩 Bangladesh", callback_data=f"country_{service}_BD")
    btn_back = InlineKeyboardButton("◀️ Back to Services", callback_data="back_to_services")
    markup.add(btn_us, btn_bd, btn_back)
    return markup

def number_action_keyboard(service, country, number):
    """নাম্বার দেখানোর পর অ্যাকশন বাটন"""
    markup = InlineKeyboardMarkup(row_width=1)
    btn_change = InlineKeyboardButton("🔄 Change Number", callback_data=f"change_{service}_{country}")
    btn_get_otp = InlineKeyboardButton("📲 Get OTP", url=f"https://t.me/{FORCE_GROUP.replace('@', '')}")
    btn_back = InlineKeyboardButton("🔙 Back to Countries", callback_data=f"back_to_countries_{service}")
    markup.add(btn_change, btn_get_otp, btn_back)
    return markup

# ========== ফোর্স জয়েন চেক ==========
def is_user_member(user_id):
    try:
        chat1 = bot.get_chat(FORCE_CHANNEL)
        member1 = bot.get_chat_member(chat1.id, user_id)
        chat2 = bot.get_chat(FORCE_GROUP)
        member2 = bot.get_chat_member(chat2.id, user_id)
        
        return (member1.status in ['member', 'administrator', 'creator'] and 
                member2.status in ['member', 'administrator', 'creator'])
    except Exception as e:
        print(f"Error checking membership: {e}")
        return False

def force_join_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    btn_join1 = InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন", url=f"https://t.me/{FORCE_CHANNEL.replace('@', '')}")
    btn_join2 = InlineKeyboardButton("👥 OTP গ্রুপে জয়েন করুন", url=f"https://t.me/{FORCE_GROUP.replace('@', '')}")
    btn_check = InlineKeyboardButton("✅ জয়েন করেছি", callback_data="check_join")
    markup.add(btn_join1, btn_join2, btn_check)
    return markup

# ========== কমান্ড হ্যান্ডলার ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    if not is_user_member(user_id):
        force_text = (
            "🤖 *বট ব্যবহার করার জন্য প্রথমে চ্যানেল ও OTP গ্রুপে জয়েন করুন:*\n\n"
            f"➡️ {FORCE_CHANNEL}\n➡️ {FORCE_GROUP}\n\n"
            "✅ জয়েন করার পর নিচের *'জয়েন করেছি'* বাটনে ক্লিক করুন।"
        )
        bot.send_message(
            message.chat.id,
            force_text,
            reply_markup=force_join_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    user_name = message.from_user.first_name
    welcome_text = f"✅ *ধন্যবাদ {user_name}!* এখন বট ব্যবহার করতে পারবেন।\n\nনিচের মেনু থেকে সিলেক্ট করুন:"
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=main_reply_keyboard(),
        parse_mode='Markdown'
    )

# ========== রিপ্লাই মেসেজ হ্যান্ডলার ==========
@bot.message_handler(func=lambda message: message.text == "📱 Get Number")
def get_number_menu(message):
    """Get Number এ ক্লিক করলে সার্ভিস দেখাবে"""
    bot.send_message(
        message.chat.id,
        "🔍 *Choose a Service:*",
        reply_markup=service_keyboard(),
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text == "👤 Profile")
def profile_menu(message):
    """প্রোফাইল দেখাবে"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    username = message.from_user.username or "No username"
    
    user_data = load_user_data()
    used_numbers = user_data.get(str(user_id), "None")
    
    profile_text = (
        "👤 *Your Profile*\n\n"
        f"📛 *Name:* {user_name}\n"
        f"🆔 *User ID:* `{user_id}`\n"
        f"👥 *Username:* @{username}\n"
        f"📱 *Last Number:* `{used_numbers if used_numbers != 'None' else 'Not taken yet'}`"
    )
    bot.send_message(
        message.chat.id,
        profile_text,
        reply_markup=main_reply_keyboard(),
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text == "♻️ Support")
def support_menu(message):
    """সাপোর্ট মেনু"""
    support_text = (
        "♻️ *Need Help?*\n\n"
        "📢 Join our support group for any assistance:\n"
        f"➡️ [Support Group](https://t.me/{SUPPORT_GROUP.replace('@', '')})\n\n"
        "👨‍💻 *Contact Admin:*\n"
        "Direct message for urgent issues.\n\n"
        "⚠️ Please be patient! We'll respond ASAP."
    )
    bot.send_message(
        message.chat.id,
        support_text,
        reply_markup=main_reply_keyboard(),
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

# ========== কলব্যাক হ্যান্ডলার ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    user_name = call.from_user.first_name
    
    # জয়েন চেক
    if call.data == "check_join":
        if is_user_member(user_id):
            try:
                # পুরনো মেসেজ ডিলিট করুন
                bot.delete_message(call.message.chat.id, call.message.message_id)
                
                # নতুন মেসেজ পাঠান
                bot.send_message(
                    call.message.chat.id,
                    f"✅ *ধন্যবাদ {user_name}!* এখন বট ব্যবহার করতে পারবেন।\n\nনিচের মেনু থেকে সিলেক্ট করুন:",
                    reply_markup=main_reply_keyboard(),
                    parse_mode='Markdown'
                )
                bot.answer_callback_query(call.id)
            except Exception as e:
                print(f"Delete/Send error: {e}")
        else:
            bot.answer_callback_query(
                call.id, 
                "❌ আপনি এখনও জয়েন করেননি! আগে চ্যানেল ও গ্রুপে জয়েন করুন।",
                show_alert=True
            )
        return
    
    # ব্যাক টু সার্ভিসেস
    if call.data == "back_to_services":
        bot.edit_message_text(
            "🔍 *Choose a Service:*",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=service_keyboard(),
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
        return
    
    # সার্ভিস সিলেক্ট
    if call.data.startswith("service_"):
        service = call.data.replace("service_", "")
        bot.edit_message_text(
            f"📱 *Select Country for {service.upper()}:*",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=country_keyboard(service),
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
        return
    
    # ব্যাক টু কান্ট্রি
    if call.data.startswith("back_to_countries_"):
        service = call.data.replace("back_to_countries_", "")
        bot.edit_message_text(
            f"📱 *Select Country for {service.upper()}:*",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=country_keyboard(service),
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
        return
    
    # কান্ট্রি সিলেক্ট ও নাম্বার দেওয়া
    if call.data.startswith("country_"):
        parts = call.data.split("_")
        service = parts[1]
        country = parts[2]
        
        available_numbers = get_available_numbers(service, country)
        
        if not available_numbers:
            bot.answer_callback_query(
                call.id,
                f"❌ No {country} numbers available for {service.upper()}!",
                show_alert=True
            )
            return
        
        selected_number = random.choice(available_numbers)
        user_data = load_user_data()
        user_data[str(user_id)] = selected_number
        save_user_data(user_data)
        
        bot.edit_message_text(
            f"📱 *Your {service.upper()} {country} Number:*\n"
            f"`{selected_number}`\n\n"
            f"👆 Tap to copy\n\n"
            f"Choose an action:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=number_action_keyboard(service, country, selected_number),
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
        return
    
    # চেঞ্জ নাম্বার
    if call.data.startswith("change_"):
        parts = call.data.split("_")
        service = parts[1]
        country = parts[2]
        
        available_numbers = get_available_numbers(service, country)
        
        if not available_numbers:
            bot.answer_callback_query(
                call.id,
                f"❌ No more {country} numbers available for {service.upper()}!",
                show_alert=True
            )
            return
        
        new_number = random.choice(available_numbers)
        user_data = load_user_data()
        user_data[str(user_id)] = new_number
        save_user_data(user_data)
        
        bot.edit_message_text(
            f"🔄 *New {service.upper()} {country} Number:*\n"
            f"`{new_number}`\n\n"
            f"👆 Tap to copy\n\n"
            f"Choose an action:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=number_action_keyboard(service, country, new_number),
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
        return

# ========== অ্যাডমিন কমান্ড ==========
@bot.message_handler(commands=['addnumber'])
def add_number(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ You are not the Admin.")
        return
    
    try:
        parts = message.text.split(' ')
        if len(parts) != 4:
            bot.reply_to(message, "❌ Format: `/addnumber <service> <country> <number>`\nExample: `/addnumber facebook BD +8801712345678`", parse_mode='Markdown')
            return
        
        service = parts[1].lower()
        country = parts[2].upper()
        new_number = parts[3]
        
        numbers_data = load_numbers()
        
        if service not in numbers_data:
            numbers_data[service] = {}
        if country not in numbers_data[service]:
            numbers_data[service][country] = []
        
        numbers_data[service][country].append(new_number)
        
        with open(NUMBERS_FILE, 'w') as f:
            json.dump(numbers_data, f, indent=4)
        
        bot.reply_to(message, f"✅ Number added: {service.upper()} {country} - `{new_number}`", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ You are not the Admin.")
        return
    
    numbers_data = load_numbers()
    user_data = load_user_data()
    
    total_numbers = 0
    for service in numbers_data.values():
        for country_numbers in service.values():
            total_numbers += len(country_numbers)
    
    used_numbers = len(set(user_data.values()))
    total_users = len(user_data)
    
    stats_text = (
        "📊 *Bot Statistics:*\n\n"
        f"📝 Total Numbers: `{total_numbers}`\n"
        f"✅ Used: `{used_numbers}`\n"
        f"🟢 Available: `{total_numbers - used_numbers}`\n"
        f"👥 Total Users: `{total_users}`"
    )
    bot.reply_to(message, stats_text, parse_mode='Markdown')

@bot.message_handler(commands=['reset'])
def reset_user_numbers(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ You are not the Admin.")
        return
    
    if os.path.exists(USER_DATA_FILE):
        os.remove(USER_DATA_FILE)
    bot.reply_to(message, "✅ Reset Done of all User's Data.")

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    """সব ইউজারকে মেসেজ পাঠানো (শুধু অ্যাডমিন)"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ You are not the Admin.")
        return
    
    try:
        broadcast_text = message.text.split(' ', 1)[1]
        user_data = load_user_data()
        
        sent = 0
        for user_id in user_data.keys():
            try:
                bot.send_message(int(user_id), broadcast_text, parse_mode='Markdown')
                sent += 1
                time.sleep(0.05)
            except:
                pass
        
        bot.reply_to(message, f"✅ Broadcast completed! Sent to {sent} users.")
    except:
        bot.reply_to(message, "❌ Format: `/broadcast Your message here`", parse_mode='Markdown')

# ========== Flask রাউট (Render এবং UptimeRobot এর জন্য) ==========
@app.route('/')
def home():
    """হোম পেজ - Render হেলথ চেকের জন্য"""
    return "OTP Bot is running!", 200

@app.route('/health')
def health():
    """হেলথ চেক এন্ডপয়েন্ট - UptimeRobot পিং করার জন্য"""
    return "OK", 200

def run_flask():
    """Flask সার্ভার চালানোর ফাংশন"""
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ========== বট চালু ==========
if __name__ == "__main__":
    # Flask থ্রেডে চালান (যাতে বট এবং ওয়েব সার্ভার একসাথে চলে)
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    print("🤖 Bot Starting....")
    print(f"✅ Force Join Channel: {FORCE_CHANNEL}")
    print(f"✅ Force Join Group: {FORCE_GROUP}")
    print(f"✅ Support Group: {SUPPORT_GROUP}")
    
    try:
        bot.get_chat(FORCE_CHANNEL)
        bot.get_chat(FORCE_GROUP)
        print("✅ Channel and Group Access Success.")
    except:
        print(f"⚠️ Access Problem! Make sure bot is admin.")
    
    print("🚀 Bot Running...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
