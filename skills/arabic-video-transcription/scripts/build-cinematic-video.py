#!/usr/bin/env python3
"""
Complete cinematic video builder — Taibah University AI Workshop
7 scenes, 35 seconds, no audio, 1920x1080@30fps
Proven working 2026-05-05 against Hermes environment.

IMPORTANT: ffmpeg drawtext with Arabic text frequently renders as hollow
squares (□□□) due to missing complex text shaping support. This script
worked on 2026-05-05 but may produce boxes on other systems/environments.
For reliable Arabic text video, prefer HTML/CSS + browser screenshot pipeline.
"""
import subprocess, os

OUTPUT = "/root/taibah-workshop-video/taibah-cinematic.mp4"
TMP = "/tmp/taibah-scenes"
os.makedirs(TMP, exist_ok=True)

W, H = 1920, 1080
BG = "0x0d0b2e"
CYAN = "0x00e5ff"
GOLD = "0xffb74d"
WHITE = "white"
DIM = "0x8080aa"
FONT_TITLE = "/usr/share/fonts/truetype/noto/NotoKufiArabic-Black.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSansArabic-CondensedBold.ttf"
FONT_REG = "/usr/share/fonts/truetype/noto/NotoSansArabicUI-Regular.ttf"
FONT_NASKH = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf"

def ff(args, desc=""):
    print(f"  {desc}...", end=" ")
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args,
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"FAIL: {r.stderr.strip()[-250:]}")
        return False
    print("OK")
    return True

def make_bg(dur):
    """Solid dark bg with vignette. Uses -vf NOT -f lavfi -i geq (which fails)."""
    out = f"{TMP}/bg_{dur}.mp4"
    ff(["-f","lavfi","-i",f"color=c={BG}:s={W}x{H}:d={dur}:r=30",
        "-vf","vignette=PI/4","-pix_fmt","yuv420p",
        "-c:v","libx264","-crf","10","-t",str(dur),out], f"BG {dur}s")
    return out

# Build backgrounds (cache for reuse)
bgs = {}
for d in [3,4,5,8]:
    bgs[d] = make_bg(d)

scenes = []

# S1: Logo (0-4s)
s1 = f"{TMP}/s1.mp4"
dts1 = [
    f"drawtext=fontfile={FONT_TITLE}:text='جامعة طيبة':fontcolor=white:fontsize=68:x=(w-text_w)/2:y=(h-text_h)/2-50:alpha='if(lt(t,0.5),t/0.5,if(gt(t,3.5),(4-t)/0.5,1))'",
    f"drawtext=fontfile={FONT_REG}:text='عمادة التطوير والجودة':fontcolor={DIM}:fontsize=36:x=(w-text_w)/2:y=(h-text_h)/2+40:alpha='if(lt(t,0.8),0,if(lt(t,1.3),(t-0.8)/0.5,if(gt(t,3.5),(4-t)/0.5,1)))'",
]
ff(["-i",bgs[4],"-vf",",".join(dts1),"-pix_fmt","yuv420p","-c:v","libx264","-crf","18","-t","4",s1], "S1 Logo")
scenes.append(s1)

# S2: Title (4-11s)
s2 = f"{TMP}/s2.mp4"
dts2 = [
    f"drawtext=fontfile={FONT_TITLE}:text='مبادرة':fontcolor=0x00e5ff:fontsize=60:x=(w-text_w)/2:y=(h-text_h)/2-70:alpha='if(lt(t,0.4),t/0.4,if(gt(t,6.5),(7-t)/0.5,1))':shadowcolor=0x00e5ff@0.3:shadowx=0:shadowy=0",
    f"drawtext=fontfile={FONT_BOLD}:text='فرص وتطبيقات الذكاء الاصطناعي':fontcolor=white:fontsize=44:x=(w-text_w)/2:y=(h-text_h)/2+20:alpha='if(lt(t,0.9),0,if(lt(t,1.5),(t-0.9)/0.6,if(gt(t,6.2),(7-t)/0.8,1)))'",
    f"drawtext=fontfile={FONT_REG}:text='---  رصد · تقييم · تفعيل الفرص ذات الأثر  ---':fontcolor=0xffb74d:fontsize=26:x=(w-text_w)/2:y=(h-text_h)/2+90:alpha='if(lt(t,1.8),0,if(lt(t,2.3),(t-1.8)/0.5,if(gt(t,5.8),(7-t)/1.2,1)))'",
]
ff(["-i",bgs[8],"-vf",",".join(dts2),"-pix_fmt","yuv420p","-c:v","libx264","-crf","18","-t","7",s2], "S2 Title")
scenes.append(s2)

