"""Диагностика GigaAM: версии, ffmpeg, импорт и (опционально) распознавание.

Только проверка окружения:   python diag_gigaam.py
Плюс загрузка модели и тест: python diag_gigaam.py my_voice.wav [v3_ctc]
"""
import importlib.metadata as md
import platform
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REQUIRED = [
    "gigaam", "torch", "torchaudio", "numpy", "sentencepiece",
    "hydra-core", "omegaconf", "soundfile", "tqdm",
]
OPTIONAL = ["onnx", "onnxruntime", "pydub"]


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def show_system() -> None:
    section("Система")
    print("Python  :", sys.version.split()[0], f"({platform.architecture()[0]})")
    print("Путь    :", sys.executable)
    print("ОС      :", platform.platform())


def show_versions() -> None:
    section("Версии пакетов")
    for name in REQUIRED + OPTIONAL:
        required = name in REQUIRED
        try:
            print(f"✅ {name:15} {md.version(name)}")
        except md.PackageNotFoundError:
            if required:
                print(f"❌ {name:15} НЕ УСТАНОВЛЕН")
            else:
                print(f"➖ {name:15} нет (для проверки не нужен)")


def run_pip_check() -> None:
    section("pip check (конфликты зависимостей)")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print((r.stdout + r.stderr).strip() or "✅ конфликтов нет")


def show_ffmpeg() -> None:
    section("ffmpeg")
    path = shutil.which("ffmpeg")
    if not path:
        print("❌ ffmpeg не найден в PATH. GigaAM вызывает его для ЛЮБОГО аудио, даже WAV.")
        return
    r = subprocess.run(
        [path, "-version"], capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    first = r.stdout.splitlines()[0] if r.stdout else "?"
    print(f"✅ {path}\n   {first}")


def show_torch() -> None:
    section("torch / GPU")
    try:
        import torch
    except Exception:
        print("❌ torch не импортируется:")
        traceback.print_exc()
        return
    print("torch          :", torch.__version__)
    print("CUDA доступна  :", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("видеокарта     :", torch.cuda.get_device_name(0))


def import_gigaam():
    section("import gigaam")
    try:
        import gigaam
    except Exception:
        print("❌ импорт упал:")
        traceback.print_exc()
        return None
    print("✅ импорт OK:", gigaam.__file__)
    names = getattr(gigaam, "_MODEL_NAMES", None) or list(
        getattr(gigaam, "_MODEL_HASHES", {})
    )
    print("модели:", names)
    return gigaam


def test_transcribe(gigaam, audio: Path, model_name: str) -> None:
    section(f"Распознавание: {audio.name} / {model_name}")
    try:
        t0 = time.perf_counter()
        model = gigaam.load_model(model_name)
        print(f"✅ модель загружена за {time.perf_counter() - t0:.1f} с")
        t0 = time.perf_counter()
        result = model.transcribe(str(audio))
        elapsed = time.perf_counter() - t0
    except Exception as exc:
        print("❌ упало:")
        traceback.print_exc()
        if "weights_only" in str(exc) or "npickl" in str(exc):
            print("\n💡 Старый gigaam (0.1.0) + новый torch: нужна версия с GitHub.")
        return
    print(f"⏱️  распознавание: {elapsed:.2f} с")
    print("📝 Результат:", getattr(result, "text", result))


def main() -> None:
    show_system()
    show_versions()
    run_pip_check()
    show_ffmpeg()
    show_torch()
    gigaam = import_gigaam()

    if gigaam is not None and len(sys.argv) > 1:
        audio = Path(sys.argv[1])
        model_name = sys.argv[2] if len(sys.argv) > 2 else "v3_ctc"
        if audio.exists():
            test_transcribe(gigaam, audio, model_name)
        else:
            print(f"\n❌ Файл не найден: {audio}")


if __name__ == "__main__":
    main()