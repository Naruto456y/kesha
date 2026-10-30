// ====== Проверка пароля и загрузка истории ======
const PASSWORD = localStorage.getItem('kesha_password');
if (!PASSWORD) {
    window.location.href = '/';
}

let chatHistory = JSON.parse(localStorage.getItem('chatHistory')) || [];
let streamActive = false;
let lastCommand = '';

// ====== Элементы ======
const messagesContainer = document.getElementById('chatMessages');
const commandInput = document.getElementById('commandInput');
const sendBtn = document.getElementById('sendBtn');
const fileInput = document.getElementById('fileInput');

// ====== Картинка в сообщении (textContent + img, без innerHTML) ======
function appendImage(div, text, imageUrl) {
    div.appendChild(document.createTextNode(text));
    div.appendChild(document.createElement('br'));
    const img = document.createElement('img');
    img.src = imageUrl;
    img.alt = 'скриншот';
    img.style.cssText = 'max-width:100%;border-radius:10px;margin-top:5px;';
    div.appendChild(img);
}

// ====== Добавление сообщения с сохранением ======
function addMessage(text, sender, imageUrl = null) {
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    if (imageUrl) {
        appendImage(div, text, imageUrl);
    } else {
        div.textContent = text;
    }
    messagesContainer.appendChild(div);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    chatHistory.push({ text, sender, imageUrl, time: Date.now() });
    if (chatHistory.length > 500) chatHistory.shift();
    localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
}

// ====== Загрузка истории при старте ======
function loadHistory() {
    chatHistory.forEach(msg => {
        const div = document.createElement('div');
        div.className = `message ${msg.sender}`;
        if (msg.imageUrl) {
            appendImage(div, msg.text, msg.imageUrl);
        } else {
            div.textContent = msg.text;
        }
        messagesContainer.appendChild(div);
    });
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ====== Очистка истории ======
function clearHistory() {
    if (confirm('Удалить всю историю чата?')) {
        chatHistory = [];
        localStorage.removeItem('chatHistory');
        messagesContainer.innerHTML = '';
        addMessage('🗑 История чата очищена', 'system');
    }
}

// ====== Отправка команды ======
async function sendCommand(text) {
    const commandText = text || commandInput.value.trim();
    if (!commandText) return;
    if (!text) commandInput.value = '';
    lastCommand = commandText;
    addMessage(commandText, 'user');
    sendBtn.disabled = true;
    try {
        const response = await fetch('/api/command', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Password': PASSWORD
            },
            body: JSON.stringify({ command: commandText })
        });
        if (response.status === 401) {
            localStorage.removeItem('kesha_password');
            window.location.href = '/';
            return;
        }
        const data = await response.json();
        if (data.image_url) {
            addMessage(data.result || '✅ Скриншот', 'bot', data.image_url);
        } else {
            addMessage(data.result || '✅ Выполнено', 'bot');
        }
        if (commandText.toLowerCase().includes('трансляция')) {
            toggleStream(true);
        }
    } catch (error) {
        addMessage('❌ Ошибка соединения с сервером', 'bot');
    } finally {
        sendBtn.disabled = false;
        if (!text) {
            // Если команда из поля ввода – возвращаем фокус
            commandInput.focus();
        } else {
            // Если команда из кнопки – убираем фокус, чтобы клавиатура не появлялась
            commandInput.blur();
        }
    }
}

// ====== Тихая отправка (джойстик): без записи в чат и без наложения запросов ======
let quietBusy = false;
async function sendQuiet(commandText) {
    if (quietBusy) return;
    quietBusy = true;
    try {
        const r = await fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Password': PASSWORD },
            body: JSON.stringify({ command: commandText })
        });
        if (r.status === 401) {
            localStorage.removeItem('kesha_password');
            window.location.href = '/';
        }
    } catch (e) { /* пропускаем кадр */ }
    finally { quietBusy = false; }
}

// ====== Повтор последней команды ======
function repeatLastCommand() {
    if (lastCommand) {
        sendCommand(lastCommand);
    } else {
        addMessage('⚠️ Нет предыдущей команды', 'system');
    }
}

// ====== Кнопки управления (pointerdown для сенсорных устройств) ======
document.querySelectorAll('.ctrl-btn, .j-btn').forEach(btn => {
    btn.addEventListener('pointerdown', function(e) {
        e.preventDefault();
        // Снимаем фокус с поля ввода, чтобы клавиатура не появлялась
        commandInput.blur();
        let cmd = this.dataset.cmd;
        if (this.dataset.scroll) {
            cmd = this.dataset.scroll === '1' ? 'скролл вверх' : 'скролл вниз';
        }
        sendCommand(cmd);
    });
});

