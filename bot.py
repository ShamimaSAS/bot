import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import json
import os
import random
import time
import threading
import requests
import re
from datetime import datetime
from collections import defaultdict
from flask import Flask, request

# ========== কনফিগারেশন ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
FORCE_CHANNEL = "@OTPness"
FORCE_GROUP = "@OTPnessCode"
SUPPORT_GROUP = "@OTPnessSupport"
ADMIN_ID = 7273011237
OTP_GROUP_ID = -1003942979970  # OTP ফরওয়ার্ড করার গ্রুপ আইডি (আপনার গ্রুপের আইডি দিন)

bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

# Flask অ্যাপ
app = Flask(__name__)

# ডাটাবেস ফাইল
USER_DATA_FILE = "user_numbers.json"
NUMBERS_FILE = "numbers.txt"
RANGES_FILE = "ranges.json"
ADMINS_FILE = "admins.json"
OTP_MONITOR_FILE = "otp_monitor.json"

# ========== API লগইন তথ্য ==========
API_EMAIL = os.environ.get('EMAIL')
API_PASSWORD = os.environ.get('PASSWORD')
API_TOKEN = None
ses = requests.Session()
# ========== ডাটাবেস ফাংশন ==========
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_ranges():
    if not os.path.exists(RANGES_FILE):
        default_ranges = {
            "facebook": {"US": "22507675XXX", "CI": "22891XXX"},
            "instagram": {"US": "22507677XXX", "BD": "22507678XXX"},
            "whatsapp": {"US": "22507679XXX", "BD": "22507680XXX"}
        }
        with open(RANGES_FILE, 'w') as f:
            json.dump(default_ranges, f, indent=4)
        return default_ranges
    
    with open(RANGES_FILE, 'r') as f:
        return json.load(f)

