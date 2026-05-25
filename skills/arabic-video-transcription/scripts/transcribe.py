#!/usr/bin/env python3
"""
Transcribe a WAV audio file to text using faster-whisper (Arabic-optimized).

Usage:
    python3 transcribe.py input.wav output.txt [--no-vad]

Options:
    --no-vad    Disable VAD filter (use if output is empty; the VAD may be
                too aggressive for quiet/sparse-audio recordings)

Output format:
    [seconds] text line
    One line per detected segment, with timestamp in seconds.
"""

from faster_whisper import WhisperModel
import sys
import os

def transcribe(wav_path: str, out_path: str, use_vad: bool = True):
    model = WhisperModel('base', device='cpu', compute_type='int8')
    
    vad_params = dict(min_silence_duration_ms=500) if use_vad else None
    
    segments, info = model.transcribe(
        wav_path,
        language='ar',
        beam_size=5,
        vad_filter=use_vad,
        vad_parameters=vad_params,
    )
    
    count = 0
    with open(out_path, 'w', encoding='utf-8') as f:
        for seg in segments:
            count += 1
            line = f'[{seg.start:.0f}s] {seg.text.strip()}'
            print(line)
            f.write(line + '\n')
    
    # Fallback: if VAD produced nothing, try without VAD
    if count == 0 and use_vad:
        no_vad_path = out_path.replace('.txt', '_novad.txt')
        print(f"WARNING: VAD produced 0 segments. Retrying without VAD → {no_vad_path}")
        transcribe(wav_path, no_vad_path, use_vad=False)
        return
    
    print(f"Done: {count} segments from {info.duration:.0f}s audio "
          f"(lang={info.language}, prob={info.language_probability:.2f})")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: transcribe.py <input.wav> <output.txt> [--no-vad]")
        sys.exit(1)
    
    wav = sys.argv[1]
    out = sys.argv[2]
    no_vad = '--no-vad' in sys.argv
    
    if not os.path.exists(wav):
        print(f"ERROR: Input file not found: {wav}")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    
    transcribe(wav, out, use_vad=not no_vad)
