<img width="500" height="500" alt="Kesha_icoc" src="https://github.com/user-attachments/assets/e110113b-f61f-4fb3-8fdc-2afe5ac8a3c0" />

# 🤖 Голосовой помощник Кеша

**Кеша** — многоканальный голосовой ассистент для Windows на Python. Одно общее ядро команд обслуживает сразу пять интерфейсов: **голос**, **десктопное окно**, **Telegram-бот**, **веб-сайт** и **навык Яндекс Алисы**. Если команда не распознана, вопрос уходит в **GigaChat**.

---

## 🧭 Как это устроено

```text
 Микрофон ─► Wake word ─► VAD ─► GigaAM (STT) ─┐
 Desktop (PyQt6 + WebEngine) ───────────────────┤
 Telegram-бот ──────────────────────────────────┼─► core.handle_command ─► commands.py ─► ответ
 Веб-сайт (FastAPI + WebSocket) ────────────────┤        │ (реестр команд)       │
 Навык Алисы (Flask) ───────────────────────────┘        └─ не нашлось ─► GigaChat
                                                                                  ▼
                                                                  gTTS ─► озвучка (pygame)
```

- [core.py](core.py) — реестр команд (`@registry.command`), `handle_command`, шина событий, AI-fallback.
- [commands.py](commands.py) — все команды, сгруппированные по категориям.
- [config.py](config.py) — пути, приложения, wake-words, порты, фразы.
- [state_manager.py](state_manager.py) — состояние ассистента (слушает / думает / говорит) для UI.
- [voice/](voice/) — цикл `wake word → VAD → GigaAM → команда → TTS`.
- [desktop/](desktop/), [website/](website/), [telegram_bot/](telegram_bot/), [alice_skill/](alice_skill/) — интерфейсы.
- [kesha_compil/](kesha_compil/) — лаунчер и сборка в `Kesha.exe` (PyInstaller).
- [tests/](tests/), [tests_wave1/](tests_wave1/) — тесты команд, ядра, голоса, GigaAM, VAD, Porcupine.

---

## 🚀 Возможности

- 🎤 **Голос** — активация словом, VAD-запись, офлайн-распознавание **GigaAM v3** (через `onnx-asr`, без PyTorch). Wake-word через **Porcupine**; если не настроен — слово-активатор ищется самим GigaAM.
- 🔊 **Озвучка** — `gTTS` + `pygame`.
- 🖥️ **Управление ПК** — запуск/закрытие приложений по ярлыкам, громкость, мышь, клавиатура, скриншоты, блокировка, выключение, перезагрузка, сон.
- 🌐 **Интернет** — поиск (Яндекс), YouTube, погода, переводчик.
- 🎵 **Музыка** — Яндекс Музыка: поиск, «моя волна», пауза, переключение, лайки.
- 🎮 **Игры** — камень-ножницы-бумага, виселица, викторина, квест, крестики-нолики, угадай число (в [Media/](Media/)).
- 📚 **Учёба** — МЭШ: ДЗ, оценки, расписание.
- 🧠 **GigaChat** — ответы на всё, что не является командой.
- 📱 **Удалённое управление** — через Telegram, веб-страницу с паролем и Алису.

---

## 📦 Требования

- Windows 10/11 (используются `pycaw`, ярлыки `.lnk`, `ctypes.windll`)
- Python **3.10+** (разрабатывалось на 3.13)
- Микрофон и динамики

---

## ⚙️ Установка

