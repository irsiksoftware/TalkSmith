"""Tests for config module imports and public API."""

import pytest
from pathlib import Path


class TestConfigModuleImports:
    """Test that config module exports work correctly."""

    def test_import_from_config_module(self):
        """Test importing from config module."""
        from config import get_config, create_default_config, TalkSmithConfig

        assert callable(get_config)
        assert callable(create_default_config)
        assert TalkSmithConfig is not None

    def test_get_config_works_from_module_import(self):
        """Test get_config works when imported from module."""
        from config import get_config

        config = get_config()
        assert config is not None
        assert config.get("Models", "whisper_model") is not None

    def test_create_default_config_from_module(self, temp_dir):
        """Test create_default_config works from module import."""
        from config import create_default_config

        config_path = temp_dir / "test_settings.ini"
        create_default_config(str(config_path))

        assert config_path.exists()

    def test_all_exports_present(self):
        """Test __all__ exports are correct."""
        import config

        assert hasattr(config, "__all__")
        assert "get_config" in config.__all__
        assert "create_default_config" in config.__all__
        assert "TalkSmithConfig" in config.__all__


class TestConfigCLIExecution:
    """Test config module CLI execution."""

    def test_settings_module_cli_creates_default_config(self, temp_dir, monkeypatch):
        """Test running settings.py as script creates config file."""
        import sys
        import subprocess

        config_path = temp_dir / "cli_test_settings.ini"

        # Run the settings module as a script
        result = subprocess.run(
            [sys.executable, "-m", "config.settings", str(config_path)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert config_path.exists()
        assert "Created default configuration" in result.stdout

    def test_settings_module_cli_default_path(self, temp_dir, monkeypatch):
        """Test running settings.py without args uses default path."""
        import sys
        import subprocess
        import os

        # Change to temp directory
        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            # Add current working directory to PYTHONPATH
            env = os.environ.copy()
            env["PYTHONPATH"] = old_cwd
            result = subprocess.run(
                [sys.executable, "-m", "config.settings"],
                capture_output=True,
                text=True,
                env=env,
            )

            assert result.returncode == 0
            assert "Created default configuration" in result.stdout
        finally:
            os.chdir(old_cwd)


class TestConfigThreadSafety:
    """Test configuration system is thread-safe."""

    def test_concurrent_config_reads(self):
        """Test multiple threads can read config simultaneously."""
        import threading
        from config import get_config

        results = []
        errors = []

        def read_config():
            try:
                config = get_config()
                value = config.get("Models", "whisper_model")
                results.append(value)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read_config) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        assert all(r == results[0] for r in results)

    def test_concurrent_config_writes(self, temp_dir):
        """Test multiple threads writing to different config instances."""
        import threading
        from config.settings import TalkSmithConfig

        errors = []

        def write_config(thread_id):
            try:
                config = TalkSmithConfig()
                config.set("Test", f"thread_{thread_id}", str(thread_id))
                config_path = temp_dir / f"config_{thread_id}.ini"
                config.save(str(config_path))
                assert config_path.exists()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_config, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"


class TestConfigPathHandling:
    """Test path handling across different platforms."""

    def test_windows_path_with_backslashes(self):
        """Test handling Windows-style paths with backslashes."""
        from config.settings import TalkSmithConfig

        config = TalkSmithConfig()
        config.set("Paths", "test_path", r"C:\Users\test\data")

        path = config.get_path("Paths", "test_path")
        assert path is not None
        assert isinstance(path, Path)

    def test_unix_path_with_forward_slashes(self):
        """Test handling Unix-style paths."""
        from config.settings import TalkSmithConfig

        config = TalkSmithConfig()
        config.set("Paths", "test_path", "/home/user/data")

        path = config.get_path("Paths", "test_path")
        assert path is not None
        assert isinstance(path, Path)

    def test_mixed_path_separators(self):
        """Test handling paths with mixed separators."""
        from config.settings import TalkSmithConfig

        config = TalkSmithConfig()
        config.set("Paths", "test_path", r"C:/Users\test/data")

        path = config.get_path("Paths", "test_path")
        assert path is not None
        assert isinstance(path, Path)

    def test_path_with_trailing_separator(self):
        """Test paths with trailing separators are handled correctly."""
        from config.settings import TalkSmithConfig
        import os

        config = TalkSmithConfig()
        config.set("Paths", "test_path", "data/test/")

        path = config.get_path("Paths", "test_path")
        assert path is not None
        # Path should still be valid regardless of trailing separator


class TestConfigValidation:
    """Test configuration validation and error handling."""

    def test_get_int_with_none_value(self):
        """Test get_int when key returns None."""
        from config.settings import TalkSmithConfig

        config = TalkSmithConfig()
        result = config.get_int("NonExistent", "key", fallback=42)
        assert result == 42

    def test_get_float_with_none_value(self):
        """Test get_float when key returns None."""
        from config.settings import TalkSmithConfig

        config = TalkSmithConfig()
        result = config.get_float("NonExistent", "key", fallback=3.14)
        assert result == 3.14

    def test_get_bool_with_none_value(self):
        """Test get_bool when key returns None."""
        from config.settings import TalkSmithConfig

        config = TalkSmithConfig()
        result = config.get_bool("NonExistent", "key", fallback=True)
        assert result is True

    def test_get_list_preserves_order(self):
        """Test get_list preserves item order."""
        from config.settings import TalkSmithConfig

        config = TalkSmithConfig()
        config.set("Test", "ordered_list", "z,y,x,w,v")

        result = config.get_list("Test", "ordered_list")
        assert result == ["z", "y", "x", "w", "v"]

    def test_get_list_with_single_item(self):
        """Test get_list with single item (no separator)."""
        from config.settings import TalkSmithConfig

        config = TalkSmithConfig()
        config.set("Test", "single", "item")

        result = config.get_list("Test", "single")
        assert result == ["item"]

    def test_to_dict_includes_all_sections(self):
        """Test to_dict returns all sections."""
        from config.settings import TalkSmithConfig

        config = TalkSmithConfig()
        config_dict = config.to_dict()

        expected_sections = [
            "Paths",
            "Models",
            "Diarization",
            "Export",
            "Processing",
            "Logging",
        ]
        for section in expected_sections:
            assert section in config_dict
            assert isinstance(config_dict[section], dict)


class TestConfigFileDiscovery:
    """Test configuration file discovery in different locations."""

    def test_finds_settings_in_cwd(self, temp_dir, monkeypatch):
        """Test config finder locates settings.ini in current directory."""
        import os
        from config.settings import TalkSmithConfig

        settings_path = temp_dir / "settings.ini"
        settings_path.write_text("[Test]\nkey = cwd\n")

        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            config = TalkSmithConfig()
            assert config.get("Test", "key") == "cwd"
        finally:
            os.chdir(old_cwd)

    def test_finds_settings_in_config_subdir(self, temp_dir, monkeypatch):
        """Test config finder locates settings.ini in config/ subdirectory."""
        import os
        from config.settings import TalkSmithConfig

        config_dir = temp_dir / "config"
        config_dir.mkdir()
        settings_path = config_dir / "settings.ini"
        settings_path.write_text("[Test]\nkey = config-subdir\n")

        old_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            config = TalkSmithConfig()
            assert config.get("Test", "key") == "config-subdir"
        finally:
            os.chdir(old_cwd)


class TestConfigReload:
    """Test configuration reloading behavior."""

    def test_reload_updates_values(self, temp_dir):
        """Test that reload=True loads updated config values."""
        from config import get_config
        import os

        config_path = temp_dir / "test_reload.ini"
        config_path.write_text("[Models]\nwhisper_model = small\n")

        # Set env var to use our test config
        old_env = os.environ.get("TALKSMITH_CONFIG")
        try:
            os.environ["TALKSMITH_CONFIG"] = str(config_path)

            # First load
            config1 = get_config(reload=True)
            assert config1.get("Models", "whisper_model") == "small"

            # Modify file
            config_path.write_text("[Models]\nwhisper_model = large\n")

            # Reload
            config2 = get_config(reload=True)
            assert config2.get("Models", "whisper_model") == "large"

        finally:
            if old_env:
                os.environ["TALKSMITH_CONFIG"] = old_env
            elif "TALKSMITH_CONFIG" in os.environ:
                del os.environ["TALKSMITH_CONFIG"]

    def test_reload_clears_singleton(self):
        """Test reload creates new instance."""
        from config import get_config

        config1 = get_config(reload=True)
        config2 = get_config(reload=True)

        # Different instances after reload
        assert config1 is not config2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
