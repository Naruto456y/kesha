from gtts import gTTS
import speech_recognition as sr
import pygame
import os
import time
import random
import keyboard
import webbrowser
from datetime import datetime
import AppOpener
import threading
import queue
import psutil
import os
import time
import threading
import queue
import tempfile
import pygame
import speech_recognition as sr
from gtts import gTTS
import webbrowser
import keyboard
from datetime import datetime
import psutil
import AppOpener
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from youtube_search import YoutubeSearch
import mouse
from pydub import AudioSegment
from pydub.playback import play
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import gig

def get_text_with_url(url, class_name):
        """
        Функция для получения текста из элемента с указанным классом на веб-странице

        Args:
        url (str): URL-адрес страницы
        class_name (str): название класса элемента

        Returns:
        str: текст элемента или сообщение об ошибке
        """
        try:
            # Кодируем URL для обработки русских символов
            encoded_url = quote(url, safe=':/?&=')
            
            # Добавляем заголовки чтобы избежать блокировки
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        
            # Отправляем запрос
            response = requests.get(encoded_url, headers=headers, timeout=10)
            response.raise_for_status()  # Проверяем статус ответа

            # Парсим HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Ищем элемент по классу
            element = soup.find(class_=class_name)

            if element:
                return element.text.strip()
            else:
                return f"Элемент с классом '{class_name}' не найден"

        except requests.exceptions.RequestException as e:
            return f"Ошибка запроса: {e}"
        except Exception as e:
            return f"Произошла ошибка: {e}"

def start(name, game = False):
    """Открывает файл или паппку в этой папке"""
    path = __file__.replace('Kesha.py', name)
    os.startfile(path)

def search_and_open_youtube(query):
    """
    Ищет видео на YouTube по запросу и открывает первое найденное видео в браузере.
    
    :param query: Строка поискового запроса.
    :return: None (открывает ссылку в браузере).
    """
    # Получаем результаты поиска
    results = YoutubeSearch(query, max_results=1).to_dict()  # Берём только первый результат
    
    if not results:
        print("Ничего не найдено.")
        return
    
    # Формируем полную ссылку на видео
    video_url = f"https://youtube.com{results[0]['url_suffix']}"
    
    # Открываем ссылку в браузере
    webbrowser.open(video_url)
    print(f"Открываю видео: {results[0]['title']}")

# Инициализация аудио системы
pygame.mixer.init()
TEMP_DIR = tempfile.gettempdir()
command_queue = queue.Queue()

# Настройки голосового помощника
class Config:
    WAKE_WORDS = ['кеша', 'кеш', 'гоша', 'кэш','валера','чебурек']
    SENSITIVITY = 0.5
    ENERGY_THRESHOLD = 1000
    PAUSE_THRESHOLD = 2
    DYNAMIC_ENERGY = True
    TIMEOUT = 1.5
    PHRASE_LIMIT = 3

# Инициализация управления громкостью
try:
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume_control = cast(interface, POINTER(IAudioEndpointVolume))
    VOLUME_CONTROL_ENABLED = True
except:
    VOLUME_CONTROL_ENABLED = False
    print("Не удалось инициализировать управление громкостью")

class AudioManager:
    """Управление воспроизведением аудио"""
    def __init__(self):
        self._init_mixer()
        self.playback_thread = None

    def _init_mixer(self):
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        except:
            print("Ошибка инициализации аудио микшера")

    def say(self, text):
        """Асинхронное воспроизведение текста"""
        if not text.strip():
            return

        try:
            filename = os.path.join(TEMP_DIR, f"voice_{int(time.time()*1000)}.mp3")
            tts = gTTS(text=text, lang='ru', slow=False)
            tts.save(filename)

            if self.playback_thread and self.playback_thread.is_alive():
                pygame.mixer.music.stop()
                self.playback_thread.join(timeout=0.1)

            try:
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()
            except:
                self._init_mixer()
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()

            self.playback_thread = threading.Thread(
                target=self._cleanup_audio,
                args=(filename,),
                daemon=True
            )
            self.playback_thread.start()

        except Exception as e:
            print(f"Ошибка воспроизведения: {e}")

    def _cleanup_audio(self, filename):
        """Очистка аудиофайлов после воспроизведения"""
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        try:
            if os.path.exists(filename):
                os.remove(filename)
        except:
            pass

