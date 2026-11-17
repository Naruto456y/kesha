# Отчёт: запуск Кеши на новом ПК (17.11.2026)

Кешу запускали на ноутбуке HP: Windows 11, Python 3.11, VS Code, PowerShell. Проект скачан zip-архивом с GitHub в `C:\Users\student\Desktop\kesha-main`.

Исправления — в PR [#1](https://github.com/Naruto456y/kesha/pull/1), ветка `ccr-7a50a091-vdjch1`.

## Коротко

| # | Проблема | Причина | Статус |
|---|----------|---------|--------|
| 1 | `pip install -r requirements.txt` падает на `help_manager` | Пакета `help_manager` нет на PyPI, модуль ставится пакетом `pycraft-tools` | ✅ исправлено в `requirements.txt` |
| 2 | Не хватает `pywinauto` | Его импортирует `features/phone.py` («найди телефон»), но в зависимостях его не было | ✅ добавлен в `requirements.txt` |
| 3 | `GigaChat недоступен: Could not find module ...\libvlc.dll` | `help_manager` при загрузке делает `import vlc`, а VLC на ПК не установлен | ✅ исправлено: заглушка `hm_compat.py` |
| 4 | Трейсбек `telegram.error.InvalidToken` | Нет файла `.env`, поэтому `TELEGRAM_TOKEN` пустой | ✅ трейсбек убран; ⚠️ `.env` нужно скопировать вручную |
| 5 | `[gigaam] ... ConnectTimeout [WinError 10060]` | Модель GigaAM качается с huggingface.co, а школьная сеть его не пропускает | ⚠️ нужно сделать на ПК (см. ниже) |
| 6 | `[tts] Silero недоступна: нет модели` | Нет файла `models\silero_v5_6_ru.pt` (не хранится в git) | ℹ️ необязательно, голос идёт через gTTS |
| 7 | `[ngrok] не установлен` | ngrok не установлен | ℹ️ нужен только для навыка Алисы из интернета |
| 8 | `TELEGRAM_ALLOWED_IDS пуст` | Нет `.env` | ⚠️ решится вместе с пунктом 4 |

**Что работает:** запуск `main.py`, голосовой модуль (с распознавателем Google вместо GigaAM), веб-интерфейс на `:8000`, навык Алисы на `127.0.0.1:5656`, pygame и викторина «Общие знания».

## Подробно

### 1. `help_manager` → `pycraft-tools`
Ошибка pip: `No matching distribution found for help_manager`. Пакета `help_manager` нет на PyPI. Внутри `pycraft-tools 1.4.0` есть файл `help_manager.py` с классами `Manager`, `GigaChat` и `ScreenReader`: именно их импортируют `core.py`, `commands.py` и `features/yamusic.py`. В `requirements.txt` строка `help_manager` заменена на `pycraft-tools`.

Весь набор зависимостей проверен через `uv pip compile --python-platform x86_64-pc-windows-msvc --python-version 3.11`: конфликтов нет, у всех пакетов есть сборки под Windows. Из исходников ставятся только `pyautogui`, `pyscreeze`, `pygetwindow`, `pyrect`, `pytweening` и `mouseinfo`. Это чистый Python, компилятор для них не нужен.

Установка тяжёлая, несколько ГБ: `pycraft-tools` тянет `easyocr`, `deepface` и OpenCV, а с ними `torch`, `torchvision` и `onnxruntime`.

### 2. `pywinauto`
`features/phone.py` → `from pywinauto import Desktop`. Без этого пакета команда «найди телефон» падала с `ModuleNotFoundError`. Пакет добавлен в `requirements.txt`.

### 3. VLC и GigaChat
В `help_manager.py` (строка 4714) на уровне модуля стоит `import vlc`. python-vlc ищет `libvlc.dll`, не находит и бросает `FileNotFoundError`. Из-за этого не загружается весь `help_manager`, и GigaChat отключается в `core.py` и `commands.py`.

VLC нужен только классу `Music` (плеер Яндекс.Музыки). Новый модуль `hm_compat.py` пробует `import vlc`; если не получилось, подставляет пустой модуль `vlc` и пишет предупреждение. Он импортируется перед каждым `from help_manager import ...`. Итог: GigaChat работает, отключается только плеер `Music`. Если нужен и плеер, поставь [VLC 64-bit](https://www.videolan.org/).

Проверка: фейковый `vlc`, который бросает `FileNotFoundError`, после чего `import hm_compat; from help_manager import GigaChat` проходит.

### 4. Telegram без токена
`telegram_bot/bot.py`: если `TELEGRAM_TOKEN` пустой, теперь пишется предупреждение «TELEGRAM_TOKEN пуст — Telegram-бот не запущен…» и бот не стартует. Раньше в потоке `telegram` вылетал трейсбек `InvalidToken`.

Чтобы бот и GigaChat заработали, скопируй с основного ПК файл **`.env`** в `kesha-main`, рядом с `main.py`. В нём лежат `TELEGRAM_TOKEN`, `TELEGRAM_ALLOWED_IDS`, `GIGACHAT_CLIENT_ID` и `GIGACHAT_CLIENT_SECRET`. Шаблон — `.env.example`.

### 5. GigaAM не скачивается
`voice/gigaam_recognizer.py` загружает модель через `onnx_asr.load_model(...)` с Hugging Face. Обе попытки (`int8` и обычная) закончились `ConnectTimeout [WinError 10060]`. Кеша сама переключилась на распознаватель Google.

Варианты:
- зеркало: `$env:HF_ENDPOINT="https://hf-mirror.com"` перед `python main.py`;
- скопировать кэш моделей с домашнего ПК: `C:\Users\<имя>\.cache\huggingface\hub` → `C:\Users\student\.cache\huggingface\hub`.

### 6–8. Не мешает работе
- **Silero**: без `models\silero_v5_6_ru.pt` голос идёт через gTTS. Файл можно скопировать с основного ПК.
- **ngrok**: нужен только для доступа к навыку Алисы из интернета.
- **Flask** `WARNING: This is a development server`: обычное сообщение, на работу не влияет.

## Что сделать на ноутбуке
1. Скачать свежий код: zip ветки `ccr-7a50a091-vdjch1` или `main` после слияния PR.
2. `pip install -r requirements.txt`.
3. Скопировать `.env` с основного ПК.
4. По желанию: VLC 64-bit, модель Silero, зеркало или кэш для GigaAM.
5. `python main.py`.

Проверено: подбор версий зависимостей под Windows и заглушка VLC. `pytest` здесь не запускался: в облачной среде нет зависимостей проекта, и тесты не собираются ни до правок, ни после. После установки на ноуте стоит прогнать `pytest`.

---

## Расшифровка логов

Расшифровано с фотографий экрана. Строки, обрезанные краем экрана или кадра, помечены `[…]`. Фрагменты идут в порядке появления в терминале. Переносы строк, которые сделал терминал, убраны.

### Лог 1. Установка зависимостей
```
pip 22.3 from C:\Users\student\AppData\Local\Programs\Python\Python311\Lib\site-packages\pip (python 3.11)
PS C:\Users\student\Desktop\kesha-main> pip install -r requirements.txt
Collecting requests
  Downloading requests-2.34.2-py3-none-any.whl (73 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 73.1/73.1 kB 1.4 MB/s eta 0:00:00
Collecting python-dotenv
  Downloading python_dotenv-1.2.4-py3-none-any.whl (23 kB)
ERROR: Could not find a version that satisfies the requirement help_manager (from versions: none)
ERROR: No matching distribution found for help_manager

[notice] A new release of pip available: 22.3 -> 26.3
```

### Лог 2. Запуск `python main.py`
```
[main] Завершение, убиваю дочерние процессы...
[main]   → terminate QtWebEngineProcess.exe (pid=14224)
[main]   → terminate python.exe (pid=16852)
[main] Всё завершено.
PS C:\Users\student\Desktop\kesha-main> python main.py
[core] GigaChat недоступен: Could not find module 'C:\Users\student\Desktop\kesha-main\libvlc.dll' (or one of its dependencies). Try using the full path with constructor syntax.
[commands] GigaChat недоступен: Could not find module 'C:\Users\student\Desktop\kesha-main\libvlc.dll' (or one of its dependencies). Try using the full path with constructor syntax.
[main] Запущено: voice
[main] Запущено: telegram
[main] Запущено: alice
[main] Запущено: web
[alice] http://127.0.0.1:5656/alice
[alice] ngrok http 5656
 * Serving Flask app 'alice_skill.alice'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5656
Press CTRL+C to quit
pygame 2.6.1 (SDL 2.28.4, Python 3.11.0)
Hello from the pygame community. https://www.pygame.org/contribute.html
[ngrok] не установлен — https://ngrok.com/download
2026-11-17 11:10:51,587 [WARNING] TELEGRAM_ALLOWED_IDS пуст — бот никому не отвечает. Напишите боту, он покажет ваш id, и впишите его в .env
2026-11-17 11:10:51,588 [INFO] Запуск Telegram-бота Кеша...
[web] http://0.0.0.0:8000
Exception in thread telegram:
Traceback (most recent call last):
  File "C:\Users\student\AppData\Local\Programs\Python\Python311\Lib\threading.py", line 1038, in _bootstrap_inner
    self.run()
  File "C:\Users\student\AppData\Local\Programs\Python\Python311\Lib\threading.py", line 975, in run
    self._target(*self._args, **self._kwargs)
  File "C:\Users\student\Desktop\kesha-main\main.py", line 93, in run_telegram
    start_bot()
  File "C:\Users\student\Desktop\kesha-main\telegram_bot\bot.py", line 107, in start_bot
    app = Application.builder().token(TELEGRAM_TOKEN).build()
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\student\AppData\Local\Programs\Python\Python311\Lib\site-packages\telegram\ext\_applicationbuilder.py", line 309, in build
    bot: Bot = self._build_ext_bot()  # build a bot
               ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\student\AppData\Local\Programs\Python\Python311\Lib\site-packages\telegram\ext\_applicationbuilder.py", line 271, in _build_ext_bot
    return ExtBot(
           ^^^^^^^
  […]
  File "C:\Users\student\AppData\Local\Programs\Python\Python311\Lib\site-packages\telegram\ext\_extbot.py", line 252, in __init__
    super().__init__(
  File "C:\Users\student\AppData\Local\Programs\Python\Python311\Lib\site-packages\telegram\_bot.py", line 337, in __init__
    raise InvalidToken("You must pass the token you received from https://t.me/Botfather!")
telegram.error.InvalidToken: You must pass the token you received from https://t.me/Botfather!
INFO:     Started server process [3412]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
[tts] Silero недоступна: нет модели Silero: C:\Users\student\Desktop\kesha-main\models\silero_v5_6_ru.pt
[gigaam] загрузка {'quantization': 'int8'} не удалась: Got: ConnectTimeout: [WinError 10060] Попытка установить соединение была безуспешной, т.к. от другого компьютера за требуемое время не получен нужный отклик, или было разорвано уже установленное соединение из-за неверного отклика уже подключенного компьютера
An error happened while trying to locate the files on the Hub and we cannot find the appropriate snapshot folder for the specified revision on the local disk. Please check your internet connection and try again.
[gigaam] загрузка {} не удалась: Got: ConnectTimeout: [WinError 10060] Попытка установить соединение была безуспешной, т.к. от другого компьютера за требуемое время не получен нужный отклик, или было разорвано уже установленное соединение из-за неверного отклика уже подключенного компьютера
An error happened while trying to locate the files on the Hub and we cannot find the appropriate snapshot folder for the specified revision on the local disk. Please check your internet connection and try again.
[voice] новый стек недоступен (GigaAM не загрузился: Got: ConnectTimeout: [WinError 10060] Попытка установить соединение была безуспешной, т.к. от другого компьютера за требуемое время не получен нужный отклик, или было разорвано уже установленное соединение из-за неверного отклика уже подключенного компьютера
An error happened while trying to locate the files on the Hub and we cannot find the appropriate snapshot folder for the specified revision on the local disk. Please check your internet connection and try again.), запускаю старый Google-распознаватель
```

Примечание: на одном из фото этот же блок GigaAM виден с наложением строк. Так терминал перерисовывается при изменении ширины окна, это не ошибка программы.

### Лог 3. Викторина (работает)
```
Ответьте на 20 вопросов по категории "Общие знания"
У вас 2 минуты

Вопрос №1. Как называется самая большая пустыня в мире?
1. Гоби
2. Сахара
3. Антарктическая
4. Аравийская
Введите номер вашего ответа (1-4): 3
✅ Правильно! +1 балл

Вопрос №2. Сколько цветов в радуге согласно традиционному делению?
1. 5
2. 7
3. 6
4. 8
Введите номер вашего ответа (1-4): 2
✅ Правильно! +1 балл

Вопрос №3. Какой химический элемент обозначается как 'Hg'?
1. Золото
2. Ртуть
3. Германий
4. Серебро
```
На фото текст викторины тоже частично наложен из-за перерисовки терминала. Варианты ответов к вопросу №1 восстановлены по видимым фрагментам.
