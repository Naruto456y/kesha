/* Логика десктоп-интерфейса Кеша */
let bridge = null;

function initBridge() {
  if (typeof qt === 'undefined' || !qt.webChannelTransport) {
    console.warn('QWebChannel недоступен');
    return;
  }
  new QWebChannel(qt.webChannelTransport, function (channel) {
    bridge = channel.objects.bridge;
    console.log('Bridge OK');
    if (bridge && bridge.core_event) {
      bridge.core_event.connect(onCoreEvent);
    }
  });
}

/* ============================================================
   КОМАНДЫ (список для правой панели)
   ============================================================ */
const COMMAND_CATEGORIES = {
  "Основные команды": [
    "привет - Поздороваться",
    "как дела - Узнать состояние",
    "молодец - Похвалить",
    "пока - Завершить работу"
  ],
  "Интернет и поиск": [
    "найди [запрос] - Поиск в интернете",
    "найди в ютуби [запрос] - Поиск на YouTube",
    "youtube - Открыть YouTube",
    "игры - Открыть Яндекс Игры",
    "погода - Узнать погоду",
    "переводчик - Открыть переводчик",
    "дипси - Открыть DeepSeek"
  ],
  "Игры": [
    "камень ножницы бумага",
    "виселица",
    "викторина",
    "квест",
    "крестики-нолики",
    "угадай число"
  ],
  "Система и приложения": [
    "открой [приложение]",
    "закрой [приложение]",
    "проводник",
    "настройки",
    "сверни",
    "закрой окно",
    "скриншот",
    "камера",
    "селфи",
    "браузер",
    "левый клик",
    "правый клик",
    "мышь вверх",
    "мышь вниз",
    "мышь влево",
    "мышь вправо",
    "напечатай [текст]",
    "нажми клавишу [x]",
    "пробел",
    "полный экран"
  ],
  "Медиа и управление": [
    "музыка [название]",
    "моя волна",
    "пауза",
    "продолжи",
    "дальше",
    "предыдущий",
    "лайк",
    "дизлайк",
    "громче",
    "тише",
    "громкость [0-100]"
  ],
  "Системная информация": [
    "время",
    "дата",
    "батарея"
  ],
  "Питание": [
    "выключи компьютер",
    "перезагрузка",
    "спящий режим",
    "заблокируй компьютер",
    "ухожу"
  ],
  "Учёба": [
    "дз",
    "оценки",
    "расписание"
  ],
  "Специальные команды": [
    "переведи на английский [текст]",
    "переведи на русский [текст]",
    "нарисуй [что-то]",
    "включи свет",
    "выключи свет",
    "таймер [минут]",
    "телефон",
    "bluetooth",
    "хаос",
    "стоп хаос"
  ]
};

