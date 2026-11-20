/* Логика десктоп-интерфейса Кеша */
let bridge = null;

const PREVIEW = /[?&]preview=1/.test(location.search);

function initBridge() {
  if (PREVIEW) return;
  if (typeof qt === 'undefined' || !qt.webChannelTransport) {
    console.warn('QWebChannel недоступен');
    return;
  }
  new QWebChannel(qt.webChannelTransport, function (channel) {
    bridge = channel.objects.bridge;
    console.log('Bridge OK');
    // события ядра/состояния/настройки приходят из Python через runJavaScript
    if (bridge && bridge.get_commands) {
      bridge.get_commands(function (json) {
        try { loadRegistryCommands(JSON.parse(json)); } catch (e) { console.warn(e); }
      });
    }
    if (bridge && bridge.get_settings) {
      bridge.get_settings(function (json) {
        try {
          const s = JSON.parse(json);
          Object.keys(s).forEach(k => onSetting(k, s[k]));
        } catch (e) { console.warn(e); }
      });
    }
  });
}

const CMD_ITEMS = {};   // name -> {id, patterns, changed, ...} из реестра

/* Окно паттернов команды */
function openPatterns(name) {
  const item = CMD_ITEMS[name];
  if (!item) return;
  closePatterns();
  const ov = document.createElement('div');
  ov.className = 'pat-overlay';
  ov.id = 'patOverlay';
  ov.innerHTML =
    '<div class="pat-modal">' +
    '<div class="pat-title">Паттерны: ' + item.id + '</div>' +
    '<div class="pat-hint">Одна фраза на строку. Нижний регистр, без знаков. ' +
    (item.risky ? 'Команда опасная: только точная фраза.' : '') + '</div>' +
    '<textarea id="patText" spellcheck="false"></textarea>' +
    '<div class="pat-btns">' +
    '<button id="patSave">Сохранить</button>' +
    '<button id="patReset">Сбросить</button>' +
    '<button id="patClose">Закрыть</button></div>' +
    '<div class="pat-status" id="patStatus"></div></div>';
  document.body.appendChild(ov);
  const ta = document.getElementById('patText');
  ta.value = item.patterns.join('\n');
  ta.focus();
  const status = t => { document.getElementById('patStatus').textContent = t; };
  const save = (patterns) => {
    if (!bridge || !bridge.save_patterns) { status('Нет связи с Python'); return; }
    bridge.save_patterns(item.id, JSON.stringify(patterns), function (ok) {
      if (!ok) { status('Не удалось сохранить'); return; }
      bridge.get_commands(function (json) {
        try { loadRegistryCommands(JSON.parse(json)); } catch (e) { console.warn(e); }
        const fresh = Object.values(CMD_ITEMS).find(i => i.id === item.id);
        if (fresh) { item.patterns = fresh.patterns; ta.value = fresh.patterns.join('\n'); }
        status('Сохранено ✓ (работает сразу)');
      });
    });
  };
  document.getElementById('patSave').onclick = () =>
    save(ta.value.split('\n').map(s => s.trim()).filter(Boolean));
  document.getElementById('patReset').onclick = () => save(null);
  document.getElementById('patClose').onclick = closePatterns;
  ov.addEventListener('mousedown', e => { if (e.target === ov) closePatterns(); });
  ta.addEventListener('keydown', e => {
    if (e.key === 'Escape') closePatterns();
    if (e.key === 'Enter' && e.ctrlKey) document.getElementById('patSave').click();
  });
}
function closePatterns() {
  const o = document.getElementById('patOverlay');
  if (o) o.remove();
}

/* Команды из реестра Python (заменяют статичный список ниже) */
function loadRegistryCommands(groups) {
  if (!Array.isArray(groups) || !groups.length) return;
  for (const k of Object.keys(COMMAND_CATEGORIES)) delete COMMAND_CATEGORIES[k];
  for (const k of Object.keys(CMD_ITEMS)) delete CMD_ITEMS[k];
  for (const g of groups) {
    COMMAND_CATEGORIES[g.category] = g.items.map(i => i.name + ' - ' + i.desc);
    g.items.forEach(i => { CMD_ITEMS[i.name] = i; });
  }
  const search = document.getElementById('cmdSearch');
  renderCommands(search ? search.value : '');
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
              (CMD_ITEMS[name] ? '<button class="cmd-pat' + (CMD_ITEMS[name].changed ? ' changed' : '') +
                '" title="Редактировать фразы-паттерны">паттерны</button>' : '') +
              '</div>';
      total++;
    }
  }
  if (!total) html = '<div class="cmd-empty">Ничего не найдено</div>';
  container.innerHTML = html;
  container.querySelectorAll('.cmd-pat').forEach(b => {
    b.addEventListener('click', function (e) {
      e.stopPropagation();
      openPatterns(this.parentElement.dataset.cmd);
    });
  });
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
  pulseReactorEngine(document.getElementById('reactor'), ms);
}