def save_ranges(data):
    with open(RANGES_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_admins():
    if not os.path.exists(ADMINS_FILE):
        default_admins = {str(ADMIN_ID): True}
        with open(ADMINS_FILE, 'w') as f:
            json.dump(default_admins, f, indent=4)
        return default_admins
    
    with open(ADMINS_FILE, 'r') as f:
        return json.load(f)

def save_admins(data):
    with open(ADMINS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def is_admin(user_id):
    admins = load_admins()
    return str(user_id) in admins

def load_otp_monitor():
    if os.path.exists(OTP_MONITOR_FILE):
        with open(OTP_MONITOR_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_otp_monitor(data):
    with open(OTP_MONITOR_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ========== API ফাংশন ==========
def get_api_token():
    """API থেকে টোকেন সংগ্রহ করে"""
    global API_TOKEN
    
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9,bn;q=0.8',
        'content-type': 'application/json',
        'origin': 'https://x.mnitnetwork.com',
        'priority': 'u=1, i',
        'referer': 'https://x.mnitnetwork.com/mauth/login',
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    }
    
    json_data = {
        'email': API_EMAIL,
        'password': API_PASSWORD,
    }
    
    try:
        response = ses.post('https://x.mnitnetwork.com/mapi/v1/mauth/login', headers=headers, json=json_data, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            API_TOKEN = response_data['data']['token']
            return True
        else:
            print(f"Login failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Token error: {e}")
        return False

def get_number_from_api(range_value):
    """API থেকে নতুন নাম্বার নেয়"""
    global API_TOKEN
    
    if not API_TOKEN:
        if not get_api_token():
            return None
    
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9,bn;q=0.8',
        'content-type': 'application/json',
        'mauthtoken': API_TOKEN,
        'origin': 'https://x.mnitnetwork.com',
        'priority': 'u=1, i',
        'referer': f'https://x.mnitnetwork.com/mdashboard/getnum?range={range_value}',
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    }
    
    json_data = {
        'range': range_value,
        'is_national': False,
        'remove_plus': False,
    }
    
    try:
        response = ses.post('https://x.mnitnetwork.com/mapi/v1/mdashboard/getnum/number', headers=headers, json=json_data, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            return response_data['data']['full_number']
        elif response.status_code in [401, 403]:
            # Token expired, try again
            get_api_token()
            return get_number_from_api(range_value)
        else:
            print(f"Get number failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting number: {e}")
        return None

def check_otp_for_number(number, range_value):
    """একটি নাম্বারের জন্য OTP চেক করে"""
    global API_TOKEN
    
    if not API_TOKEN:
        if not get_api_token():
            return None
    
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9,bn;q=0.8',
        'content-type': 'application/json',
        'mauthtoken': API_TOKEN,
        'priority': 'u=1, i',
        'referer': f'https://x.mnitnetwork.com/mdashboard/getnum?range={range_value}',
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    }
    
    params = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'page': '1',
        'search': '',
        'status': 'success',
    }
    
    try:
        response = ses.get('https://x.mnitnetwork.com/mapi/v1/mdashboard/getnum/info', headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            numbers_list = response_data.get('data', {}).get('numbers', [])
            
            for item in numbers_list:
                if item.get('full_number') == number or item.get('number') == number:
                    message = item.get('message', '')
                    otp = extract_otp_from_message(message)
                    if otp:
                        return {'otp': otp, 'message': message, 'full_number': item.get('full_number', number)}
            return None
        elif response.status_code in [401, 403]:
            get_api_token()
            return check_otp_for_number(number, range_value)
        else:
            return None
    except Exception as e:
        print(f"OTP check error: {e}")
        return None

def extract_otp_from_message(message):
    """মেসেজ থেকে OTP কোড বের করে"""
    pattern = r'(\b\d{5,8}\b)'
    match = re.search(pattern, message)
    if match:
        return match.group(1)
    return None

# ========== OTP মনিটরিং থ্রেড ==========
def monitor_otp(user_id, number, service, country, range_value):
    """ব্যাকগ্রাউন্ডে OTP মনিটর করে"""
    monitor_data = load_otp_monitor()
    
    if str(user_id) not in monitor_data:
        monitor_data[str(user_id)] = {
            'number': number,
            'service': service,
            'country': country,
            'range': range_value,
            'start_time': datetime.now().isoformat(),
            'status': 'monitoring'
        }
        save_otp_monitor(monitor_data)
    
    start_time = datetime.now()
    max_duration = 20 * 60  # 20 minutes
    
    while (datetime.now() - start_time).total_seconds() < max_duration:
        time.sleep(5)  # প্রতি 5 সেকেন্ডে চেক করে
        
        result = check_otp_for_number(number, range_value)
        
        if result and result.get('otp'):
            # OTP পাওয়া গেছে
            otp = result['otp']
            full_message = result['message']
            
            # ইউজারকে OTP মেসেজ পাঠানো
            user_text = (
                f"🔐 *OTP Received!*\n\n"
                f"📱 *Number:* `{number}`\n"
                f"📝 *OTP:* `{otp}`\n\n"
                f"👆 ট্যাপ করে কপি করুন\n\n"
                f"📄 *Full Message:*\n`{full_message[:200]}`"
            )
            
            markup = InlineKeyboardMarkup()
            btn_copy = InlineKeyboardButton("📋 Copy OTP", callback_data=f"copy_otp_{otp}")
            markup.add(btn_copy)
            
            try:
                bot.send_message(user_id, user_text, reply_markup=markup, parse_mode='Markdown')
                
                # গ্রুপে ফরওয়ার্ড
                bot.send_message(OTP_GROUP_ID, f"🔐 *New OTP*\n\n📱 {number}\n📝 OTP: `{otp}`\n\n📄 {full_message[:200]}", parse_mode='Markdown')
                
                # মনিটরিং স্ট্যাটাস আপডেট
                monitor_data[str(user_id)]['status'] = 'completed'
                monitor_data[str(user_id)]['otp'] = otp
                save_otp_monitor(monitor_data)
                
                break
            except Exception as e:
                print(f"Failed to send OTP: {e}")
                break
    
    # 20 মিনিট পরেও OTP না পেলে
    if monitor_data.get(str(user_id), {}).get('status') == 'monitoring':
        monitor_data[str(user_id)]['status'] = 'timeout'
        save_otp_monitor(monitor_data)
        try:
            bot.send_message(user_id, "⏰ *Time out!* 20 minutes passed. No OTP received.", parse_mode='Markdown')
        except:
            pass

# ========== কিবোর্ড ফাংশন ==========
def main_reply_keyboard():
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = KeyboardButton("📱 Get Number")
    btn2 = KeyboardButton("👤 Profile")
    btn3 = KeyboardButton("♻️ Support")
    markup.add(btn1, btn2, btn3)
    return markup

def service_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    ranges_data = load_ranges()
    for service in ranges_data.keys():
        btn = InlineKeyboardButton(f"📘 {service.capitalize()}", callback_data=f"service_{service}")
        markup.add(btn)
    return markup

def country_keyboard(service):
    markup = InlineKeyboardMarkup(row_width=1)
    ranges_data = load_ranges()
    if service in ranges_data:
        for country in ranges_data[service].keys():
            btn = InlineKeyboardButton(f"🌍 {country}", callback_data=f"country_{service}_{country}")
            markup.add(btn)
    btn_back = InlineKeyboardButton("◀️ Back to Services", callback_data="back_to_services")
    markup.add(btn_back)
    return markup

def number_action_keyboard(service, country, number):
    markup = InlineKeyboardMarkup(row_width=1)
    btn_change = InlineKeyboardButton("🔄 Change Number", callback_data=f"change_{service}_{country}")
    markup.add(btn_change)
    btn_back = InlineKeyboardButton("🔙 Back to Countries", callback_data=f"back_to_countries_{service}")
    markup.add(btn_back)
    return markup

def admin_panel_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    btn_admins = InlineKeyboardButton("👑 Manage Admins", callback_data="admin_manage_admins")
    btn_services = InlineKeyboardButton("📂 Manage Services", callback_data="admin_manage_services")
    btn_countries = InlineKeyboardButton("🌍 Manage Countries/Ranges", callback_data="admin_manage_countries")
    btn_stats = InlineKeyboardButton("📊 System Stats", callback_data="admin_stats")
    btn_reset = InlineKeyboardButton("🔄 Reset All Data", callback_data="admin_reset")
    btn_broadcast = InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")
    markup.add(btn_admins, btn_services, btn_countries, btn_stats, btn_reset, btn_broadcast)
    return markup

def force_join_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    btn_join1 = InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন", url=f"https://t.me/{FORCE_CHANNEL.replace('@', '')}")
    btn_join2 = InlineKeyboardButton("👥 OTP গ্রুপে জয়েন করুন", url=f"https://t.me/{FORCE_GROUP.replace('@', '')}")
    btn_check = InlineKeyboardButton("✅ জয়েন করেছি", callback_data="check_join")
    markup.add(btn_join1, btn_join2, btn_check)
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
        bot.send_message(message.chat.id, force_text, reply_markup=force_join_keyboard(), parse_mode='Markdown')
        return
    
    user_name = message.from_user.first_name
    welcome_text = f"✅ *ধন্যবাদ {user_name}!* এখন বট ব্যবহার করতে পারবেন।\n\nনিচের মেনু থেকে সিলেক্ট করুন:"
    bot.send_message(message.chat.id, welcome_text, reply_markup=main_reply_keyboard(), parse_mode='Markdown')
    
    # অ্যাডমিন হলে অতিরিক্ত বাটন দেখানোর জন্য
    if is_admin(user_id):
        bot.send_message(message.chat.id, "🔧 *Admin Panel*", reply_markup=admin_panel_keyboard(), parse_mode='Markdown')

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔ You are not an Admin!")
        return
    
    bot.send_message(message.chat.id, "🔧 *Admin Control Panel*", reply_markup=admin_panel_keyboard(), parse_mode='Markdown')

# ========== রিপ্লাই মেসেজ হ্যান্ডলার ==========
@bot.message_handler(func=lambda message: message.text == "📱 Get Number")
def get_number_menu(message):
    bot.send_message(message.chat.id, "🔍 *Choose a Service:*", reply_markup=service_keyboard(), parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "👤 Profile")
def profile_menu(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    username = message.from_user.username or "No username"
    
    profile_text = (
        "👤 *Your Profile*\n\n"
        f"📛 *Name:* {user_name}\n"
        f"🆔 *User ID:* `{user_id}`\n"
        f"👥 *Username:* @{username}\n"
        f"👑 *Admin:* {'Yes' if is_admin(user_id) else 'No'}"
    )
    bot.send_message(message.chat.id, profile_text, reply_markup=main_reply_keyboard(), parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "♻️ Support")
def support_menu(message):
    support_text = (
        "♻️ *Need Help?*\n\n"
        "📢 Join our support group for any assistance:\n"
        f"➡️ [Support Group](https://t.me/{SUPPORT_GROUP.replace('@', '')})\n\n"
        "👨‍💻 *Contact Admin:* Direct message for urgent issues."
    )
    bot.send_message(message.chat.id, support_text, reply_markup=main_reply_keyboard(), parse_mode='Markdown', disable_web_page_preview=True)

# ========== কলব্যাক হ্যান্ডলার ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    user_name = call.from_user.first_name
    
    # জয়েন চেক
    if call.data == "check_join":
        if is_user_member(user_id):
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
                bot.send_message(call.message.chat.id, f"✅ *ধন্যবাদ {user_name}!* এখন বট ব্যবহার করতে পারবেন।\n\nনিচের মেনু থেকে সিলেক্ট করুন:", reply_markup=main_reply_keyboard(), parse_mode='Markdown')
                if is_admin(user_id):
                    bot.send_message(call.message.chat.id, "🔧 *Admin Panel*", reply_markup=admin_panel_keyboard(), parse_mode='Markdown')
                bot.answer_callback_query(call.id)
            except Exception as e:
                print(f"Error: {e}")
        else:
            bot.answer_callback_query(call.id, "❌ আপনি এখনও জয়েন করেননি!", show_alert=True)
        return
    
    # কপি OTP
    if call.data.startswith("copy_otp_"):
        otp = call.data.replace("copy_otp_", "")
        bot.answer_callback_query(call.id, f"✅ OTP copied: {otp}", show_alert=True)
        return
    
    # ব্যাক টু সার্ভিসেস
    if call.data == "back_to_services":
        bot.edit_message_text("🔍 *Choose a Service:*", call.message.chat.id, call.message.message_id, reply_markup=service_keyboard(), parse_mode='Markdown')
        bot.answer_callback_query(call.id)
        return
    
    # সার্ভিস সিলেক্ট
    if call.data.startswith("service_"):
        service = call.data.replace("service_", "")
        bot.edit_message_text(f"📱 *Select Country for {service.upper()}:*", call.message.chat.id, call.message.message_id, reply_markup=country_keyboard(service), parse_mode='Markdown')
        bot.answer_callback_query(call.id)
        return
    
    # ব্যাক টু কান্ট্রি
    if call.data.startswith("back_to_countries_"):
        service = call.data.replace("back_to_countries_", "")
        bot.edit_message_text(f"📱 *Select Country for {service.upper()}:*", call.message.chat.id, call.message.message_id, reply_markup=country_keyboard(service), parse_mode='Markdown')
        bot.answer_callback_query(call.id)
        return
    
    # কান্ট্রি সিলেক্ট ও নাম্বার দেওয়া
    if call.data.startswith("country_"):
        parts = call.data.split("_")
        service = parts[1]
        country = parts[2]
        
        ranges_data = load_ranges()
        if service not in ranges_data or country not in ranges_data[service]:
            bot.answer_callback_query(call.id, f"❌ No range configured for {service} {country}!", show_alert=True)
            return
        
        range_value = ranges_data[service][country]
        
        # API থেকে নাম্বার নেওয়া
        bot.edit_message_text(f"⏳ *Getting number for {service.upper()} {country}...*\nPlease wait.", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        
        selected_number = get_number_from_api(range_value)
        
        if not selected_number:
            bot.edit_message_text(f"❌ *Failed to get number!*\nNo numbers available for {service.upper()} {country}.\nPlease try again later.", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
            bot.answer_callback_query(call.id)
            return
        
        # ইউজারের ডাটা সেভ
        user_data = load_user_data()
        user_data[str(user_id)] = {
            'number': selected_number,
            'service': service,
            'country': country,
            'range': range_value,
            'timestamp': datetime.now().isoformat()
        }
        save_user_data(user_data)
        
        # OTP মনিটরিং শুরু
        monitor_thread = threading.Thread(target=monitor_otp, args=(user_id, selected_number, service, country, range_value))
        monitor_thread.start()
        
        bot.edit_message_text(
            f"📱 *Your {service.upper()} {country} Number:*\n`{selected_number}`\n\n👆 Tap to copy\n\n⏳ *Waiting for OTP...* (20 minutes max)\nYou will receive OTP automatically when it arrives.",
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
        
        ranges_data = load_ranges()
        if service not in ranges_data or country not in ranges_data[service]:
            bot.answer_callback_query(call.id, f"❌ No range configured!", show_alert=True)
            return
        
        range_value = ranges_data[service][country]
        
        bot.edit_message_text(f"⏳ *Getting new number...*", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        
        new_number = get_number_from_api(range_value)
        
        if not new_number:
            bot.edit_message_text(f"❌ *Failed to get new number!*", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
            bot.answer_callback_query(call.id)
            return
        
        # ইউজারের ডাটা আপডেট
        user_data = load_user_data()
        user_data[str(user_id)] = {
            'number': new_number,
            'service': service,
            'country': country,
            'range': range_value,
            'timestamp': datetime.now().isoformat()
        }
        save_user_data(user_data)
        
        # OTP মনিটরিং শুরু
        monitor_thread = threading.Thread(target=monitor_otp, args=(user_id, new_number, service, country, range_value))
        monitor_thread.start()
        
        bot.edit_message_text(
            f"🔄 *New {service.upper()} {country} Number:*\n`{new_number}`\n\n👆 Tap to copy\n\n⏳ *Waiting for OTP...*",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=number_action_keyboard(service, country, new_number),
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
        return
    
    # ========== অ্যাডমিন কলব্যাক ==========
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "⛔ Admin only!", show_alert=True)
        return
    
    if call.data == "admin_manage_admins":
        markup = InlineKeyboardMarkup(row_width=1)
        btn_add = InlineKeyboardButton("➕ Add Admin", callback_data="admin_add_admin")
        btn_remove = InlineKeyboardButton("❌ Remove Admin", callback_data="admin_remove_admin")
        btn_list = InlineKeyboardButton("📋 List Admins", callback_data="admin_list_admins")
        btn_back = InlineKeyboardButton("◀️ Back", callback_data="admin_back")
        markup.add(btn_add, btn_remove, btn_list, btn_back)
        bot.edit_message_text("👑 *Manage Admins*", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    
    elif call.data == "admin_add_admin":
        msg = bot.send_message(call.message.chat.id, "📝 *Send the User ID to add as Admin:*\n\nExample: `7273011237`", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_add_admin)
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_remove_admin":
        admins = load_admins()
        if len(admins) <= 1:
            bot.answer_callback_query(call.id, "❌ Cannot remove the last admin!", show_alert=True)
            return
        msg = bot.send_message(call.message.chat.id, "📝 *Send the User ID to remove from Admin:*", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_remove_admin)
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_list_admins":
        admins = load_admins()
        admin_list = "\n".join([f"🆔 `{uid}`" for uid in admins.keys()])
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"📋 *Admin List:*\n\n{admin_list}", parse_mode='Markdown')
    
    elif call.data == "admin_manage_services":
        markup = InlineKeyboardMarkup(row_width=1)
        btn_add = InlineKeyboardButton("➕ Add Service", callback_data="admin_add_service")
        btn_remove = InlineKeyboardButton("❌ Remove Service", callback_data="admin_remove_service")
        btn_list = InlineKeyboardButton("📋 List Services", callback_data="admin_list_services")
        btn_back = InlineKeyboardButton("◀️ Back", callback_data="admin_back")
        markup.add(btn_add, btn_remove, btn_list, btn_back)
        bot.edit_message_text("📂 *Manage Services*", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    
    elif call.data == "admin_add_service":
        msg = bot.send_message(call.message.chat.id, "📝 *Send the Service Name to add:*\n\nExample: `tiktok`", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_add_service)
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_remove_service":
        ranges_data = load_ranges()
        if not ranges_data:
            bot.answer_callback_query(call.id, "❌ No services to remove!", show_alert=True)
            return
        markup = InlineKeyboardMarkup(row_width=1)
        for service in ranges_data.keys():
            markup.add(InlineKeyboardButton(f"❌ {service.capitalize()}", callback_data=f"admin_remove_service_{service}"))
        markup.add(InlineKeyboardButton("◀️ Back", callback_data="admin_manage_services"))
        bot.edit_message_text("📂 *Select service to remove:*", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    
    elif call.data.startswith("admin_remove_service_"):
        service = call.data.replace("admin_remove_service_", "")
        ranges_data = load_ranges()
        if service in ranges_data:
            del ranges_data[service]
            save_ranges(ranges_data)
            bot.answer_callback_query(call.id, f"✅ Service '{service}' removed!", show_alert=True)
            bot.edit_message_text(f"✅ *Service '{service}' removed successfully!*", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    
    elif call.data == "admin_list_services":
        ranges_data = load_ranges()
        if not ranges_data:
            bot.send_message(call.message.chat.id, "📋 *No services found!*", parse_mode='Markdown')
        else:
            service_list = "\n".join([f"📘 *{s.capitalize()}*: {', '.join(ranges_data[s].keys())}" for s in ranges_data.keys()])
            bot.send_message(call.message.chat.id, f"📋 *Services & Countries:*\n\n{service_list}", parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_manage_countries":
        ranges_data = load_ranges()
        if not ranges_data:
            bot.answer_callback_query(call.id, "❌ No services found!", show_alert=True)
            return
        markup = InlineKeyboardMarkup(row_width=1)
        for service in ranges_data.keys():
            markup.add(InlineKeyboardButton(f"🌍 {service.capitalize()}", callback_data=f"admin_manage_country_{service}"))
        markup.add(InlineKeyboardButton("◀️ Back", callback_data="admin_back"))
        bot.edit_message_text("🌍 *Select service to manage countries:*", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    
    elif call.data.startswith("admin_manage_country_"):
        service = call.data.replace("admin_manage_country_", "")
        markup = InlineKeyboardMarkup(row_width=1)
        btn_add = InlineKeyboardButton("➕ Add Country + Range", callback_data=f"admin_add_country_{service}")
        btn_remove = InlineKeyboardButton("❌ Remove Country", callback_data=f"admin_remove_country_{service}")
        btn_list = InlineKeyboardButton("📋 List Countries", callback_data=f"admin_list_countries_{service}")
        btn_back = InlineKeyboardButton("◀️ Back", callback_data="admin_manage_countries")
        markup.add(btn_add, btn_remove, btn_list, btn_back)
        bot.edit_message_text(f"🌍 *Manage Countries for {service.upper()}*", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    
    elif call.data.startswith("admin_add_country_"):
        service = call.data.replace("admin_add_country_", "")
        msg = bot.send_message(call.message.chat.id, f"📝 *Send Country and Range for {service.upper()}:*\n\nFormat: `COUNTRY RANGE`\nExample: `IN 22507681XXX`", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_add_country, service)
        bot.answer_callback_query(call.id)
    
    elif call.data.startswith("admin_remove_country_"):
        service = call.data.replace("admin_remove_country_", "")
        ranges_data = load_ranges()
        if service not in ranges_data or not ranges_data[service]:
            bot.answer_callback_query(call.id, "❌ No countries to remove!", show_alert=True)
            return
        markup = InlineKeyboardMarkup(row_width=1)
        for country in ranges_data[service].keys():
            markup.add(InlineKeyboardButton(f"❌ {country}", callback_data=f"admin_remove_country_{service}_{country}"))
        markup.add(InlineKeyboardButton("◀️ Back", callback_data=f"admin_manage_country_{service}"))
        bot.edit_message_text(f"🌍 *Select country to remove from {service.upper()}:*", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    
    elif call.data.startswith("admin_remove_country_"):
        parts = call.data.split("_")
        if len(parts) == 5:
            service = parts[3]
            country = parts[4]
            ranges_data = load_ranges()
            if service in ranges_data and country in ranges_data[service]:
                del ranges_data[service][country]
                save_ranges(ranges_data)
                bot.answer_callback_query(call.id, f"✅ Country '{country}' removed!", show_alert=True)
                bot.edit_message_text(f"✅ *Country '{country}' removed from {service.upper()}!*", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    
    elif call.data.startswith("admin_list_countries_"):
        service = call.data.replace("admin_list_countries_", "")
        ranges_data = load_ranges()
        if service in ranges_data and ranges_data[service]:
            country_list = "\n".join([f"🌍 *{c}*: `{r}`" for c, r in ranges_data[service].items()])
            bot.send_message(call.message.chat.id, f"📋 *Countries for {service.upper()}:*\n\n{country_list}", parse_mode='Markdown')
        else:
            bot.send_message(call.message.chat.id, f"📋 *No countries found for {service.upper()}!*", parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_stats":
        user_data = load_user_data()
        ranges_data = load_ranges()
        monitor_data = load_otp_monitor()
        
        completed = sum(1 for m in monitor_data.values() if m.get('status') == 'completed')
        timeout = sum(1 for m in monitor_data.values() if m.get('status') == 'timeout')
        
        stats_text = (
            "📊 *System Stats:*\n\n"
            f"👥 Total Users: `{len(user_data)}`\n"
            f"📂 Services: `{len(ranges_data)}`\n"
            f"✅ OTP Completed: `{completed}`\n"
            f"⏰ OTP Timeout: `{timeout}`\n"
            f"🔄 Active Monitors: `{len(monitor_data)}`"
        )
        bot.edit_message_text(stats_text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_reset":
        markup = InlineKeyboardMarkup(row_width=1)
        btn_confirm = InlineKeyboardButton("⚠️ CONFIRM RESET ⚠️", callback_data="admin_reset_confirm")
        btn_back = InlineKeyboardButton("◀️ Cancel", callback_data="admin_back")
        markup.add(btn_confirm, btn_back)
        bot.edit_message_text("⚠️ *WARNING!*\n\nThis will reset ALL user data!\nAre you sure?", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
    
    elif call.data == "admin_reset_confirm":
        if os.path.exists(USER_DATA_FILE):
            os.remove(USER_DATA_FILE)
        if os.path.exists(OTP_MONITOR_FILE):
            os.remove(OTP_MONITOR_FILE)
        bot.edit_message_text("✅ *All user data has been reset!*", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 *Send your broadcast message:*\n\n(Everyone will receive this)", parse_mode='Markdown')
        bot.register_next_step_handler(msg, process_broadcast)
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_back":
        bot.edit_message_text("🔧 *Admin Control Panel*", call.message.chat.id, call.message.message_id, reply_markup=admin_panel_keyboard(), parse_mode='Markdown')
        bot.answer_callback_query(call.id)

# ========== অ্যাডমিন প্রসেস ফাংশন ==========
def process_add_admin(message):
    try:
        user_id = int(message.text.strip())
        admins = load_admins()
        admins[str(user_id)] = True
        save_admins(admins)
        bot.reply_to(message, f"✅ User `{user_id}` added as Admin!", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ Invalid User ID!")

def process_remove_admin(message):
    try:
        user_id = int(message.text.strip())
        admins = load_admins()
        if str(user_id) in admins and len(admins) > 1:
            del admins[str(user_id)]
            save_admins(admins)
            bot.reply_to(message, f"✅ User `{user_id}` removed from Admin!", parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Cannot remove or user not found!")
    except:
        bot.reply_to(message, "❌ Invalid User ID!")

def process_add_service(message):
    service = message.text.strip().lower()
    ranges_data = load_ranges()
    if service in ranges_data:
        bot.reply_to(message, f"❌ Service '{service}' already exists!")
        return
    ranges_data[service] = {}
    save_ranges(ranges_data)
    bot.reply_to(message, f"✅ Service '{service}' added!\n\nNow add countries using Admin Panel -> Manage Countries.", parse_mode='Markdown')

def process_add_country(message, service):
    try:
        parts = message.text.strip().upper().split()
        if len(parts) != 2:
            bot.reply_to(message, "❌ Invalid format! Use: `COUNTRY RANGE`\nExample: `IN 22507681XXX`", parse_mode='Markdown')
            return
        country = parts[0]
        range_value = parts[1]
        
        ranges_data = load_ranges()
        if service not in ranges_data:
            ranges_data[service] = {}
        ranges_data[service][country] = range_value
        save_ranges(ranges_data)
        bot.reply_to(message, f"✅ Country '{country}' with range `{range_value}` added to {service.upper()}!", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ Error adding country!")

def process_broadcast(message):
    broadcast_text = message.text
    user_data = load_user_data()
    sent = 0
    for user_id in user_data.keys():
        try:
            bot.send_message(int(user_id), f"📢 *Broadcast Message:*\n\n{broadcast_text}", parse_mode='Markdown')
            sent += 1
            time.sleep(0.05)
        except:
            pass
    bot.reply_to(message, f"✅ Broadcast sent to {sent} users!")

# ========== Flask রাউট ==========
@app.route('/')
def home():
    return "OTP Bot is running!", 200

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ========== বট চালু ==========
if __name__ == "__main__":
    # প্রাথমিক API টোকেন সেটআপ
    get_api_token()
    
    # ফ্লাস্ক থ্রেড
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    print("🤖 Bot Starting....")
    print(f"✅ Force Join Channel: {FORCE_CHANNEL}")
    print(f"✅ Force Join Group: {FORCE_GROUP}")
    
    try:
        bot.get_chat(FORCE_CHANNEL)
        bot.get_chat(FORCE_GROUP)
        print("✅ Channel and Group Access Success.")
    except:
        print("⚠️ Access Problem! Make sure bot is admin.")
    
    print("🚀 Bot Running...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
