import csv
import hashlib
import json
from pathlib import Path

from scripts.build_detector_splits import BKTree, family_id


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_family_id_binds_generators_by_numeric_suffix():
    assert family_id(Path("real_img_00042.png")) == "western-blot-00042"
    assert family_id(Path("ddpm_img_00042.png")) == "western-blot-00042"


def test_bk_tree_finds_hashes_within_hamming_distance():
    tree = BKTree()
    tree.add(0b0000)
    tree.add(0b1111)

    assert tree.has_within(0b0001, 1)
    assert tree.has_within(0b1110, 1)
    assert not tree.has_within(0b0011, 1)


def test_calibration_predictions_and_blocked_result_are_frozen():
    split_root = PROJECT_ROOT / "sample_data" / "western_blots_dataset" / "splits"
    manifest_path = split_root / "detector_calibration_manifest.csv"
    predictions_path = split_root / "detector_calibration_predictions.csv"
    result_path = split_root / "detector_calibration_result.json"

    with manifest_path.open(newline="", encoding="utf-8") as stream:
        manifest = list(csv.DictReader(stream))
    with predictions_path.open(newline="", encoding="utf-8") as stream:
        predictions = list(csv.DictReader(stream))
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert len(manifest) == len(predictions) == 2500
    assert [row["sample_path"] for row in predictions] == [
        row["sample_path"] for row in manifest
    ]
    assert [row["sample_sha256"] for row in predictions] == [
        row["sample_sha256"] for row in manifest
    ]
    assert hashlib.sha256(predictions_path.read_bytes()).hexdigest() == (
        result["source_predictions_sha256"]
    )
    assert result["status"] == "blocked_model_quality"
    assert result["deployable"] is False
    assert result["test_evaluation_authorized"] is False
    assert result["acceptance"]["ddpm_recall_gte_0_80"] is False
    assert result["acceptance"]["pix2pix_recall_gte_0_90"] is False
    assert not (split_root / "detector_test_predictions.csv").exists()
