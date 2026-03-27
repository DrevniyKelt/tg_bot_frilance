from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "exports" / "figma-handoff"
BASE_URL = "http://127.0.0.1:8000"


def wait_for_server(timeout_seconds: int = 45) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(f"{BASE_URL}/health", timeout=2) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"Server did not become ready: {last_error}")


def clean_output() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    (OUTPUT_DIR / "desktop").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "mobile").mkdir(parents=True, exist_ok=True)


def write_manifest(manifest: dict) -> None:
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def write_readme(manifest: dict) -> None:
    lines = [
        "# Figma Handoff Pack",
        "",
        "Import the PNG files from `desktop/` and `mobile/` directly into Figma.",
        "",
        "Suggested workflow:",
        "1. Open Figma.",
        "2. Drag the PNG files from this folder into a new file.",
        "3. Use each image as a reference frame or convert repeated blocks into components.",
        "",
        "Generated screens:",
    ]
    for item in manifest["screens"]:
        lines.append(f"- {item['name']}: {item['path_desktop']}")
    (OUTPUT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def capture_page(page, *, name: str, url: str, viewport: dict[str, int], folder: str) -> None:
    page.set_viewport_size(viewport)
    page.goto(url, wait_until="networkidle")
    page.screenshot(path=str(OUTPUT_DIR / folder / f"{name}.png"), full_page=True)


def main() -> int:
    clean_output()

    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        wait_for_server()
        manifest: dict[str, object] = {"base_url": BASE_URL, "screens": []}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()

            page.goto(f"{BASE_URL}/auth/demo/1", wait_until="networkidle")
            page.goto(f"{BASE_URL}/catalog", wait_until="networkidle")

            order_href = page.locator("a[href^='/orders/']:not([href='/orders/new'])").first.get_attribute("href")
            if not order_href:
                raise RuntimeError("Could not find an order detail link on the site.")

            screens = [
                ("home", f"{BASE_URL}/"),
                ("catalog", f"{BASE_URL}/catalog"),
                ("order_detail", f"{BASE_URL}{order_href}"),
                ("new_order", f"{BASE_URL}/orders/new"),
                ("profile", f"{BASE_URL}/profile"),
                ("swipe", f"{BASE_URL}/swipe"),
                ("tariffs", f"{BASE_URL}/tariffs"),
            ]

            for name, url in screens:
                capture_page(page, name=name, url=url, viewport={"width": 1440, "height": 2200}, folder="desktop")
                capture_page(page, name=name, url=url, viewport={"width": 430, "height": 2200}, folder="mobile")
                manifest["screens"].append(
                    {
                        "name": name,
                        "url": url,
                        "path_desktop": f"desktop/{name}.png",
                        "path_mobile": f"mobile/{name}.png",
                    }
                )

            browser.close()

        write_manifest(manifest)
        write_readme(manifest)
        return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
