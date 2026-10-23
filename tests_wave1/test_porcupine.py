"""Тест Porcupine: слушаем 10 секунд, ждём слово 'computer'."""
import sys
from _common import load

mod = load("wake_word")
try:
    det = mod.WakeWordDetector()
except Exception as e:
    print(f"❌ Porcupine не стартовал: {e}")
    sys.exit(1)

print("Скажи «computer» (у тебя 10 секунд)...")
heard = det.wait_for_wake(timeout=10)
det.close()
if heard:
    print("УСЛЫШАЛ!")
    sys.exit(0)
print("❌ За 10 секунд ничего не услышал")
sys.exit(1)
