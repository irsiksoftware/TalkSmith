"""Unit tests for FFmpeg verification script."""

import subprocess
from unittest.mock import patch, MagicMock

from scripts.check_ffmpeg import (
    check_ffmpeg_installed,
    get_ffmpeg_version,
    check_ffmpeg_codecs,
    check_ffprobe_installed,
    print_section,
    print_status,
    main,
)


class TestCheckFFmpegInstalled:
    """Test FFmpeg installation detection."""

    def test_ffmpeg_installed(self):
        """Test when FFmpeg is installed."""
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            assert check_ffmpeg_installed() is True

    def test_ffmpeg_not_installed(self):
        """Test when FFmpeg is not installed."""
        with patch("shutil.which", return_value=None):
            assert check_ffmpeg_installed() is False


class TestGetFFmpegVersion:
    """Test FFmpeg version detection."""

    def test_get_version_success(self):
        """Test successful version retrieval."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ffmpeg version 4.4.2-0ubuntu0.22.04.1\n"

        with patch("subprocess.run", return_value=mock_result):
            version = get_ffmpeg_version()

            assert version == "ffmpeg version 4.4.2-0ubuntu0.22.04.1"

    def test_get_version_not_found(self):
        """Test when FFmpeg is not found."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            version = get_ffmpeg_version()

            assert version is None

    def test_get_version_timeout(self):
        """Test timeout handling."""
        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 5)
        ):
            version = get_ffmpeg_version()

            assert version is None

    def test_get_version_error(self):
        """Test when FFmpeg returns error."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            version = get_ffmpeg_version()

            assert version is None

    def test_get_version_multiline_output(self):
        """Test version extraction from multiline output."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = """ffmpeg version 5.1.2
built with gcc 11.2.0
configuration: --enable-gpl"""

        with patch("subprocess.run", return_value=mock_result):
            version = get_ffmpeg_version()

            assert version == "ffmpeg version 5.1.2"


class TestCheckFFmpegCodecs:
    """Test FFmpeg codec detection."""

    def test_all_codecs_available(self):
        """Test when all required codecs are available."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = """Codecs:
 D..... = Decoding supported
 .E.... = Encoding supported
 ..V... = Video codec
 ..A... = Audio codec
 DEA    pcm_s16le       PCM signed 16-bit little-endian
 DEA    aac             AAC (Advanced Audio Coding)
"""

        with patch("subprocess.run", return_value=mock_result):
            has_pcm, has_aac = check_ffmpeg_codecs()

            assert has_pcm is True
            assert has_aac is True

    def test_missing_codecs(self):
        """Test when codecs are missing."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = """Codecs:
 D..... = Decoding supported
"""

        with patch("subprocess.run", return_value=mock_result):
            has_pcm, has_aac = check_ffmpeg_codecs()

            assert has_pcm is False
            assert has_aac is False

    def test_codecs_check_case_insensitive(self):
        """Test that codec check is case-insensitive."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = """Codecs:
 DEA    PCM_S16LE       PCM signed 16-bit little-endian
 DEA    AAC             AAC (Advanced Audio Coding)
"""

        with patch("subprocess.run", return_value=mock_result):
            has_pcm, has_aac = check_ffmpeg_codecs()

            assert has_pcm is True
            assert has_aac is True

    def test_codecs_check_error(self):
        """Test when codec check fails."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            has_pcm, has_aac = check_ffmpeg_codecs()

            assert has_pcm is False
            assert has_aac is False

    def test_codecs_check_timeout(self):
        """Test timeout handling for codec check."""
        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 5)
        ):
            has_pcm, has_aac = check_ffmpeg_codecs()

            assert has_pcm is False
            assert has_aac is False


class TestCheckFFprobeInstalled:
    """Test ffprobe installation detection."""

    def test_ffprobe_installed(self):
        """Test when ffprobe is installed."""
        with patch("shutil.which", return_value="/usr/bin/ffprobe"):
            assert check_ffprobe_installed() is True

    def test_ffprobe_not_installed(self):
        """Test when ffprobe is not installed."""
        with patch("shutil.which", return_value=None):
            assert check_ffprobe_installed() is False


class TestPrintFunctions:
    """Test print utility functions."""

    def test_print_section(self, capsys):
        """Test section header printing."""
        print_section("Test Section")
        captured = capsys.readouterr()

        assert "Test Section" in captured.out
        assert "=" in captured.out

    def test_print_section_custom_char(self, capsys):
        """Test section header with custom character."""
        print_section("Test", "-")
        captured = capsys.readouterr()

        assert "Test" in captured.out
        assert "-" in captured.out

    def test_print_status_success(self, capsys):
        """Test status printing for success."""
        print_status("FFmpeg", "Installed", True)
        captured = capsys.readouterr()

        assert "FFmpeg" in captured.out
        assert "Installed" in captured.out
        assert "✓" in captured.out

    def test_print_status_failure(self, capsys):
        """Test status printing for failure."""
        print_status("FFmpeg", "NOT FOUND", False)
        captured = capsys.readouterr()

        assert "FFmpeg" in captured.out
        assert "NOT FOUND" in captured.out
        assert "✗" in captured.out


