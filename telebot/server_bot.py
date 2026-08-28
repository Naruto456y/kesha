# Вот полный код для Replit сервера
from flask import Flask, request, jsonify
from datetime import datetime
import threading
import time

app = Flask(__name__)

# Хранилище команд для всех пользователей
user_commands = {}
user_info = {}

# Главная страница
@app.route('/')
def home():
    users_count = len(user_info)
    active_users = len([u for u in user_commands if user_commands.get(u)])
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 Сервер Кеша</title>
        <style>
            body {{ font-family: Arial; padding: 20px; }}
            .status {{ color: green; font-weight: bold; }}
            .box {{ background: #f0f0f0; padding: 15px; border-radius: 10px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <h1>🚀 Сервер управления "Кеша"</h1>
        
        <div class="box">
            <h3>📊 Статистика:</h3>
            <p>👥 Всего пользователей: <span class="status">{users_count}</span></p>
            <p>🟢 Активных сейчас: <span class="status">{active_users}</span></p>
            <p>🕒 Время сервера: {datetime.now().strftime("%H:%M:%S")}</p>
        </div>
        
        <div class="box">
            <h3>🔧 API эндпоинты:</h3>
            <ul>
                <li><code>/api/ping</code> - Проверка работы</li>
                <li><code>/api/send_command</code> - Отправить команду</li>
                <li><code>/api/get_commands/&lt;user_id&gt;</code> - Получить команды</li>
                <li><code>/api/register</code> - Регистрация</li>
            </ul>
        </div>
        
        <div class="box">
            <h3>📱 Для Telegram бота:</h3>
            <p>Используйте этот URL: <code>https://{request.host}</code></p>
        </div>
        
        <p>Сервер работает! ✅</p>
    </body>
    </html>
    '''

# Проверка работы сервера
@app.route('/api/ping')
def ping():
    return jsonify({
        "status": "online",
        "time": datetime.now().isoformat(),
        "users": len(user_info)
    })

# Регистрация нового пользователя
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    user_name = data.get('name', 'Аноним')
    
    # Генерируем ID
    import hashlib
    import random
    user_id = hashlib.md5(f"{user_name}{random.random()}".encode()).hexdigest()[:8]
    
    # Сохраняем информацию
    user_info[user_id] = {
        "name": user_name,
        "registered": datetime.now().isoformat(),
        "last_seen": datetime.now().isoformat()
    }
    user_commands[user_id] = []
    
    return jsonify({
        "success": True,
        "user_id": user_id,
        "message": f"Привет, {user_name}! Твой ID: {user_id}",
        "instructions": "Сохрани этот ID. Он понадобится для клиента."
    })

# Отправка команды от бота к серверу
@app.route('/api/send_command', methods=['POST'])
def send_command():
    try:
        data = request.json
        user_id = str(data.get('user_id'))
        command = data.get('command')
        
        if not user_id:
            return jsonify({"error": "Нет user_id"}), 400
        if not command:
            return jsonify({"error": "Нет команды"}), 400
        
        # Создаем очередь если пользователь новый
        if user_id not in user_commands:
            user_commands[user_id] = []
            user_info[user_id] = {
                "name": "Новый пользователь",
                "registered": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat()
            }
        
        # Добавляем команду в очередь
        user_commands[user_id].append({
            "command": command,
            "timestamp": datetime.now().isoformat(),
            "id": len(user_commands[user_id]) + 1
        })
        
        # Обновляем время последней активности
        if user_id in user_info:
            user_info[user_id]["last_seen"] = datetime.now().isoformat()
        
        # Ограничиваем очередь (макс 100 команд)
        if len(user_commands[user_id]) > 100:
            user_commands[user_id] = user_commands[user_id][-100:]
        
        return jsonify({
            "success": True,
            "message": "Команда отправлена",
            "queue_size": len(user_commands[user_id])
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Получение команд клиентом
@app.route('/api/get_commands/<user_id>')
def get_commands(user_id):
    user_id = str(user_id)
    
    if user_id in user_commands and user_commands[user_id]:
        # Возвращаем все команды
        commands = user_commands[user_id].copy()
        # Очищаем очередь
        user_commands[user_id] = []
        
        # Обновляем время последней активности
        if user_id in user_info:
            user_info[user_id]["last_seen"] = datetime.now().isoformat()
        
        return jsonify({
            "success": True,
            "commands": commands,
            "count": len(commands)
        })
    
    return jsonify({
        "success": True,
        "commands": [],
        "count": 0,
        "message": "Нет новых команд"
    })

# Получение информации о пользователе
@app.route('/api/user_info/<user_id>')
def get_user_info(user_id):
    user_id = str(user_id)
    
    if user_id in user_info:
        return jsonify({
            "success": True,
            "user": user_info[user_id]
        })
    
    return jsonify({
        "success": False,
        "error": "Пользователь не найден"
    }), 404

# Очистка старых данных (автоматическая)
def cleanup_old_data():
    """Удаляет неактивных пользователей (не были онлайн 24 часа)"""
    while True:
        time.sleep(3600)  # Каждый час
        try:
            now = datetime.now()
            to_delete = []
            
            for user_id, info in user_info.items():
                last_seen = datetime.fromisoformat(info["last_seen"])
                hours_diff = (now - last_seen).total_seconds() / 3600
                
                if hours_diff > 24:  # 24 часа
                    to_delete.append(user_id)
            
            for user_id in to_delete:
                user_info.pop(user_id, None)
                user_commands.pop(user_id, None)
                
            print(f"🧹 Очищено {len(to_delete)} неактивных пользователей")
            
        except Exception as e:
            print(f"Ошибка очистки: {e}")

# Запуск сервера
def run_server():
    # Запускаем очистку в отдельном потоке
    cleanup_thread = threading.Thread(target=cleanup_old_data, daemon=True)
    cleanup_thread.start()
    
    # Запускаем Flask
    app.run(host='0.0.0.0', port=8080)

# Для Replit - нужно запускать так
if __name__ == "__main__":
    print("🚀 Запуск сервера Кеша...")
    print("🌐 Сервер будет доступен по ссылке из Replit")
    run_server()