audio_manager = AudioManager()

class VoiceRecognizer:
    """Распознавание голосовых команд"""
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = Config.ENERGY_THRESHOLD
        self.recognizer.pause_threshold = Config.PAUSE_THRESHOLD
        self.recognizer.dynamic_energy_threshold = Config.DYNAMIC_ENERGY

    def listen(self, timeout=1.5):
        """Слушаем микрофон с таймаутом"""
        with sr.Microphone() as source:
            try:
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout,
                    phrase_time_limit=Config.PHRASE_LIMIT
                )
                return self.recognizer.recognize_google(audio, language='ru-RU').lower()
            except (sr.WaitTimeoutError, sr.UnknownValueError):
                return ""
            except Exception as e:
                print(f"Ошибка распознавания: {e}")
                return ""

def re(text):
    """Быстрый вывод и озвучивание текста"""
    print(text)
    audio_manager.say(text)

def listen_for_wake_word():
    """Прослушивание ключевого слова для активации"""
    recognizer = VoiceRecognizer()
    re("Готов к работе, жду ключевое слово...")
    print("кеша, кеш, гоша, кэш, валера, чебурек")
    while True:
        try:
            text = recognizer.listen(timeout=Config.TIMEOUT)
            if any(word in text for word in Config.WAKE_WORDS):
                command_queue.put("wake_word_detected")
        except Exception as e:
            print(f"Ошибка в listen_for_wake_word: {e}")
            time.sleep(0.1)

def recognize_command():
    """Распознавание команды после активации"""
    recognizer = VoiceRecognizer()
    re("Слушаю...")
    return recognizer.listen()

def process_commands():
    """Обработка команд из очереди"""
    while True:
        command = command_queue.get()
        if command == "wake_word_detected":
            command_text = recognize_command()
            if command_text:
                threading.Thread(
                    target=handle_command,
                    args=(command_text,),
                    daemon=True
                ).start()
            else:
                re("Я вас не расслышал, повторите пожалуйста")

def set_system_volume(level):
    """Установка громкости системы"""
    if not VOLUME_CONTROL_ENABLED:
        return False
    try:
        volume_control.SetMasterVolumeLevelScalar(level, None)
        return True
    except:
        return False

def get_system_volume():
    """Получение текущей громкости"""
    if not VOLUME_CONTROL_ENABLED:
        return 0.5
    try:
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

