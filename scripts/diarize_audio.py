#!/usr/bin/env python3
"""
Speaker diarization for Hyperflow using pyannote.audio and Whisper.

This script processes audio files to:
1. Transcribe speech using Whisper
2. Identify speakers using pyannote.audio
3. Output a formatted transcript with speaker labels

Requirements:
    pip install pyannote.audio whisper torch torchaudio

For best results, also install:
    pip install faster-whisper  # Faster transcription

Usage:
    # Basic transcription with diarization
    python diarize_audio.py meeting.mp3

    # Specify output format
    python diarize_audio.py meeting.mp3 --format markdown --output transcript.md

    # Use known speaker names
    python diarize_audio.py meeting.mp3 --speakers "Alice,Bob,Charlie"

    # Specify number of speakers (improves accuracy)
    python diarize_audio.py meeting.mp3 --num-speakers 3

Note: Requires a Hugging Face access token for pyannote models.
Set HF_TOKEN environment variable or pass --hf-token argument.
Get your token at: https://huggingface.co/settings/tokens
"""

import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click

# Check for required packages
PYANNOTE_AVAILABLE = False
WHISPER_AVAILABLE = False
FASTER_WHISPER_AVAILABLE = False

try:
    from pyannote.audio import Pipeline
    PYANNOTE_AVAILABLE = True
except ImportError:
    pass

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    pass

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    pass


def format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS or MM:SS."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class SpeakerDiarizer:
    """Combines Whisper transcription with pyannote speaker diarization."""

    def __init__(self, hf_token: str, whisper_model: str = "base",
                 use_faster_whisper: bool = True):
        self.hf_token = hf_token
        self.whisper_model_name = whisper_model

        # Initialize pyannote pipeline
        if not PYANNOTE_AVAILABLE:
            raise RuntimeError(
                "pyannote.audio not available. Install with: pip install pyannote.audio"
            )

        click.echo("Loading pyannote diarization model...")
        self.diarization_pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=hf_token
        )

        # Initialize Whisper
        click.echo(f"Loading Whisper model ({whisper_model})...")
        if use_faster_whisper and FASTER_WHISPER_AVAILABLE:
            self.whisper = WhisperModel(whisper_model, device="cpu", compute_type="int8")
            self.use_faster = True
        elif WHISPER_AVAILABLE:
            self.whisper = whisper.load_model(whisper_model)
            self.use_faster = False
        else:
            raise RuntimeError(
                "Whisper not available. Install with: pip install openai-whisper"
            )

    def transcribe(self, audio_path: Path) -> list[dict]:
        """Transcribe audio and return segments with timestamps."""
        click.echo(f"Transcribing: {audio_path.name}")

        if self.use_faster:
            segments, _ = self.whisper.transcribe(str(audio_path))
            return [
                {
                    'start': seg.start,
                    'end': seg.end,
                    'text': seg.text.strip()
                }
                for seg in segments
            ]
        else:
            result = self.whisper.transcribe(str(audio_path))
            return [
                {
                    'start': seg['start'],
                    'end': seg['end'],
                    'text': seg['text'].strip()
                }
                for seg in result['segments']
            ]

    def diarize(self, audio_path: Path, num_speakers: Optional[int] = None,
                min_speakers: Optional[int] = None,
                max_speakers: Optional[int] = None) -> list[dict]:
        """Run speaker diarization and return speaker segments."""
        click.echo("Running speaker diarization...")

        kwargs = {}
        if num_speakers:
            kwargs['num_speakers'] = num_speakers
        if min_speakers:
            kwargs['min_speakers'] = min_speakers
        if max_speakers:
            kwargs['max_speakers'] = max_speakers

        diarization = self.diarization_pipeline(str(audio_path), **kwargs)

        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                'start': turn.start,
                'end': turn.end,
                'speaker': speaker
            })

        return segments

    def merge_transcription_diarization(
        self,
        transcription: list[dict],
        diarization: list[dict],
        speaker_names: Optional[dict] = None
    ) -> list[dict]:
        """Merge transcription with speaker labels."""
        result = []

        for trans_seg in transcription:
            # Find overlapping speaker segment
            trans_mid = (trans_seg['start'] + trans_seg['end']) / 2

            best_speaker = "Unknown"
            best_overlap = 0

            for diar_seg in diarization:
                # Calculate overlap
                overlap_start = max(trans_seg['start'], diar_seg['start'])
                overlap_end = min(trans_seg['end'], diar_seg['end'])
                overlap = max(0, overlap_end - overlap_start)

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = diar_seg['speaker']

            # Map speaker ID to name if provided
            if speaker_names and best_speaker in speaker_names:
                best_speaker = speaker_names[best_speaker]

            result.append({
                'start': trans_seg['start'],
                'end': trans_seg['end'],
                'speaker': best_speaker,
                'text': trans_seg['text']
            })

        return result

    def process(self, audio_path: Path, num_speakers: Optional[int] = None,
                min_speakers: Optional[int] = None,
                max_speakers: Optional[int] = None,
                speaker_names: Optional[list[str]] = None) -> list[dict]:
        """Process audio file with transcription and diarization."""
        # Transcribe
        transcription = self.transcribe(audio_path)

        # Diarize
        diarization = self.diarize(
            audio_path,
            num_speakers=num_speakers,
            min_speakers=min_speakers,
            max_speakers=max_speakers
        )

        # Map speaker names
        speaker_map = None
        if speaker_names:
            # Get unique speakers from diarization
            unique_speakers = sorted(set(seg['speaker'] for seg in diarization))
            speaker_map = dict(zip(unique_speakers, speaker_names))

        # Merge results
        return self.merge_transcription_diarization(
            transcription, diarization, speaker_map
        )


