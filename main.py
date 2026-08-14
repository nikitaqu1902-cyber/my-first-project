# =============================================
# ИМПОРТ БИБЛИОТЕК
# =============================================
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
import aiohttp
import asyncio
from datetime import datetime, timedelta
import os

# =============================================
# НАСТРОЙКА
# =============================================
logging.basicConfig(level=logging.INFO)

# ТОКЕН БОТА (ВСТАВЬ СВОЙ)
BOT_TOKEN = "8407396049:AAH1aq8TpKIfPvSXpJFFrp5X18AtnllBhtY"

# СОЗДАЁМ БОТА
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =============================================
# ФУНКЦИЯ ПОЛУЧЕНИЯ ПОГОДЫ (БЕЗ КЛЮЧА!)
# =============================================
async def get_weather_7days(city: str):
    """
    Получает погоду на 7 дней через Open-Meteo
    Сначала переводит название города в координаты
    """
    try:
        # =============================================
        # ШАГ 1: ПОЛУЧАЕМ КООРДИНАТЫ ГОРОДА
        # =============================================
        geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {
            'name': city,
            'count': 1,
            'language': 'ru'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(geocoding_url, params=params) as resp:
                geo_data = await resp.json()
                
                if not geo_data.get('results'):
                    return None, "❌ Город не найден!"
                
                # Берём первый результат
                location = geo_data['results'][0]
                lat = location['latitude']
                lon = location['longitude']
                city_name = location['name']
                country = location.get('country', '')
                
                # =============================================
                # ШАГ 2: ПОЛУЧАЕМ ПОГОДУ НА 7 ДНЕЙ
                # =============================================
                weather_url = "https://api.open-meteo.com/v1/forecast"
                weather_params = {
                    'latitude': lat,
                    'longitude': lon,
                    'timezone': 'Europe/Moscow',
                    'daily': 'temperature_2m_max,temperature_2m_min,weathercode,windspeed_10m_max',
                    'forecast_days': 7
                }
                
                async with session.get(weather_url, params=weather_params) as resp:
                    weather_data = await resp.json()
                    
                    # =============================================
                    # ШАГ 3: РАСШИФРОВЫВАЕМ ПОГОДУ
                    # =============================================
                    daily = weather_data['daily']
                    dates = daily['time']
                    temp_max = daily['temperature_2m_max']
                    temp_min = daily['temperature_2m_min']
                    weather_codes = daily['weathercode']
                    wind_speed = daily['windspeed_10m_max']
                    
                    # Расшифровка кодов погоды
                    def decode_weather(code):
                        weather_map = {
                            0: "☀️ Ясно",
                            1: "🌤 Малооблачно",
                            2: "⛅ Переменная облачность",
                            3: "☁️ Пасмурно",
                            45: "🌫 Туман",
                            48: "🌫 Туман с изморозью",
                            51: "🌧 Легкая морось",
                            53: "🌧 Морось",
                            55: "🌧 Сильная морось",
                            61: "🌧 Небольшой дождь",
                            63: "🌧 Дождь",
                            65: "🌧 Сильный дождь",
                            71: "🌨 Небольшой снег",
                            73: "🌨 Снег",
                            75: "🌨 Сильный снег",
                            80: "🌧 Ливень",
                            81: "🌧 Сильный ливень",
                            95: "⛈ Гроза",
                            96: "⛈ Гроза с градом"
                        }
                        return weather_map.get(code, f"❓ Код: {code}")
                    
                    # Формируем прогноз на 7 дней
                    forecast = []
                    today = datetime.now().date()
                    
                    for i in range(7):
                        date_obj = datetime.strptime(dates[i], '%Y-%m-%d').date()
                        day_name = "Сегодня" if i == 0 else "Завтра" if i == 1 else date_obj.strftime("%A")
                        
                        # Перевод дней недели на русский
                        days_ru = {
                            'Monday': 'Понедельник',
                            'Tuesday': 'Вторник',
                            'Wednesday': 'Среда',
                            'Thursday': 'Четверг',
                            'Friday': 'Пятница',
                            'Saturday': 'Суббота',
                            'Sunday': 'Воскресенье'
                        }
                        day_name_ru = days_ru.get(day_name, day_name)
                        
                        forecast.append({
                            'date': date_obj.strftime('%d.%m'),
                            'day': day_name_ru,
                            'temp_max': round(temp_max[i]),
                            'temp_min': round(temp_min[i]),
                            'weather': decode_weather(weather_codes[i]),
                            'wind': round(wind_speed[i])
                        })
                    
                    return {
                        'city': city_name,
                        'country': country,
                        'forecast': forecast
                    }, None
                    
    except Exception as e:
        return None, f"❌ Ошибка: {str(e)}"

# =============================================
# КОМАНДА /start
# =============================================
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "🌤 Привет! Я покажу погоду на 7 дней!\n\n"
        "Просто напиши название города:\n"
        "Например: Москва\n"
        "Или: /weather Москва\n\n"
        "Доступно: прогноз на неделю + текущая погода!"
    )

