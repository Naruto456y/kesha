/* ============================================================
   РЕАКТОР КЕШИ: картинка, цвета и анимации по состояниям.
   Общий для окна Кеши (index.html) и редактора (reactor_editor.html).
   Свои цвета — reactor_config.js (window.REACTOR_CONFIG), его делает редактор.
   ============================================================ */
const REACTOR_STATES = ['IDLE', 'WAKE', 'LISTENING', 'THINKING', 'SPEAKING', 'ERROR'];
const REACTOR_LABELS = { IDLE: 'ЖДУ', WAKE: 'СЛЫШУ', LISTENING: 'СЛУШАЮ',
  THINKING: 'ДУМАЮ', SPEAKING: 'ГОВОРЮ', ERROR: 'ОШИБКА' };
const REACTOR_FX = { ripple: 'Волны', orbit: 'Орбиты', eq: 'Эквалайзер', radar: 'Радар',
  sparks: 'Искры', breathe: 'Дыхание', flicker: 'Мерцание' };

// main — кольца и шестерня, accent — блики и точки, core — ядро, glow — свечение вокруг;
// spin — оборот шестерни, с; pulse — удар ядра, с; pulseScale — насколько ядро раздувается
const REACTOR_DEFAULT = {
  dark: '#0A2A38',
  fade: 0.7,                   // с: переход между состояниями (цвета, эффекты, скорости)
  states: {
    IDLE:      { main: '#00E5FF', accent: '#7FFFFF', core: '#DFFFFF', glow: '#00E5FF',
                 glowSize: 24, spin: 22, pulse: 1.8, pulseScale: 1.06, fx: [] },
    WAKE:      { main: '#FFFFFF', accent: '#CFFFFF', core: '#FFFFFF', glow: '#FFFFFF',
                 glowSize: 44, spin: 10, pulse: 0.8, pulseScale: 1.12, fx: ['ripple', 'breathe'] },
    LISTENING: { main: '#00FFAA', accent: '#9CFFD8', core: '#E6FFF5', glow: '#00FFAA',
                 glowSize: 40, spin: 12, pulse: 0.9, pulseScale: 1.1, fx: ['ripple', 'breathe'] },
    THINKING:  { main: '#FFC400', accent: '#FFE27A', core: '#FFF6D6', glow: '#FFC400',
                 glowSize: 36, spin: 5, pulse: 1.2, pulseScale: 1.05, fx: ['radar', 'orbit'] },
    SPEAKING:  { main: '#3D8BFF', accent: '#9CC8FF', core: '#E3F0FF', glow: '#3D8BFF',
                 glowSize: 40, spin: 14, pulse: 0.5, pulseScale: 1.08, fx: ['eq'] },
    ERROR:     { main: '#FF3355', accent: '#FF8FA2', core: '#FFE0E6', glow: '#FF3355',
                 glowSize: 40, spin: 30, pulse: 1.4, pulseScale: 1.04, fx: ['flicker'] }
  }
};

function reactorConfig(override) {
  const user = override || window.REACTOR_CONFIG || {};
  const cfg = { dark: user.dark || REACTOR_DEFAULT.dark,
                fade: user.fade != null ? user.fade : REACTOR_DEFAULT.fade, states: {} };
  REACTOR_STATES.forEach(s => {
    cfg.states[s] = Object.assign({}, REACTOR_DEFAULT.states[s], (user.states || {})[s] || {});
    cfg.states[s].fx = (cfg.states[s].fx || []).slice();
  });
  return cfg;
}

const _HEX = Array.from({ length: 8 }, (_, i) => {
  const a = i * Math.PI / 4;
  return [200 + 160 * Math.sin(a), 200 - 160 * Math.cos(a)];
});

