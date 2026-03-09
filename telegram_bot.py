import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# Простой HTTP сервер для Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_http_server():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHandler)
    server.serve_forever()

# Запускаем HTTP сервер в отдельном потоке
threading.Thread(target=run_http_server, daemon=True).start()
print("📡 HTTP сервер запущен на порту 10000")

import telebot
import os
import requests
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# Загружаем переменные из .env файла
load_dotenv()

# Получаем токены
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')

# Проверяем, что токены загружены
if not BOT_TOKEN:
    raise ValueError("❌ Токен бота не найден! Проверь файл .env")
if not WEATHER_API_KEY:
    raise ValueError("❌ Ключ погоды не найден! Проверь файл .env")

# Создаём бота
bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище последних городов пользователей
user_last_cities = {}

# Функция для получения погоды (текущая)
def get_weather(city):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
        response = requests.get(url)
        weather_data = response.json()
        
        if weather_data.get('cod') == 200:
            temp = weather_data['main']['temp']
            feels_like = weather_data['main']['feels_like']
            humidity = weather_data['main']['humidity']
            description = weather_data['weather'][0]['description']
            wind_speed = weather_data['wind']['speed']
            city_name = weather_data['name']
            
            weather_text = f"🌍 Погода в {city_name}:\n\n"
            weather_text += f"🌡 Температура: {temp:.1f}°C (ощущается как {feels_like:.1f}°C)\n"
            weather_text += f"☁️ Описание: {description.capitalize()}\n"
            weather_text += f"💧 Влажность: {humidity}%\n"
            weather_text += f"💨 Ветер: {wind_speed} м/с"
            
            return weather_text
        else:
            return f"❌ Город '{city}' не найден. Проверь название."
    except Exception as e:
        return f"❌ Ошибка при получении погоды: {e}"

# Функция для получения прогноза
def get_forecast(city, days=3):
    try:
        if days > 5:
            days = 5
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru&cnt={days*8}"
        response = requests.get(url)
        forecast_data = response.json()
        
        if forecast_data.get('cod') != '200':
            return f"❌ Город '{city}' не найден"
        
        city_name = forecast_data['city']['name']
        forecast_text = f"📅 Прогноз погоды в {city_name} на {days} дней:\n\n"
        
        # Группируем по дням
        daily_data = {}
        for item in forecast_data['list']:
            date = item['dt_txt'].split()[0]
            if date not in daily_data:
                daily_data[date] = {
                    'temps': [],
                    'descriptions': []
                }
            daily_data[date]['temps'].append(item['main']['temp'])
            daily_data[date]['descriptions'].append(item['weather'][0]['description'])
        
        # Формируем прогноз по дням
        for i, (date, data) in enumerate(list(daily_data.items())[:days]):
            avg_temp = sum(data['temps']) / len(data['temps'])
            main_desc = max(set(data['descriptions']), key=data['descriptions'].count)
            
            if 'дождь' in main_desc.lower():
                emoji = "🌧"
            elif 'снег' in main_desc.lower():
                emoji = "❄️"
            elif 'облач' in main_desc.lower():
                emoji = "☁️"
            else:
                emoji = "☀️"
            
            forecast_text += f"{emoji} {date}: {avg_temp:.1f}°C, {main_desc}\n"
        
        return forecast_text
        
    except Exception as e:
        return f"❌ Ошибка при получении прогноза: {e}"

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    popular_cities = ['Москва', 'Санкт-Петербург', 'Екатеринбург', 'Казань', 
                     'Новосибирск', 'Краснодар', 'Сочи', 'Калининград']
    
    buttons = []
    for city in popular_cities:
        buttons.append(KeyboardButton(f"🌤 {city}"))
    
    markup.add(*buttons[:4])
    markup.add(*buttons[4:])
    markup.add(KeyboardButton("🔍 Поиск города"))
    markup.add(KeyboardButton("📅 Прогноз"))
    markup.add(KeyboardButton("❓ Помощь"))
    
    welcome_text = """
👋 Привет! Я бот погоды.

🔹 Нажми на кнопку с городом для быстрого поиска
🔹 Или нажми "Поиск города" и введи название
🔹 Можно писать на русском или английском

Пример: Москва, London, Нью-Йорк
    """
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)
    user_last_cities[message.chat.id] = {'state': 'main_menu'}

