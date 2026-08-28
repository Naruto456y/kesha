import logging
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters
import os
import time
import webbrowser
from datetime import datetime, timedelta, date
import psutil
import requests
import keyboard
import mouse
import random
from youtube_search import YoutubeSearch
import ctypes
import AppOpener
import help_meneger
from help_meneger import gTTS
import uuid
import string

path_folder = __file__.replace(r'KeshaBot_fm.py', '')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

COMMAND_CATEGORIES = (
    "🎯 Основные команды\n",
        "Кеша привет - Поприветствовать\n",
        "Кеша как дела - Узнать состояние\n",
        "Кеша молодец - Похвалить\n",
        "Кеша пока/стоп/выход - Завершить работу\n",
    "🌐 Интернет и поиск\n",
        "Кеша найди [запрос] - Поиск в интернете\n",
        "Кеша найди в ютуби [запрос] - Поиск на YouTube\n",
        "Кеша youtube - Открыть YouTube\n",
        "Кеша игры - Открыть Яндекс Игры\n",
        "Кеша погода - Узнать погоду\n",
        "Кеша переводчик - Открыть переводчик\n",
        "Кеша дипси - Открыть нейросеть DeepSeek\n",
    "🎮 Игры\n",
        "Кеша камень ножницы бумага - Запустить игру\n",
        "Кеша виселица - Запустить игру\n",
        "Кеша викторина - Запустить игру\n",
        "Кеша квест - Запустить игру\n",
        "Кеша крестики-нолики - Запустить игру\n",
        "Кеша угадай число - Запустить игру\n",
    "💻 Система и приложения\n",
        "Кеша открой [приложение] - Открыть программу\n",
        "Кеша закрой [приложение] - Закрыть программу\n",
        "Кеша открой проводник - Открыть файловый менеджер\n",
        "Кеша открой настройки - Открыть настройки системы\n",
        "Кеша сверни окно - Свернуть текущее окно\n",
        "Кеша закрой окно - Закрыть текущее окно\n",
        "Кеша открой roblox - Запустить Roblox\n",
        "Кеша открой minecraft - Запустить Minecraft\n",
        "Кеша камера - Открыть камеру\n",
        "Кеша селфи - Сделать селфи\n",
        "Кеша браузер - Открыть браузер\n",
        "Кеша левый/правый клик - Клик мышью\n",
    "🎵 Медиа и управление\n",
        "Кеша музыка [название] - Найти музыку\n",
        "Кеша моя волна - Включить мою волну\n",
        "Кеша пауза/стоп - Поставить на паузу\n",
        "Кеша дальше/следующий - Следующий трек\n",
        "Кеша предыдущий/прошлый - Предыдущий трек\n",
        "Кеша лайк/нравится - Добавить в избранное\n",
        "Кеша дизлайк/не нравится - Убрать из рекомендаций\n",
        "Кеша громче - Увеличить громкость\n",
        "Кеша тише - Уменьшить громкость\n",
        "Кеша громкость [1-100] - Установить громкость\n",
    "⚙️ Системная информация\n",
        "Кеша время - Текущее время\n",
        "Кеша состояние батареи - Информация о батарее\n",
        "Кеша выключи компьютер - Выключить ПК\n",
        "Кеша перезагрузка - Перезагрузить компьютер\n"
        "Кеша спящий режим - Включить спящий режим\n",
    "📚 Учеба\n",
        "Кеша дз/домашнее - Показать домашнее задание\n",
        "Кеша оценки - Показать оценки\n",
        "Кеша расписание - Расписание на завтра\n",
    "🔧 Специальные команды\n",
        "Кеша переведи на английский [текст] - Перевод\n",
        "Кеша переведи на русский [текст] - Перевод\n",
        "Кеша нарисуй [что-то] - Нарисовать\n",
        "Кеша включи свет - Умный дом\n",
        "Кеша выключи свет - Умный дом\n",
        "Кеша вниз - Скролл вниз\n",
        "Кеша верх - Скролл вверх\n",
        "Кеша поставь таймер на [минуты] - Таймер\n",
        "Кеша телефон - Совершить звонок\n",
        "Кеша пробел - Нажать пробел\n",
        "Кеша Bluetooth - Преключить Bluetooth\n"
        "(Кеша писать необезательно)"
)

TOKEN = "8115695282:AAG3h6fIDBcvVhn1ScV7yiKqmpsQDWXBtJk"

