"""Run Pi with a verified request hook before releasing task content."""

import base64
import hashlib
import json
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from provider_routing import validate_provider_policy_receipt

EXTENSION_PATH = Path(__file__).with_name("provider_policy.mjs")
SUPPORTED_PI_VERSIONS = {"0.85.1"}
READINESS_TIMEOUT = 15
GATEWAY_BASE_URL = "https://openrouter.ai/api/v1"


def canonical_digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def read_receipt(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def image_content(path: str) -> dict:
    data = Path(path).read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif data[:6] in (b"GIF87a", b"GIF89a"):
        mime = "image/gif"
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ValueError("Image file must be PNG, JPEG, GIF, or WebP")
    return {"type": "image", "data": base64.b64encode(data).decode(), "mimeType": mime}


def run_controlled(command: list[str], *, prompt: str, cwd: str, timeout: int,
                   config: dict, image_files: list[str]) -> tuple[subprocess.CompletedProcess, dict | None]:
    started = time.monotonic()
    deadline = started + timeout if timeout > 0 else float("inf")
    version = subprocess.run([command[0], "--version"], capture_output=True, text=True,
                             timeout=min(timeout or 10, 10), check=False, stdin=subprocess.DEVNULL)
    if version.returncode != 0 or version.stdout.strip() not in SUPPORTED_PI_VERSIONS:
        raise ValueError("Pi runtime has no verified request hook support")
    if not EXTENSION_PATH.is_file():
        raise ValueError("Packaged request hook is missing")
    images = [image_content(path) for path in image_files]
    # Bind the destination independently of the mutable model registry.
    config = {**config, "base_url": GATEWAY_BASE_URL}
    expected_digest = canonical_digest(config)
    with tempfile.TemporaryDirectory(prefix="pi-request-") as temp:
        root = Path(temp)
        config_path, receipt_path = root / "config.json", root / "receipt.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False))
        config_path.chmod(0o600)
        environment = dict(os.environ, RAR_PI_RUN_CONFIG=str(config_path), RAR_PI_RUN_RECEIPT=str(receipt_path))
        actual = [*command, "-e", str(EXTENSION_PATH)]
        with tempfile.TemporaryFile(mode="w+") as out, tempfile.TemporaryFile(mode="w+") as err:
            process = subprocess.Popen(actual, cwd=cwd, stdout=out, stderr=err, stdin=subprocess.PIPE,
                                       text=True, env=environment, start_new_session=True)
            try:
                # No prompt, attachment, or task text enters Pi before this handshake.
                ready_deadline = min(deadline, time.monotonic() + READINESS_TIMEOUT)
                while process.poll() is None and time.monotonic() < ready_deadline:
                    ready = read_receipt(receipt_path)
                    if ready.get("state") == "ready":
                        break
                    time.sleep(0.02)
                else:
                    raise ValueError("Request hook did not confirm readiness")
                if (ready.get("config_sha256") != expected_digest or ready.get("model") != config["model"]
                        or ready.get("gateway") != config["gateway"] or ready.get("request_count") != 0):
                    raise ValueError("Request hook readiness does not match the selected route")
                process.stdin.write(json.dumps({"type": "prompt", "message": prompt, "images": images}) + "\n")
                process.stdin.flush()
                stream_offset, pending = 0, b""
                while process.poll() is None:
                    if time.monotonic() >= deadline:
                        raise subprocess.TimeoutExpired(command, timeout)
                    # RPC can reject prompt preflight without ending the agent.
                    # Positional reads leave the child's output offset unchanged.
                    data = os.pread(out.fileno(), 65536, stream_offset)
                    stream_offset += len(data)
                    pending += data
                    while b"\n" in pending:
                        line, pending = pending.split(b"\n", 1)
                        try:
                            event = json.loads(line)
                        except ValueError:
                            continue
                        if isinstance(event, dict) and event.get("command") == "prompt" and event.get("success") is False:
                            raise ValueError("Prompt preflight failed before a provider request")
                    if read_receipt(receipt_path).get("state") == "complete":
                        # EOF asks RPC mode to dispose its session and flush all output.
                        process.stdin.close()
                        process.wait(timeout=max(0.01, min(5, deadline - time.monotonic())))
                        break
                    time.sleep(0.02)
                observed = read_receipt(receipt_path)
                if observed.get("config_sha256") != expected_digest or canonical_digest(json.loads(config_path.read_text())) != expected_digest:
                    raise ValueError("Request policy changed during execution")
                receipt = None
                if config["policy"]:
                    receipt = {"status": "enforced", "gateway": observed.get("gateway"),
                               "policy_sha256": observed.get("policy_sha256"), "request_count": observed.get("request_count")}
                    validate_provider_policy_receipt(receipt, config["policy"])
                out.seek(0)
                err.seek(0)
                return subprocess.CompletedProcess(actual, process.returncode, out.read(), err.read()), receipt
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