# Функция отправки погоды
def get_weather_and_send(chat_id, city):
    bot.send_chat_action(chat_id, 'typing')
    weather_info = get_weather(city)
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{city}"),
        InlineKeyboardButton("📅 Прогноз", callback_data=f"forecast_{city}")
    )
    markup.add(
        InlineKeyboardButton("🔍 Другой город", callback_data="search_city"),
        InlineKeyboardButton("◀️ Меню", callback_data="back_to_menu")
    )
    
    bot.send_message(chat_id, weather_info, reply_markup=markup)
    
    if chat_id not in user_last_cities:
        user_last_cities[chat_id] = {}
    user_last_cities[chat_id]['last_city'] = city

# Меню выбора дней для прогноза
def show_forecast_days_menu(chat_id, city):
    markup = InlineKeyboardMarkup(row_width=3)
    days = [3, 5, 7]
    for d in days:
        markup.add(InlineKeyboardButton(
            f"{d} дней", 
            callback_data=f"show_forecast_{city}_{d}"
        ))
    markup.add(InlineKeyboardButton("◀️ Назад", callback_data=f"back_to_weather_{city}"))
    
    bot.send_message(
        chat_id,
        f"📅 На сколько дней показать прогноз для {city}?",
        reply_markup=markup
    )

# Обработка текстовых сообщений
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    chat_id = message.chat.id
    text = message.text
    
    if text == "🔍 Поиск города":
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("◀️ Назад в меню"))
        bot.send_message(
            chat_id, 
            "🌆 Введи название любого города:",
            reply_markup=markup
        )
        user_last_cities[chat_id] = {'state': 'waiting_city'}
    
    elif text == "📅 Прогноз":
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(KeyboardButton("◀️ Назад в меню"))
        bot.send_message(
            chat_id,
            "🌆 Введи название города для прогноза:",
            reply_markup=markup
        )
        user_last_cities[chat_id] = {'state': 'waiting_forecast_city'}
    
    elif text == "❓ Помощь":
        help_text = """
❓ Как пользоваться ботом:

1️⃣ Нажми на кнопку с городом для быстрой погоды
2️⃣ Нажми "Поиск города" и введи любой город
3️⃣ Нажми "Прогноз" для погоды на несколько дней

Команды:
/start - Главное меню
        """
        bot.send_message(chat_id, help_text)
    
    elif text == "◀️ Назад в меню":
        start(message)
    
    elif text.startswith("🌤 "):
        city = text.replace("🌤 ", "")
        get_weather_and_send(chat_id, city)
    
    elif user_last_cities.get(chat_id, {}).get('state') == 'waiting_city':
        city = text
        get_weather_and_send(chat_id, city)
        user_last_cities[chat_id] = {'state': 'main_menu'}
        start(message)
    
    elif user_last_cities.get(chat_id, {}).get('state') == 'waiting_forecast_city':
        city = text
        show_forecast_days_menu(chat_id, city)
        user_last_cities[chat_id] = {'state': 'main_menu'}
    
    else:
        get_weather_and_send(chat_id, text)

# Обработка инлайн-кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    if call.data.startswith("refresh_"):
        city = call.data.replace("refresh_", "")
        weather_info = get_weather(city)
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{city}"),
            InlineKeyboardButton("📅 Прогноз", callback_data=f"forecast_{city}")
        )
        markup.add(
            InlineKeyboardButton("🔍 Другой город", callback_data="search_city"),
            InlineKeyboardButton("◀️ Меню", callback_data="back_to_menu")
        )
        
        bot.edit_message_text(
            weather_info,
            chat_id,
            message_id,
            reply_markup=markup
        )
    
    elif call.data.startswith("forecast_"):
        city = call.data.replace("forecast_", "")
        show_forecast_days_menu(chat_id, city)
        bot.delete_message(chat_id, message_id)
    
    elif call.data.startswith("show_forecast_"):
        parts = call.data.replace("show_forecast_", "").split("_")
        city = parts[0]
        days = int(parts[1])
        forecast_info = get_forecast(city, days)
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("◀️ К погоде", callback_data=f"refresh_{city}"),
            InlineKeyboardButton("🔍 Другой город", callback_data="search_city")
        )
        
        bot.edit_message_text(
            forecast_info,
            chat_id,
            message_id,
            reply_markup=markup
        )
    
    elif call.data.startswith("back_to_weather_"):
        city = call.data.replace("back_to_weather_", "")
        get_weather_and_send(chat_id, city)
        bot.delete_message(chat_id, message_id)
    
    elif call.data == "search_city":
        bot.edit_message_text(
            "🌆 Введи название города:",
            chat_id,
            message_id
        )
        user_last_cities[chat_id] = {'state': 'waiting_city'}
    
    elif call.data == "back_to_menu":
        bot.delete_message(chat_id, message_id)
        start(call.message)

print("✅ Бот с погодой запущен! Нажми Ctrl+C для остановки.")
bot.polling()