# File: aky_voice_backend.py (Final Version for New Library)
# -*- coding: utf-8 -*-
import os
import struct
import subprocess
import google.generativeai as genai
# --- [แก้ไข] Import รูปแบบใหม่จาก genai โดยตรง ไม่ผ่าน types ---
from google.generativeai.types import GenerationConfig, SpeechConfig, VoiceConfig, PrebuiltVoiceConfig

def run_tts_generation(
    api_key: str, style_instructions: str, main_text: str, voice_name: str,
    output_folder: str, output_filename: str, temperature: float,
    ffmpeg_path: str
):
    """
    ฟังก์ชันหลักที่รับการตั้งค่าทั้งหมดเข้ามา
    Returns: Path ของไฟล์ MP3 ที่สำเร็จ
    Raises: ValueError หากเกิดข้อผิดพลาด
    """
    try:
        genai.configure(api_key=api_key)

        # --- [แก้ไข] รูปแบบการสร้าง prompt จะถูกส่งเป็น list ของ string โดยตรง ---
        contents = [style_instructions, main_text]
        config = prepare_api_config(temperature, voice_name)
        wav_path, mp3_path = determine_output_paths(
            output_folder, output_filename)

        tts_model = genai.GenerativeModel(model_name="gemini-2.5-pro-preview-tts")
        # --- [แก้ไข] การเรียกใช้ API เปลี่ยนแปลงเล็กน้อย ---
        response = tts_model.generate_content(
            contents=contents,
            generation_config=config,
            stream=False # เปลี่ยนเป็น False เพื่อให้จัดการง่ายขึ้น
        )

        # --- [แก้ไข] วิธีการเข้าถึงข้อมูลเสียงที่ได้รับกลับมา ---
        audio_buffer = response.candidates[0].content.parts[0].inline_data.data

        if audio_buffer:
            final_wav_data = convert_to_wav(
                audio_buffer, "audio/L16;rate=24000")
            save_binary_file(wav_path, final_wav_data)
            convert_with_ffmpeg(ffmpeg_path, wav_path, mp3_path)
            os.remove(wav_path)
            return mp3_path
        else:
            raise ValueError("No audio data received from the API.")

    except Exception as e:
        raise ValueError(f"Backend Error: {e}")


def convert_with_ffmpeg(ffmpeg_path, wav_path, mp3_path):
    """แปลงไฟล์ .wav เป็น .mp3 โดยใช้ ffmpeg"""
    try:
        command = [ffmpeg_path, '-i', wav_path, '-y',
                   '-acodec', 'libmp3lame', '-q:a', '2', mp3_path]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise FileNotFoundError(f"FFMPEG not found. Make sure '{ffmpeg_path}' is accessible.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFMPEG conversion failed:\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred during FFMPEG conversion: {e}")

# --- ฟังก์ชัน Helper อื่นๆ ---

# --- [ลบออก] ฟังก์ชันนี้ไม่จำเป็นอีกต่อไป เพราะเราส่ง prompt เป็น list ของ string ง่ายๆ แทน ---
# def prepare_prompt(style, text):
#     return ...

def prepare_api_config(temp, voice):
    # --- [แก้ไข] ใช้ Class รูปแบบใหม่ที่ import มาโดยตรง ---
    return GenerationConfig(
        temperature=temp,
        response_modalities=["audio"],
        speech_config=SpeechConfig(
            voice_config=VoiceConfig(
                prebuilt_voice_config=PrebuiltVoiceConfig(
                    voice_name=voice
                )
            )
        )
    )

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
    return wav_output, mp3_path

def save_binary_file(file_name, data):
    with open(file_name, "wb") as f:
        f.write(data)

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    header = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(audio_data), b"WAVE", b"fmt ", 16, 1, 1, sample_rate,
                         sample_rate * (bits_per_sample // 8), (bits_per_sample // 8), bits_per_sample, b"data", len(audio_data))
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    bits_per_sample = 16
    rate = 24000
    for param in mime_type.split(";"):
        if param.lower().strip().startswith("rate="):
            try: rate = int(param.split("=", 1)[1])
            except: pass
        elif param.strip().startswith("audio/L"):
            try: bits_per_sample = int(param.split("L", 1)[1])
            except: pass
    return {"bits_per_sample": bits_per_sample, "rate": rate}
