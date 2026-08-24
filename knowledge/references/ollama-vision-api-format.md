# Ollama Vision API Format Reference

## The Core Finding

**Ollama vision models (especially older/smaller ones like Moondream) use the OLD `images` field format, NOT the new OpenAI-compatible multimodal `content` array.**

## Correct Format (works with Moondream, LLaVA, etc.)

```python
import json, urllib.request

image_base64 = "..."
data = json.dumps({
    "model": "moondream",  # or llava, bakllava, etc.
    "messages": [
        {
            "role": "user", 
            "content": "Describe this image in Arabic.",  # plain text
            "images": [image_base64]                      # ✅ old format
        }
    ],
    "stream": False
}).encode()

req = urllib.request.Request(
    "http://localhost:11434/api/chat",
    data=data,
    headers={"Content-Type": "application/json"}
)
resp = urllib.request.urlopen(req, timeout=60)
result = json.loads(resp.read())
print(result["message"]["content"])
```

## ❌ Wrong Format (returns 400 Bad Request)

```python
# THIS FAILS on Moondream and many Ollama vision models:
messages = [{"role": "user", "content": [
    {"type": "text", "text": "Describe this image."},
    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}}
]}]
```

The OpenAI-compatible multimodal format (`content` as an array of typed parts) only works with newer Ollama models like LLaVA-NeXT, Llama 3.2 Vision, and Gemma 3. **It does NOT work with Moondream, original LLaVA, or BakLLaVA.**

## Detection Pattern

Try the new format first → if 400 → fall back to old format:

```python
def call_ollama_vision(model, text, image_b64, ollama_host="http://localhost:11434"):
    """Try new format, fall back to old images format."""
    # Attempt 1: new multimodal format
    msg = {
        "role": "user", 
        "content": [
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
        ]
    }
    resp = _ollama_chat(model, [msg], ollama_host)
    if resp:
        return resp
    
    # Attempt 2: old images field format
    msg = {"role": "user", "content": text, "images": [image_b64]}
    return _ollama_chat(model, [msg], ollama_host)

def _ollama_chat(model, messages, host):
    import json, urllib.request
    data = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
    req = urllib.request.Request(f"{host}/api/chat", data=data, 
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read()).get("message", {}).get("content", "")
    except Exception:
        return ""
```

## Models Tested

| Model | Size | New Format | Old Format | Arabic | Charts |
|-------|------|-----------|-----------|--------|--------|
| Moondream | 1.7 GB | ❌ 400 | ✅ Works | Weak | ❌ Hallucinates |
| LLaVA 7B | 4.1 GB | ✅ Works | ✅ Works | Moderate | Better |
| LLaVA 13B | 7.5 GB | ✅ Works | ✅ Works | Good | Good |

## Smart Router Pattern (Windows)

A complete Python HTTP server on Windows that auto-detects text vs image and routes accordingly:

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import json, base64
from urllib.request import Request, urlopen

OLLAMA_HOST = "http://localhost:11434"
MODEL_TEXT = "nashmi"     # or your text model
MODEL_VISION = "moondream"  # or your vision model

class RouterHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        data = json.loads(body.decode("utf-8"))
        text = data.get("text", "")
        image_b64 = data.get("image_base64", "")
        
        if image_b64:
            # Old format for vision models
            messages = [{"role": "user", "content": text, "images": [image_b64]}]
            model = MODEL_VISION
        else:
            messages = [{"role": "user", "content": text}]
            model = MODEL_TEXT
        
        response = call_ollama(model, messages)
        self._respond(200, {"response": response, "model": model})

def call_ollama(model, messages):
    data = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
    req = Request(f"{OLLAMA_HOST}/api/chat", data=data, 
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=120) as resp:
        return json.loads(resp.read()).get("message", {}).get("content", "")
```

## Windows Auto-Start via Scheduled Task

```batch
schtasks /CREATE /SC ONLOGON /TN MyRouter /TR "C:\Python314\python.exe C:\Users\me\router.py" /RL HIGHEST /F
```

Key flags:
- `/SC ONLOGON` — starts when user logs in (not ONSTART which needs system context)
- `/TR` — command to run (full paths!)
- `/RL HIGHEST` — runs with highest privileges (needs password prompt, skip if headless)
- `/F` — force overwrite if exists

## Windows Console Encoding Pitfall

When writing Python scripts for Windows that print Unicode/Arabic/emoji from a service or scheduled task:

**Symptom:** `UnicodeEncodeError: 'charmap' codec can't encode character`

**Fix:** Remove ALL emoji and non-Latin characters from `print()` statements. The Windows console uses cp1256 (Arabic Windows) which cannot print emoji. Even `print("🚀")` crashes the script silently. Use ASCII-only in print/logger calls, or write to a file instead of stdout.
