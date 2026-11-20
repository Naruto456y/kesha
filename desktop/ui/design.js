/* Дизайн интерфейса Кеши: настройки -> CSS-переменные. Общий для index.html и design.html. */
const DESIGN_DEFAULTS = {
  bg: '#4B3FBF',          // фон окна
  accent: '#00E5FF',      // основной неон
  panel: '#0A1E3C',       // цвет подложки панелей
  radius: 20,             // скругление панелей, px
  titleSize: 40,          // размер главного заголовка, px
  sideWidth: 1.25,        // ширина боковых панелей (fr; центр = 2)
};

function _hexToRgb(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex || '');
  if (!m) return null;
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function _lighten(rgb, k) {
  return '#' + rgb.map(c => Math.round(c + (255 - c) * k).toString(16).padStart(2, '0')).join('');
}

function applyDesign(d, root) {
  d = Object.assign({}, DESIGN_DEFAULTS, d || {});
  const st = (root || document.documentElement).style;
  const acc = _hexToRgb(d.accent), pan = _hexToRgb(d.panel);
  st.setProperty('--bg', d.bg);
  if (acc) {
    st.setProperty('--cyan', d.accent);
    st.setProperty('--cyan-rgb', acc.join(','));
    st.setProperty('--cyan-soft', _lighten(acc, 0.5));
  }
  if (pan) st.setProperty('--panel-rgb', pan.join(','));
  st.setProperty('--radius', d.radius + 'px');
  st.setProperty('--title-size', d.titleSize + 'px');
  st.setProperty('--side-l', d.sideWidth + 'fr');
  st.setProperty('--side-r', d.sideWidth + 'fr');
  return d;
}
