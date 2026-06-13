import modal, time, json, urllib.request, os

app = modal.App("nim-latency-test")
image = modal.Image.debian_slim(python_version="3.11")

@app.function(image=image, secrets=[modal.Secret.from_name("nvidia-nim-key")], timeout=30)
def test():
    key = os.environ.get("NVIDIA_NIM_API_KEY", "")
    models = ["meta/llama-3.1-8b-instruct", "meta/llama-3.3-70b-instruct"]
    prompt = "SPY: ret20=-0.08, z20=-2.0, vol20=0.03, mom5=0.01. Classify regime and action."
    sys_msg = "Classify the market regime and return ONLY a JSON object, no other text. Output format (nothing else): {\"regime\":\"TREND_UP\",\"action\":\"BUY\",\"confidence\":0.7}"

    for model in models:
        print(f"\n  Model: {model}")
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0, "max_tokens": 120,
        }).encode()
        req = urllib.request.Request(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            method="POST"
        )
        for i in range(3):
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    body = json.loads(resp.read())
                elapsed = time.time() - t0
                content = body["choices"][0]["message"]["content"]
                print(f"    Call {i+1}: {elapsed:.1f}s — {content[:100]}")
            except Exception as e:
                print(f"    Call {i+1}: FAILED ({time.time()-t0:.1f}s) — {e}")

@app.local_entrypoint()
def main():
    test.remote()