# S3: Pillars (11-15s)
s3 = f"{TMP}/s3.mp4"
dts3 = [
    f"drawtext=fontfile={FONT_TITLE}:text='رصد  ·  تقييم  ·  تفعيل':fontcolor=0x00e5ff:fontsize=54:x=(w-text_w)/2:y=(h-text_h)/2-40:alpha='if(lt(t,0.3),t/0.3,if(gt(t,3.7),(4-t)/0.3,1))'",
    f"drawtext=fontfile={FONT_BOLD}:text='الفرص ذات الأثر':fontcolor=0xffb74d:fontsize=40:x=(w-text_w)/2:y=(h-text_h)/2+40:alpha='if(lt(t,0.6),0,if(lt(t,1.0),(t-0.6)/0.4,if(gt(t,3.5),(4-t)/0.5,1)))'",
]
ff(["-i",bgs[4],"-vf",",".join(dts3),"-pix_fmt","yuv420p","-c:v","libx264","-crf","18","-t","4",s3], "S3 Pillars")
scenes.append(s3)

# S4: Presenter (15-20s)
s4 = f"{TMP}/s4.mp4"
dts4 = [
    f"drawtext=fontfile={FONT_REG}:text='تقديم':fontcolor={DIM}:fontsize=30:x=(w-text_w)/2:y=(h-text_h)/2-120:alpha='if(lt(t,0.3),t/0.3,if(gt(t,4.7),(5-t)/0.3,1))'",
    f"drawtext=fontfile={FONT_NASKH}:text='د. رانيا بنت جمعة العوفي':fontcolor=white:fontsize=50:x=(w-text_w)/2:y=(h-text_h)/2-50:alpha='if(lt(t,0.5),0,if(lt(t,1.0),(t-0.5)/0.5,if(gt(t,4.5),(5-t)/0.5,1)))'",
    f"drawtext=fontfile={FONT_REG}:text='مشرفة إدارة البحث العلمي':fontcolor=0x00e5ff:fontsize=32:x=(w-text_w)/2:y=(h-text_h)/2+30:alpha='if(lt(t,1.0),0,if(lt(t,1.5),(t-1.0)/0.5,if(gt(t,4.3),(5-t)/0.7,1)))'",
    f"drawtext=fontfile={FONT_REG}:text='وكالة الجامعة للدراسات العليا والبحث العلمي':fontcolor={DIM}:fontsize=26:x=(w-text_w)/2:y=(h-text_h)/2+80:alpha='if(lt(t,1.5),0,if(lt(t,2.0),(t-1.5)/0.5,if(gt(t,4.0),(5-t)/1.0,1)))'",
]
ff(["-i",bgs[5],"-vf",",".join(dts4),"-pix_fmt","yuv420p","-c:v","libx264","-crf","18","-t","5",s4], "S4 Presenter")
scenes.append(s4)

# S5: 7 Domains (20-28s)
s5 = f"{TMP}/s5.mp4"
domains = ["البحث العلمي والابتكار","الإنتاجية الإدارية","الخدمات الطلابية","تجربة التعلم","دعم القرار القيادي","المناهج والمحتوى","الحوكمة والأخلاقيات"]
icons = ["🔬","📊","🎓","📚","🏛️","📖","⚖️"]
dts5 = [f"drawtext=fontfile={FONT_BOLD}:text='٧ مجالات حيوية':fontcolor=0x00e5ff:fontsize=44:x=(w-text_w)/2:y=70:alpha='if(lt(t,0.3),t/0.3,if(gt(t,7.7),(8-t)/0.3,1))'"]
for i,(dom,ic) in enumerate(zip(domains,icons)):
    row, col = i//2, i%2
    x, y = 220 + col*820, 220 + row*125
    delay = 0.6 + i*0.35
    dts5.append(f"drawtext=fontfile={FONT_REG}:text='{ic}  {dom}':fontcolor=white:fontsize=28:x={x}:y={y}:alpha='if(lt(t,{delay}),0,if(lt(t,{delay+0.5}),(t-{delay})/0.5,if(gt(t,7.5),(8-t)/0.5,1)))'")
