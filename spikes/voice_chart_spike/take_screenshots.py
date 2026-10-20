"""Automated UI screenshot taker using Chrome DevTools Protocol (CDP).
Captures authentic screenshots of the Next.js UI rendering the ECharts donut and stacked bar charts.
"""

import asyncio
import base64
import json
import logging
import subprocess
import time
from pathlib import Path
import websockets
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("take_screenshots")

SCREENSHOTS_DIR = Path("/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC/spikes/voice_chart_spike/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


async def cdp_call(ws, method: str, params: dict = None) -> dict:
    call_id = int(time.time() * 1000) % 1000000
    msg = {"id": call_id, "method": method, "params": params or {}}
    await ws.send(json.dumps(msg))
    while True:
        res_raw = await ws.recv()
        res = json.loads(res_raw)
        if res.get("id") == call_id:
            return res.get("result", {})


async def capture_ui():
    chrome_proc = subprocess.Popen([
        "google-chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--remote-debugging-port=9222",
        "--window-size=1440,900"
    ])
    logger.info("Launched headless Chrome (PID %d)...", chrome_proc.pid)
    await asyncio.sleep(2)

    try:
        # Discover target page
        targets = requests.get("http://localhost:9222/json/list").json()
        ws_url = None
        for t in targets:
            if t.get("type") == "page":
                ws_url = t.get("webSocketDebuggerUrl")
                break
        
        if not ws_url:
            new_target = requests.put("http://localhost:9222/json/new?http://localhost:3100").json()
            ws_url = new_target.get("webSocketDebuggerUrl")

        logger.info("Connecting to CDP at %s...", ws_url)
        async with websockets.connect(ws_url) as ws:
            # Enable Page & Runtime
            await cdp_call(ws, "Page.enable")
            await cdp_call(ws, "Runtime.enable")

            # Navigate to local UI
            logger.info("Navigating to http://localhost:3100...")
            await cdp_call(ws, "Page.navigate", {"url": "http://localhost:3100"})
            await asyncio.sleep(3)

            # Click the prompt button: '📊 English: Delhi ≥5yr'
            logger.info("Triggering query via prompt chip click...")
            eval_res = await cdp_call(ws, "Runtime.evaluate", {
                "expression": """
                    (() => {
                        const buttons = Array.from(document.querySelectorAll('.prompt-chip'));
                        const btn = buttons.find(b => b.textContent.includes('English'));
                        if (btn) {
                            btn.click();
                            return 'clicked';
                        }
                        return 'not found';
                    })()
                """
            })
            logger.info("Button click result: %s", eval_res)
            
            # Wait 2.5 seconds for tool call to finish and ECharts animation to settle
            await asyncio.sleep(2.5)

            # Capture Screenshot 1: Donut Chart View
            logger.info("Capturing Screenshot 1: Donut Chart View...")
            shot1 = await cdp_call(ws, "Page.captureScreenshot", {"format": "png"})
            shot1_bytes = base64.b64decode(shot1.get("data", ""))
            shot1_path = SCREENSHOTS_DIR / "screenshot_headcount_chart.png"
            shot1_path.write_bytes(shot1_bytes)
            logger.info("Saved Screenshot 1 (%d bytes) to %s", len(shot1_bytes), shot1_path)

            # Click Tab: 'Stacked Bar (Discipline)'
            logger.info("Switching to Stacked Bar View...")
            await cdp_call(ws, "Runtime.evaluate", {
                "expression": """
                    (() => {
                        const tabs = Array.from(document.querySelectorAll('.btn-tab'));
                        const barTab = tabs.find(b => b.textContent.includes('Stacked Bar'));
                        if (barTab) {
                            barTab.click();
                            return 'tab clicked';
                        }
                        return 'tab not found';
                    })()
                """
            })

            # Wait 1.5 seconds for animation transition
            await asyncio.sleep(1.5)

            # Capture Screenshot 2: Stacked Bar Chart View
            logger.info("Capturing Screenshot 2: Stacked Bar View...")
            shot2 = await cdp_call(ws, "Page.captureScreenshot", {"format": "png"})
            shot2_bytes = base64.b64decode(shot2.get("data", ""))
            shot2_path = SCREENSHOTS_DIR / "screenshot_stacked_bar_chart.png"
            shot2_path.write_bytes(shot2_bytes)
            logger.info("Saved Screenshot 2 (%d bytes) to %s", len(shot2_bytes), shot2_path)

    finally:
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=2)
        except Exception:
            chrome_proc.kill()


if __name__ == "__main__":
    asyncio.run(capture_ui())
