"""Run browser regression checks against an isolated demo, without product dependencies.

Install Playwright separately; SDLC_PLAYWRIGHT can name its absolute module path.
SDLC_CHROMIUM optionally selects an already installed Chromium executable.
"""

import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sdlc import demo, server  # noqa: E402


def main():
    with tempfile.TemporaryDirectory(prefix="sdlc-browser-") as tmp:
        root = demo.build(Path(tmp) / "demo-shop")
        httpd = server.serve(root, port=0)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{httpd.server_address[1]}"
            for suite in ("frontend.js", "discovery.js"):
                result = subprocess.run(["node", str(ROOT / "tests" / suite), base, str(root)], cwd=ROOT)
                if result.returncode:
                    return result.returncode
            return 0
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
