#!/usr/bin/env python3
"""ask_glm — طبقة احتياطية مجانية/رخيصة خلف DeepSeek.

يستخدم GLM 5.3 Flash عبر Merge Gateway (عرض 90% off حتى نهاية سبتمبر 2026).
الرابط الصحيح: api-gateway.merge.dev/v1/openai/chat/completions
المفتاح: /root/.hermes/secrets/glm_merge.key

الاستخدام:
  from ask_glm import ask_glm
  print(ask_glm("اكتب كود بايثون..."))
"""
import json
import urllib.request
import urllib.error

MERGE_KEY_FILE = "/root/.hermes/secrets/glm_merge.key"
MERGE_URL = "https://api-gateway.merge.dev/v1/openai/chat/completions"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def _load_key():
    try:
        return open(MERGE_KEY_FILE).read().strip()
    except Exception:
        return ""


def ask_glm(prompt, model="glm-5.3-flash", max_tokens=800):
    """يرسل prompt لـ GLM عبر Merge Gateway ويرجّع النص أو رسالة خطأ."""
    key = _load_key()
    if not key:
        return "❌ مفتاح GLM/Merge غير موجود في /root/.hermes/secrets/glm_merge.key"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        MERGE_URL, data=payload,
        headers={"Content-Type": "application/json",
                  "Authorization": f"Bearer {key}",
                  "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        return f"❌ GLM HTTP {e.code}: {e.read().decode()[:150]}"
    except Exception as e:
        return f"❌ GLM خطأ: {str(e)[:120]}"


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "قل: مرحبا"
    print(ask_glm(q))