```bash
git clone https://github.com/Naruto456y/kesha.git
cd kesha
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Модель GigaAM скачивается в `models/gigaam/` — можно заранее: `python tests_wave1/download_gigaam.py`.
Для сборки `Kesha.exe`: `pip install -r requirements-dev.txt`.

### Секреты

Скопируйте [.env.example](.env.example) в `.env` (он в `.gitignore`) и заполните:

| Переменная | Для чего |
|---|---|
| `TELEGRAM_TOKEN` | Telegram-бот (токен от @BotFather) |
| `WEB_PASSWORD` | пароль веб-интерфейса |
| `TELEGRAM_ALLOWED_IDS` | числовые id пользователей Telegram через запятую. **Пусто = бот никому не отвечает.** Напишите боту — он ответит «Ваш id: …» |
| `ALICE_ALLOWED_IDS` | id пользователя/устройства Алисы. Пусто = навык отключён; запрещённый id печатается в консоли: `[alice] отказано, ids=[...]` |
| `WEATHER_API_KEY` | погода (OpenWeatherMap) |
| `GIGACHAT_CLIENT_ID`, `GIGACHAT_CLIENT_SECRET` | ответы GigaChat |
| `YANDEX_MUSIC_TOKEN` | Яндекс Музыка |
| `PICOVOICE_ACCESS_KEY` | wake-word Porcupine (необязательно) |
| `SMART_HOME_TOKEN`, `ADMIN_PASSWORD`, `ALLOWED_IPS`, `ROBOT_MAC`, `ROBOT_UUID` | умный дом и робот (необязательно) |

[config.py](config.py) читает значения из `.env` через `os.getenv`, в коде секретов нет.

### Безопасность

Кеша умеет выключать ПК, нажимать клавиши и снимать экран, поэтому доступ закрыт по умолчанию:
- **Telegram и Алиса** — только пользователи из белых списков выше.
- **Веб** — пароль в заголовке, затем кука сессии для картинок и трансляции (пароль в URL больше не передаётся); скриншоты и загрузки отдаются только после входа; `/ws` тоже закрыт.
- Загрузка файлов: только безопасное имя, лимит 50 МБ.
- Не выставляйте порт 8000 в интернет без HTTPS-прокси (кука без `Secure`).

### Настройка под себя

В [config.py](config.py) поправьте:
- `APP_PATHS` — пути к вашим ярлыкам (сейчас указаны `C:\Users\Yusuf\Desktop\...`);
- `WAKE_WORDS`, `WEATHER_CITY`, порты `WEB_PORT` (8000) и `ALICE_PORT` (5656).

---

## ▶️ Запуск

```bash
python main.py              # всё сразу: голос + Telegram + Алиса + сайт + окно
python main.py --voice      # только голос
python main.py --desktop    # только окно
python main.py --telegram   # только Telegram-бот
python main.py --web        # только сайт (http://localhost:8000)
python main.py --alice      # только навык Алисы
```

Флаги можно комбинировать. Без флагов (или с `--all`) стартуют все интерфейсы. Для Алисы нужен публичный адрес (например, ngrok — см. [alice_skill/ngrok.txt](alice_skill/ngrok.txt)).

Готовая сборка: [kesha_compil/Kesha.exe](kesha_compil/Kesha.exe) (спека — `Kesha.spec`).

---

## 🎮 Использование

Скажите слово-активатор из `WAKE_WORDS` (*«Кеша»*, *«Гоша»*, *«Чебурек»*…) и команду, например *«Кеша, открой браузер»*. Ответ придёт голосом и в интерфейсе. Списки фраз — в декораторах [commands.py](commands.py); у каждой команды несколько синонимов.

| Категория | Примеры |
|---|---|
| Общение | `привет`, `как дела`, `спасибо`, `пока` |
| Время и система | `время`, `дата`, `батарея`, `выключи компьютер`, `перезагрузка`, `спящий режим`, `заблокируй компьютер`, `сверни окно`, `закрой окно` |
| Приложения | `открой <название>`, `закрой <название>`, `открой проводник/настройки/вс код` |
| Звук | `громче`, `тише`, `громкость 40` |
| Мышь и клавиатура | `левый клик`, `правый клик`, `мышь вверх/вниз/влево/вправо`, `скролл вниз/вверх`, `напечатай …`, `нажми …` |
| Интернет | `найди …`, `найди в ютуби …`, `погода`, `переводчик`, `дипси` |
| Музыка | `музыка …`, `моя волна`, `пауза`, `дальше`, `предыдущий`, `лайк`, `дизлайк` |
| Экран и камера | `скриншот`, `камера`, `селфи` |
| Учёба | `дз`, `оценки`, `расписание` |
| Игры | `камень ножницы бумага`, `виселица`, `викторина`, `квест`, `крестики-нолики`, `угадай число` |

### Добавить свою команду

В [commands.py](commands.py):

```python
from core import registry

@registry.command(["привет мир", "хелло"], "Описание команды", "Общее", priority=0)
def hello(text):
    return "Привет, мир!"
```

Команды с большим `priority` проверяются раньше. Функция возвращает строку — её произнесут и покажут.

---

## 🧪 Тесты

```bash
python -m pytest tests
```

Тесты ядра и команд — в [tests/](tests/). В [tests_wave1/](tests_wave1/) — ручные проверки компонентов голоса (GigaAM, VAD, Porcupine): `python tests_wave1/test_vad.py` и т.п.

---

## 🗂️ Структура

```text
kesha/
├── main.py            # точка входа и CLI-флаги
├── core.py            # реестр команд, handle_command, AI-fallback
├── commands.py        # все команды
├── config.py          # настройки
├── state_manager.py
├── voice/             # wake_word, vad_recorder, gigaam_recognizer, speaker, listener
├── desktop/           # PyQt6-окно + HTML/JS интерфейс
├── website/           # FastAPI-сервер, auth, WebSocket, фронтенд
├── telegram_bot/
├── alice_skill/
├── Media/             # игры, иконки, звук будильника
├── kesha_compil/      # лаунчер и сборка exe
├── tests/  tests_wave1/
└── backups/           # старые копии (можно не коммитить)
```

---

## 🔮 Планы

- Свой wake-word «Кеша» вместо `computer` в Porcupine
- Макросы (запись и воспроизведение)
- Больше устройств умного дома, не только свет

---

## 📄 Лицензия

MIT — см. [LICENSE](LICENSE).

**Автор:** Юсуф Гусейнов ([GitHub](https://github.com/Naruto456y))

*Вопросы и идеи — через Issue или Pull Request.* 😊