function _reactorSVG() {
  const hex = _HEX.map(([x, y]) =>
    `<g class="hex-blink" transform="translate(${x.toFixed(0)},${y.toFixed(0)})">` +
    `<polygon points="0,-22 19,-11 19,11 0,22 -19,11 -19,-11" fill="url(#hexGrad)" filter="url(#softGlow)"/></g>`
  ).join('');
  const eq = Array.from({ length: 32 }, (_, i) =>
    `<g transform="rotate(${i * 11.25} 200 200)"><rect class="eq-bar" x="198" y="84" width="4" height="26" rx="2"
      style="animation-delay:${((i * 7) % 13) * -0.09}s"/></g>`).join('');
  const sparks = Array.from({ length: 10 }, (_, i) =>
    `<g transform="rotate(${i * 36 + 13} 200 200)"><circle class="spark" cx="200" cy="140" r="3"
      style="animation-delay:${i * -0.17}s"/></g>`).join('');
  return `
<svg viewBox="0 0 400 400">
  <defs>
    <radialGradient id="glowGrad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:var(--r-accent);stop-opacity:.55"/>
      <stop offset="55%" style="stop-color:var(--r-main);stop-opacity:.25"/>
      <stop offset="100%" style="stop-color:var(--r-main);stop-opacity:0"/>
    </radialGradient>
    <radialGradient id="coreGrad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:#FFFFFF"/>
      <stop offset="45%" style="stop-color:var(--r-core)"/>
      <stop offset="80%" style="stop-color:var(--r-accent)"/>
      <stop offset="100%" style="stop-color:var(--r-main)"/>
    </radialGradient>
    <radialGradient id="coreInner" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#FFFFFF"/><stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="hexGrad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:#FFFFFF"/>
      <stop offset="60%" style="stop-color:var(--r-accent)"/>
      <stop offset="100%" style="stop-color:var(--r-main)"/>
    </radialGradient>
    <linearGradient id="radarGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" style="stop-color:var(--r-main);stop-opacity:0"/>
      <stop offset="100%" style="stop-color:var(--r-main);stop-opacity:.55"/>
    </linearGradient>
    <filter id="softGlow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <g class="fx-layer fx-ripple">
    <circle class="ripple" cx="200" cy="200" r="70"/><circle class="ripple" cx="200" cy="200" r="70"/>
    <circle class="ripple" cx="200" cy="200" r="70"/>
  </g>
  <circle class="pulse-glow" cx="200" cy="200" r="195" fill="url(#glowGrad)"/>
  <circle class="spin spin-a r-dark" cx="200" cy="200" r="160" stroke-width="70"
          stroke-dasharray="48 30" stroke-linecap="round"/>
  <circle class="spin spin-a r-main-stroke" cx="200" cy="200" r="160" fill="none" stroke-width="3"
          stroke-dasharray="48 30" stroke-linecap="round" opacity="0.7"/>
  <g class="spin spin-b">${hex}</g>
  <circle class="r-dark-fill" cx="200" cy="200" r="115" opacity="0.95"/>
  <g class="fx-layer fx-radar"><g class="spin spin-radar">
    <path d="M200,200 L200,88 A112,112 0 0,1 272,114 Z" fill="url(#radarGrad)"/>
    <line x1="200" y1="200" x2="272" y2="114" class="r-main-stroke" stroke-width="2"/>
  </g></g>
  <g class="fx-layer fx-eq">${eq}</g>
  <circle class="spin spin-b r-accent-stroke" cx="200" cy="200" r="98" fill="none" stroke-width="5"
          stroke-dasharray="1 36" stroke-linecap="round" filter="url(#softGlow)"/>
  <circle class="r-main-stroke" cx="200" cy="200" r="72" fill="none" stroke-width="5" filter="url(#softGlow)"/>
  <circle class="r-accent-stroke" cx="200" cy="200" r="62" fill="none" stroke-width="1.5" opacity="0.6"/>
  <g class="fx-layer fx-orbit">
    <g class="spin spin-o1"><circle cx="200" cy="65" r="6" class="r-accent-fill" filter="url(#softGlow)"/></g>
    <g class="spin spin-o2"><circle cx="200" cy="105" r="4" class="r-main-fill" filter="url(#softGlow)"/></g>
    <g class="spin spin-o3"><circle cx="200" cy="35" r="3.5" class="r-core-fill" filter="url(#softGlow)"/></g>
  </g>
  <g class="fx-layer fx-sparks">${sparks}</g>
  <circle class="pulse-core" cx="200" cy="200" r="55" fill="url(#coreGrad)" filter="url(#softGlow)"/>
  <circle cx="185" cy="185" r="18" fill="url(#coreInner)" opacity="0.9"/>
</svg>`;
}

