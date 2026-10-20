"""Authentic Gemini Voice Sample Generator for ONGC HR & Finance.
Calls Vertex AI Gemini Live native-audio / TTS API to generate real speech samples
for candidate female voices (Aoede, Kore, Leda) reciting the C1 answer in English and Hindi.
Run this script once ADC credentials are refreshed.
"""

import asyncio
import os
import sys
from pathlib import Path
from google import genai
from google.genai import types

VOICE_DIR = Path(__file__).parent
OUTPUT_DIR = VOICE_DIR / "real_gemini_voices"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROJECT_ID = os.getenv("TARGET_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT") or "ongc-hr-finance-agent"
LOCATION = os.getenv("TARGET_LOCATION") or "us-central1"

C1_ENGLISH_PROMPT = (
    "Please read the following text aloud clearly and professionally in Indian English: "
    "'In Delhi, there are 419 executives with continuous tenure of 5 years or more. "
    "Of these, 402 are eligible for transfer rotation and 17 are exempt due to retirement within 3 years.'"
)

C1_HINDI_PROMPT = (
    "Please read the following text aloud clearly and professionally in natural Hindi / Hinglish: "
    "'Delhi mein 5 saal ya usse zyada se posted kul 419 executives hain. "
    "Inme se 402 transfer rotation ke liye eligible hain, aur 17 agle teen saal mein retire ho rahe hain.'"
)

CANDIDATE_VOICES = ["Aoede", "Kore", "Leda"]


import wave

async def generate_voice_clip(client: genai.Client, model_id: str, voice_name: str, language: str, prompt_text: str, out_path: Path):
    print(f"Generating real audio for {voice_name} [{language}] using model {model_id}...")
    try:
        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
        )
        async with client.aio.live.connect(model=model_id, config=config) as session:
            await session.send(input=prompt_text, end_of_turn=True)
            audio_bytes = bytearray()
            async for response in session.receive():
                server_content = response.server_content
                if server_content and server_content.model_turn:
                    for part in server_content.model_turn.parts:
                        if part.inline_data and part.inline_data.data:
                            audio_bytes.extend(part.inline_data.data)
                if server_content and server_content.turn_complete:
                    break
            
            if audio_bytes:
                # Write raw PCM
                out_path.write_bytes(bytes(audio_bytes))
                
                # Write WAV file
                wav_path = out_path.with_suffix(".wav")
                with wave.open(str(wav_path), "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(24000)
                    wav_file.writeframes(bytes(audio_bytes))
                print(f"  ✓ Saved real audio: {wav_path.name} ({len(audio_bytes)} bytes)")
            else:
                print(f"  ⚠ No audio received for {voice_name} [{language}]")
    except Exception as e:
        print(f"  ✗ Error generating audio for {voice_name} [{language}]: {e}")


async def main():
    print(f"Initializing Vertex AI GenAI Client (Project: {PROJECT_ID}, Location: {LOCATION})...")
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

    # Discover candidate models
    target_model = os.getenv("LIVE_MODEL", "gemini-live-2.5-flash-native-audio")
    print(f"Targeting model: {target_model}")

    for voice in CANDIDATE_VOICES:
        en_out = OUTPUT_DIR / f"{voice.lower()}_en_c1_real.pcm"
        hi_out = OUTPUT_DIR / f"{voice.lower()}_hi_c1_real.pcm"
        await generate_voice_clip(client, target_model, voice, "en-IN", C1_ENGLISH_PROMPT, en_out)
        await generate_voice_clip(client, target_model, voice, "hi-IN", C1_HINDI_PROMPT, hi_out)

    print("\nReal voice generation complete. Inspect samples in:", OUTPUT_DIR)


if __name__ == "__main__":
    asyncio.run(main())
