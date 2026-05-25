---
name: arabic-video-transcription
description: Download Arabic videos from Google Drive/YouTube, extract audio, and transcribe to text using local faster-whisper. Zero API cost, zero tokens for transcription step.
triggers:
  - user sends video for transcription
  - تحويل فديو لنص
  - استخراج نص من فديو عربي
  - trading video analysis / strategy extraction
  - تحليل فديوهات تعليمية
  - video to Arabic text
---

# Arabic Video Transcription Pipeline

Download, extract audio, and transcribe Arabic videos using 100% local tools — zero API tokens for transcription.

## Prerequisites

```bash
python3 -m venv voice-pro
source voice-pro/bin/activate
pip install yt-dlp faster-whisper
```

Required system tools: `ffmpeg`, `ffprobe`

## Download Options

### SSH Direct Transfer from A6 (BEST — zero upload time) ✅

When videos are on the user's A6 Windows machine and SSH is configured:

```bash
# Credentials
A6_USER="adel.966"          # Note: lowercase! whoami = a6\adel.966
A6_PASS="207676"
A6_IP="100.69.168.86"
A6_PROFILE="C:\\Users\\adel9"  # Windows profile ≠ SSH username!
A6_VIDEOS="C:\\Users\\adel.966\\adel.a6"  # Trading videos folder (user moved here from OneDrive)

# List files
sshpass -p "$A6_PASS" ssh -o StrictHostKeyChecking=no \
  $A6_USER@$A6_IP "dir \"$A6_PROFILE\\Desktop\\FOLDER\" /b"

# Download via SCP
sshpass -p "$A6_PASS" scp -o StrictHostKeyChecking=no \
  "$A6_USER@$A6_IP:$A6_PROFILE\\Desktop\\FOLDER\\video*.mp4" /tmp/videos/
```

**CRITICAL:** The Windows SSH username (`Adel.966`) does NOT match the profile folder (`C:\Users\\adel9`). Always check with `echo %USERPROFILE%` over SSH.

**PITFALL: PowerShell `$_` variables in inline SSH commands** — When running `powershell -Command` over SSH, bash expands `$_` as an empty environment variable BEFORE PowerShell sees it. This mangles computed properties like `@{N='Size';E={[math]::Round($_.Length/1MB,1)}}` into `@{N='Size';E={[math]::Round(/root.Length/1MB,1)}}` (syntactic garbage). **Fix:** Use only built-in properties (`Name, LastWriteTime, Length`) without calculated columns, OR escape with backtick: `` `$_.Length ``. Simple `Length` raw bytes + manual MB calc on your side is safer.

### Telegram Private Channel (NEW — pipeline WIP) 🚧

User can send videos from iPhone via Telegram private channel to avoid Google Drive upload time. Hermes's bot (`@Ardadi_ai_bot`, NOT `@hermes_fazza_bot`) must be admin.

Channel: invite link `t.me/+76pfJntRmAsyYWQ0`. Bot is added as admin with full permissions.

**WARNING:** Video attachments in Telegram channels are not auto-downloaded to the server. The download step is still being worked out. Test with a small file first. See `fazza-router` skill → `references/telegram-channel-video-pipeline.md` for full setup instructions, pitfalls, and SSH fallback.

### Google Drive (works, slower, reliable) ✅

YouTube blocks yt-dlp as of May 2026. Use Google Drive — user uploads video as "Anyone with the link."

**Method 1: curl direct (BEST — bypasses virus scan)** ✅

For files >25MB, Google Drive shows a virus scan warning that Python `requests` can't bypass. Use curl:

```bash
curl -L -o /tmp/video.mp4 \
  "https://drive.usercontent.google.com/download?id=FILE_ID&export=download&confirm=t"
```

**Method 2: Python requests (for smaller files only)**

```python
import requests, re, os

file_id = "EXTRACT_FROM_URL"
output = "/tmp/video.mp4"
session = requests.Session()

url = f"https://drive.google.com/uc?id={file_id}&export=download"
response = session.get(url, stream=True)

# Handle confirm token for large files
confirm_token = None
for key, value in response.cookies.items():
    if key.startswith("download_warning"):
        confirm_token = value; break
if not confirm_token:
    match = re.search(r"confirm=([0-9A-Za-z_]+)", response.text)
    if match: confirm_token = match.group(1)

if confirm_token:
    url = f"https://drive.google.com/uc?id={file_id}&export=download&confirm={confirm_token}"
    response = session.get(url, stream=True)

# Check for HTML response (virus scan / login page)
first_bytes = response.content[:200]
if b"html" in first_bytes[:200].lower():
    print("ERROR: Got HTML — fall back to curl method")
else:
    with open(output, "wb") as f:
        f.write(response.content)