RESPONSE_VARIANTS = {
    'ok': ['Принял!', 'Выполняю!', 'Сделано!', 'Уже делаю!', 'Есть!', 'Оброботал!'],
    'search': ['Ищу информацию...', 'Начинаю поиск...', 'Секунду...', 'Ищу в интернете...'],
    'open': ['Открываю...', 'Запускаю...', 'Выполняю...', 'Сейчас открою...'],
    'error': ['Не удалось выполнить', 'Возникла проблема', 'Не получилось', 'Ошибка выполнения'],
    'thanks': ['Всегда пожалуйста!', 'Рад помочь!', 'Обращайтесь!', 'К вашим услугам!']
}

def get_random_response(response_type):
    """Получить случайный вариант ответа"""
    variants = RESPONSE_VARIANTS.get(response_type, ['Выполняю!'])
    return random.choice(variants)

def get_layout():
    try:
        u = ctypes.windll.LoadLibrary("user32.dll")
        # Получаем текущую раскладку
        hkl = u.GetKeyboardLayout(0)
        lang_id = hkl & 0xFFFF
        
        if lang_id == 0x0419:  # Русский
            return False
        elif lang_id == 0x0409:  # Английский
            return True
        return True  # по умолчанию английская
    except:
        return True

def start_file(name):
    """Открывает файл в папке с программой"""
    try:
        os.startfile(path_folder + name)
        return True
    except Exception as e:
        print(f"Ошибка запуска {name}: {e}")
        return False

def get_text_with_url(api="28c9d95c5e0b423d23e81c1d43c10cf0", city="Москва"):
    # URL API
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api}&units=metric&lang=ru"

    try:
        # Отправляем запрос с таймаутом
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        
        # Извлекаем данные (они уже числа)
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        description = data["weather"][0]["description"]
        humidity = data["main"]["humidity"]
        wind_speed = data["wind"]["speed"]

        # Преобразуем числа в строки для конкатенации
        result = {
            "Температура": f"{temp} °C",
            "Ощущается как": f"{feels_like} °C",
            "Описание": description,
            "Влажность": f"{humidity} %",
            "Скорость ветра": f"{wind_speed} м/с"
        }
        return result['Температура']
        
    except requests.exceptions.RequestException as e:
        return f"Ошибка запроса: {str(e)}"
    except Exception as e:
        return f"Произошла ошибка: {str(e)}"

def search_and_open_youtube(query):
    """Поиск и открытие видео на YouTube"""
    try:
        results = YoutubeSearch(query, max_results=1).to_dict()
        if results:
            video_url = f"https://youtube.com{results[0]['url_suffix']}"
            webbrowser.open_new_tab(video_url)
            return True
        return False
    except:
        return False

def set_system_volume(level):
    """Установка громкости системы"""
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume_control = cast(interface, POINTER(IAudioEndpointVolume))
        volume_control.SetMasterVolumeLevelScalar(level, None)
        return True
    except:
        return False

def get_system_volume():
    """Получение текущей громкости"""
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume_control = cast(interface, POINTER(IAudioEndpointVolume))
        return volume_control.GetMasterVolumeLevelScalar()
    except:
        return 0.5

def change_volume(direction):
    """Изменение громкости"""
    current = get_system_volume()
    if direction == 'up':
        new_vol = min(1.0, current + 0.1)
    elif direction == 'down':
        new_vol = max(0.0, current - 0.1)
    else:
        return current

    if set_system_volume(new_vol):
        return new_vol
    return current

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} started the bot")
    cm = ""
    for i in COMMAND_CATEGORIES: 
        cm = cm + i
    await update.message.reply_photo(path_folder + r"\Media\Kesha_icoc.jpeg")
    await update.message.reply_text(cm)

