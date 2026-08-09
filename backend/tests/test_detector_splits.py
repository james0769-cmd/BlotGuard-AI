from pathlib import Path

from scripts.build_detector_splits import BKTree, family_id


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