```

### YouTube (BLOCKED — May 2026)

yt-dlp requires cookies/OAuth. Even with Deno JS runtime, YouTube returns "Sign in to confirm you're not a bot." **Use Google Drive instead.**

## Audio Extraction

```bash
ffmpeg -y -i video.mp4 -vn -ar 16000 -ac 1 audio.wav
```

## Transcription (faster-whisper)

### Recommended: Use the script (avoids shell-profile issues)

```bash
# Save the helper script (already saved in the skill's scripts/)
# /root/.hermes/skills/media/arabic-video-transcription/scripts/transcribe.py

# Basic usage:
python3 /root/.hermes/skills/media/arabic-video-transcription/scripts/transcribe.py \
  /tmp/audio.wav /tmp/transcript.txt

# If output is empty, script auto-retries without VAD filter
```

### What the script does (equivalent inline code):

```python
from faster_whisper import WhisperModel

model = WhisperModel('base', device='cpu', compute_type='int8')
segments, info = model.transcribe('audio.wav', language='ar', 
                                   beam_size=5, vad_filter=True,
                                   vad_parameters=dict(min_silence_duration_ms=500))

for seg in segments:
    print(f"[{seg.start:.0f}s] {seg.text.strip()}")
```

### Why the script is better than inline `-c`

When running in `terminal(background=true)`, the shell's profile (`.bashrc`, `.zshrc`) 
loads BEFORE the `-c` argument runs. On this server, the profile prints 
`"✅ تم تحميل اختصارات نظام فزاع للمهام"` plus `"EOF: command not found"` — 
these pollute the output redirect. A dedicated script file has clean stdout/stderr.

## Model Selection

| Model | Speed (22min audio) | Arabic Quality | Use Case |
|-------|---------------------|----------------|----------|
| `tiny` | ~2.5 min | Mediocre — garbled words, missing phrases | Quick scan, topic detection |
| `base` | ~3.5 min | Good — clear sentences, minor errors | Strategy extraction, analysis ✅ |
| `small` | ~8 min | Better — but slower | Precision work |

**Default: `base`** — best balance for Arabic strategy extraction.

Real-world benchmarks (CPU, 12GB RAM, Intel):
- 22min video → ~3.7min (base model)
- 33min video → ~5.5min (base model)

## Concurrency Limits (LOW-RAM / LOW-CPU HOSTS)

This server has **2 cores + 3.7GB RAM** (3.5GB usable). Each faster-whisper `base` 
model instance uses **~1.7GB RAM at peak** (model loading). After loading, 
memory drops to ~500-600MB for transcription. **Max 1 concurrent process** — 
even 2 causes OOM killer (exit code 137/SIGKILL).

### Batch sizing guide per host spec

| CPU cores | RAM     | Max concurrent | Notes                          |
|-----------|---------|----------------|--------------------------------|
| 2         | ≤4 GB   | **1**          | One `base` at a time — OOM if 2|
| 4         | 8 GB    | 2-3            | `small` model may strain       |
| 8+        | 16+ GB  | 5-8            | `small` model fine             |

### Workflow for batch processing

```bash
# 1. Extract all audio first (sequential — fast, negligible CPU)
for f in *.mp4; do ffmpeg -y -i "$f" -vn -ar 16000 -ac 1 "${f%.mp4}.wav"; done

# 2. Transcribe ONE at a time (memory constraint)
terminal background=true notify_on_complete=true -- \
  python3 /path/to/transcribe.py video1.wav t1.txt

# 3. Wait for completion BEFORE starting next
process action=wait session_id=proc_xxx
# OR poll periodically
process action=poll session_id=proc_xxx

# 4. Start next only after previous finished
terminal background=true notify_on_complete=true -- \
  python3 /path/to/transcribe.py video2.wav t2.txt
```

### Handling Timeouts / Interruptions

Long videos (>60 min) often exceed the gateway's timeout. If a transcription 
is killed mid-way (SIGKILL/exit 137 or exit 143):

1. **Check how far it got** — look at the last timestamp in the partial output:
   ```bash
   tail -5 partial.txt
   # e.g. [2845s] some text
   ```

2. **Extract the remaining audio** from where it stopped:
   ```bash
   ffmpeg -y -ss 2845 -i original.wav remaining.wav
   ```

3. **Transcribe the remaining chunk** (with --no-vad):
   ```bash
   python3 /path/to/transcribe.py remaining.wav part2.txt --no-vad
   ```

4. **Concatenate results**:
   ```bash
   cat partial.txt part2.txt > full.txt
   ```

This split technique works because faster-whisper segments are timestamped, 
so `cat` produces a seamless transcript without duplication.

### What NOT to do

- ❌ Do NOT run multiple transcribe jobs simultaneously on ≤4GB RAM — OOM kills all
- ❌ Do NOT use `terminal(foreground)` for long audio (>600s max foreground timeout)
- ❌ Do NOT rely on `notify_on_complete` alone — poll periodically as fallback
- ❌ Do NOT use `python3 -c "..."` in background mode — shell profile prints pollute output

## Handling Duplicate / Near-Identical Videos

When processing a batch from the same source (e.g., multiple takes of same 
tutorial), compare transcripts to detect duplicates:

```bash
# Quick byte-size comparison (same topic ≈ similar size)
wc -c t_*.txt