# =============================================
# КОМАНДА /weather [город]
# =============================================
@dp.message(Command("weather"))
async def weather_command(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Напиши город: /weather Москва")
        return
    
    city = parts[1].strip()
    await send_weather(message, city)

# =============================================
# ОБРАБОТКА ЛЮБОГО ТЕКСТА (как город)
# =============================================
@dp.message()
async def handle_text(message: Message):
    city = message.text.strip()
    await send_weather(message, city)

# =============================================
# ФУНКЦИЯ ОТПРАВКИ ПОГОДЫ
# =============================================
async def send_weather(message: Message, city: str):
    # Отправляем сообщение "ищу..."
    wait_msg = await message.answer(f"🔍 Ищу погоду для {city}...")
    
    # Получаем погоду
    result, error = await get_weather_7days(city)
    
    if error:
        await wait_msg.edit_text(error)
        return
    
    # =============================================
    # ФОРМИРУЕМ КРАСИВЫЙ ОТВЕТ
    # =============================================
    forecast_text = f"🌍 **{result['city']}, {result['country']}**\n"
    forecast_text += f"📅 Прогноз на 7 дней:\n\n"
    
    for day in result['forecast']:
        forecast_text += (
            f"**{day['day']}** ({day['date']})\n"
            f"{day['weather']}\n"
            f"🌡 {day['temp_min']}°C ~ {day['temp_max']}°C\n"
            f"💨 Ветер: {day['wind']} км/ч\n\n"
        )
    
    # Сокращаем, если сообщение слишком длинное
    if len(forecast_text) > 4000:
        forecast_text = forecast_text[:3990] + "..."
    
    # Удаляем сообщение "ищу..." и отправляем результат
    await wait_msg.delete()
    await message.answer(forecast_text, parse_mode="Markdown")

# =============================================
# ЗАПУСК БОТА
# =============================================
async def main():
    print("🚀 БОТ ЗАПУЩЕН!")
    print("Бот сам ищет погоду в интернете на 7 дней!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

# =============================================
# КОМАНДА /recommendations - РЕКОМЕНДАЦИИ
# =============================================
@dp.message(Command("recommendations"))
async def recommendations_command(message: Message):
    """Даёт рекомендации на основе прогноза"""
    await message.answer("🌤 Скажите город для рекомендаций:\nНапример: Москва")

# =============================================
# КОМАНДА /agents - ПОКАЗАТЬ ПРАВИЛА
# =============================================
@dp.message(Command("agents"))
async def agents_command(message: Message):
    """Показывает файл agents.md"""
    try:
        with open("agents.md", "r", encoding="utf-8") as f:
            agents_text = f.read()
            # Отправляем файл или текст
            if len(agents_text) > 4096:
                # Если слишком длинный - отправляем файлом
                await message.answer_document(
                    types.InputFile("agents.md"),
                    caption="📋 Правила работы агента погодных рекомендаций"
                )
            else:
                await message.answer(agents_text)
    except FileNotFoundError:
        await message.answer("❌ Файл agents.md не найден!")

# =============================================
# ФУНКЦИЯ ГЕНЕРАЦИИ РЕКОМЕНДАЦИЙ
# =============================================
async def get_recommendations(city: str, weather_data: dict):
    """Генерирует рекомендации на основе weather_data"""
    forecast = weather_data['forecast']
    today = forecast[0]
    tomorrow = forecast[1] if len(forecast) > 1 else None
    
    # Находим самый тёплый и холодный день
    max_temp_day = max(forecast, key=lambda x: x['temp_max'])
    min_temp_day = min(forecast, key=lambda x: x['temp_min'])
    
    # Формируем рекомендации
    rec = f"📋 **Погодные рекомендации для {weather_data['city']}**\n\n"
    
    # 1. ОДЕЖДА НА СЕГОДНЯ
    t = today['temp_max']
    if t < -20:
        clothes = "🥶 Пуховик, шапка-ушанка, шерстяные носки, термобельё"
    elif t < -10:
        clothes = "❄️ Пуховик, тёплая шапка, шарф, варежки"
    elif t < 0:
        clothes = "🧥 Зимняя куртка, шапка, перчатки"
    elif t < 5:
        clothes = "🧥 Демисезонная куртка, шапка"
    elif t < 10:
        clothes = "🧥 Лёгкая куртка или ветровка"
    elif t < 15:
        clothes = "👕 Кофта с длинным рукавом, джинсы"
    elif t < 20:
        clothes = "👕 Футболка, лёгкая рубашка"
    elif t < 25:
        clothes = "👕 Футболка, шорты"
    elif t < 30:
        clothes = "🩳 Лёгкая одежда, головной убор"
    else:
        clothes = "🥵 Светлая одежда, панама, пить воду"
    
    rec += f"**🧥 СЕГОДНЯ ({today['day']}):**\n{clothes}\n\n"
    
    # 2. ЗАВТРА
    if tomorrow:
        t2 = tomorrow['temp_max']
        if t2 - t > 5:
            rec += f"**📈 ЗАВТРА теплее на {round(t2 - t)}°C** — можно одеться легче!\n"
        elif t - t2 > 5:
            rec += f"**📉 ЗАВТРА холоднее на {round(t - t2)}°C** — одевайтесь теплее!\n"
        else:
            rec += f"**👌 ЗАВТРА** температура без резких изменений.\n"
        rec += "\n"
    
    # 3. ОСАДКИ И ВЕТЕР
    rain_days = [d for d in forecast if 'дождь' in d['weather'].lower() or 'ливень' in d['weather'].lower()]
    windy_days = [d for d in forecast if d['wind'] > 30]
    snow_days = [d for d in forecast if 'снег' in d['weather'].lower()]
    
    if rain_days:
        days_str = ", ".join([d['day'] for d in rain_days])
        rec += f"☂️ **ДОЖДЬ:** {days_str} — не забудьте зонт!\n\n"
    
    if snow_days:
        days_str = ", ".join([d['day'] for d in snow_days])
        rec += f"❄️ **СНЕГ:** {days_str} — обувайтесь теплее!\n\n"
    
    if windy_days:
        days_str = ", ".join([d['day'] for d in windy_days])
        rec += f"💨 **СИЛЬНЫЙ ВЕТЕР:** {days_str} — осторожно, возможны проблемы с зонтами!\n\n"
    
    # 4. АКТИВНОСТИ
    sunny_days = [d for d in forecast if 'Ясно' in d['weather'] or 'Малооблачно' in d['weather']]
    if sunny_days:
        days_str = ", ".join([d['day'] for d in sunny_days[:3]])
        rec += f"🌳 **ЛУЧШИЕ ДНИ ДЛЯ ПРОГУЛОК:** {days_str}\n\n"
    
    # 5. САМЫЙ ТЁПЛЫЙ И ХОЛОДНЫЙ ДЕНЬ
    rec += f"🌟 **САМЫЙ ТЁПЛЫЙ ДЕНЬ:** {max_temp_day['day']} (+{max_temp_day['temp_max']}°C)\n"
    rec += f"❄️ **САМЫЙ ХОЛОДНЫЙ:** {min_temp_day['day']} (+{min_temp_day['temp_min']}°C)\n"
    
    return rec

# =============================================
# ОБРАБОТЧИК КОМАНДЫ "рекомендации"
# =============================================
@dp.message()
async def handle_recommendations(message: Message):
    text = message.text.lower().strip()
    
    # Если пользователь пишет "рекомендации", "советы", "агент"
    if text in ['рекомендации', 'советы', 'что надеть', 'агент', 'agents', 'recommendations']:
        await message.answer("🌤 Напишите город для рекомендаций:")
        # Сохраняем состояние, что ждём город
        # (упрощённо - в следующем сообщении будет город)
        return
    
    # Проверяем, был ли запрос на рекомендации (храним в глобальной переменной)
    # Для простоты - если сообщение НЕ команда, проверяем, что это город
    if not text.startswith('/'):
        # Получаем погоду
        result, error = await get_weather_7days(text)
        if error:
            await message.answer(error)
            return
        
        # Генерируем рекомендации
        rec_text = await get_recommendations(text, result)
        await message.answer(rec_text, parse_mode="Markdown")