// ====== Трансляция ======
function toggleStream(forceStart = false) {
    const container = document.getElementById('streamContainer');
    const img = document.getElementById('streamImage');
    if (streamActive && !forceStart) {
        img.src = '';
        container.style.display = 'none';
        streamActive = false;
        addMessage('Трансляция остановлена', 'system');
        return;
    }
    img.src = '/stream?_=' + Date.now();   // авторизация — по куке из /login
    container.style.display = 'block';
    streamActive = true;
    addMessage('📺 Трансляция запущена!', 'system');
}

function toggleFullscreen() {
    const img = document.getElementById('streamImage');
    if (img.requestFullscreen) {
        img.requestFullscreen();
    } else if (img.webkitRequestFullscreen) {
        img.webkitRequestFullscreen();
    }
}

// ====== Напечатай текст ======
function sendTypeText() {
    const input = document.getElementById('typeTextInput');
    const text = input.value.trim();
    if (!text) return;
    // Убираем фокус с поля ввода команд, чтобы не мешать
    commandInput.blur();
    sendCommand('напечатай ' + text);
    input.value = '';
}

// ====== Нажми клавишу ======
function sendKey() {
    const input = document.getElementById('keyInput');
    const key = input.value.trim();
    if (!key) return;
    commandInput.blur();
    sendCommand('нажми клавишу ' + key);
    input.value = '';
}

// ====== Сенсорный джойстик ======
const joystick = document.getElementById('joystick');
const thumb = document.getElementById('thumb');

let joystickActive = false;
let joystickInterval = null;
let joystickDirection = '';
let joystickForce = 0;

function getJoystickDirection(dx, dy) {
    const absX = Math.abs(dx);
    const absY = Math.abs(dy);
    if (absX < 0.1 && absY < 0.1) return '';

    if (absX > absY) {
        return dx > 0 ? 'мышь вправо' : 'мышь влево';
    } else {
        return dy > 0 ? 'мышь вниз' : 'мышь вверх';
    }
}

function updateJoystick(clientX, clientY) {
    const rect = joystick.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    let dx = clientX - centerX;
    let dy = clientY - centerY;
    const maxDist = rect.width / 2 - thumb.offsetWidth / 2;
    const distance = Math.sqrt(dx*dx + dy*dy);
    let clampedDist = Math.min(distance, maxDist);
    if (distance > 0) {
        dx = dx / distance * clampedDist;
        dy = dy / distance * clampedDist;
    } else {
        dx = 0;
        dy = 0;
    }

    thumb.style.transform = `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px))`;
    joystickForce = clampedDist / maxDist;
    joystickDirection = getJoystickDirection(dx, dy);
}

function startJoystick(e) {
    e.preventDefault();
    // Убираем фокус с поля ввода
    commandInput.blur();
    joystickActive = true;
    const point = e.touches ? e.touches[0] : e;
    updateJoystick(point.clientX, point.clientY);

    if (joystickInterval) clearInterval(joystickInterval);
    joystickInterval = setInterval(() => {
        if (joystickDirection && joystickForce > 0.1) {
            const step = Math.max(10, Math.round(joystickForce * 50));
            sendQuiet(joystickDirection + ' ' + step);
        }
    }, 100);
}

function moveJoystick(e) {
    e.preventDefault();
    if (!joystickActive) return;
    const point = e.touches ? e.touches[0] : e;
    updateJoystick(point.clientX, point.clientY);
}

function stopJoystick(e) {
    e.preventDefault();
    if (!joystickActive) return;
    joystickActive = false;
    thumb.style.transform = `translate(-50%, -50%)`;
    joystickDirection = '';
    joystickForce = 0;
    if (joystickInterval) {
        clearInterval(joystickInterval);
        joystickInterval = null;
    }
}

joystick.addEventListener('mousedown', startJoystick);
document.addEventListener('mousemove', moveJoystick);
document.addEventListener('mouseup', stopJoystick);

joystick.addEventListener('touchstart', startJoystick, { passive: false });
document.addEventListener('touchmove', moveJoystick, { passive: false });
document.addEventListener('touchend', stopJoystick, { passive: false });

// ====== Кнопка ЛК (pointerdown) ======
document.getElementById('leftClickBtn').addEventListener('pointerdown', function(e) {
    e.preventDefault();
    commandInput.blur();
    sendCommand('левый клик');
});

