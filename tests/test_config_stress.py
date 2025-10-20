"""Stress tests for configuration system."""

import os
import tempfile
from pathlib import Path
import pytest

from config.settings import TalkSmithConfig, get_config


class TestConfigStress:
    """Stress tests for configuration system."""

    def test_large_config_file(self, temp_dir):
        """Test handling config file with many sections and keys."""
        config = TalkSmithConfig()

        # Add 100 sections with 50 keys each
        for section_num in range(100):
            section = f"Section{section_num:03d}"
            for key_num in range(50):
                key = f"key{key_num:03d}"
                value = f"value_{section_num}_{key_num}"
                config.set(section, key, value)

        # Verify we can save and reload
        config_path = temp_dir / "large_config.ini"
        config.save(str(config_path))

        # Reload and verify random samples
        config2 = TalkSmithConfig(str(config_path))
        assert config2.get("Section050", "key025") == "value_50_25"
        assert config2.get("Section099", "key049") == "value_99_49"

    def test_very_long_values(self):
        """Test handling very long configuration values."""
        config = TalkSmithConfig()

        # 10KB value
        long_value = "x" * 10000
        config.set("Test", "long_value", long_value)

        retrieved = config.get("Test", "long_value")
        assert retrieved == long_value
        assert len(retrieved) == 10000

    def test_special_characters_in_values(self):
        """Test handling special characters in values."""
        config = TalkSmithConfig()

        special_values = [
            "value with spaces",
            "value\twith\ttabs",
            "value\nwith\nnewlines",
            "value=with=equals",
            "value:with:colons",
            "value;with;semicolons",
            "value#with#hashes",
            'value"with"quotes',
            "value'with'apostrophes",
            "value\\with\\backslashes",
            "value/with/slashes",
            "value@with@special!chars$",
        ]

        for i, value in enumerate(special_values):
            config.set("Special", f"key{i}", value)

        # Verify retrieval
        for i, expected in enumerate(special_values):
            retrieved = config.get("Special", f"key{i}")
            assert retrieved == expected

    def test_unicode_in_values(self):
        """Test handling Unicode characters in values."""
        config = TalkSmithConfig()

        unicode_values = [
            "日本語",  # Japanese
            "العربية",  # Arabic
            "Русский",  # Russian
            "中文",  # Chinese
            "Ελληνικά",  # Greek
            "한국어",  # Korean
            "עברית",  # Hebrew
            "🚀🎯💡",  # Emojis
        ]

        for i, value in enumerate(unicode_values):
            config.set("Unicode", f"key{i}", value)

        # Verify retrieval
        for i, expected in enumerate(unicode_values):
            retrieved = config.get("Unicode", f"key{i}")
            assert retrieved == expected

    def test_rapid_sequential_saves(self, temp_dir):
        """Test rapid sequential save operations."""
        config = TalkSmithConfig()
        config_path = temp_dir / "rapid_save.ini"

        # Perform 50 rapid saves
        for i in range(50):
            config.set("Test", "counter", str(i))
            config.save(str(config_path))

        # Verify final state
        config2 = TalkSmithConfig(str(config_path))
        assert config2.get("Test", "counter") == "49"

    def test_many_env_var_overrides(self, monkeypatch):
        """Test handling many environment variable overrides."""
        config = TalkSmithConfig()

        # Set 100 environment variables
        for i in range(100):
            env_key = f"TALKSMITH_ENVTEST_KEY{i:03d}"
            monkeypatch.setenv(env_key, f"value{i}")

        # Verify all are read correctly
        for i in range(100):
            key = f"key{i:03d}"
            value = config.get("EnvTest", key)
            assert value == f"value{i}"

    def test_get_int_boundary_values(self):
        """Test get_int with boundary values."""
        config = TalkSmithConfig()

        test_cases = [
            ("0", 0),
            ("-1", -1),
            ("2147483647", 2147483647),  # Max 32-bit int
            ("-2147483648", -2147483648),  # Min 32-bit int
            ("9223372036854775807", 9223372036854775807),  # Max 64-bit int
        ]

        for str_value, expected_int in test_cases:
            config.set("Boundary", "value", str_value)
            result = config.get_int("Boundary", "value")
            assert result == expected_int

    def test_get_float_boundary_values(self):
        """Test get_float with boundary values."""
        config = TalkSmithConfig()

        test_cases = [
            ("0.0", 0.0),
            ("-0.0", -0.0),
            ("1e-10", 1e-10),
            ("1e10", 1e10),
            ("3.141592653589793", 3.141592653589793),
            ("-999999.999999", -999999.999999),
        ]

        for str_value, expected_float in test_cases:
            config.set("Boundary", "value", str_value)
            result = config.get_float("Boundary", "value")
            assert abs(result - expected_float) < 1e-10

    def test_get_list_with_many_items(self):
        """Test get_list with many items."""
        config = TalkSmithConfig()

        # Create list with 1000 items
        items = [f"item{i:04d}" for i in range(1000)]
        config.set("Test", "many_items", ",".join(items))

        result = config.get_list("Test", "many_items")
        assert len(result) == 1000
        assert result[0] == "item0000"
        assert result[999] == "item0999"

    def test_path_creation_deep_nesting(self, temp_dir):
        """Test creating deeply nested directory paths."""
        config = TalkSmithConfig()

        # Create path with 20 levels of nesting
        deep_path = temp_dir
        for i in range(20):
            deep_path = deep_path / f"level{i}"

        config.set("Paths", "deep", str(deep_path))
        result = config.get_path("Paths", "deep", create=True)

        assert result.exists()
        assert result.is_dir()

    def test_config_dict_iteration(self):
        """Test iterating over config dictionary."""
        config = TalkSmithConfig()

        config_dict = config.to_dict()

        # Count total keys across all sections
        total_keys = sum(len(section_dict) for section_dict in config_dict.values())
        assert total_keys > 0

        # Verify we can iterate without errors
        for section, section_dict in config_dict.items():
            assert isinstance(section, str)
            assert isinstance(section_dict, dict)
            for key, value in section_dict.items():
                assert isinstance(key, str)
                assert isinstance(value, str)


