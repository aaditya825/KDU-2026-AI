from pathlib import Path


def test_seed_config_exists() -> None:
    assert Path("configs/config.yaml").exists()


def test_seed_pricing_exists() -> None:
    assert Path("configs/pricing.yaml").exists()


def test_seed_prompts_exist() -> None:
    assert Path("prompts/faq/v1.yaml").exists()
    assert Path("prompts/booking/v1.yaml").exists()
    assert Path("prompts/complaint/v1.yaml").exists()
    assert Path("prompts/base/v1.yaml").exists()