def handle_command(text):
    """Обработка конкретной команды"""
    if not text:
        return

    print(f"Распознанная команда: {text}")
    text = text.lower().strip()
    try:
        if any(word in text for word in ['пока', 'выход', 'стоп']):
            re('До свидания!')
            time.sleep(2)
            os._exit(0)

        elif 'найди в ютуби' in text:
            quertty = text.replace("найди в ютуби", "").strip()
            if quertty:
                search_and_open_youtube(quertty)
                re('Вот что я нашёл')
            else:
                re('Что именно вам найти?')

        elif 'открой roblox' in text:
            os.startfile(r'C:\Users\Yusuf\AppData\Local\Roblox\Versions\version-fe20d41d8fec4770\RobloxPlayerBeta')
            re('Открываю')

        elif 'открой minecraft' in text:
            os.startfile(r'C:\Users\Yusuf\OneDrive\Рабочий стол\MINECRAFT')
            re('Открываю')
            
        elif 'переведи на' in text:
                if 'английский' in text:
                    m = text.replace("переведи на английский", "").strip()
                    while True:
                        try:
                            webbrowser.open(f'https://translate.yandex.ru/?from=tableau_yabro&source_lang=ru&target_lang=en&text={m}')
                            time.sleep(2)
                            for i in range(13):
                                time.sleep(0.0000001)
                                keyboard.send('Tab')
                            re(f'{m} на английском')
                            time.sleep(2)
                            keyboard.send('alt+ctrl+V')
                            break
                        except:
                            keyboard.send('alt+Shift')
                            keyboard.send('alt+ctrl+V')
                            break

                elif 'русский' in text:
                    m = text.replace("переведи на русский", "").strip()
                    while True:
                        try:
                            webbrowser.open(f'https://translate.yandex.ru/?from=tableau_yabro&source_lang=en&target_lang=ru&text={m}')
                            time.sleep(2)
                            for i in range(13):
                                time.sleep(0.0000001)
                                keyboard.send('Tab')
                            re(f'{m} на русском')
                            time.sleep(2)
                            keyboard.send('alt+ctrl+V')
                            break
                        except:
                            keyboard.send('alt+Shift')
                            keyboard.send('alt+ctrl+V')
                            break

        elif 'youtube' in text:
            webbrowser.open('https://www.youtube.com/')
            re('Открываю YouTube')
        
        elif 'камень ножницы бумага' in text:
            re('Запускаю игру камень ножницы бумага\n')
            start('stone_knots_paper.py')

        elif 'виселиц' in text:
            re('Запускаю игру виселица\n')
            start('hangman.py')

        elif 'викторин' in text:
            re('Запускаю игру викторина\n')
            start('quiz.py')

        elif 'вниз' in text:
            mouse.wheel(-1)

        elif 'верх' in text:
            mouse.wheel(1)

        elif 'квест' in text:
            re('Запускаю игру квест\n')
            start('quest.py')

        elif 'крестики-нолики' in text:
            re('Запускаю игру крестики нолики\n')
            start('tictactoe.py')

        elif 'угадай число' in text:
            re('Запускаю игру угадай число\n')
            start('rand_game.py')

        elif any(word in text for word in ['дипси', 'deep', 'deepseek']):
            re('Открываю нейросеть дипсик')
            webbrowser.open('https://chat.deepseek.com/a/chat/s/5e62a9fe-9717-452d-9a82-89c2ca2dd30b')

        elif 'переводчик' in text:
            re('Открываю переводчик')
            webbrowser.open('https://translate.yandex.ru/?111=')

        elif 'игры' in text:
            re('Открываю яндекс игры')
            webbrowser.open('https://yandex.ru/games/')

        elif 'как дела' in text:
           re('Всё отлично!Будет ещё лучше если я смогу вам помочь')

        elif 'молодец' in text:
            re('Спасибо!Всегда к вашим услугам')

        elif 'привет' in text:
            re('Привет! Чем могу помочь?')

        elif 'найди' in text:
            querty = text.replace("найди", "").strip()
            if querty:
                webbrowser.open_new_tab(f'https://yandex.ru/search/?text={querty}')
                re(f'Ищу {querty}')
            else:
                re('Что именно вам найти?')

        elif 'погод' in text:
            a = get_text_with_url('https://rp5.ru/Погода_в_Сосенках,_Москва','t_0')
            re(a)
            
        elif 'fire kill' in text:
            start(r'game\FireKill.py')
            re('Запускаю')
            
        elif 'отстань' in text:
            start(r'game\FireKill.py')
            re('Запускаю')
            
        elif 'открой настройки' in text:
            keyboard.send('Win + I')
            re('Есть')

        # Для тех у кого умный дом

        elif 'включи свет' in text:
            webbrowser.open('https://alice.yandex.ru?')
            time.sleep(2)
            keyboard.write('Включи светильник')
            keyboard.send('Enter')
            re('Ок')
        
        elif 'выключи свет' in text:
            webbrowser.open('https://alice.yandex.ru?')
            time.sleep(2)
            keyboard.write('Выключи свет')
            keyboard.send('Enter')
            re('Ок')

        elif 'поставь таймер на' in text:
            w = text.replace("поставь таймер на", "").strip()
            w = w.replace("минуту", "").strip()
            w = w.replace("минут", "").strip()
            w = w.replace("ы", "").strip()
            if w:
                start('timer.py')
                time.sleep(3)
                keyboard.write(w)
                keyboard.send('Enter') 
                re('Таймер успешно запущен') 
            else:
                re('Уточните на сколько поставить таймер')

        elif 'музыка' in text:
            q = text.replace("музыка", "").strip()
            if q:
                AppOpener.open('Yandex',True)
                webbrowser.open(f'https://rus.hitmotop.com/search?q={q}')
                time.sleep(1)
                keyboard.send('Tab')
                keyboard.send('space')
                re('Послушайте, что я нашёл')
                time.sleep(2)
                mouse.move(252, 794)
                mouse.click('left')
            else:
                AppOpener.open('Yandex',True)
                webbrowser.open('https://rus.hitmotop.com')
                re('Открываю')

        elif 'открой проводник' in text:
            keyboard.send('Win + E')
            re('Есть')

        elif 'дальше' in text:
            keyboard.send('shift + N')
            re('Есть')

        elif 'пробел' in text:
            keyboard.send('space')
            re('Есть')

        elif 'полный экран' in text:
            keyboard.send('F')
            re('Есть')

        elif 'время' in text:
            current_time = datetime.now().strftime("%H:%M")
            re(f'Сейчас {current_time}')

        elif 'времени' in text:
            current_time = datetime.now().strftime("%H:%M")
            re(f'Сейчас {current_time}')    

        elif 'состояние' in text or 'батарея' in text:
            battery = psutil.sensors_battery()
            if battery.power_plugged:
                status = "заряжается"
            else:
                status = "работает от батареи"
            re(f'Батарея {status}, уровень заряда {battery.percent}%')

        elif any(word in text for word in ['громче', 'увеличь громкость']):
            new_vol = change_volume('up')
            re(f'Громкость увеличена до {int(new_vol * 100)}%')

        elif any(word in text for word in ['тише', 'уменьши громкость']):
            new_vol = change_volume('down')
            re(f'Громкость уменьшена до {int(new_vol * 100)}%')

        elif 'громкость' in text:
            try:
                vol_level = int(''.join(filter(str.isdigit, text)))
                vol_level = max(0, min(100, vol_level))
                if set_system_volume(vol_level / 100):
                    re(f'Установлена громкость {vol_level}%')
            except:
                re('Скажите, например, "поставь громкость 50"')

        elif 'открой' in text:
            app = text.replace("открой", "").strip()
            if app:
                try:
                    AppOpener.open(app,match_closest=True)
                    re(f'Открываю {app}')
                except:
                    re(f'Не удалось открыть {app}')
            else:
                re('Какое приложение открыть?')

        elif 'закрой' in text:
            app = text.replace("закрой", "").strip()
            if app:
                try:
                    AppOpener.close(app,match_closest=True)
                    re(f'Закрываю {app}')
                except:
                    re(f'Не удалось закрыть {app}')
            else:
                re('Какое приложение закрыть?')

        elif 'выключи компьютер' in text:
            re('Выключаю компьютер через 10 секунд')
            os.system("shutdown /s /t 10")

        else:
            ans = gig.ask_gigachat(text)
            for i in ['*%»`#$"']:
                ans = ans.replace(i, '')
            re(ans)

    except Exception as e:
        re('Произошла ошибка при обработке команды')
        print(f"Ошибка: {e}")

