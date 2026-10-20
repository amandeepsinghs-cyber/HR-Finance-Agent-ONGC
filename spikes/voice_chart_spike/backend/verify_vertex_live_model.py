"""Verification probe for Vertex AI Gemini Live models.
Checks models.list in us-central1 and performs a live connection smoke test
comparing gemini-3.8-live, gemini-live-2.5-flash-native-audio, and gemini-2.0-flash-exp.
"""

import asyncio
import os
import sys
from google import genai
from google.genai import types

PROJECT_ID = os.getenv("TARGET_PROJECT", "ongc-hr-finance-agent")
LOCATION = os.getenv("TARGET_LOCATION", "us-central1")

CANDIDATES = [
    "gemini-3.8-live",
    "gemini-live-2.5-flash-native-audio",
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash-realtime-exp",
]


async def smoke_test_model(client: genai.Client, model_id: str) -> bool:
    print(f"\n--- Smoke Testing: {model_id} in {LOCATION} ---")
    try:
        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
                )
            ),
        )
        async with client.aio.live.connect(model=model_id, config=config) as session:
            await session.send(input="Hello, can you hear me?", end_of_turn=True)
            async for response in session.receive():
                if response.server_content and response.server_content.turn_complete:
                    print(f"  ✓ SUCCESS: {model_id} connected and returned turn_complete!")
                    return True
        return False
    except Exception as exc:
        print(f"  ✗ FAILED: {model_id} -> {type(exc).__name__}: {exc}")
        return False


async def main():
    print(f"Probing Vertex AI Models in project={PROJECT_ID}, location={LOCATION}...")
    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
        models = list(client.models.list())
        live_models = [m.name for m in models if "live" in m.name.lower() or "realtime" in m.name.lower()]
        print(f"Found {len(live_models)} models with 'live'/'realtime' in name:")
        for lm in live_models:
            print(f"  - {lm}")
    except Exception as e:
        print(f"Failed to list models: {type(e).__name__}: {e}")
        return

    working_model = None
    for candidate in CANDIDATES:
        ok = await smoke_test_model(client, candidate)
        if ok and not working_model:
            working_model = candidate

    print("\n=======================================================")
    if working_model:
        print(f"VERIFIED WORKING LIVE MODEL: {working_model}")
        print(f"Export with: export LIVE_MODEL={working_model}")
    else:
        print("No tested live candidate succeeded. Check permissions and location.")
    print("=======================================================")


if __name__ == "__main__":
    asyncio.run(main())
