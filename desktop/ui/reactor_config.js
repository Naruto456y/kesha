// Конфиг реактора из редактора (кнопка «Копировать конфиг»). null — цвета по умолчанию из reactor.js.
window.REACTOR_CONFIG = {
  "dark": "#1A1A1A",
  "fade": 0.7,
  "states": {
    "IDLE": {
      "main": "#00E5FF", "accent": "#7FFFFF", "core": "#DFFFFF", "glow": "#00E5FF",
      "glowSize": 24, "spin": 22, "pulse": 1.8, "pulseScale": 1.06, "fx": []
    },
    "WAKE": {
      "main": "#FFFFFF", "accent": "#CFFFFF", "core": "#FFFFFF", "glow": "#FFFFFF",
      "glowSize": 44, "spin": 9.5, "pulse": 0.8, "pulseScale": 1.12, "fx": ["ripple", "breathe"]
    },
    "LISTENING": {
      "main": "#00FFAA", "accent": "#9CFFD8", "core": "#E6FFF5", "glow": "#00FFAA",
      "glowSize": 40, "spin": 12, "pulse": 0.9, "pulseScale": 1.1, "fx": ["ripple", "breathe", "sparks"]
    },
    "THINKING": {
      "main": "#FFC400", "accent": "#FFE27A", "core": "#FFF6D6", "glow": "#FFC400",
      "glowSize": 36, "spin": 7, "pulse": 1.2, "pulseScale": 1.05, "fx": ["radar", "orbit"]
    },
    "SPEAKING": {
      "main": "#3D8BFF", "accent": "#9CC8FF", "core": "#E3F0FF", "glow": "#3D8BFF",
      "glowSize": 50, "spin": 11.5, "pulse": 0.5, "pulseScale": 1.08, "fx": ["eq", "breathe", "sparks"]
    },
    "ERROR": {
      "main": "#FF3355", "accent": "#FF8FA2", "core": "#FFE0E6", "glow": "#FF3355",
      "glowSize": 40, "spin": 30, "pulse": 1.4, "pulseScale": 1.04, "fx": ["flicker", "sparks"]
    }
  }
};
