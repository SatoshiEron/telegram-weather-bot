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

# Функция для получения погоды
def get_weather(city):
    try:
        # Делаем запрос к API OpenWeatherMap
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
        response = requests.get(url)
        weather_data = response.json()
        
        if weather_data.get('cod') == 200:
            # Парсим данные
            temp = weather_data['main']['temp']
            feels_like = weather_data['main']['feels_like']
            humidity = weather_data['main']['humidity']
            description = weather_data['weather'][0]['description']
            wind_speed = weather_data['wind']['speed']
            city_name = weather_data['name']
            
            # Формируем ответ
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

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = """
👋 Привет! Я бот с прогнозом погоды!

Доступные команды:
/weather [город] - узнать погоду (например: /weather Москва)
/help - список команд
    """
    bot.send_message(message.chat.id, welcome_text)

# Команда /help
@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
📋 Список команд:

/start - Начать работу
/help - Показать это сообщение
/weather [город] - Узнать погоду

Пример: /weather Санкт-Петербург
    """
    bot.send_message(message.chat.id, help_text)

# Команда /weather
@bot.message_handler(commands=['weather'])
def weather_command(message):
    # Получаем название города после команды
    try:
        city = message.text.split('/weather ')[1]
        if not city.strip():
            bot.send_message(message.chat.id, "❌ Напиши название города после команды. Например: /weather Москва")
            return
    except:
        bot.send_message(message.chat.id, "❌ Напиши название города после команды. Например: /weather Москва")
        return
    
    # Отправляем сообщение, что ищем погоду
    msg = bot.send_message(message.chat.id, f"🔍 Ищу погоду в городе {city}...")
    
    # Получаем погоду
    weather_info = get_weather(city)
    
    # Обновляем сообщение с результатом
    bot.edit_message_text(weather_info, message.chat.id, msg.message_id)

# Обработка всех остальных сообщений
@bot.message_handler(func=lambda message: True)
def echo(message):
    bot.send_message(message.chat.id, f"Ты написал: {message.text}\n\nИспользуй /help чтобы узнать команды.")

print("✅ Бот с погодой запущен! Нажми Ctrl+C для остановки.")
bot.polling()