class TestMain:
    """Test main function execution."""

    @patch("scripts.check_ffmpeg.check_ffmpeg_codecs")
    @patch("scripts.check_ffmpeg.check_ffprobe_installed")
    @patch("scripts.check_ffmpeg.get_ffmpeg_version")
    @patch("scripts.check_ffmpeg.check_ffmpeg_installed")
    def test_main_all_checks_pass(
        self, mock_installed, mock_version, mock_ffprobe, mock_codecs
    ):
        """Test main when all checks pass."""
        mock_installed.return_value = True
        mock_version.return_value = "ffmpeg version 4.4.2"
        mock_ffprobe.return_value = True
        mock_codecs.return_value = (True, True)  # Both PCM and AAC available

        # Mock the functionality test
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            exit_code = main()

            assert exit_code == 0

    @patch("scripts.check_ffmpeg.check_ffmpeg_installed")
    def test_main_ffmpeg_not_installed(self, mock_installed):
        """Test main when FFmpeg is not installed."""
        mock_installed.return_value = False

        exit_code = main()

        assert exit_code == 1

    @patch("scripts.check_ffmpeg.check_ffmpeg_codecs")
    @patch("scripts.check_ffmpeg.check_ffprobe_installed")
    @patch("scripts.check_ffmpeg.get_ffmpeg_version")
    @patch("scripts.check_ffmpeg.check_ffmpeg_installed")
    def test_main_ffprobe_missing(
        self, mock_installed, mock_version, mock_ffprobe, mock_codecs
    ):
        """Test main when ffprobe is missing."""
        mock_installed.return_value = True
        mock_version.return_value = "ffmpeg version 4.4.2"
        mock_ffprobe.return_value = False
        mock_codecs.return_value = (True, True)

        # Mock the functionality test
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            exit_code = main()

            assert exit_code == 1

    @patch("scripts.check_ffmpeg.check_ffmpeg_codecs")
    @patch("scripts.check_ffmpeg.check_ffprobe_installed")
    @patch("scripts.check_ffmpeg.get_ffmpeg_version")
    @patch("scripts.check_ffmpeg.check_ffmpeg_installed")
    def test_main_missing_codecs(
        self, mock_installed, mock_version, mock_ffprobe, mock_codecs
    ):
        """Test main when essential codecs are missing."""
        mock_installed.return_value = True
        mock_version.return_value = "ffmpeg version 4.4.2"
        mock_ffprobe.return_value = True
        mock_codecs.return_value = (False, True)  # PCM missing

        # Mock the functionality test
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            exit_code = main()

            assert exit_code == 1

    @patch("scripts.check_ffmpeg.check_ffmpeg_codecs")
    @patch("scripts.check_ffmpeg.check_ffprobe_installed")
    @patch("scripts.check_ffmpeg.get_ffmpeg_version")
    @patch("scripts.check_ffmpeg.check_ffmpeg_installed")
    def test_main_functionality_test_fails(
        self, mock_installed, mock_version, mock_ffprobe, mock_codecs
    ):
        """Test main when functionality test fails."""
        mock_installed.return_value = True
        mock_version.return_value = "ffmpeg version 4.4.2"
        mock_ffprobe.return_value = True
        mock_codecs.return_value = (True, True)

        # Mock the functionality test to fail
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch("subprocess.run", return_value=mock_result):
            exit_code = main()

            assert exit_code == 1

    @patch("scripts.check_ffmpeg.check_ffmpeg_codecs")
    @patch("scripts.check_ffmpeg.check_ffprobe_installed")
    @patch("scripts.check_ffmpeg.get_ffmpeg_version")
    @patch("scripts.check_ffmpeg.check_ffmpeg_installed")
    def test_main_functionality_test_exception(
        self, mock_installed, mock_version, mock_ffprobe, mock_codecs
    ):
        """Test main when functionality test raises exception."""
        mock_installed.return_value = True
        mock_version.return_value = "ffmpeg version 4.4.2"
        mock_ffprobe.return_value = True
        mock_codecs.return_value = (True, True)

        # Mock the functionality test to raise exception
        with patch("subprocess.run", side_effect=Exception("Test error")):
            exit_code = main()

            assert exit_code == 1

    @patch("scripts.check_ffmpeg.check_ffmpeg_codecs")
    @patch("scripts.check_ffmpeg.check_ffprobe_installed")
    @patch("scripts.check_ffmpeg.get_ffmpeg_version")
    @patch("scripts.check_ffmpeg.check_ffmpeg_installed")
    def test_main_partial_codec_support(
        self, mock_installed, mock_version, mock_ffprobe, mock_codecs
    ):
        """Test main when only some codecs are available."""
        mock_installed.return_value = True
        mock_version.return_value = "ffmpeg version 4.4.2"
        mock_ffprobe.return_value = True
        mock_codecs.return_value = (True, False)  # PCM available, AAC missing

        # Mock the functionality test
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            exit_code = main()

            assert exit_code == 1


class TestIntegration:
    """Integration tests for FFmpeg checker."""

    def test_combined_checks_workflow(self):
        """Test the complete workflow of checks."""
        with patch("shutil.which") as mock_which:
            # Test when nothing is installed
            mock_which.return_value = None

            assert check_ffmpeg_installed() is False
            assert check_ffprobe_installed() is False

            # Test when both are installed
            mock_which.return_value = "/usr/bin/ffmpeg"

            assert check_ffmpeg_installed() is True
            assert check_ffprobe_installed() is True

    def test_version_parsing_real_formats(self):
        """Test version parsing with real-world version strings."""
        test_versions = [
            "ffmpeg version 4.4.2-0ubuntu0.22.04.1",
            "ffmpeg version N-109868-g16e251c774 Copyright (c) 2000-2023",
            "ffmpeg version 5.1.2-static https://johnvansickle.com/ffmpeg/",
        ]

        for version_string in test_versions:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = version_string + "\nMore output..."

            with patch("subprocess.run", return_value=mock_result):
                result = get_ffmpeg_version()

                assert result == version_string