# Движение мышью
async def move_direction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Универсальная функция для перемещения во все стороны с параметром шага"""
    
    # Определяем направление из команды
    command = update.message.text.split()[0].lower()
    
    # Парсим шаг из аргументов
    step = 10  # значение по умолчанию
    if context.args:
        try:
            step = int(context.args[0])
            if step <= 0:
                step = 10
        except ValueError:
            step = 10
    
    # Получаем текущую позицию
    pos = mouse.get_position()
    direction = ""
    
    # Перемещаем в нужном направлении
    if command == '/move_right':
        mouse.move(pos[0] + step, pos[1])
        direction = "вправо"
    elif command == '/move_left':
        mouse.move(pos[0] - step, pos[1])
        direction = "влево"
    elif command == '/move_up':
        mouse.move(pos[0], pos[1] - step)
        direction = "вверх"
    elif command == '/move_down':
        mouse.move(pos[0], pos[1] + step)
        direction = "вниз"
    else:
        await update.message.reply_text("Неизвестная команда")
        return
    
    await update.message.reply_text(
        f"✅ Курсор перемещен {direction} на {step} пикселей"
    )

# КЛИКИ мышью
async def click_left(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mouse.click('left')
    await update.message.reply_text("Левая кнопка мыши нажата")

async def click_right(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mouse.click('right')
    await update.message.reply_text("Правая кнопка мыши нажата")

async def click_middle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mouse.click('middle')
    await update.message.reply_text("Средняя кнопка мыши нажата")

async def say_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace("/say", "")
    if not text:
        await update.message.reply_text("Что я должен сказать?")
        return
    await update.message.reply_text(text)
    help_meneger.manager.say(text)

async def convert_text_to_mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Извлекаем текст после команды
    text = update.message.text.replace("/text_to_audio", "").strip()
    if not text:
        await update.message.reply_text("⚠️ Пожалуйста, введите текст после команды.")
        return
    
    # Определяем язык (простая проверка на кириллицу)
    lang = "ru" if any('а' <= c.lower() <= 'я' for c in text) else "en"
    
    try:
        # Безопасное имя файла
        timestamp = int(time.time())
        safe_filename = f"audio_{timestamp}_{uuid.uuid4().hex[:8]}.mp3"
        temp_file = os.path.join(path_folder, safe_filename)
        tts = gTTS(text=text, lang=lang)
        tts.save(temp_file)
        with open(temp_file, 'rb') as audio_file:
            await update.message.reply_audio(
                audio=audio_file,
                title=f"Аудио из текста",
                performer="Кеша Бот",
                caption=f"📝 Текст: {text[:50]}..." if len(text) > 50 else f"📝 Текст: {text}"
            )
        os.remove(temp_file)
        
    except ImportError:
        await update.message.reply_text(
            "❌ Ошибка: модуль gTTS не установлен или не найден."
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при создании аудио: {str(e)}")

# Обработка текстовых сообщений
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принимает текст и запускает скрипты"""
    text = update.message.text.lower()
    result = None

    if 'привет' in text:
        result = 'Приветствую! Чем могу быть полезен?'

    elif 'как' in text and 'дел' in text:
        result = 'Всё отлично! Готов к работе и жду ваших команд!'

    elif 'молодец' in text:
        result = get_random_response('thanks')

    # Интернет и поиск
    elif 'найди в ютубе' in text:
        query = text.replace("найди в ютубе", "").strip()
        if query:
            if search_and_open_youtube(query):
                result = 'Вот что я нашёл'
            else:
                result = "Не удалось найти видео"
        else:
            result = "Уточните, что искать?"

    elif 'youtube' in text or 'ютуб' in text:
        webbrowser.open_new_tab('https://www.youtube.com/')
        result = get_random_response('open')

    elif 'найди' in text:
        query = text.replace("найди", "").strip()
        if query:
            webbrowser.open_new_tab(f'https://yandex.ru/search/?text={query}')
            result = get_random_response('search')
        else:
            result = "Что именно найти?"

    elif 'погод' in text:
        weather = get_text_with_url()
        result = f"Погода: {weather}"

    elif 'дипси' in text or 'deepseek' in text:
        webbrowser.open_new_tab('https://chat.deepseek.com/')
        result = "Открываю DeepSeek"

    elif 'переводчик' in text:
        webbrowser.open_new_tab('https://translate.yandex.ru/')
        result = get_random_response('open')
    
    elif 'bluetooth' in text or 'блютуз' in text:
        keyboard.send('win + a')
        time.sleep(0.2)
        keyboard.send('right')
        time.sleep(0.1)
        keyboard.send('enter')
        time.sleep(0.1)
        keyboard.send('win + a')
        result = "Переключаю Bluetooth"
        
    # Игры
    elif 'игр' in text:
        webbrowser.open_new_tab('https://yandex.ru/games/')
        result = "Открываю Яндекс Игры"

    elif 'камень ножницы бумага' in text:
        if start_file(r'games\stone_knots_paper.py'):
            result = "Запускаю игру"
        else:
            result = "Файл игры не найден"

    elif 'виселиц' in text:
        if start_file(r'games\hangman.py'):
            result = "Запускаю игру"
        else:
            result = "Файл игры не найден"

    elif 'викторин' in text:
        if start_file(r'games\quiz.py'):
            result = "Запускаю игру" 
        else:
            result = "Файл игры не найден"

    elif 'квест' in text:
        if start_file(r'games\quest.py'):
            result = "Запускаю игру"
        else:
            result = "Файл игры не найден"

    elif 'крестики-нолики' in text:
        if start_file(r'games\tictactoe.py'):
            result = "Запускаю игру"
        else:
            result = "Файл игры не найден"

    elif 'угадай число' in text:
        if start_file(r'games\rand_game.py'):
            result = "Запускаю игру"
        else:
            result = "Файл игры не найден"

    # Система
    elif 'ухож' in text or 'ушол' in text:
        webbrowser.open_new_tab('https://alice.yandex.ru?')
        time.sleep(2)
        keyboard.write('Выключи светильник')
        keyboard.send('Enter')
        os.system("shutdown /s /t 10")
        result = "Выключаю компьютер и свет, до свидания!"

    elif 'открой minecraft' in text:
        try:
            a = __file__.split('\\')
            b = fr'{a[0]}\\{a[1]}\\{a[2]}\\OneDrive\\Рабочий стол\\МАЕНКРАФТ.exe'
            os.startfile(b)
            result = get_random_response('open')
        except:
            result = "Не удалось открыть Minecraft"

    elif 'вниз' in text:
        mouse.wheel(-1)
        result = get_random_response('ok')

    elif 'верх' in text:
        mouse.wheel(1)
        result = get_random_response('ok')

    elif 'камер' in text:
        keyboard.send('win+2')
        result = get_random_response('open')

    elif 'селф' in text:
        keyboard.send('win+2')
        time.sleep(2)
        await update.message.reply_text('Улыбнитесь!')
        time.sleep(1.5)
        keyboard.send('space')
        result = None  # уже ответили

    elif 'сверн' in text:
        keyboard.send('Win + down')
        time.sleep(0.001)
        keyboard.send('Win + down')
        result = get_random_response('ok')

    elif 'закр' in text:
        keyboard.send('alt+F4')
        result = get_random_response('ok')

    elif 'открой проводник' in text:
        keyboard.send('win + e')
        result = get_random_response('ok')

    elif 'открой настройки' in text:
        keyboard.send('win + i')
        result = get_random_response('ok')

    # Медиа
    elif 'музык' in text:
        words = text.split()
        # Ищем слово "музык" или "музыку" и берём всё после него
        try:
            idx = next(i for i, w in enumerate(words) if 'музык' in w)
            query = ' '.join(words[idx+1:]).strip()
        except StopIteration:
            query = ''
        
        if query:
            try:
                b = '+'.join(query.split())
                webbrowser.open_new_tab(f'https://music.yandex.ru/search?text={b}')
                time.sleep(3)
                result = 'Включаю'
                time.sleep(1)
                mouse.move(259, 266)
                time.sleep(0.1)
                mouse.click('left')
            except:
                result = "Ошибка при открытии музыки"
        else:
            result = "Какую музыку найти?"

    elif 'вол' in text or 'избр' in text:
        try:
            webbrowser.open_new_tab('https://music.yandex.ru/playlists/lk.82335139-7584-4913-b6b7-7943bb94a098')
            time.sleep(3.5)
            mouse.move(446, 321)
            mouse.click('left')
            result = 'Включаю вашу волну'
        except:
            result = "Ошибка при открытии музыки"

    elif any(word in text for word in ['дальше', 'след']):
        time.sleep(0.5)
        keyboard.send('n')
        result = get_random_response('ok')

    elif any(word in text for word in ['стоп', 'пауз', 'заткн', 'продолж']):
        time.sleep(0.5)
        keyboard.send('k')
        result = get_random_response('ok')
        
    elif any(word in text for word in ['пред', 'прошл', 'назад']):
        time.sleep(0.5)
        keyboard.send('p')
        result = get_random_response('ok')

    elif 'лайк' in text or 'нравит' in text:
        time.sleep(0.5)
        keyboard.send('f')
        result = 'Ок, добавил в избранное!'

    elif any(word in text for word in ['дизлайк', 'не нравит']):
        time.sleep(0.5)
        keyboard.send('d')
        result = 'Ок, больше не буду включать такое'

    # Системная информация
    elif 'врем' in text:
        current_time = datetime.now().strftime("%H:%M")
        result = f"Сейчас {current_time}"

    elif 'дат' in text:
        current_date = datetime.now().strftime("%d.%m.%Y")
        result = f"Сегодня {current_date}"

    elif 'батар' in text:
        battery = psutil.sensors_battery()
        if battery:
            if battery.power_plugged:
                result = f"Батарея заряжается. Уровень: {battery.percent}%"
            else:
                if battery.secsleft == psutil.POWER_TIME_UNLIMITED:
                    result = f"Батарея не заряжается. Уровень: {battery.percent}%"
                elif battery.secsleft == -1:
                    result = f"Батарея разряжается. Уровень: {battery.percent}%. Оставшееся время неизвестно."
                else:
                    total_minutes = battery.secsleft // 60
                    hours = total_minutes // 60
                    minutes = total_minutes % 60
                    result = f"Батарея разряжается. Уровень: {battery.percent}%. Осталось примерно {hours} ч {minutes} мин."
        else:
            result = "Информация о батарее недоступна"

    elif 'выкл' in text and 'комп' in text:
        result = "Выключаю компьютер через 10 секунд"
        os.system("shutdown /s /t 10")

    # Учеба
    elif any(word in text for word in ['дз', 'домашн']):
        webbrowser.open_new_tab('https://school.mos.ru/diary/homeworks/')
        result = "Открываю домашнее задание"

    elif 'оценк' in text:
        webbrowser.open_new_tab('https://school.mos.ru/diary/marks/current-marks')
        result = "Показываю оценки"

    elif 'расписан' in text:
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_str = tomorrow.strftime("%d-%m-%Y")
        webbrowser.open_new_tab(f'https://school.mos.ru/diary/schedules/day/?date={tomorrow_str}')
        result = "Показываю расписание на завтра"
    
    # Специальные команды
    elif 'переведи на английский' in text:
        text_to_translate = text.replace("переведи на английский", "").strip()
        if text_to_translate:
            webbrowser.open_new_tab(f'https://translate.yandex.ru/?lang=ru-en&text={text_to_translate}')
            result = "Открываю переводчик"
        else:
            result = "Что перевести?"
    
    elif 'спящий' in text:
        keyboard.send('Win + d')
        time.sleep(1)
        keyboard.send('alt + F4')
        time.sleep(0.1)
        keyboard.send('up')
        time.sleep(0.1)
        keyboard.send('enter')
        result = "Перевожу компьютер в спящий режим"

    elif 'переведи на русский' in text:
        text_to_translate = text.replace("переведи на русский", "").strip()
        if text_to_translate:
            webbrowser.open_new_tab(f'https://translate.yandex.ru/?lang=en-ru&text={text_to_translate}')
            result = "Открываю переводчик"
        else:
            result = "Что перевести?"

    elif 'нарисуй' in text:
        query = text.replace("нарисуй", "").strip()
        if query:
            webbrowser.open_new_tab(f'https://yandex.ru/images/search?text={query}')
            result = "Ищу изображения..."
        else:
            result = "Что нарисовать?"

    elif 'полн' in text and 'экран' in text:
        keyboard.send("f")
        result = get_random_response('ok')

    elif 'включи свет' in text:
        webbrowser.open_new_tab('https://alice.yandex.ru?')
        time.sleep(2)
        keyboard.write('Включи светильник')
        keyboard.send('Enter')
        result = get_random_response('ok')

    elif 'выключи свет' in text:
        webbrowser.open_new_tab('https://alice.yandex.ru?')
        time.sleep(2)
        keyboard.write('Выключи светильник')
        keyboard.send('Enter')
        result = get_random_response('ok')

    elif 'браузер' in text:
        keyboard.send('WIN + 9')
        result = get_random_response('ok')

    elif 'заблок' in text and 'комп' in text:
        keyboard.send('Win + m')
        time.sleep(0.2)
        keyboard.send('alt + F4')
        time.sleep(0.1)
        for i in range(3): 
            keyboard.send('up')
        time.sleep(0.01)
        keyboard.send('enter')
        result = "Компьютер заблокирован"

    elif 'телефон' in text:
        keyboard.send('Win + 3')
        time.sleep(4)
        mouse.move(299, 180)
        time.sleep(0.1)
        mouse.click('left')
        time.sleep(0.1)
        mouse.move(350, 129)
        time.sleep(0.1)
        mouse.click('left')
        result = 'Уже звоню, ищите телефон'

    elif 'поставь таймер на' in text:
        w = text.replace("поставь таймер на", "").strip()
        w = w.replace("минуту", "").replace("минут", "").replace("ы", "").strip()
        if w and w.isdigit():
            if start_file(r'Media\timer.py'):  # исправлено start → start_file
                time.sleep(3)
                keyboard.write(w)
                keyboard.send('Enter')
                result = 'Таймер успешно запущен'
            else:
                result = "Файл таймера не найден"
        else:
            result = 'Уточните, на сколько поставить таймер'

    # Управление громкостью
    elif any(word in text for word in ['громче', 'увеличь громкость']):
        new_vol = change_volume('up')
        result = f'Громкость увеличена до {int(new_vol * 100)}%'

    elif any(word in text for word in ['тише', 'уменьши громкость']):
        new_vol = change_volume('down')
        result = f'Громкость уменьшена до {int(new_vol * 100)}%'
    
    elif 'перезагруз' in text:
        keyboard.send('Win + m')
        time.sleep(0.2)
        keyboard.send('alt + F4')
        time.sleep(0.1)
        keyboard.send('down')
        time.sleep(0.1)
        keyboard.send('enter')
        result = "Перезагружаю компьютер"

    elif 'громкость' in text:
        if 'макс' in text:
            set_system_volume(1)
            result = 'Громкость установлена на максимум'
        elif 'мин' in text:
            set_system_volume(0)
            result = 'Громкость установлена на минимум'
        else:
            try:
                vol_level = int(''.join(filter(str.isdigit, text)))
                vol_level = max(0, min(100, vol_level))
                if set_system_volume(vol_level / 100):
                    result = f'Установлена громкость {vol_level}%'
                else:
                    result = "Не удалось изменить громкость"
            except:
                result = 'Скажите, например, "поставь громкость 50"'

    # Открытие приложений
    elif 'открой' in text and not any(word in text for word in ['проводник', 'настройки', 'roblox', 'minecraft']):
        app = text.replace("открой", "").strip()
        if app:
            try:
                AppOpener.open(app, match_closest=True)
                result = f'Открываю {app}'
            except:
                result = f'Не удалось открыть {app}'
        else:
            result = 'Какое приложение открыть?'

    elif 'закрой' in text:
        app = text.replace("закрой", "").strip()
        if app:
            try:
                AppOpener.close(app, match_closest=True)
                result = f'Закрываю {app}'
            except:
                result = f'Не удалось закрыть {app}'
        else:
            result = 'Какое приложение закрыть?'

    else:
        # Если команда не распознана - передаем в Gigachat
        try:
            import gig 
            ans = gig.ask_gigachat(text)
            for i in '*%»`#$"': 
                ans = ans.replace(i, '')
            ans = ans.replace(r'\times', 'х')
            result = ans
        except ImportError:
            result = "Не понял команду. Модуль Gigachat не установлен."
        except Exception as e:
            result = "Не понял команду. Попробуйте другую."
            
    if result:
        await update.message.reply_text(result)

def main():
    try:
        print("🤖 Запуск бота Кеша...")
        
        # Создаем приложение
        application = Application.builder().token(TOKEN).build()
        
        # Регистрируем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("click_right", click_right))
        application.add_handler(CommandHandler("click_left", click_left))
        application.add_handler(CommandHandler("click_middle", click_middle))
        application.add_handler(CommandHandler("move_left", move_direction))
        application.add_handler(CommandHandler("move_right", move_direction))
        application.add_handler(CommandHandler("move_down", move_direction))
        application.add_handler(CommandHandler("move_up", move_direction))
        application.add_handler(CommandHandler("say", say_text))
        application.add_handler(CommandHandler("text_to_audio", convert_text_to_mp3))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        print("✅ Бот запущен и готов к работе!")
        print("⏳ Ожидаем сообщений...")
        
        # Запускаем бота
        application.run_polling()
        
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        print("\nПроверьте:")
        print("1. Интернет соединение")
        print("2. Токен бота (текущий: {})".format(TOKEN[:10] + "..." if TOKEN else "не указан"))
        print("3. Установлены ли зависимости: pip install python-telegram-bot requests")
        input("Нажмите Enter для выхода...")
        
if __name__ == "__main__":
    main()