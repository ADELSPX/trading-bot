# FFmpeg Cinematic Text Video Recipes

Recipes for building professional text-overlay videos with pure ffmpeg. 
These work for English and non-complex-script text. For Arabic text, prefer
HTML/CSS + browser screenshot pipeline — ffmpeg's drawtext filter does not
support complex text shaping required for Arabic ligatures (verified May 2026:
Noto Kufi/Naskh Arabic fonts produce hollow squares □□□).

## Color Palette (cinematic dark)

```
BG   = 0x0d0b2e   (deep navy)
CYAN = 0x00e5ff   (neon cyan accent)
GOLD = 0xffb74d   (warm gold highlight)
DIM  = 0x8080aa   (muted text)
```

## Fonts (Hermes environment)

| Font | Path | Use |
|------|------|-----|
| Noto Kufi Arabic Black | `/usr/share/fonts/truetype/noto/NotoKufiArabic-Black.ttf` | Bold titles |
| Noto Sans Arabic Condensed Bold | `/usr/share/fonts/truetype/noto/NotoSansArabic-CondensedBold.ttf` | Headlines |
| Noto Sans Arabic UI Regular | `/usr/share/fonts/truetype/noto/NotoSansArabicUI-Regular.ttf` | Body text |
| Noto Naskh Arabic Bold | `/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf` | Elegant text |

## Recipe 1: Background Clip

```bash
ffmpeg -f lavfi -i "color=c=0x0d0b2e:s=1920x1080:d=5:r=30" \
  -vf "vignette=PI/4" \
  -pix_fmt yuv420p -c:v libx264 -crf 10 -t 5 bg.mp4
```

## Recipe 2: Scene with Drawtext + Alpha Animation

```bash
ffmpeg -i bg.mp4 -vf \
  "drawtext=fontfile=/path/to/font.ttf:text='Title Text':fontcolor=white:fontsize=56:\
   x=(w-text_w)/2:y=(h-text_h)/2:\
   alpha='if(lt(t,0.5),t/0.5,if(gt(t,4.5),(5-t)/0.5,1))'" \
  -pix_fmt yuv420p -t 5 scene.mp4
```

### Alpha Animation Patterns

- **Fade in:** `alpha='if(lt(t,0.5),t/0.5,...)'` — linear 0→1 over first 0.5s
- **Fade out:** `if(gt(t,4.5),(5-t)/0.5,1)` — linear 1→0 over last 0.5s
- **Delayed reveal:** `if(lt(t,0.8),0,if(lt(t,1.3),(t-0.8)/0.5,...))` — invisible then fades in
- **Stay visible:** `1` — no transparency

## Recipe 3: Multi-line Scene

Chain multiple drawtext filters with commas. Each line has independent timing:

```bash
ffmpeg -i bg.mp4 -vf \
  "drawtext=...line1...,\
   drawtext=...line2...,\
   drawtext=...line3..." \
  -pix_fmt yuv420p -t 5 scene.mp4
```

## Recipe 4: Glow Effects (No Overlay Chains!)

**DO NOT chain overlay in -vf** — `drawtext=...,gblur=...,overlay=0:0` fails because 
overlay expects 2 inputs. Use drawtext's built-in shadow/border properties instead:

```bash
drawtext=...:shadowcolor=0x00e5ff@0.3:shadowx=0:shadowy=0:bordercolor=0x00e5ff@0.15:borderw=3
```

## Recipe 5: Concatenate Scenes (Demuxer Method)

The concat demuxer is simpler and more reliable than xfade:

```bash
# Create list file
echo "file '/tmp/scene1.mp4'
file '/tmp/scene2.mp4'
file '/tmp/scene3.mp4'" > list.txt

# Stream copy (if all scenes have same codec)
ffmpeg -f concat -safe 0 -i list.txt -c copy output.mp4

# Re-encode (if codecs differ)
ffmpeg -f concat -safe 0 -i list.txt -c:v libx264 -crf 18 -pix_fmt yuv420p output.mp4
```

## Recipe 6: Final Encode with faststart

```bash
ffmpeg -i concat.mp4 -c:v libx264 -crf 17 -preset medium \
  -pix_fmt yuv420p -movflags +faststart final.mp4
```

## Pitfalls

- **Arabic text → boxes:** ffmpeg drawtext does NOT support complex text shaping (Arabic ligatures).
  Use HTML/CSS + browser screenshot pipeline for Arabic text videos.
- **NO overlay chains in -vf:** Chaining drawtext with overlay and gblur fails. Use
  drawtext's shadowcolor/bordercolor for glow effects.
- **NO geq as lavfi input:** `-f lavfi -i "geq=..."` fails. Use `-vf geq=...` on an existing input.
- **Concat over xfade:** The concat demuxer (`-f concat`) is simpler and more reliable
  than `-filter_complex xfade=...` for joining scenes.
