# File: aky_voice_backend.py (Updated Version)
# -*- coding: utf-8 -*-
import os
import struct
import subprocess
import google.generativeai as genai
from google.generativeai import types
from tqdm import tqdm


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
        # --- [แก้ไข] เปลี่ยนวิธีการยืนยันตัวตนเป็นแบบใหม่ ---
        genai.configure(api_key=api_key)

        contents = prepare_prompt(style_instructions, main_text)
        config = prepare_api_config(temperature, voice_name)
        wav_path, mp3_path = determine_output_paths(
            output_folder, output_filename)

        # --- [แก้ไข] เปลี่ยนวิธีการเรียกใช้โมเดลเป็นแบบใหม่ ---
        tts_model = genai.GenerativeModel(model_name="gemini-2.5-pro-preview-tts")
        stream = tts_model.generate_content(
            contents=contents,
            generation_config=config,
            stream=True
        )

        audio_buffer = b''
        for chunk in stream:
            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts and chunk.candidates[0].content.parts[0].inline_data:
                audio_buffer += chunk.candidates[0].content.parts[0].inline_data.data

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
        # [แก้ไข] เพิ่มการดักจับ output ของ FFMPEG
        result = subprocess.run(command, check=True,
                                capture_output=True, text=True)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"FFMPEG not found. Make sure '{ffmpeg_path}' is accessible.")
    except subprocess.CalledProcessError as e:
        # หาก FFMPEG ทำงานผิดพลาด ให้แสดง log ออกมา
        raise RuntimeError(
            f"FFMPEG conversion failed:\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")
    except Exception as e:
        raise RuntimeError(
            f"An unexpected error occurred during FFMPEG conversion: {e}")


# --- ฟังก์ชัน Helper อื่นๆ (เหมือนเดิม ไม่ต้องแก้ไข) ---

def prepare_prompt(style, text):
    return [types.Content(role="user", parts=[types.Part.from_text(text=style), types.Part.from_text(text=text)])]


def prepare_api_config(temp, voice):
    return types.GenerateContentConfig(temperature=temp, response_modalities=["audio"], speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))))


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
    header = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(audio_data), b"WAVE", b"fmt ", 16, 1, 1, sample_rate,
                         sample_rate * (bits_per_sample // 8), (bits_per_sample // 8), bits_per_sample, b"data", len(audio_data))
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


