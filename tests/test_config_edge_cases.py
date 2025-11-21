"""Additional edge case tests for configuration system."""

import os
import tempfile
from pathlib import Path

import pytest

from config.settings import TalkSmithConfig


class TestConfigFinderEdgeCases:
    """Test configuration file discovery edge cases."""

    def test_config_file_priority_explicit_path(self):
        """Test explicit config_path has highest priority."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ini", delete=False
        ) as f1, tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f2:
            f1.write("[Models]\nwhisper_model = explicit\n")
            f2.write("[Models]\nwhisper_model = env-var\n")
            explicit_path = f1.name
            env_path = f2.name

        try:
            os.environ["TALKSMITH_CONFIG"] = env_path
            config = TalkSmithConfig(config_path=explicit_path)
            assert config.get("Models", "whisper_model") == "explicit"
        finally:
            del os.environ["TALKSMITH_CONFIG"]
            os.unlink(explicit_path)
            os.unlink(env_path)

    def test_config_finder_returns_default_when_none_exist(self):
        """Test config finder returns default path when no files exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                config = TalkSmithConfig()
                # Should use defaults even though file doesn't exist
                assert config.get("Models", "whisper_model") == "large-v3"
            finally:
                os.chdir(old_cwd)


class TestTypeConversionEdgeCases:
    """Test edge cases in type conversion methods."""

    def test_get_int_with_invalid_string(self):
        """Test get_int with non-numeric string returns fallback."""
        config = TalkSmithConfig()
        config.set("Test", "value", "not-a-number")
        result = config.get_int("Test", "value", fallback=99)
        assert result == 99

    def test_get_int_with_float_string(self):
        """Test get_int with float string returns fallback."""
        config = TalkSmithConfig()
        config.set("Test", "value", "42.7")
        result = config.get_int("Test", "value", fallback=0)
        assert result == 0  # int() raises ValueError on "42.7", so fallback is returned

    def test_get_float_with_invalid_string(self):
        """Test get_float with non-numeric string returns fallback."""
        config = TalkSmithConfig()
        config.set("Test", "value", "invalid")
        result = config.get_float("Test", "value", fallback=3.14)
        assert result == 3.14

    def test_get_bool_various_truthy_values(self):
        """Test get_bool recognizes various truthy values."""
        config = TalkSmithConfig()
        for value in [
            "true",
            "True",
            "TRUE",
            "yes",
            "Yes",
            "YES",
            "1",
            "on",
            "On",
            "ON",
        ]:
            config.set("Test", "bool", value)
            assert config.get_bool("Test", "bool") is True, f"Failed for: {value}"

    def test_get_bool_various_falsy_values(self):
        """Test get_bool recognizes various falsy values."""
        config = TalkSmithConfig()
        for value in [
            "false",
            "False",
            "FALSE",
            "no",
            "No",
            "0",
            "off",
            "anything-else",
        ]:
            config.set("Test", "bool", value)
            assert config.get_bool("Test", "bool") is False, f"Failed for: {value}"

    def test_get_list_with_empty_string(self):
        """Test get_list with empty string returns empty list."""
        config = TalkSmithConfig()
        config.set("Test", "list", "")
        result = config.get_list("Test", "list")
        assert result == []

    def test_get_list_with_custom_separator(self):
        """Test get_list with custom separator."""
        config = TalkSmithConfig()
        config.set("Test", "list", "a|b|c")
        result = config.get_list("Test", "list", separator="|")
        assert result == ["a", "b", "c"]

    def test_get_list_strips_whitespace(self):
        """Test get_list strips whitespace from items."""
        config = TalkSmithConfig()
        config.set("Test", "list", "a , b  ,  c")
        result = config.get_list("Test", "list")
        assert result == ["a", "b", "c"]

    def test_get_list_ignores_empty_items(self):
        """Test get_list ignores empty items."""
        config = TalkSmithConfig()
        config.set("Test", "list", "a,,b,,,c")
        result = config.get_list("Test", "list")
        assert result == ["a", "b", "c"]

    def test_get_path_with_none_value(self):
        """Test get_path returns None when value is None."""
        config = TalkSmithConfig()
        result = config.get_path("NonExistent", "key", fallback=None)
        assert result is None

    def test_get_path_expands_user_home(self):
        """Test get_path expands ~ to user home."""
        config = TalkSmithConfig()
        config.set("Test", "path", "~/test")
        result = config.get_path("Test", "path")
        assert "~" not in str(result)
        assert str(result).startswith(str(Path.home()))

    def test_get_path_makes_relative_absolute(self):
        """Test get_path converts relative to absolute."""
        config = TalkSmithConfig()
        config.set("Test", "path", "relative/path")
        result = config.get_path("Test", "path")
        assert result.is_absolute()

    def test_get_path_create_nested_dirs(self):
        """Test get_path can create nested directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TalkSmithConfig()
            nested_path = os.path.join(tmpdir, "a", "b", "c", "deep")
            config.set("Test", "path", nested_path)
            result = config.get_path("Test", "path", create=True)
            assert result.exists()
            assert result.is_dir()


class TestEnvironmentVariableEdgeCases:
    """Test edge cases with environment variable overrides."""

    def test_env_var_with_empty_string(self):
        """Test environment variable with empty string value."""
        config = TalkSmithConfig()
        try:
            os.environ["TALKSMITH_MODELS_WHISPER_MODEL"] = ""
            result = config.get("Models", "whisper_model")
            assert result == ""
        finally:
            del os.environ["TALKSMITH_MODELS_WHISPER_MODEL"]

    def test_env_var_with_special_characters(self):
        """Test environment variable with special characters."""
        config = TalkSmithConfig()
        try:
            os.environ["TALKSMITH_PATHS_INPUT_DIR"] = "/path/with spaces/and-dashes"
            result = config.get("Paths", "input_dir")
            assert result == "/path/with spaces/and-dashes"
        finally:
            del os.environ["TALKSMITH_PATHS_INPUT_DIR"]

    def test_multiple_env_vars_override(self):
        """Test multiple environment variables can override config."""
        config = TalkSmithConfig()
        try:
            os.environ["TALKSMITH_MODELS_WHISPER_MODEL"] = "tiny"
            os.environ["TALKSMITH_MODELS_BATCH_SIZE"] = "32"
            os.environ["TALKSMITH_DIARIZATION_MODE"] = "off"

            assert config.get("Models", "whisper_model") == "tiny"
            assert config.get_int("Models", "batch_size") == 32
            assert config.get("Diarization", "mode") == "off"
        finally:
            for key in [
                "TALKSMITH_MODELS_WHISPER_MODEL",
                "TALKSMITH_MODELS_BATCH_SIZE",
                "TALKSMITH_DIARIZATION_MODE",
            ]:
                if key in os.environ:
                    del os.environ[key]


class TestConfigurationDefaults:
    """Test default configuration values are correct."""

    def test_all_default_sections_present(self):
        """Test all expected default sections are present."""
        config = TalkSmithConfig()
        expected_sections = [
            "Paths",
            "Models",
            "Diarization",
            "Export",
            "Processing",
            "Logging",
        ]

        for section in expected_sections:
            assert config.parser.has_section(section), f"Missing default section: {section}"

    def test_default_models_section(self):
        """Test default Models section values."""
        config = TalkSmithConfig()
        assert config.get("Models", "whisper_model") == "large-v3"
        assert config.get("Models", "whisper_device") == "auto"
        assert config.get("Models", "compute_type") == "float16"
        assert config.get_int("Models", "batch_size") == 16
        assert config.get_int("Models", "num_workers") == 4

    def test_default_diarization_section(self):
        """Test default Diarization section values."""
        config = TalkSmithConfig()
        assert config.get("Diarization", "mode") == "whisperx"
        assert config.get_float("Diarization", "vad_threshold") == 0.5
        assert config.get_int("Diarization", "min_speakers") == 1
        assert config.get_int("Diarization", "max_speakers") == 10
        assert config.get_float("Diarization", "min_segment_length") == 0.5

    def test_default_export_section(self):
        """Test default Export section values."""
        config = TalkSmithConfig()
        formats = config.get_list("Export", "formats")
        assert "txt" in formats
        assert "json" in formats
        assert "srt" in formats
        assert config.get_bool("Export", "include_timestamps") is True
        assert config.get_bool("Export", "include_confidence") is True
        assert config.get_bool("Export", "word_level") is False

    def test_default_processing_section(self):
        """Test default Processing section values."""
        config = TalkSmithConfig()
        assert config.get_bool("Processing", "denoise") is False
        assert config.get_bool("Processing", "normalize_audio") is True
        assert config.get_bool("Processing", "trim_silence") is False
        assert config.get_int("Processing", "sample_rate") == 16000

    def test_default_logging_section(self):
        """Test default Logging section values."""
        config = TalkSmithConfig()
        assert config.get("Logging", "level") == "INFO"
        assert config.get("Logging", "format") == "json"
        assert config.get_bool("Logging", "console_output") is True


class TestConfigurationErrorHandling:
    """Test error handling and edge cases."""

    def test_set_creates_section_if_not_exists(self):
        """Test set creates section if it doesn't exist."""
        config = TalkSmithConfig()
        config.set("NewSection", "new_key", "new_value")

        assert config.parser.has_section("NewSection")
        assert config.get("NewSection", "new_key") == "new_value"

    def test_get_with_none_fallback(self):
        """Test get with None fallback returns None."""
        config = TalkSmithConfig()
        result = config.get("NonExistent", "key", fallback=None)
        assert result is None

    def test_save_creates_parent_directory(self):
        """Test save creates parent directories if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "nested", "dir", "config.ini")
            config = TalkSmithConfig()
            config.set("Models", "whisper_model", "test")
            config.save(config_path)

            assert os.path.exists(config_path)
            # Verify it can be loaded
            config2 = TalkSmithConfig(config_path)
            assert config2.get("Models", "whisper_model") == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