ff(["-i",bgs[8],"-vf",",".join(dts5),"-pix_fmt","yuv420p","-c:v","libx264","-crf","18","-t","8",s5], "S5 Domains")
scenes.append(s5)

# S6: Details (28-32s)
s6 = f"{TMP}/s6.mp4"
dts6 = [
    f"drawtext=fontfile={FONT_BOLD}:text='📅  الأربعاء 19 ذو القعدة':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=(h-text_h)/2-80:alpha='if(lt(t,0.3),t/0.3,if(gt(t,3.7),(4-t)/0.3,1))'",
    f"drawtext=fontfile={FONT_BOLD}:text='⏰  9:00 - 10:00 مساءً':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=(h-text_h)/2-10:alpha='if(lt(t,0.5),0,if(lt(t,0.9),(t-0.5)/0.4,if(gt(t,3.5),(4-t)/0.5,1)))'",
    f"drawtext=fontfile={FONT_BOLD}:text='💻  Microsoft Teams':fontcolor=0x00e5ff:fontsize=42:x=(w-text_w)/2:y=(h-text_h)/2+60:alpha='if(lt(t,0.9),0,if(lt(t,1.3),(t-0.9)/0.4,if(gt(t,3.3),(4-t)/0.7,1)))'",
]
ff(["-i",bgs[4],"-vf",",".join(dts6),"-pix_fmt","yuv420p","-c:v","libx264","-crf","18","-t","4",s6], "S6 Details")
scenes.append(s6)

# S7: CTA (32-35s)
s7 = f"{TMP}/s7.mp4"
dts7 = [
    f"drawtext=fontfile={FONT_TITLE}:text='لا تفوّت الفرصة':fontcolor=0xffb74d:fontsize=64:x=(w-text_w)/2:y=(h-text_h)/2-70:alpha='if(lt(t,0.3),t/0.3,if(gt(t,2.7),(3-t)/0.3,1))':shadowcolor=0xffb74d@0.25:shadowx=0:shadowy=0",
    f"drawtext=fontfile={FONT_REG}:text='سجّل الآن .. وكن جزءاً من صناعة المستقبل':fontcolor=white:fontsize=34:x=(w-text_w)/2:y=(h-text_h)/2+20:alpha='if(lt(t,0.5),0,if(lt(t,0.9),(t-0.5)/0.4,if(gt(t,2.5),(3-t)/0.5,1)))'",
    f"drawtext=fontfile={FONT_BOLD}:text='    تسجيل    ':fontcolor=0x0d0b2e:fontsize=40:x=(w-text_w)/2:y=(h-text_h)/2+90:box=1:boxcolor=0x00e5ff@0.85:boxborderw=20:alpha='if(lt(t,0.8),0,if(lt(t,1.3),(t-0.8)/0.5,if(gt(t,2.5),(3-t)/0.5,1)))'",
]
ff(["-i",bgs[3],"-vf",",".join(dts7),"-pix_fmt","yuv420p","-c:v","libx264","-crf","18","-t","3",s7], "S7 CTA")
scenes.append(s7)

# Concatenate with demuxer (reliable, no xfade complexity)
list_file = f"{TMP}/list.txt"
with open(list_file, 'w') as f:
    for s in scenes:
        f.write(f"file '{s}'\n")

concat = f"{TMP}/concat.mp4"
ff(["-f","concat","-safe","0","-i",list_file,"-c","copy",concat], "Concat")

# Final re-encode for faststart
ff(["-i",concat,"-c:v","libx264","-crf","17","-preset","medium",
    "-pix_fmt","yuv420p","-movflags","+faststart",OUTPUT], "Final")

if os.path.exists(OUTPUT):
    print(f"\nDONE: {OUTPUT} ({os.path.getsize(OUTPUT)/(1024*1024):.1f}MB)")