# Content comparison via diff
diff <(head -20 t_04.txt) <(head -20 t_16.txt)
```

Flag duplicates to the user and exclude from final reports unless requested.

## Venv Path (CRITICAL)

faster-whisper is installed in `/root/voice-pro/`. The `execute_code` sandbox uses a different Python. Always run transcription via `terminal` with the explicit venv path:

```bash
/root/voice-pro/bin/python3 -c "..."
```

NOT: `execute_code` or plain `python3`.

## Token Cost

| Step | API Tokens |
|------|------------|
| Download | 0 |
| Audio extraction | 0 |
| faster-whisper transcription | **0** (100% local) |
| Analysis of extracted text | ~2000 per 20min video |

11 videos ≈ 25K tokens total for analysis only.

## FFmpeg Video Creation (Text → Video)

Build cinematic text-overlay videos using pure ffmpeg. **For English/non-complex-script text only.** 
Arabic text in ffmpeg drawtext produces hollow squares (□□□) — use HTML/CSS + browser screenshot 
pipeline for Arabic text video instead (see pitfall below).

### Quick Start

```bash
# Generate dark cinematic background
ffmpeg -f lavfi -i "color=c=0x0d0b2e:s=1920x1080:d=5:r=30" \
  -vf "vignette=PI/4" -pix_fmt yuv420p -crf 10 -t 5 bg.mp4

# Add text with fade animation
ffmpeg -i bg.mp4 -vf \
  "drawtext=fontfile=/path/to/font.ttf:text='Title':fontcolor=white:fontsize=56:\
   x=(w-text_w)/2:y=(h-text_h)/2:\
   alpha='if(lt(t,0.5),t/0.5,if(gt(t,4.5),(5-t)/0.5,1))'" \
  -pix_fmt yuv420p -t 5 scene.mp4

# Concatenate scenes (demuxer — simpler than xfade)
ffmpeg -f concat -safe 0 -i list.txt -c copy output.mp4

# Final encode with faststart for web streaming
ffmpeg -i concat.mp4 -c:v libx264 -crf 17 -preset medium \
  -pix_fmt yuv420p -movflags +faststart final.mp4
```

Full recipes, animation patterns, glow effects, and pitfalls in `references/ffmpeg-cinematic-recipes.md`.
Working 7-scene Python builder at `scripts/build-cinematic-video.py` (Taibah University workshop, 2026-05-05).

## OpenMontage & Advanced Video Production

OpenMontage is an open-source agentic video production system (9-stage pipeline). For quick Arabic video production without API keys, skip the full pipeline and use Edge TTS + ffmpeg directly.

### OpenMontage Setup (Linux, no GPU)

```bash
cd ~ && git clone https://github.com/calesthio/OpenMontage.git
cd OpenMontage
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install numpy opencv-python-headless  # missing from requirements.txt
.venv/bin/pip install piper-tts yt-dlp youtube-transcript-api edge-tts
```

### Arabic Voiceover — Edge TTS (Free, No API Keys)

```bash
edge-tts --voice "ar-SA-HamedNeural" --text "النص العربي هنا" --write-media scene.mp3
```

Available Arabic voices: `ar-SA-HamedNeural` (male), `ar-SA-ZariyahNeural` (female).

### Arabic Slides — FFmpeg drawtext (Fix: Arabic works!)

Contrary to the standard drawtext limitation (hollow squares for complex scripts), **Arabic text DOES render correctly** with Noto Sans Arabic fonts installed on this server:

```bash
# Verify fonts available
fc-list :lang=ar

# Generate slide with Arabic title + subtitle
ffmpeg -y -f lavfi -i color=c=#0a1628:s=1920x1080:d=1 \
  -vf "drawtext=text='العنوان':fontcolor=#D4AF37:fontsize=72:\
x=(w-text_w)/2:y=(h-text_h)/2-80:\
fontfile=/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf, \
drawtext=text='الوصف':fontcolor=white:fontsize=40:\
x=(w-text_w)/2:y=(h-text_h)/2+40:\
fontfile=/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf" \
  -frames:v 1 scene1.png
```

See `references/arabic-slides-recipe.md` for color schemes, batch generation, and centering patterns.

### Audio Concatenation

```bash
ffmpeg -y -i scene1.mp3 -i scene2.mp3 -i scene3.mp3 \
  -filter_complex "[0:a][1:a][2:a]concat=n=3:v=0:a=1[a]" \
  -map "[a]" narration_full.mp3
