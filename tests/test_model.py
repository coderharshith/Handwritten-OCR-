"""Tests for model loading, CPU detection, offline mode."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import DEVICE, MODEL_PATH, apply_offline_env
from app.model import TrOCRModel
from app.errors import ModelNotFoundError
from app.utils import get_system_info


def test_cpu_device() -> None:
    """Test CPU device configuration."""
    assert DEVICE == "cpu"


def test_model_singleton() -> None:
    """Test model singleton pattern."""
    assert TrOCRModel() is TrOCRModel()


def test_get_instance() -> None:
    """Test get_instance returns TrOCRModel."""
    instance = TrOCRModel.get_instance()
    assert isinstance(instance, TrOCRModel)


def test_model_not_found_error() -> None:
    """Test loading from non-existent path raises error."""
    model = TrOCRModel()
    # Reset singleton state for this test
    original_loaded = TrOCRModel._loaded
    TrOCRModel._loaded = False
    try:
        with pytest.raises(ModelNotFoundError):
            model.load(model_path="invalid/path/that/does/not/exist")
    finally:
        TrOCRModel._loaded = original_loaded


def test_system_info() -> None:
    """Test get_system_info dictionary format."""
    info = get_system_info()
    assert isinstance(info, dict)
    for key in ["device", "gpu_status", "offline_mode", "model_name", "python_version", "torch_version"]:
        assert key in info


def test_offline_env_vars() -> None:
    """Test apply_offline_env sets correct environment variables."""
    apply_offline_env()
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
    assert os.environ.get("TRANSFORMERS_OFFLINE") == "1"
