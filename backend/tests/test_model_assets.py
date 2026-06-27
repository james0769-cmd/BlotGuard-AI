import hashlib
from pathlib import Path

import yaml

from backend.blotguard.core.config import PROJECT_ROOT, load_runtime_config


def test_manifest_matches_default_config():
    manifest_path = PROJECT_ROOT / "models" / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    config = load_runtime_config()
    weights_root = PROJECT_ROOT / manifest["weights_root"]

    assert config.detect.sam_checkpoint == (
        weights_root / manifest["artifacts"]["sam_vit_b"]["path"]
    )
    assert config.detect.lora_weight == (
        weights_root / manifest["artifacts"]["detector_lora"]["path"]
    )
    assert config.segment.lora_weight == (
        weights_root / manifest["artifacts"]["localizer_lora"]["path"]
    )


def test_smoke_fixture_is_stable():
    fixture = PROJECT_ROOT / "tests" / "fixtures" / "western_blot_sample.png"

    assert fixture.is_file()
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == (
        "cfc702b120ef31b50e3a2ba190ddd1bd9990b98b6bbc5f5b0446a766b8465723"
    )
