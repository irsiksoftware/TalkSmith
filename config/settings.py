"""
Configuration management system for TalkSmith.

Provides centralized access to settings from:
1. settings.ini (default configuration)
2. Environment variables (override)
3. CLI flags (highest priority, handled by caller)

Usage:
    from config.settings import get_config

    config = get_config()
    model = config.get('Models', 'whisper_model')
    input_dir = config.get_path('Paths', 'input_dir')
"""

import configparser
import os
from pathlib import Path
from typing import Any, Optional


class TalkSmithConfig:
    """Configuration manager with env var override support."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to settings.ini file. If None, looks in standard locations.
        """
        self.parser = configparser.ConfigParser()
        self.config_path = self._find_config_file(config_path)

        if self.config_path and os.path.exists(self.config_path):
            self.parser.read(self.config_path)
        else:
            # Load defaults if no config file found
            self._load_defaults()

    def _find_config_file(self, config_path: Optional[str] = None) -> str:
        """
        Find configuration file in standard locations.

        Priority:
        1. Provided config_path
        2. TALKSMITH_CONFIG env var
        3. ./settings.ini
        4. ./config/settings.ini
        5. ~/.talksmith/settings.ini
        """
        if config_path:
            return config_path

        if "TALKSMITH_CONFIG" in os.environ:
            return os.environ["TALKSMITH_CONFIG"]

        # Check standard locations
        candidates = [
            Path.cwd() / "settings.ini",
            Path.cwd() / "config" / "settings.ini",
            Path.home() / ".talksmith" / "settings.ini",
        ]

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        # Default to config/settings.ini even if doesn't exist
        return str(Path.cwd() / "config" / "settings.ini")

    def _load_defaults(self):
        """Load default configuration values."""
        self.parser["Paths"] = {
            "input_dir": "data/inputs",
            "output_dir": "data/outputs",
            "samples_dir": "data/samples",
            "cache_dir": ".cache",
        }

        self.parser["Models"] = {
            "whisper_model": "large-v3",
            "whisper_device": "auto",
            "compute_type": "float16",
            "diarization_model": "pyannote/speaker-diarization-3.1",
            "batch_size": "16",
            "num_workers": "4",
        }

        self.parser["Diarization"] = {
            "mode": "whisperx",
            "vad_threshold": "0.5",
            "min_speakers": "1",
            "max_speakers": "10",
            "min_segment_length": "0.5",
        }

        self.parser["Export"] = {
            "formats": "txt,json,srt",
            "include_timestamps": "true",
            "include_confidence": "true",
            "word_level": "false",
        }

        self.parser["Processing"] = {
            "denoise": "false",
            "normalize_audio": "true",
            "trim_silence": "false",
            "sample_rate": "16000",
        }

        self.parser["Logging"] = {
            "level": "INFO",
            "format": "json",
            "log_dir": "data/outputs/{slug}/logs",
            "console_output": "true",
        }

    def get(self, section: str, key: str, fallback: Any = None) -> str:
        """
        Get configuration value with environment variable override.

        Environment variable format: TALKSMITH_<SECTION>_<KEY>
        Example: TALKSMITH_MODELS_WHISPER_MODEL=medium.en

        Args:
            section: Configuration section name
            key: Configuration key name
            fallback: Default value if not found

        Returns:
            Configuration value as string
        """
        # Check environment variable first
        env_key = f"TALKSMITH_{section.upper()}_{key.upper()}"
        if env_key in os.environ:
            return os.environ[env_key]

        # Fall back to config file
        return self.parser.get(section, key, fallback=fallback)

    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """Get configuration value as integer."""
        value = self.get(section, key)
        if value is None:
            return fallback
        try:
            return int(value)
        except ValueError:
            return fallback

    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """Get configuration value as float."""
        value = self.get(section, key)
        if value is None:
            return fallback
        try:
            return float(value)
        except ValueError:
            return fallback

    def get_bool(self, section: str, key: str, fallback: bool = False) -> bool:
        """Get configuration value as boolean."""
        value = self.get(section, key)
        if value is None:
            return fallback
        return value.lower() in ("true", "yes", "1", "on")

    def get_list(self, section: str, key: str, separator: str = ",", fallback: list = None) -> list:
        """Get configuration value as list."""
        value = self.get(section, key)
        if value is None:
            return fallback or []
        return [item.strip() for item in value.split(separator) if item.strip()]

    def get_path(self, section: str, key: str, create: bool = False, fallback: str = None) -> Path:
        """
        Get configuration value as Path object.

        Args:
            section: Configuration section name
            key: Configuration key name
            create: Create directory if it doesn't exist
            fallback: Default value if not found

        Returns:
            Path object
        """
        value = self.get(section, key, fallback=fallback)
        if value is None:
            return None

        path = Path(value).expanduser()

        # Make absolute if relative
        if not path.is_absolute():
            path = Path.cwd() / path

        if create and not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        return path

    def set(self, section: str, key: str, value: str):
        """
        Set configuration value.

        Args:
            section: Configuration section name
            key: Configuration key name
            value: Value to set
        """
        if not self.parser.has_section(section):
            self.parser.add_section(section)

        self.parser.set(section, key, str(value))

    def save(self, path: Optional[str] = None):
        """
        Save configuration to file.

        Args:
            path: Path to save to. If None, uses original config path.
        """
        save_path = path or self.config_path

        # Create directory if needed
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "w") as f:
            self.parser.write(f)

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {section: dict(self.parser[section]) for section in self.parser.sections()}


# Global config instance
_config: Optional[TalkSmithConfig] = None


def get_config(config_path: Optional[str] = None, reload: bool = False) -> TalkSmithConfig:
    """
    Get global configuration instance (singleton pattern).

    Args:
        config_path: Path to settings.ini file
        reload: Force reload configuration

    Returns:
        TalkSmithConfig instance
    """
    global _config

    if _config is None or reload:
        _config = TalkSmithConfig(config_path)

    return _config


def create_default_config(path: str = "config/settings.ini"):
    """
    Create a default settings.ini file.

    Args:
        path: Path where to create the file
    """
    config = TalkSmithConfig()
    config.save(path)
    print(f"Created default configuration at: {path}")


if __name__ == "__main__":
    # CLI for creating default config
    import sys

    if len(sys.argv) > 1:
        create_default_config(sys.argv[1])
    else:
        create_default_config()
