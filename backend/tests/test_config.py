from backend.blotguard.core.config import PROJECT_ROOT, load_runtime_config


def test_default_config_resolves_from_project_root():
    config = load_runtime_config()

    assert config.project_root == PROJECT_ROOT
    assert config.detect.code_dir == PROJECT_ROOT / "models" / "source"
    assert config.detect.sam_checkpoint == (
        PROJECT_ROOT / "models" / "weights" / "sam_vit_b_01ec64.pth"
    )
    assert config.detect.image_size == 512
    assert config.detect.lora_layers == (0, 1, 2, 3, 4, 5)
    assert config.segment.image_size == 1024
    assert config.segment.lora_layers is None
    assert config.segment.code_dir == PROJECT_ROOT / "models" / "source"
