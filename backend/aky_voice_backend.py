# File: backend/aky_voice_backend.py
# -*- coding: utf-8 -*-
import os
import struct
import subprocess
import google.generativeai as genai

def run_tts_generation(
    api_key: str, style_instructions: str, main_text: str, voice_name: str,
    output_folder: str, output_filename: str, temperature: float,
    ffmpeg_path: str
):
    """
    ฟังก์ชันหลักสำหรับ WebApp (Streamlit)
    ใช้ google-generativeai แบบปัจจุบัน
    """
    try:
        # --- ตั้งค่า API Key ---
        genai.configure(api_key=api_key)

        # --- สร้าง model ---
        model = genai.GenerativeModel("gemini-2.5-pro-preview-tts")

        # --- ส่ง prompt ---
        response = model.generate_content(
            contents=[
                {"role": "user", "parts": [
                    {"text": style_instructions},
                    {"text": main_text}
                ]}
            ],
            generation_config={
                "temperature": temperature,
                "response_modalities": ["audio"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": voice_name
                        }
                    }
                }
            }
        )

        # --- ดึงข้อมูลเสียง (audio) ---
        audio_buffer = b''
        if response and response.candidates:
            part = response.candidates[0].content.parts[0]
            if hasattr(part, "inline_data") and part.inline_data:
                audio_buffer = part.inline_data.data

        if not audio_buffer:
            raise ValueError("❌ No audio data received from the API.")

        wav_path, mp3_path = determine_output_paths(output_folder, output_filename)
        final_wav_data = convert_to_wav(audio_buffer, "audio/L16;rate=24000")
        save_binary_file(wav_path, final_wav_data)
        convert_with_ffmpeg(ffmpeg_path, wav_path, mp3_path)
        os.remove(wav_path)
        return mp3_path

    except Exception as e:
        raise ValueError(f"Backend Error: {e}")


def convert_with_ffmpeg(ffmpeg_path, wav_path, mp3_path):
    try:
        command = [ffmpeg_path, '-i', wav_path, '-y',
                   '-acodec', 'libmp3lame', '-q:a', '2', mp3_path]
        subprocess.run(command, check=True, capture_output=True)
    except FileNotFoundError:
        raise FileNotFoundError(f"FFMPEG not found. Make sure '{ffmpeg_path}' is accessible.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFMPEG conversion failed: {e.stderr}")


def determine_output_paths(folder, filename_base):
    os.makedirs(folder, exist_ok=True)
    mp3_folder = os.path.join(folder, "MP3_Output")
    os.makedirs(mp3_folder, exist_ok=True)
    file_base_path = os.path.join(folder, filename_base)
    mp3_base_path = os.path.join(mp3_folder, filename_base)
    wav_output = f"{file_base_path}.wav"
    mp3_output = f"{mp3_base_path}.mp3"
    counter = 1
    while os.path.exists(mp3_output):
        wav_output = f"{file_base_path} ({counter}).wav"
        mp3_output = f"{mp3_base_path} ({counter}).mp3"
        counter += 1
    return wav_output, mp3_output


def save_binary_file(file_name, data):
    with open(file_name, "wb") as f:
        f.write(data)


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(audio_data),
        b"WAVE", b"fmt ", 16, 1, 1,
        sample_rate,
        sample_rate * (bits_per_sample // 8),
        (bits_per_sample // 8),
        bits_per_sample, b"data", len(audio_data)
    )
    return header + audio_data


def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    bits_per_sample = 16
    rate = 24000
    for param in mime_type.split(";"):
        if param.lower().strip().startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except:
                pass
        elif param.strip().startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except:
                pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}