// ====== Кнопка "Повтор" (pointerdown) ======
document.getElementById('repeatBtn').addEventListener('pointerdown', function(e) {
    e.preventDefault();
    commandInput.blur();
    repeatLastCommand();
});

// ====== Загрузка быстрых кнопок ======
async function loadQuickButtons() {
    try {
        const response = await fetch('/api/commands', {
            headers: { 'X-Password': PASSWORD }
        });
        const data = await response.json();
        const container = document.getElementById('quickCommands');
        const sample = data.commands.slice(0, 8);
        sample.forEach(cmd => {
            const name = (cmd.patterns && cmd.patterns[0]) || cmd.description || '';
            if (!name) return;
            const btn = document.createElement('button');
            btn.textContent = name;
            btn.title = cmd.description || name;
            btn.addEventListener('pointerdown', function(e) {
                e.preventDefault();
                commandInput.value = name;
                commandInput.focus(); // при вставке в поле даём фокус для удобства
            });
            container.appendChild(btn);
        });
        const helpBtn = document.createElement('button');
        helpBtn.textContent = '❓ Помощь';
        helpBtn.addEventListener('pointerdown', function(e) {
            e.preventDefault();
            const cats = {};
            for (const c of data.commands) {
                const key = c.category || 'Общее';
                (cats[key] = cats[key] || []).push((c.patterns && c.patterns[0]) || c.description);
            }
            let msg = '📋 Доступные команды (категории):\n\n';
            for (const [cat, names] of Object.entries(cats)) {
                msg += `🔹 ${cat}\n`;
                for (const n of names) msg += `   ${n}\n`;
                msg += '\n';
            }
            addMessage(msg, 'bot');
        });
        container.appendChild(helpBtn);
    } catch (e) {
        console.error('Ошибка загрузки команд', e);
    }
}

// ====== Загрузка файлов ======
fileInput.addEventListener('change', async function() {
    if (this.files.length === 0) return;
    const file = this.files[0];
    const formData = new FormData();
    formData.append('file', file);
    addMessage(`📎 Загружаю файл: ${file.name}...`, 'user');
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            headers: { 'X-Password': PASSWORD },
            body: formData
        });
        const data = await response.json();
        if (data.file_url) {
            addMessage(`✅ Файл загружен: ${data.file_url}`, 'bot');
        } else {
            addMessage('❌ Ошибка загрузки файла', 'bot');
        }
    } catch (e) {
        addMessage('❌ Ошибка при загрузке', 'bot');
    }
    this.value = '';
});

// ====== Обработка Enter ======
commandInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendCommand();
});
document.getElementById('typeTextInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendTypeText();
});
document.getElementById('keyInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendKey();
});

// ====== Выход ======
function logout() {
    localStorage.removeItem('kesha_password');
    localStorage.removeItem('chatHistory');
    window.location.href = '/';
}

// ====== Состояние Кеши в реальном времени (WebSocket /ws) ======
const STATE_LABELS = {
    IDLE: 'ждёт', WAKE: 'слышит', LISTENING: 'слушает', THINKING: 'думает',
    SPEAKING: 'говорит', ERROR: 'ошибка', OFFLINE: 'нет связи'
};

function setStatus(state, info) {
    const box = document.getElementById('kStatus');
    const label = document.getElementById('kStatusText');
    if (!box || !label) return;
    box.dataset.state = STATE_LABELS[state] ? state : 'IDLE';
    label.textContent = STATE_LABELS[state] || state;
    box.title = (info && (info.error || info.text)) || 'Что сейчас делает Кеша';
}

let wsRetry = 1000;
function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    let ws;
    try {
        ws = new WebSocket(`${proto}://${location.host}/ws`);   // авторизация — по куке из /login
    } catch (e) {
        return;
    }
    ws.onopen = () => { wsRetry = 1000; };
    ws.onmessage = (event) => {
        let d;
        try { d = JSON.parse(event.data); } catch (e) { return; }
        if (d.type === 'state') {
            setStatus(d.state, d.info);
        } else if (d.type === 'message' && d.source === 'kesha') {
            addMessage('⏰ ' + d.response, 'bot');   // напоминание / будильник / таймер
        }
    };
    ws.onclose = () => {
        setStatus('OFFLINE');
        setTimeout(connectWS, wsRetry);
        wsRetry = Math.min(wsRetry * 2, 30000);
    };
}

// ====== Инициализация ======
loadHistory();
// кука сессии нужна для <img> (скриншоты, трансляция) и WebSocket; обновляем её при каждом открытии чата
fetch('/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: PASSWORD })
}).finally(() => {
    loadQuickButtons();
    connectWS();
});