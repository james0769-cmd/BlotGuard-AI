import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SAMPLE_IMAGE = (
    ROOT
    / "sample_data"
    / "western_blots_dataset"
    / "real"
    / "real_img_00000.png"
)
SAMPLE_DATASET = ROOT / "sample_data" / "western_blots_dataset"
SMOKE_SCRIPT = ROOT / "scripts" / "smoke_detect.py"


def test_smoke_detect_mock_single_image_outputs_detector_contract():
    completed = subprocess.run(
        [
            sys.executable,
            str(SMOKE_SCRIPT),
            "--mode",
            "mock",
            "--image",
            str(SAMPLE_IMAGE),
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )

    payload = json.loads(completed.stdout)
    assert payload["mode"] == "mock"
    assert payload["sample_count"] == 1
    assert payload["results"][0]["sample_id"] == "real_img_00000.png"
    assert payload["results"][0]["model"]["is_mock"] is True
    assert 0 <= payload["results"][0]["score_generated"] <= 1


def test_smoke_detect_mock_dataset_writes_25_sample_baseline(tmp_path):
    output = tmp_path / "detector_mock_baseline.json"

    subprocess.run(
        [
            sys.executable,
            str(SMOKE_SCRIPT),
            "--mode",
            "mock",
            "--dataset",
            str(SAMPLE_DATASET),
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["mode"] == "mock"
    assert payload["sample_count"] == 25
    assert payload["summary"]["total"] == 25
    assert set(payload["summary_by_group"]) == {
        "real",
        "synth/cyclegan",
        "synth/ddpm",
        "synth/pix2pix",
        "synth/stylegan2ada",
    }
    assert len(payload["results"]) == 25