/* ============================================================
   ЕДИНЫЙ ОБРАБОТЧИК СОБЫТИЙ ЯДРА
   ============================================================ */
function onCoreEvent(source, text, response) {
  if (source === 'kesha') {
    // Кеша сама: напоминание, будильник, таймер
    spawnCenterBurst('#FFC400');
    pulseReactor(1500);
    addMessage('⏰ ' + (response || ''), 'bot', 'kesha');
    return;
  }
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
   СОСТОЯНИЯ РЕАКТОРА (state_manager -> bridge -> сюда)
   ============================================================ */
// цвета и анимации — reactor.js / reactor_config.js (редактор: reactor_editor.html)
let REACTOR_CFG = reactorConfig();
let curState = 'IDLE', curText = '';

function onState(state, text) {
  if (!REACTOR_LABELS[state]) state = 'IDLE';
  curState = state; curText = text;
  const r = document.getElementById('reactor');
  const s = document.getElementById('statusBar');
  if (r && !!uiSettings.mic_muted !== !!r._muted) r._muted = !!uiSettings.mic_muted;
  const view = r ? applyReactorState(r, state, REACTOR_CFG) : REACTOR_CFG.states[state];
  if (s) {
    s.textContent = REACTOR_LABELS[state] + (state === 'ERROR' && text ? ': ' + text : '');
    s.style.color = uiSettings.mic_muted ? '#FF2840' : view.main;
    if (uiSettings.mic_muted) s.textContent = 'МИКРОФОН ВЫКЛ';
  }
}

/* ============================================================
   НАСТРОЙКИ (тема, тихий режим)
   ============================================================ */
const uiSettings = {};
function onSetting(key, value) {
  uiSettings[key] = value;
  if (key === 'design' && !PREVIEW) {
    let d = value; if (typeof d === 'string') { try { d = JSON.parse(d); } catch (e) { d = null; } }
    if (d) applyDesign(d);
  }
  if (key === 'reactor' && value && !PREVIEW) {
    REACTOR_CFG = reactorConfig(value);
    onState(curState, curText);
  }
  if (key === 'floating_icon') {
    const f = document.getElementById('btnFloat');
    if (f) f.textContent = value ? 'СКРЫТЬ' : 'ПОКАЗАТЬ';
  }
  if (key === 'mic_muted') {
    const m = document.getElementById('btnMic');
    if (m) {
      m.classList.toggle('active', !!value);
      if (typeof curState !== 'undefined') onState(curState, curText);
      m.title = value ? 'Микрофон выключен: Кеша не слышит (нажми — включить)' : 'Микрофон включён (нажми — Кеша перестанет слышать)';
    }
  }
  if (key === 'silent') {
    const m = document.getElementById('btnSilent');
    if (m) {
      m.classList.toggle('active', !!value);
      m.title = value ? 'Тихий режим: Кеша молча выполняет команды (нажми — включить звук)' : 'Звук включён (нажми — тихий режим)';
    }
  }
}

function setSetting(key, value) {
  if (bridge && bridge.set_setting) bridge.set_setting(key, JSON.stringify(value));
  else onSetting(key, value);
}

function openDesign() {
  if (bridge && bridge.open_design) bridge.open_design();
  else window.open('studio.html', '_blank');
}
function toggleFloat() { setSetting('floating_icon', !uiSettings.floating_icon); }
function toggleMic() { setSetting('mic_muted', !uiSettings.mic_muted); }
function toggleSilent() { setSetting('silent', !uiSettings.silent); }

/* ============================================================
   ИНИЦИАЛИЗАЦИЯ
   ============================================================ */
window.addEventListener('load', function () {
  const reactor = document.getElementById('reactor');
  if (reactor) { buildReactor(reactor); onState('IDLE', ''); }
  renderCommands("");
  const inp = document.getElementById('commandInput');
  if (inp) inp.addEventListener('keypress', e => { if (e.key === 'Enter') sendFromInput(); });
  const search = document.getElementById('cmdSearch');
  if (search) search.addEventListener('input', () => renderCommands(search.value));
  const btn = document.getElementById('btnSend');
  if (btn) btn.addEventListener('click', sendFromInput);
  window.addEventListener('message', e => {
    if (PREVIEW && e.data && e.data.kesha_design) applyDesign(e.data.kesha_design);
  });
  if (!PREVIEW) setTimeout(initBridge, 200);
});
