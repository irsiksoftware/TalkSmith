"""
WhisperX diarization pipeline.

Uses WhisperX for alignment and pyannote.audio for speaker diarization.
Requires HuggingFace token for pyannote models.
"""

import os
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import torch
import whisperx

from pipeline.diarization.base import BaseDiarizer, DiarizationResult


class WhisperXDiarizer(BaseDiarizer):
    """Diarizer using WhisperX + pyannote.audio for speaker diarization."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cuda",
        compute_type: str = "float16",
        hf_token: Optional[str] = None,
        vad_onset: float = 0.5,
        vad_offset: float = 0.363,
        logger=None,
    ):
        """
        Initialize the diarizer.

        Args:
            model_size: Whisper model size (base, small, medium.en, large-v3)
            device: Device to use (cuda or cpu)
            compute_type: Compute precision (float16, int8)
            hf_token: HuggingFace token for pyannote models
            vad_onset: VAD onset threshold (0.0-1.0)
            vad_offset: VAD offset threshold (0.0-1.0)
            logger: Optional logger instance
        """
        super().__init__(logger)

        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self.vad_onset = vad_onset
        self.vad_offset = vad_offset

        if not self.hf_token:
            raise ValueError(
                "HuggingFace token required for pyannote models. "
                "Set HF_TOKEN environment variable or pass hf_token parameter. "
                "Get token at: https://huggingface.co/settings/tokens"
            )

        self.logger.info(
            "Initializing WhisperX diarizer",
            model_size=model_size,
            device=device,
            compute_type=compute_type,
            vad_onset=vad_onset,
            vad_offset=vad_offset,
        )

        # Suppress WhisperX warnings
        warnings.filterwarnings("ignore", category=UserWarning)

        # Load Whisper model
        self.logger.info("Loading Whisper model", model=model_size)
        self.model = whisperx.load_model(
            model_size,
            device=device,
            compute_type=compute_type,
        )

    def _diarize_implementation(
        self,
        audio_path: Path,
        num_speakers: Optional[int] = None,
        language: Optional[str] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
        **kwargs,
    ) -> DiarizationResult:
        """
        WhisperX diarization implementation.

        Args:
            audio_path: Path to audio file
            num_speakers: Number of speakers (not used, kept for compatibility)
            language: Language code (e.g., 'en'). None for auto-detection.
            min_speakers: Minimum number of speakers (None for auto-detection)
            max_speakers: Maximum number of speakers (None for auto-detection)
            **kwargs: Additional parameters

        Returns:
            DiarizationResult with transcribed and diarized segments
        """
        start_time = time.time()
        audio_path_str = str(audio_path)

        self.logger.info(
            "Starting WhisperX diarization",
            audio_path=audio_path_str,
            language=language,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )

        # Step 1: Load audio
        self.logger.info("Loading audio", audio_path=audio_path_str)
        audio = whisperx.load_audio(audio_path_str)

        # Step 2: Transcribe with Whisper
        self.logger.info("Transcribing audio", model=self.model_size)
        transcribe_start = time.time()
        result = self.model.transcribe(
            audio,
            language=language,
            batch_size=16,
        )
        transcribe_time = time.time() - transcribe_start
        self.logger.info(
            "Transcription complete",
            duration=transcribe_time,
            segments=len(result.get("segments", [])),
            language=result.get("language"),
        )

        detected_language = result.get("language", language or "en")

        # Step 3: Align whisper output
        self.logger.info("Aligning segments", language=detected_language)
        align_start = time.time()

        try:
            model_a, metadata = whisperx.load_align_model(
                language_code=detected_language,
                device=self.device,
            )
            result = whisperx.align(
                result["segments"],
                model_a,
                metadata,
                audio,
                self.device,
                return_char_alignments=False,
            )
            align_time = time.time() - align_start
            self.logger.info("Alignment complete", duration=align_time)
        except Exception as e:
            self.logger.warning(
                "Alignment failed, using original timestamps",
                error=str(e),
            )
            align_time = 0

        # Step 4: Diarize with pyannote
        self.logger.info("Loading diarization model")
        diarize_start = time.time()

        detected_speakers = None
        try:
            diarize_model = whisperx.DiarizationPipeline(
                use_auth_token=self.hf_token,
                device=self.device,
            )

            # Apply diarization
            diarize_segments = diarize_model(
                audio,
                min_speakers=min_speakers,
                max_speakers=max_speakers,
            )

            # Assign speaker labels to words
            result = whisperx.assign_word_speakers(diarize_segments, result)
            diarize_time = time.time() - diarize_start
            self.logger.info("Diarization complete", duration=diarize_time)

            # Count speakers
            speakers = set()
            for segment in result.get("segments", []):
                if "speaker" in segment:
                    speakers.add(segment["speaker"])
            detected_speakers = len(speakers) if speakers else None

        except Exception as e:
            self.logger.error(
                "Diarization failed",
                error=str(e),
            )
            # Continue without speaker labels
            diarize_time = 0

        # Step 5: Format output
        segments = self._format_whisperx_segments(result.get("segments", []))

        total_time = time.time() - start_time
        audio_duration = segments[-1]["end"] if segments else 0

        metadata = {
            "language": detected_language,
            "duration": audio_duration,
            "model_size": self.model_size,
            "device": self.device,
            "rtf": total_time / audio_duration if audio_duration > 0 else 0,
            "timings": {
                "transcribe": transcribe_time,
                "align": align_time,
                "diarize": diarize_time,
            },
        }

        return DiarizationResult(
            segments=segments,
            audio_path=audio_path_str,
            num_speakers=detected_speakers,
            processing_time=total_time,
            metadata=metadata,
        )

    def _format_whisperx_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Format WhisperX segments to standard format.

        Args:
            segments: Raw WhisperX segments

        Returns:
            List of formatted segments: {start, end, text, speaker}
        """
        formatted = []

        for segment in segments:
            formatted_segment = {
                "start": segment.get("start", 0.0),
                "end": segment.get("end", 0.0),
                "text": segment.get("text", "").strip(),
            }

            # Add speaker if available
            if "speaker" in segment:
                formatted_segment["speaker"] = segment["speaker"]

            # Add words if available
            if "words" in segment and segment["words"]:
                formatted_segment["words"] = [
                    {
                        "start": word.get("start", 0.0),
                        "end": word.get("end", 0.0),
                        "word": word.get("word", ""),
                        "speaker": word.get("speaker"),
                    }
                    for word in segment["words"]
                ]

            formatted.append(formatted_segment)

        return formatted

    def diarize(
        self,
        audio_path: str,
        language: Optional[str] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
    ) -> Dict:
        """
        Transcribe and diarize audio file.

        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en'). None for auto-detection.
            min_speakers: Minimum number of speakers (None for auto-detection)
            max_speakers: Maximum number of speakers (None for auto-detection)

        Returns:
            Dictionary with diarized segments and metadata
        """
        result = self._diarize_implementation(
            audio_path=Path(audio_path),
            num_speakers=None,
            language=language,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )

        # Convert to old format for backwards compatibility
        output = {
            "segments": result.segments,
            "language": result.metadata.get("language"),
            "duration": result.metadata.get("duration"),
            "processing_time": result.processing_time,
            "rtf": result.metadata.get("rtf"),
            "model_size": result.metadata.get("model_size"),
            "device": result.metadata.get("device"),
            "timings": result.metadata.get("timings"),
        }

        return output