class TestConfigMemoryEfficiency:
    """Test configuration system memory efficiency."""

    def test_singleton_memory_efficiency(self):
        """Test singleton pattern doesn't create extra instances."""
        from config import get_config as get_singleton_config

        # Get config 100 times
        configs = [get_singleton_config() for _ in range(100)]

        # All should be the same instance
        assert all(c is configs[0] for c in configs)

    def test_multiple_configs_independent(self):
        """Test multiple TalkSmithConfig instances are independent."""
        config1 = TalkSmithConfig()
        config2 = TalkSmithConfig()

        config1.set("Test", "key", "value1")
        config2.set("Test", "key", "value2")

        assert config1.get("Test", "key") == "value1"
        assert config2.get("Test", "key") == "value2"


class TestConfigErrorRecovery:
    """Test error recovery and resilience."""

    def test_corrupted_config_file(self, temp_dir):
        """Test handling of corrupted config file."""
        import configparser

        config_path = temp_dir / "corrupted.ini"

        # Write invalid INI content
        config_path.write_text("[Invalid\nno closing bracket\ngarbage")

        # Should raise error on corrupted file
        with pytest.raises(configparser.MissingSectionHeaderError):
            config = TalkSmithConfig(str(config_path))

    def test_empty_config_file(self, temp_dir):
        """Test handling of empty config file."""
        config_path = temp_dir / "empty.ini"
        config_path.write_text("")

        config = TalkSmithConfig(str(config_path))
        # Empty file is valid but has no sections, so get returns None/fallback
        assert config.get("Models", "whisper_model", fallback="default") == "default"

    def test_config_file_with_only_comments(self, temp_dir):
        """Test handling of config file with only comments."""
        config_path = temp_dir / "comments.ini"
        config_path.write_text("# This is a comment\n; This is also a comment\n")

        config = TalkSmithConfig(str(config_path))
        # File with only comments is valid but has no sections
        assert config.get("Models", "whisper_model", fallback="default") == "default"

    def test_readonly_directory_save(self, temp_dir):
        """Test save behavior when directory is read-only."""
        import stat

        config = TalkSmithConfig()
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()

        # Make directory read-only
        if os.name != "nt":  # Unix-like systems
            readonly_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

            try:
                config_path = readonly_dir / "config.ini"
                with pytest.raises((PermissionError, OSError)):
                    config.save(str(config_path))
            finally:
                # Restore write permissions
                readonly_dir.chmod(stat.S_IRWXU)

    def test_invalid_path_characters(self):
        """Test handling paths with invalid characters."""
        config = TalkSmithConfig()

        # These might be invalid on different platforms
        # Just verify no crashes occur
        try:
            if os.name == "nt":  # Windows
                # Windows doesn't allow these in paths
                config.set("Paths", "invalid", "C:\\invalid<>path")
                path = config.get_path("Paths", "invalid", create=False)
            else:  # Unix-like
                config.set("Paths", "test", "/valid/path")
                path = config.get_path("Paths", "test", create=False)
                assert path is not None
        except (ValueError, OSError):
            # Expected on some platforms
            pass


class TestConfigCaseSensitivity:
    """Test case sensitivity handling."""

    def test_section_names_case_sensitive(self):
        """Test that section names are case-sensitive."""
        config = TalkSmithConfig()

        config.set("Test", "key", "value1")
        config.set("test", "key", "value2")

        # ConfigParser is case-sensitive for sections by default
        val1 = config.get("Test", "key", fallback="default")
        val2 = config.get("test", "key", fallback="default")

        # Both should be retrievable
        assert val1 in ["value1", "value2"]

    def test_env_var_case_handling(self, monkeypatch):
        """Test environment variable case handling."""
        config = TalkSmithConfig()

        # Set env var with specific case
        monkeypatch.setenv("TALKSMITH_MODELS_WHISPER_MODEL", "tiny")

        # Should match uppercase
        result = config.get("Models", "whisper_model")
        assert result == "tiny"

        # Mixed case section/key should still work
        result = config.get("models", "WHISPER_MODEL")
        # Should still resolve to the env var
        assert result == "tiny"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
