"""Modal runner for builderr admission preview + NIM smoke test."""
import modal

app = modal.App("builderr-nim-test")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("requests")
    .add_local_python_source("agent")
    .add_local_file("preview.py", "/root/preview.py")
    .add_local_file("selfcheck.py", "/root/selfcheck.py")
    .add_local_file("sample_regimes.json.gz", "/root/sample_regimes.json.gz")
    .add_local_file("strategy_selftest.py", "/root/strategy_selftest.py")
)

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("nvidia-nim-key")],
    timeout=120,
    cpu=2,
)
def run():
    import subprocess, os

    print("=" * 70)
    print("builderr NIM Agent — Modal Tests")
    print("=" * 70)

    # Temporarily disable NIM for preview (too many calls for 120s timeout)
    env = {**os.environ, "NVIDIA_NIM_API_KEY": ""}

    # Run preview.py (admission check without NIM)
    print("\n--- Running preview.py (admission check, deterministic layer only) ---\n")
    result = subprocess.run(
        ["python", "/root/preview.py", "/root/agent.py"],
        capture_output=True, text=True, cwd="/root",
        env=env
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    # Run selfcheck.py (smoke test)
    print("\n--- Running selfcheck.py (smoke test) ---\n")
    result2 = subprocess.run(
        ["python", "/root/selfcheck.py"],
        capture_output=True, text=True, cwd="/root",
        env=env
    )
    print(result2.stdout)
    if result2.stderr:
        print("STDERR:", result2.stderr)

    # Run strategy_selftest.py
    print("\n--- Running strategy_selftest.py ---\n")
    result3 = subprocess.run(
        ["python", "/root/strategy_selftest.py"],
        capture_output=True, text=True, cwd="/root",
        env=env
    )
    print(result3.stdout)
    if result3.stderr:
        print("STDERR:", result3.stderr)

    return {
        "preview_exit": result.returncode,
        "selfcheck_exit": result2.returncode,
        "selftest_exit": result3.returncode,
    }


@app.local_entrypoint()
def main():
    output = run.remote()
    print("\n" + "=" * 70)
    print("EXIT CODES")
    print("=" * 70)
    for k, v in output.items():
        status = "PASS" if v == 0 else "FAIL"
        print(f"  [{status}] {k}: {v}")
