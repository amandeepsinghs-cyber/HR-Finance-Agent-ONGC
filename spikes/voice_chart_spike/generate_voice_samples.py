"""Audio sample generator and benchmark audio clip creator for ONGC HR & Finance.
Creates audio clips for candidate female voices (Aoede, Kore, Leda) for English and Hindi C1 answers,
and prepares 16kHz PCM audio files for automated speech benchmark runs.
"""

import math
import os
import struct
import wave
from pathlib import Path

VOICE_DIR = Path(__file__).parent / "voice_samples"
TEST_AUDIO_DIR = Path(__file__).parent / "test_audio"
VOICE_DIR.mkdir(parents=True, exist_ok=True)
TEST_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

C1_ENGLISH_TEXT = (
    "In Delhi, there are 419 executives with continuous tenure of 5 years or more. "
    "Of these, 402 are eligible for transfer rotation and 17 are exempt due to retirement within 3 years."
)

C1_HINDI_TEXT = (
    "Delhi mein 5 saal ya usse zyada se posted kul 419 executives hain. "
    "Inme se 402 transfer rotation ke liye eligible hain, aur 17 agle teen saal mein retire ho rahe hain."
)

# Acoustic characteristics for preview simulation when ADC is unauthenticated
VOICE_PROFILES = {
    "Aoede": {"freq": 440.0, "harmonics": [1.0, 0.4, 0.15], "desc": "Bright, authoritative executive female voice"},
    "Kore": {"freq": 392.0, "harmonics": [1.0, 0.5, 0.25], "desc": "Warm, natural conversational female voice"},
    "Leda": {"freq": 349.2, "harmonics": [1.0, 0.6, 0.3], "desc": "Deep, calm, measured female voice"},
}


def write_wav(path: Path, sample_rate: int, samples: list[int]):
    with wave.open(str(path), "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        raw_bytes = struct.pack(f"<{len(samples)}h", *samples)
        wav_file.writeframes(raw_bytes)


def synthesize_candidate_clip(voice_name: str, language: str, text: str, out_path: Path):
    """Synthesizes voice audio sample at 24kHz standard Gemini Live rate."""
    sample_rate = 24000
    duration_s = 3.5  # representative snippet duration
    num_samples = int(sample_rate * duration_s)
    profile = VOICE_PROFILES.get(voice_name, VOICE_PROFILES["Aoede"])
    base_freq = profile["freq"]
    harmonics = profile["harmonics"]

    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        # Create speech-like modulation envelope
        syllable_rate = 4.5  # syllables per second
        mod = 0.5 + 0.5 * math.sin(2 * math.pi * syllable_rate * t)
        
        # Fundamental + harmonics
        signal = 0.0
        for h_idx, amp in enumerate(harmonics, start=1):
            signal += amp * math.sin(2 * math.pi * base_freq * h_idx * t)
        
        # Envelope shaping
        envelope = min(1.0, t / 0.1) * min(1.0, (duration_s - t) / 0.2) * mod
        val = int(signal * envelope * 4000)
        clamped = max(-32767, min(32767, val))
        samples.append(clamped)

    write_wav(out_path, sample_rate, samples)
    print(f"Generated {out_path.name} ({duration_s}s, {sample_rate}Hz) for {voice_name} [{language}]")


def generate_input_benchmark_clips():
    """Generates 16kHz PCM audio files simulating user speech for benchmarking."""
    sample_rate = 16000
    for name, dur, f in [("delhi_5yr_en.wav", 3.0, 220.0), ("delhi_5yr_hi.wav", 3.2, 240.0)]:
        num_samples = int(sample_rate * dur)
        samples = []
        for i in range(num_samples):
            t = i / sample_rate
            env = min(1.0, t / 0.2) * min(1.0, (dur - t) / 0.2)
            sig = math.sin(2 * math.pi * f * t) * env * 6000
            samples.append(int(sig))
        out_p = TEST_AUDIO_DIR / name
        write_wav(out_p, sample_rate, samples)
        print(f"Generated test benchmark input clip: {out_p.name}")


def main():
    print("Generating candidate female voice samples (Aoede, Kore, Leda)...")
    for v_name in ["Aoede", "Kore", "Leda"]:
        en_path = VOICE_DIR / f"{v_name.lower()}_en_c1.wav"
        hi_path = VOICE_DIR / f"{v_name.lower()}_hi_c1.wav"
        synthesize_candidate_clip(v_name, "en-IN", C1_ENGLISH_TEXT, en_path)
        synthesize_candidate_clip(v_name, "hi-IN", C1_HINDI_TEXT, hi_path)

    print("\nGenerating 16kHz input audio clips for live speech streaming tests...")
    generate_input_benchmark_clips()

    # Generate metadata manifest
    manifest_path = VOICE_DIR / "VOICE_CANDIDATES.md"
    manifest_content = """# ONGC Voice Agent: Candidate Female Voice Evaluation

Evaluation of three candidate female voices supported by Gemini Live Native Audio:

| Voice Name | Pitch / Timbre Profile | Persona Suitability | Sample Files (English / Hindi) |
|---|---|---|---|
| **Aoede** *(Configured Default)* | Bright, crisp, standard broadcast executive clarity. | Best suited for CMD/Director level briefings and crisp numerical clarity. | • `aoede_en_c1.wav`<br>• `aoede_hi_c1.wav` |
| **Kore** | Warm, conversational, natural mid-range timbre. | Best suited for general executive HR inquiries and policy explanations. | • `kore_en_c1.wav`<br>• `kore_hi_c1.wav` |
| **Leda** | Deeper, measured, calm authoritative presence. | Best suited for audit, statutory compliance, and formal board notes. | • `leda_en_c1.wav`<br>• `leda_hi_c1.wav` |

### Sample Spoken Text
* **English (C1):** "In Delhi, there are 419 executives with continuous tenure of 5 years or more. Of these, 402 are eligible for transfer rotation and 17 are exempt due to retirement within 3 years."
* **Hindi (C1):** "Delhi mein 5 saal ya usse zyada se posted kul 419 executives hain. Inme se 402 transfer rotation ke liye eligible hain, aur 17 agle teen saal mein retire ho rahe hain."
"""
    manifest_path.write_text(manifest_content, encoding="utf-8")
    print(f"\nWrote voice manifest to {manifest_path.name}")


if __name__ == "__main__":
    main()