// ---------- движок: скорости и «дыхание» меняются плавно ----------

function _targets(s) {
  return {
    spin: 360 / s.spin,                       // град/с шестерни
    pulse: 1 / s.pulse,                       // ударов ядра в секунду
    pulseAmp: s.pulseScale - 1,
    breath: s.fx.indexOf('breathe') >= 0 ? 0.06 : 0,
    flicker: s.fx.indexOf('flicker') >= 0 ? 1 : 0,
  };
}

function _startEngine(el) {
  const svg = el.querySelector('svg');
  const q = c => Array.from(el.querySelectorAll('.' + c));
  // [элементы, во сколько раз быстрее шестерни, направление]
  const spins = [[q('spin-a'), 1], [q('spin-b'), -1 / 1.36], [q('spin-radar'), 4],
                 [q('spin-o1'), 6], [q('spin-o2'), -4], [q('spin-o3'), 3]];
  const angles = spins.map(() => 0);
  const core = q('pulse-core'), glow = q('pulse-glow');
  const st = el._reactor = { cur: null, target: null, ease: 0.4 };
  let last = performance.now(), pulsePh = 0, breathPh = 0, flickT = 0, flickV = 1;
  const wave = ph => 0.5 - 0.5 * Math.cos(2 * Math.PI * ph);

  function frame(now) {
    if (!el.isConnected || el._reactor !== st) return;
    const dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    const t = st.target;
    if (t) {
      if (!st.cur) st.cur = Object.assign({}, t);
      const c = st.cur, k = 1 - Math.exp(-dt / Math.max(0.05, st.ease));
      for (const key in t) c[key] += (t[key] - c[key]) * k;
      spins.forEach(([els, mul], i) => {
        angles[i] = (angles[i] + c.spin * mul * dt) % 360;
        els.forEach(e => { e.style.transform = 'rotate(' + angles[i].toFixed(2) + 'deg)'; });
      });
      pulsePh = (pulsePh + c.pulse * dt) % 1;
      breathPh = (breathPh + c.pulse / 1.4 * dt) % 1;
      const coreScale = 1 + c.pulseAmp * wave(pulsePh);
      core.forEach(e => { e.style.transform = 'scale(' + coreScale.toFixed(4) + ')'; });
      glow.forEach(e => { e.style.opacity = (0.75 + 0.25 * wave(pulsePh / 1.33)).toFixed(3); });
      svg.style.transform = 'scale(' + (1 + c.breath * wave(breathPh)).toFixed(4) + ')';
      flickT -= dt;
      if (flickT <= 0) {               // мерцание ошибки: случайные короткие провалы яркости
        flickT = 0.05 + Math.random() * 0.25;
        flickV = Math.random() < 0.3 ? 0.45 + Math.random() * 0.3 : 1;
      }
      svg.style.opacity = (1 - c.flicker * (1 - flickV)).toFixed(3);
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

function buildReactor(el) {
  el.innerHTML = _reactorSVG();
  _startEngine(el);
}

function applyReactorState(el, state, cfg) {
  cfg = cfg || reactorConfig();
  const s = cfg.states[state] || cfg.states.IDLE;
  const st = el.style;
  st.setProperty('--r-main', s.main);
  st.setProperty('--r-accent', s.accent);
  st.setProperty('--r-core', s.core);
  st.setProperty('--r-glow', s.glow);
  st.setProperty('--r-glow-size', s.glowSize + 'px');
  st.setProperty('--r-dark', cfg.dark);
  st.setProperty('--r-fade', cfg.fade + 's');
  if (el._reactor) {
    el._reactor.target = _targets(s);
    el._reactor.ease = cfg.fade * 0.6;   // экспонента: за fade скорость догоняет цель на ~80%
  }
  Object.keys(REACTOR_FX).forEach(fx => el.classList.toggle('fx-' + fx, s.fx.indexOf(fx) >= 0));
  return s;
}
