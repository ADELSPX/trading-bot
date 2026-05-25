# وصفة السلايدات العربية بـ FFmpeg drawtext

## نمط السلايدة الأساسي

```bash
ffmpeg -y -f lavfi -i color=c=COLOR:s=1920x1080:d=1 \
  -vf "TEXTS" \
  -frames:v 1 OUTPUT.png
```

## الألوان المقترحة

| النمط | الخلفية | العنوان | النص |
|-------|---------|---------|------|
| احترافي داكن | `#0a1628` | `#D4AF37` (ذهبي) | أبيض |
| فاتح نظيف | `#f5f5f5` | `#1a1a2e` | `#333333` |
| تقني | `#0d1117` | `#58a6ff` | `#8b949e` |

## الخطوط العربية في النظام

```bash
# خطوط Noto Arabic (الافتراضية)
/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf
/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf

# للتأكد:
fc-list :lang=ar
```

## صيغة drawtext للعربي

```
drawtext=text='النص العربي':fontcolor=COLOR:fontsize=SIZE:\
x=(w-text_w)/2:y=(h-text_h)/2:fontfile=PATH
```

ملاحظة: `(w-text_w)/2` = توسيط أفقي، `(h-text_h)/2` = توسيط عمودي

## مثال: سلايدة بعنوان + وصف

```bash
ffmpeg -y -f lavfi -i color=c=#0a1628:s=1920x1080:d=1 \
  -vf "drawtext=text='العنوان الرئيسي':fontcolor=#D4AF37:fontsize=72:\
x=(w-text_w)/2:y=(h-text_h)/2-80:\
fontfile=/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf, \
drawtext=text='النص التوضيحي هنا':fontcolor=white:fontsize=40:\
x=(w-text_w)/2:y=(h-text_h)/2+40:\
fontfile=/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf" \
  -frames:v 1 slide.png
```

## توليد عدة سلايدات دفعة واحدة

```bash
N=1
for title in "الأول" "الثاني" "الثالث" "الرابع"; do
  ffmpeg -y -f lavfi -i color=c=#0a1628:s=1920x1080:d=1 \
    -vf "drawtext=text='$title':fontcolor=#D4AF37:fontsize=72:\
x=(w-text_w)/2:y=(h-text_h)/2:\
fontfile=/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf" \
    -frames:v 1 scene${N}.png
  N=$((N+1))
done
```
