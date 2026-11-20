import json

from voice.text_norm import apply_stress, load_stress


def test_apply_stress(tmp_path):
    f = tmp_path / "s.json"
    f.write_text(json.dumps({"кеша": "ке+ша", "плохо": "без плюса"}), encoding="utf-8")
    assert apply_stress("Кеша, привет. кеша!", str(f)) == "Ке+ша, привет. ке+ша!"
    assert "плохо" not in load_stress(str(f))
    assert apply_stress("текст", str(tmp_path / "нет.json")) == "текст"
