from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
import tempfile
import os
import speech_recognition as sr
import pygame
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import requests
import numpy as np
import matplotlib.pyplot as plt
from tensorflow import keras
# from tensorflow.keras import layers

class manager():
    """Это класс помагатор для меня"""
    
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
    
    def get_weather(api="YOUR_OPENWEATHER_KEY", city="Москва"):
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
                "Температура": f"{round(temp)} °C",
                "Ощущается как": f"{round(feels_like)} °C",
                "Описание": description,
                "Влажность": f"{humidity} %",
                "Скорость ветра": f"{wind_speed} м/с"
            }
            return result

        except requests.exceptions.RequestException as e:
            return f"Ошибка запроса: {str(e)}"
        except Exception as e:
            return f"Произошла ошибка: {str(e)}"

    def open_file(name):
        """Открывает файл с помощью терминала"""
        os.system(f'start cmd /k python "{name}"')

    def search_file_path(file_path):
        """Помагает узнавать путь к файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(current_dir, file_path)
        return absolute_path
    
    def play_music(file_path):
        """Воспроизводит mp3 файлы"""
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            # Ждем пока музыка играет
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except Exception as e:
            print(f"Ошибка при воспроизведении: {e}")

    def listen_text(listen_seconds=5):
        """
        Слушает микрофон в течение указанного времени и возвращает распознанный текст.
        :param listen_seconds: количество секунд для прослушивания (по умолчанию 5)
        :return: распознанный текст или '' в случае ошибки
        """
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        try:
                with microphone as source:
                    recognizer.adjust_for_ambient_noise(source)  # Уменьшение шума
                    audio = recognizer.listen(source, timeout=listen_seconds, phrase_time_limit=listen_seconds)
                text = recognizer.recognize_google(audio, language="ru-RU")  # Для русского языка
                return text
        except AssertionError:
                print("Время ожидания истекло, речь не обнаружена.")
                return ''            
        except sr.WaitTimeoutError:
                print("Время ожидания истекло, речь не обнаружена.")
                return ''
        except sr.UnknownValueError:
                print("Речь не распознана.")
                return ''
        except Exception as e:
                print(f"Произошла ошибка: {e}")
                return ''
            
    def say(text, lang='ru'):
        """Озвучка текста с использованием gTTS и pydub"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as fp:
                temp_file = fp.name
            
            tts = gTTS(text=text, lang=lang)
            tts.save(temp_file)
            
            sound = AudioSegment.from_mp3(temp_file)
            play(sound)
            
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    


    # # Создание простой генеративной модели
    # def build_generator(latent_dim):
    #     model = keras.Sequential([
    #         layers.Dense(128, activation='relu', input_dim=latent_dim),
    #         layers.Dense(256, activation='relu'),
    #         layers.Dense(512, activation='relu'),
    #         layers.Dense(28*28, activation='sigmoid'),
    #         layers.Reshape((28, 28, 1))
    #     ])
    #     return model
    
    # # Генерация и сохранение изображений
    # def generate_and_save_images(generator, epoch, test_input):
    #     predictions = generator(test_input, training=False)
        
    #     fig = plt.figure(figsize=(4, 4))
    #     for i in range(predictions.shape[0]):
    #         plt.subplot(4, 4, i+1)
    #         plt.imshow(predictions[i, :, :, 0] * 255, cmap='gray')
    #         plt.axis('off')
        
    #     plt.savefig(f'image_at_epoch_{epoch:04d}.png')
    #     plt.close()