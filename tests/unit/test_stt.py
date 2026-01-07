"""
Tests for speech-to-text
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import os
from stt import WhisperSTT


class TestWhisperSTT:
    """Test WhisperSTT class"""

    def test_init_default_params(self):
        """Test initialization with default parameters"""
        stt = WhisperSTT()

        assert stt.model_path == "./models/ggml-tiny.en.bin"
        assert stt.whisper_bin == "whisper-cpp"
        assert stt.sample_rate == 16000

    def test_init_custom_params(self):
        """Test initialization with custom parameters"""
        stt = WhisperSTT(
            model_path="/custom/model.bin",
            whisper_bin="custom-whisper"
        )

        assert stt.model_path == "/custom/model.bin"
        assert stt.whisper_bin == "custom-whisper"

    @patch('stt.subprocess.run')
    @patch('stt.os.path.exists')
    @patch('stt.os.remove')
    @patch.object(WhisperSTT, '_convert_to_wav')
    def test_transcribe_success(self, mock_convert, mock_remove, mock_exists, mock_run):
        """Test successful transcription"""
        stt = WhisperSTT()

        audio_path = "/tmp/test_audio.raw"
        wav_path = audio_path + ".wav"
        txt_path = wav_path + ".txt"

        # Mock file operations
        mock_exists.return_value = True

        # Mock successful whisper execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Mock reading transcript file
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.read.return_value = "This is a test transcript"
            mock_open.return_value.__enter__.return_value = mock_file

            result = stt.transcribe(audio_path)

            assert result == "This is a test transcript"
            mock_convert.assert_called_once_with(audio_path, wav_path)

    @patch('stt.subprocess.run')
    @patch('stt.os.path.exists')
    @patch.object(WhisperSTT, '_convert_to_wav')
    def test_transcribe_from_stdout(self, mock_convert, mock_exists, mock_run):
        """Test transcription from stdout when file not created"""
        stt = WhisperSTT()

        audio_path = "/tmp/test_audio.raw"

        # Mock file doesn't exist (whisper didn't create output file)
        mock_exists.return_value = False

        # Mock result with transcript in stdout
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Transcript from stdout"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = stt.transcribe(audio_path)

        assert result == "Transcript from stdout"

    @patch('stt.subprocess.run')
    @patch.object(WhisperSTT, '_convert_to_wav')
    def test_transcribe_whisper_failure(self, mock_convert, mock_run):
        """Test handling of whisper execution failure"""
        stt = WhisperSTT()

        audio_path = "/tmp/test_audio.raw"

        # Mock failed whisper execution
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Whisper error"
        mock_run.return_value = mock_result

        result = stt.transcribe(audio_path)

        assert result is None

    @patch('stt.subprocess.run')
    @patch.object(WhisperSTT, '_convert_to_wav')
    def test_transcribe_timeout(self, mock_convert, mock_run):
        """Test handling of transcription timeout"""
        stt = WhisperSTT()

        audio_path = "/tmp/test_audio.raw"

        # Mock timeout
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("whisper-cpp", 30)

        result = stt.transcribe(audio_path)

        assert result is None

    @patch('stt.subprocess.run')
    @patch('stt.os.path.exists')
    @patch.object(WhisperSTT, '_convert_to_wav')
    def test_transcribe_no_output(self, mock_convert, mock_exists, mock_run):
        """Test handling when no transcript is generated"""
        stt = WhisperSTT()

        audio_path = "/tmp/test_audio.raw"

        mock_exists.return_value = False
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        result = stt.transcribe(audio_path)

        assert result is None

    @patch('stt.subprocess.run')
    @patch('stt.os.path.exists')
    @patch('stt.os.remove')
    def test_transcribe_cleans_up_files(self, mock_remove, mock_exists, mock_run):
        """Test that temporary files are cleaned up"""
        stt = WhisperSTT()

        audio_path = "/tmp/test_audio.raw"
        wav_path = audio_path + ".wav"
        txt_path = wav_path + ".txt"

        # Mock file operations
        def exists_side_effect(path):
            if path == wav_path:
                return True
            elif path == txt_path:
                return True
            return False

        mock_exists.side_effect = exists_side_effect

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        # Mock conversion
        with patch.object(WhisperSTT, '_convert_to_wav'):
            with patch('builtins.open', create=True) as mock_open:
                mock_file = MagicMock()
                mock_file.read.return_value = "Test"
                mock_open.return_value.__enter__.return_value = mock_file

                stt.transcribe(audio_path)

                # Should remove both WAV and TXT files
                assert mock_remove.call_count >= 1

    @patch('stt.subprocess.run')
    def test_convert_to_wav_sox(self, mock_run):
        """Test audio conversion using sox"""
        stt = WhisperSTT()

        raw_path = "/tmp/test.raw"
        wav_path = "/tmp/test.wav"

        # Mock successful sox execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        stt._convert_to_wav(raw_path, wav_path)

        # Verify sox was called with correct parameters
        call_args = mock_run.call_args[0][0]
        assert "sox" in call_args
        assert raw_path in call_args
        assert wav_path in call_args

    @patch('stt.subprocess.run')
    def test_convert_to_wav_ffmpeg_fallback(self, mock_run):
        """Test audio conversion falls back to ffmpeg if sox fails"""
        stt = WhisperSTT()

        raw_path = "/tmp/test.raw"
        wav_path = "/tmp/test.wav"

        # Mock sox failure, then ffmpeg success
        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            if "sox" in cmd:
                result = Mock()
                result.returncode = 1
                return result
            elif "ffmpeg" in cmd:
                result = Mock()
                result.returncode = 0
                return result

        mock_run.side_effect = run_side_effect

        stt._convert_to_wav(raw_path, wav_path)

        # Should have called both sox and ffmpeg
        assert mock_run.call_count == 2

    @patch('stt.subprocess.run')
    def test_convert_to_wav_timeout(self, mock_run):
        """Test handling of conversion timeout"""
        stt = WhisperSTT()

        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("sox", 5)

        with pytest.raises(subprocess.TimeoutExpired):
            stt._convert_to_wav("/tmp/test.raw", "/tmp/test.wav")

    @patch('stt.subprocess.run')
    def test_convert_to_wav_not_found(self, mock_run):
        """Test handling when neither sox nor ffmpeg is found"""
        stt = WhisperSTT()

        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(FileNotFoundError):
            stt._convert_to_wav("/tmp/test.raw", "/tmp/test.wav")

    @patch('stt.subprocess.run')
    @patch.object(WhisperSTT, '_convert_to_wav')
    def test_transcribe_command_format(self, mock_convert, mock_run):
        """Test that transcribe uses correct command format"""
        stt = WhisperSTT(
            model_path="/custom/model.bin",
            whisper_bin="custom-whisper"
        )

        audio_path = "/tmp/test.raw"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Test transcript"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        with patch('stt.os.path.exists', return_value=False):
            stt.transcribe(audio_path)

        # Verify command format
        call_args = mock_run.call_args[0][0]
        assert "custom-whisper" in call_args
        assert "-m" in call_args
        assert "/custom/model.bin" in call_args
        assert "-nt" in call_args  # No timestamps
        assert "-otxt" in call_args  # Output as text