```

### Final Video Compositing — concat (NOT xfade)

⚠️ xfade chain causes frame drops and clipping. Use concat filter instead:

```bash
ffmpeg -y \
  -loop 1 -t 8.83 -i scene1.png \
  -loop 1 -t 6.77 -i scene2.png \
  -i narration_full.mp3 \
  -filter_complex "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=25,format=yuv420p[v0];\
[1:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=25,format=yuv420p[v1];\
[v0][v1]concat=n=2:v=1:a=0,format=yuv420p[vout]" \
  -map "[vout]" -map 2:a \
  -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k -shortest \
  output.mp4
```

### OpenMontage Problems & Solutions

| Problem | Cause | Fix |
|---------|-------|-----|
| `pip install` fails with `externally-managed-environment` | PEP 668 | Use venv: `.venv/bin/pip install` |
| `numpy` missing | Not in requirements.txt | `.venv/bin/pip install numpy opencv-python-headless` |
| FAL_KEY/Nous subscription doesn't work | OpenMontage has its own env system | Use Edge TTS + ffmpeg drawtext for free Arabic production |
| Pixabay Music API returns error | Key expired or API changed | Skip music or use alternative |
| xfade chain clips video mid-way | Frame drops from offset calculations | Use concat filter instead of xfade |

### When to Use Full Pipeline vs Quick

- **Quick** (Edge TTS + ffmpeg): experiments, demos, <1 min videos, no API keys
- **Full** (OpenMontage 9-stage): professional production, complex videos, needs AI-generated images, professional music

## Pitfalls

- **Telegram videos NOT auto-saved** → Telegram video attachments are NOT downloaded to the server filesystem. User must use Google Drive \"Anyone with the link\" or send as File/Document. Do NOT attempt to find Telegram-sent videos on disk — they won't be there.
- **Google Drive: virus scan warning** → For files >25MB, Google shows a virus scan warning instead of the file. Python `requests` gets HTML, not video. Use `curl -L` with the `drive.usercontent.google.com` direct URL + `&confirm=t` — this bypasses the warning. See Download Options section.
- **Google Drive: file not public** → gdown and curl fail with HTML login page. User MUST set "Anyone with the link" in Share settings. Verify by checking if response is HTML before processing.
- **faster-whisper venv path** → installed in `/root/voice-pro/`. The `execute_code` sandbox uses a different Python/venv. Always use `terminal` with `/root/voice-pro/bin/python3` for transcription.
- **faster-whisper first run downloads model** (~150MB for base). Ensure disk space.
- **VAD filter cuts filler words** — with `min_silence_duration_ms=500`, pauses >500ms are used as segment boundaries. Good for Arabic speech flow.
- **ffprobe may not be installed** — `apt install ffprobe` or skip duration check.
- **YouTube is dead for yt-dlp** — don't waste time. Even with Deno JS runtime, YouTube returns "Sign in to confirm you're not a bot." Use Google Drive.
- **Long videos on CPU** — 33min audio takes ~5.5min with base model. Use `terminal` with `background=true` and `notify_on_complete=true` to avoid blocking.
- **Telegram private channel: bot must join as member FIRST** — For private Telegram channels, adding the bot (@Ardadi_ai_bot) as admin directly does NOT work. It must be added as a subscriber/member FIRST via "Add Members", THEN promoted to admin. Otherwise the bot never receives channel messages.
- **VAD filter may produce ZERO segments** — If a video has sparse speech (e.g., only a few words, or the person speaks softly, or background noise is high), the VAD filter can filter EVERYTHING out. The model reports "NO SEGMENTS FOUND" with correct language detection. **Fix:** Retry with `vad_filter=False` (i.e. `--no-vad` flag in the script). The script does this automatically on empty output.
- **VAD filter FREEZES on long audio files (>30 min)** — On files >30 minutes, VAD filter causes faster-whisper to stall silently (process stays in 'S' sleeping state, no CPU activity, no output growth). The process appears alive but is deadlocked internally. **Fix:** Always use `--no-vad` for audio files longer than 30 minutes. See "Handling Timeouts / Interruptions" for split technique if a long file was already partially transcribed with VAD enabled.
- **Shell profile pollutes background terminal output** — When running `terminal(background=true)` with `python3 -c "...", the shell profile (`~/.bashrc`) prints "✅ تم تحميل اختصارات…" before Python runs. This mixes into the redirected output file. **Fix:** Use a dedicated script file (like `scripts/transcribe.py`) instead of inline `-c`.
- **Duplicate detection** — Batches of videos from the same source often contain duplicate/near-identical takes. Compare file sizes + head content to detect. **User preference:** احذف المكرره فوراً بدون ما تسأل أو تذكرها في التقرير. Just delete them silently, no report mention.
