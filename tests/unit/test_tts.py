"""
Tests for text-to-speech
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
from tts import TTSManager, KokoroTTS, KittenTTS


class TestKokoroTTS:
    """Test KokoroTTS engine"""

    def test_init_default(self):
        """Test initialization with default parameters"""
        with patch('tts.os.path.exists', return_value=False):
            tts = KokoroTTS()

            assert tts.model_path == "./models/kokoro/kokoro-v0_19.onnx"
            assert tts.voice == "af_sarah"
            assert tts.kokoro_impl is None  # Falls back when model not found

    def test_init_custom_voice(self):
        """Test initialization with custom voice"""
        with patch('tts.os.path.exists', return_value=False):
            tts = KokoroTTS(voice="custom_voice")

            assert tts.voice == "custom_voice"

    @patch('tts.subprocess.run')
    def test_espeak_fallback(self, mock_run):
        """Test espeak fallback when Kokoro not available"""
        with patch('tts.os.path.exists', return_value=False):
            tts = KokoroTTS()

            # Mock successful espeak execution
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            result = tts.synthesize("Hello world", "/tmp/output.wav")

            assert result is True
            mock_run.assert_called_once()

            # Verify espeak command
            call_args = mock_run.call_args[0][0]
            assert "espeak-ng" in call_args
            assert "Hello world" in call_args
            assert "/tmp/output.wav" in call_args

    @patch('tts.subprocess.run')
    def test_espeak_failure(self, mock_run):
        """Test handling of espeak failure"""
        with patch('tts.os.path.exists', return_value=False):
            tts = KokoroTTS()

            # Mock failed espeak execution
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr.decode.return_value = "Error"
            mock_run.return_value = mock_result

            result = tts.synthesize("Test", "/tmp/output.wav")

            assert result is False

    @patch('tts.subprocess.run')
    def test_espeak_not_found(self, mock_run):
        """Test handling when espeak is not installed"""
        with patch('tts.os.path.exists', return_value=False):
            tts = KokoroTTS()

            mock_run.side_effect = FileNotFoundError()

            result = tts.synthesize("Test", "/tmp/output.wav")

            assert result is False

    @patch('tts.subprocess.run')
    def test_espeak_timeout(self, mock_run):
        """Test handling of espeak timeout"""
        with patch('tts.os.path.exists', return_value=False):
            tts = KokoroTTS()

            import subprocess
            mock_run.side_effect = subprocess.TimeoutExpired("espeak-ng", 30)

            result = tts.synthesize("Test", "/tmp/output.wav")

            assert result is False


class TestKittenTTS:
    """Test KittenTTS engine"""

    def test_init(self):
        """Test initialization"""
        tts = KittenTTS()
        assert tts.model_path is None

    def test_init_custom_model(self):
        """Test initialization with custom model"""
        tts = KittenTTS(model_path="/custom/model.bin")
        assert tts.model_path == "/custom/model.bin"

    @patch('tts.subprocess.run')
    def test_fallback_to_espeak(self, mock_run):
        """Test that KittenTTS falls back to espeak"""
        tts = KittenTTS()

        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = tts.synthesize("Test text", "/tmp/output.wav")

        assert result is True
        # Should use espeak fallback
        call_args = mock_run.call_args[0][0]
        assert "espeak-ng" in call_args


class TestTTSManager:
    """Test TTSManager class"""

    def test_init_default_engine(self):
        """Test initialization with default engine"""
        with patch('tts.os.path.exists', return_value=False):
            manager = TTSManager()

            assert manager.engine_name == "kokoro"
            assert isinstance(manager.engine, KokoroTTS)
            assert manager.sample_rate == 16000
            assert manager.output_dir == "/tmp"

    def test_init_kitten_engine(self):
        """Test initialization with kitten engine"""
        manager = TTSManager(engine="kitten")

        assert manager.engine_name == "kitten"
        assert isinstance(manager.engine, KittenTTS)

    def test_init_unknown_engine_fallback(self):
        """Test initialization with unknown engine falls back to kokoro"""
        with patch('tts.os.path.exists', return_value=False):
            manager = TTSManager(engine="unknown")

            assert isinstance(manager.engine, KokoroTTS)

    @patch('tts.subprocess.run')
    @patch('tts.os.path.exists')
    def test_synthesize_success(self, mock_exists, mock_run):
        """Test successful synthesis"""
        with patch('tts.os.path.exists', return_value=False):
            manager = TTSManager()

        # Mock successful synthesis
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        mock_exists.return_value = True

        result = manager.synthesize("Hello world")

        assert result is not None
        assert result.endswith(".wav")
        assert os.path.dirname(result) == "/tmp"

    @patch('tts.subprocess.run')
    @patch('tts.os.path.exists')
    def test_synthesize_with_custom_filename(self, mock_exists, mock_run):
        """Test synthesis with custom filename"""
        with patch('tts.os.path.exists', return_value=False):
            manager = TTSManager()

        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        mock_exists.return_value = True

        result = manager.synthesize("Test", output_filename="custom.wav")

        assert result == "/tmp/custom.wav"

    @patch('tts.subprocess.run')
    @patch('tts.os.path.exists')
    def test_synthesize_failure(self, mock_exists, mock_run):
        """Test handling of synthesis failure"""
        with patch('tts.os.path.exists', return_value=False):
            manager = TTSManager()

        # Mock failed synthesis
        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        mock_exists.return_value = False

        result = manager.synthesize("Test")

        assert result is None

    def test_synthesize_empty_text(self):
        """Test handling of empty text"""
        with patch('tts.os.path.exists', return_value=False):
            manager = TTSManager()

        result = manager.synthesize("")

        assert result is None

    @patch('tts.subprocess.run')
    @patch('tts.os.path.exists')
    def test_synthesize_generates_hash_filename(self, mock_exists, mock_run):
        """Test that synthesis generates hash-based filename"""
        with patch('tts.os.path.exists', return_value=False):
            manager = TTSManager()

        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        mock_exists.return_value = True

        result1 = manager.synthesize("Same text")
        result2 = manager.synthesize("Same text")

        # Same text should generate same filename
        assert result1 == result2

    @patch('tts.subprocess.run')
    @patch('tts.os.path.exists')
    def test_synthesize_different_text_different_filename(self, mock_exists, mock_run):
        """Test that different text generates different filenames"""
        with patch('tts.os.path.exists', return_value=False):
            manager = TTSManager()

        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        mock_exists.return_value = True

        result1 = manager.synthesize("Text one")
        result2 = manager.synthesize("Text two")

        # Different text should generate different filenames
        assert result1 != result2

    @patch('tts.os.listdir')
    @patch('tts.os.path.isfile')
    @patch('tts.os.path.getmtime')
    @patch('tts.os.remove')
    def test_cleanup_old_files(self, mock_remove, mock_getmtime, mock_isfile, mock_listdir):
        """Test cleanup of old TTS files"""
        with patch('tts.os.path.exists', return_value=False):
            manager = TTSManager()

        import time
        current_time = time.time()

        # Mock files in output directory
        mock_listdir.return_value = [
            "tts_abc123.wav",  # Old file
            "tts_def456.wav",  # Recent file
            "other_file.wav",  # Should be ignored
        ]

        mock_isfile.return_value = True

        def getmtime_side_effect(path):
            if "abc123" in path:
                return current_time - 7200  # 2 hours old
            else:
                return current_time - 1800  # 30 minutes old

        mock_getmtime.side_effect = getmtime_side_effect

        # Clean up files older than 1 hour (3600 seconds)
        manager.cleanup_old_files(max_age_seconds=3600)

        # Should only remove the old file
        mock_remove.assert_called_once()
        assert "abc123" in str(mock_remove.call_args)

    @patch('tts.os.listdir')
    def test_cleanup_handles_errors(self, mock_listdir):
        """Test that cleanup handles errors gracefully"""
        with patch('tts.os.path.exists', return_value=False):
            manager = TTSManager()

        # Mock error in listdir
        mock_listdir.side_effect = OSError("Permission denied")

        # Should not raise exception
        manager.cleanup_old_files()

    @patch('tts.os.listdir')
    @patch('tts.os.path.isfile')
    @patch('tts.os.path.getmtime')
    def test_cleanup_only_removes_tts_files(self, mock_getmtime, mock_isfile, mock_listdir):
        """Test that cleanup only removes TTS files"""
        with patch('tts.os.path.exists', return_value=False):
            manager = TTSManager()

        import time
        current_time = time.time()

        # Mock various files
        mock_listdir.return_value = [
            "tts_old.wav",
            "other_old.wav",
            "random_file.txt",
        ]

        mock_isfile.return_value = True
        mock_getmtime.return_value = current_time - 7200  # All files are old

        with patch('tts.os.remove') as mock_remove:
            manager.cleanup_old_files(max_age_seconds=3600)

            # Should only attempt to remove files starting with "tts_" and ending with ".wav"
            if mock_remove.called:
                for call in mock_remove.call_args_list:
                    filepath = call[0][0]
                    filename = os.path.basename(filepath)
                    assert filename.startswith("tts_")
                    assert filename.endswith(".wav")