function renderCommands(filterText) {
  filterText = filterText || "";
  const container = document.getElementById('commandsScroll');
  if (!container) return;
  const filter = filterText.trim().toLowerCase();
  let html = "", total = 0;
  for (const [cat, cmds] of Object.entries(COMMAND_CATEGORIES)) {
    const matched = cmds.filter(c => !filter || c.toLowerCase().includes(filter));
    if (!matched.length) continue;
    html += '<div class="cmd-category">' + cat + '</div>';
    for (const cmd of matched) {
      const parts = cmd.split(' - ');
      const name = parts[0] || cmd;
      const desc = parts[1] || '';
      html += '<div class="cmd-item" data-cmd="' + name.replace(/"/g, '&quot;') + '">' +
              '<span class="cmd-name">' + name + '</span>' +
              (desc ? '<span class="cmd-desc">- ' + desc + '</span>' : '') +
              '</div>';
      total++;
    }
  }
  if (!total) html = '<div class="cmd-empty">Ничего не найдено</div>';
  container.innerHTML = html;
  container.querySelectorAll('.cmd-item').forEach(el => {
    el.addEventListener('click', function () {
      document.querySelectorAll('.cmd-item.active').forEach(e => e.classList.remove('active'));
      this.classList.add('active');
      const cmd = this.dataset.cmd;
      const inp = document.getElementById('commandInput');
      if (inp) inp.value = cmd;
      sendCommand(cmd);
    });
  });
}

/* ============================================================
   АНИМАЦИИ
   ============================================================ */
const SOURCE_CONFIG = {
  app:      { color:'#FFFFFF', edgeId:'edge-app',
              from:()=>({x: innerWidth/2,   y:4}) },
  alice:    { color:'#B45CFF', edgeId:'edge-alice',
              from:()=>({x: innerWidth-4,   y: innerHeight/2}) },
  website:  { color:'#FFD700', edgeId:'edge-website',
              from:()=>({x: innerWidth/2,   y: innerHeight-4}) },
  telegram: { color:'#468CFF', edgeId:'edge-telegram',
              from:()=>({x:4,              y: innerHeight/2}) }
};

function spawnRay(source) {
  const cfg = SOURCE_CONFIG[source];
  if (!cfg) return;
  const edge = document.getElementById(cfg.edgeId);
  if (edge) {
    edge.classList.remove('flash');
    void edge.offsetWidth;
    edge.classList.add('flash');
    setTimeout(() => edge.classList.remove('flash'), 1000);
  }
  const start = cfg.from();
  const r = document.getElementById('reactor').getBoundingClientRect();
  const cx = r.left + r.width/2;
  const cy = r.top + r.height/2;

  const ray = document.createElement('div');
  ray.className = 'ray';
  ray.style.left = start.x + 'px';
  ray.style.top = start.y + 'px';
  ray.style.background = cfg.color;
  ray.style.boxShadow = '0 0 18px 6px ' + cfg.color + ',0 0 40px 12px ' + cfg.color;
  document.body.appendChild(ray);

  requestAnimationFrame(() => {
    ray.style.left = cx + 'px';
    ray.style.top = cy + 'px';
    ray.classList.add('shrink');
  });
  setTimeout(() => spawnCenterBurst(cfg.color), 850);
  setTimeout(() => ray.remove(), 1000);
}

function spawnCenterBurst(color) {
  const r = document.getElementById('reactor').getBoundingClientRect();
  const cx = r.left + r.width/2;
  const cy = r.top + r.height/2;
  const b = document.createElement('div');
  b.className = 'burst';
  b.style.left = cx + 'px';
  b.style.top = cy + 'px';
  b.style.background = color;
  b.style.boxShadow = '0 0 30px 12px ' + color;
  document.body.appendChild(b);
  setTimeout(() => b.remove(), 750);
}

function pulseReactor(ms) {
  ms = ms || 1000;
  const r = document.getElementById('reactor');
  r.classList.add('listening');
  setTimeout(() => r.classList.remove('listening'), ms);
}

/* ============================================================
   ЕДИНЫЙ ОБРАБОТЧИК СОБЫТИЙ ЯДРА
   ============================================================ */
function onCoreEvent(source, text, response) {
  if (!text) return;

  const labels = {
    app:'Приложение', alice:'Алиса', telegram:'Telegram',
    website:'Сайт', voice:'Голос'
  };
  const prefix = labels[source] ? (labels[source] + ': «' + text + '»') : text;

  // Визуал зависит от источника
  if (source === 'voice') {
    // Голос: только свечение реактора на 1 сек, без луча
    pulseReactor(1000);
    spawnCenterBurst('#00FFAA');
  } else if (source === 'app') {
    // App: белый луч сверху
    spawnRay('app');
  } else {
    // Алиса / Сайт / Telegram: свой луч со своего края
    spawnRay(source);
  }

  addMessage(prefix, 'user', source);
  setTimeout(() => {
    addMessage('Кеша: ' + (response || '...'), 'bot', source);
  }, 300);
}

/* ============================================================
   ОТПРАВКА КОМАНДЫ ИЗ UI
   ============================================================ */
async function sendCommand(text) {
  text = (text || '').trim();
  if (!text) return;
  if (bridge) {
    try { await bridge.send_command(text); }
    catch (e) { console.warn('send_command:', e); }
  } else {
    onCoreEvent('app', text, '(нет моста с Python)');
  }
}

function sendFromInput() {
  const inp = document.getElementById('commandInput');
  if (!inp) return;
  const t = inp.value.trim();
  if (!t) return;
  inp.value = '';
  sendCommand(t);
}

/* ============================================================
   СООБЩЕНИЯ
   ============================================================ */
function addMessage(text, sender, source) {
  const c = document.getElementById('chatMessages');
  if (!c) return;
  const d = document.createElement('div');
  d.className = 'message ' + sender;
  if (source) d.dataset.source = source;
  d.textContent = text;
  c.appendChild(d);
  c.scrollTop = c.scrollHeight;
}

/* ============================================================
   КНОПКА "СЛУШАТЬ" (только для ручного управления микрофоном)
   ============================================================ */
let listening = false;
function toggleListening() {
  listening = !listening;
  const r = document.getElementById('reactor');
  const b = document.getElementById('btnListen');
  const s = document.getElementById('statusBar');
  if (listening) {
    r.classList.add('listening');
    b.classList.add('active');
    b.textContent = 'СТОП';
    s.textContent = 'LISTENING';
    s.style.color = '#00FFAA';
  } else {
    r.classList.remove('listening');
    b.classList.remove('active');
    b.textContent = 'СЛУШАТЬ';
    s.textContent = 'IDLE';
    s.style.color = 'rgba(0,229,255,0.7)';
  }
}

/* ============================================================
   ИНИЦИАЛИЗАЦИЯ
   ============================================================ */
window.addEventListener('load', function () {
  renderCommands("");
  const inp = document.getElementById('commandInput');
  if (inp) inp.addEventListener('keypress', e => { if (e.key === 'Enter') sendFromInput(); });
  const search = document.getElementById('cmdSearch');
  if (search) search.addEventListener('input', () => renderCommands(search.value));
  const btn = document.getElementById('btnSend');
  if (btn) btn.addEventListener('click', sendFromInput);
  setTimeout(initBridge, 200);
});
