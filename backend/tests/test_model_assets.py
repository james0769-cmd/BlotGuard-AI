import csv
import hashlib
import json
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


def test_detector_golden_set_is_complete_and_stable():
    sample_root = PROJECT_ROOT / "sample_data" / "western_blots_dataset"
    with (sample_root / "sample_manifest.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        manifest = list(csv.DictReader(stream))
    with (sample_root / "detector_golden.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        csv_results = list(csv.DictReader(stream))
    json_results = json.loads(
        (sample_root / "detector_golden.json").read_text(encoding="utf-8")
    )

    assert len(manifest) == len(csv_results) == len(json_results) == 25
    assert [row["sample_path"] for row in csv_results] == [
        row["sample_path"] for row in json_results
    ]
    for sample in manifest:
        path = PROJECT_ROOT / sample["sample_path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sample["sample_sha256"]

    expected_model_version = "detector-sam-vit-b-lora-r8-all-img512-51265aec"
    expected_weight_sha256 = (
        "51265aecd96858feeead19cc47f9bd3dc0af3fa7d793582482a9287a153c3e25"
    )
    assert all(
        row["model_version"] == expected_model_version
        and row["weight_sha256"] == expected_weight_sha256
        for row in json_results
    )
    assert all(
        row["model_version"] == expected_model_version
        and row["weight_sha256"] == expected_weight_sha256
        for row in csv_results
    )

    correct = [
        row
        for row in json_results
        if row["prediction"] == row["expected_source_class"]
    ]
    assert len(correct) == 23
    assert sum(
        row["generator"] == "ddpm" and row["prediction"] == "generated"
        for row in json_results
    ) == 1
