"""Unit tests for configuration system."""

import os
import tempfile
from pathlib import Path
import pytest

from config.settings import TalkSmithConfig, get_config, create_default_config


class TestTalkSmithConfig:
    """Test configuration loading and access."""

    def test_load_defaults_when_no_file(self):
        """Test that defaults are loaded when no config file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "nonexistent.ini")
            config = TalkSmithConfig(config_path)

            assert config.get("Models", "whisper_model") == "large-v3"
            assert config.get("Paths", "input_dir") == "data/inputs"

    def test_load_from_file(self):
        """Test loading configuration from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            f.write("[Models]\n")
            f.write("whisper_model = medium.en\n")
            f.write("[Paths]\n")
            f.write("input_dir = /custom/path\n")
            config_path = f.name

        try:
            config = TalkSmithConfig(config_path)
            assert config.get("Models", "whisper_model") == "medium.en"
            assert config.get("Paths", "input_dir") == "/custom/path"
        finally:
            os.unlink(config_path)

    def test_env_var_override(self):
        """Test that environment variables override config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            f.write("[Models]\n")
            f.write("whisper_model = large-v3\n")
            config_path = f.name

        try:
            os.environ["TALKSMITH_MODELS_WHISPER_MODEL"] = "tiny.en"
            config = TalkSmithConfig(config_path)

            assert config.get("Models", "whisper_model") == "tiny.en"
        finally:
            del os.environ["TALKSMITH_MODELS_WHISPER_MODEL"]
            os.unlink(config_path)

    def test_get_int(self):
        """Test getting integer values."""
        config = TalkSmithConfig()
        batch_size = config.get_int("Models", "batch_size")
        assert isinstance(batch_size, int)
        assert batch_size == 16

    def test_get_float(self):
        """Test getting float values."""
        config = TalkSmithConfig()
        threshold = config.get_float("Diarization", "vad_threshold")
        assert isinstance(threshold, float)
        assert threshold == 0.5

    def test_get_bool(self):
        """Test getting boolean values."""
        config = TalkSmithConfig()
        assert config.get_bool("Export", "include_timestamps") is True
        assert config.get_bool("Processing", "denoise") is False

    def test_get_list(self):
        """Test getting list values."""
        config = TalkSmithConfig()
        formats = config.get_list("Export", "formats")
        assert isinstance(formats, list)
        assert "txt" in formats
        assert "json" in formats
        assert "srt" in formats

    def test_get_path(self):
        """Test getting path values."""
        config = TalkSmithConfig()
        input_dir = config.get_path("Paths", "input_dir")
        assert isinstance(input_dir, Path)

    def test_get_path_create(self):
        """Test creating directory when getting path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TalkSmithConfig()
            config.set("Paths", "test_dir", os.path.join(tmpdir, "new_dir"))

            new_path = config.get_path("Paths", "test_dir", create=True)
            assert new_path.exists()
            assert new_path.is_dir()

    def test_set_and_save(self):
        """Test setting values and saving to file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            config_path = f.name

        try:
            config = TalkSmithConfig()
            config.set("Models", "whisper_model", "base.en")
            config.save(config_path)

            # Load again and verify
            config2 = TalkSmithConfig(config_path)
            assert config2.get("Models", "whisper_model") == "base.en"
        finally:
            if os.path.exists(config_path):
                os.unlink(config_path)

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = TalkSmithConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert "Models" in config_dict
        assert "Paths" in config_dict
        assert config_dict["Models"]["whisper_model"] == "large-v3"

    def test_fallback_values(self):
        """Test fallback values when key doesn't exist."""
        config = TalkSmithConfig()

        assert config.get("NonExistent", "key", fallback="default") == "default"
        assert config.get_int("NonExistent", "key", fallback=42) == 42
        assert config.get_float("NonExistent", "key", fallback=3.14) == 3.14
        assert config.get_bool("NonExistent", "key", fallback=True) is True
        assert config.get_list("NonExistent", "key", fallback=["a", "b"]) == ["a", "b"]


class TestGlobalConfig:
    """Test global configuration singleton."""

    def test_get_config_singleton(self):
        """Test that get_config returns singleton."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_get_config_reload(self):
        """Test reloading configuration."""
        config1 = get_config()
        config2 = get_config(reload=True)
        # Should be different instances after reload
        assert config1 is not config2


class TestConfigCreation:
    """Test configuration file creation."""

    def test_create_default_config(self):
        """Test creating default config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "settings.ini")
            create_default_config(config_path)

            assert os.path.exists(config_path)

            # Verify it can be loaded
            config = TalkSmithConfig(config_path)
            assert config.get("Models", "whisper_model") == "large-v3"


class TestConfigFinder:
    """Test configuration file discovery."""

    def test_talksmith_config_env_var(self):
        """Test TALKSMITH_CONFIG environment variable."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
            f.write("[Models]\n")
            f.write("whisper_model = from-env\n")
            config_path = f.name

        try:
            os.environ["TALKSMITH_CONFIG"] = config_path
            config = TalkSmithConfig()
            assert config.get("Models", "whisper_model") == "from-env"
        finally:
            del os.environ["TALKSMITH_CONFIG"]
            os.unlink(config_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