def format_as_markdown(segments: list[dict], title: str = "Transcript") -> str:
    """Format diarized transcript as markdown."""
    lines = [
        "---",
        f'title: "{title}"',
        f"date: {datetime.now().isoformat()}",
        "source: audio_diarization",
        "status: pending_review",
        "content_type: meeting",
        "tags:",
        "  - meeting",
        "  - transcript",
        "---",
        "",
        f"# {title}",
        "",
        "## Transcript",
        ""
    ]

    current_speaker = None
    for seg in segments:
        if seg['speaker'] != current_speaker:
            current_speaker = seg['speaker']
            timestamp = format_timestamp(seg['start'])
            lines.append(f"\n*{timestamp}*\n")
            lines.append(f"**[{current_speaker}]:** {seg['text']}")
        else:
            lines.append(seg['text'])

    return '\n'.join(lines)


def format_as_json(segments: list[dict]) -> str:
    """Format diarized transcript as JSON."""
    import json
    return json.dumps(segments, indent=2)


def format_as_srt(segments: list[dict]) -> str:
    """Format diarized transcript as SRT subtitles."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = format_timestamp(seg['start']).replace(':', ',') + ',000'
        end = format_timestamp(seg['end']).replace(':', ',') + ',000'
        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(f"[{seg['speaker']}]: {seg['text']}")
        lines.append("")
    return '\n'.join(lines)


@click.command()
@click.argument('audio_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', '-f', 'output_format',
              type=click.Choice(['markdown', 'json', 'srt']),
              default='markdown', help='Output format')
@click.option('--hf-token', envvar='HF_TOKEN',
              help='Hugging Face access token (or set HF_TOKEN env var)')
@click.option('--whisper-model', default='base',
              type=click.Choice(['tiny', 'base', 'small', 'medium', 'large']),
              help='Whisper model size')
@click.option('--speakers', help='Comma-separated list of speaker names')
@click.option('--num-speakers', type=int, help='Exact number of speakers (improves accuracy)')
@click.option('--min-speakers', type=int, help='Minimum number of speakers')
@click.option('--max-speakers', type=int, help='Maximum number of speakers')
def main(audio_file: str, output: Optional[str], output_format: str,
         hf_token: Optional[str], whisper_model: str, speakers: Optional[str],
         num_speakers: Optional[int], min_speakers: Optional[int],
         max_speakers: Optional[int]):
    """Transcribe audio with speaker diarization.

    AUDIO_FILE is the path to an audio file (mp3, wav, m4a, etc.)

    Examples:
        diarize_audio.py meeting.mp3
        diarize_audio.py meeting.mp3 --speakers "Alice,Bob" --num-speakers 2
        diarize_audio.py interview.wav --format srt --output subtitles.srt
    """
    if not hf_token:
        click.echo("Error: Hugging Face token required.", err=True)
        click.echo("Get one at: https://huggingface.co/settings/tokens", err=True)
        click.echo("Set HF_TOKEN env var or use --hf-token", err=True)
        sys.exit(1)

    audio_path = Path(audio_file)

    try:
        diarizer = SpeakerDiarizer(
            hf_token=hf_token,
            whisper_model=whisper_model
        )
    except Exception as e:
        click.echo(f"Error initializing: {e}", err=True)
        click.echo("\nRequired packages:", err=True)
        click.echo("  pip install pyannote.audio openai-whisper torch torchaudio", err=True)
        sys.exit(1)

    # Parse speaker names
    speaker_names = speakers.split(',') if speakers else None

    # Process audio
    click.echo("\nProcessing audio...")
    segments = diarizer.process(
        audio_path,
        num_speakers=num_speakers,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        speaker_names=speaker_names
    )

    # Format output
    title = audio_path.stem.replace('_', ' ').replace('-', ' ').title()

    if output_format == 'markdown':
        result = format_as_markdown(segments, title)
        default_ext = '.md'
    elif output_format == 'json':
        result = format_as_json(segments)
        default_ext = '.json'
    else:  # srt
        result = format_as_srt(segments)
        default_ext = '.srt'

    # Write output
    if output:
        output_path = Path(output)
    else:
        output_path = audio_path.with_suffix(default_ext)

    output_path.write_text(result, encoding='utf-8')
    click.echo(f"\nTranscript saved to: {output_path}")

    # Summary
    speakers_found = len(set(seg['speaker'] for seg in segments))
    click.echo(f"Found {speakers_found} speakers, {len(segments)} segments")


if __name__ == '__main__':
    main()