def main():
    """Основная функция"""
    print("\033[1;32m" + ' 🚀 Голосовой помощник активирован 🚀' + "\033[0m")
    print("Для выхода скажите кеша пока/стоп/выход")
    print("Доступные команды:")

    print("- Привет/Молодец/Как дела")
    print("- Мызыка/Музыка [название]")
    print("- Поставь таймер на [минут]")
    print("- Включи свет/Выключи свет (Для тех у кого есть умный дом алисой)")
    print("- Переведи на английский [слово]")
    print("- Дальше/Пауза")
    print("- Найди в ютубе [запрос]")
    print("- Найди [запрос]")
    print("- Открой/Закрой [приложение] (иногда не работает)-")
    print("- Погода")
    print("- Переводчик")
    print("- Время")
    print("- Состояние батареи")
    print("- Громче/Тише")
    print("- Громкость [громкость от 1 до 100]")
    print("- Выключи компьютер")

    print("Доступные игры:")

    print("Что бы начать игру скажите Кеше название игры")

    print("- Игры - Открывает яндекс игры")
    print("- FIreKill (Поиграйте очень интересно =) - ")
    print("- Виселица - ")
    print("- Крестики-Нолики - ")
    print("- Угадай число - ")
    print("- Квест - ")
    print("- Викторина - ")
    print("- Камень ножницы бумага - ")
    print("- Угадай число - ")

    # Запуск потоков
    threading.Thread(target=listen_for_wake_word, daemon=True).start()
    threading.Thread(target=process_commands, daemon=True).start()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        re("Выключаюсь")
        os._exit(0)

if __name__ == "__main__":
    main()
