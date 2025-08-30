# File: aky_voice_backend.py (Streamlit Cloud Compatible Version)
# -*- coding: utf-8 -*-
import os
import struct
import subprocess
import requests
import json
import base64


def run_tts_generation(
    api_key: str, style_instructions: str, main_text: str, voice_name: str,
    output_folder: str, output_filename: str, temperature: float,
    ffmpeg_path: str
):
    """
    ฟังก์ชันหลักสำหรับสร้าง TTS ด้วย Google AI Studio
    ใช้ REST API เพื่อความเสถียรบน Streamlit Cloud
    """
    try:
        # เตรียม prompt
        full_prompt = f"""
        {style_instructions}
        
        {main_text}
        """

        # สร้าง request payload
        payload = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": voice_name
                        }
                    }
                }
            }
        }

        # เพิ่ม temperature ถ้ามีค่า
        if temperature != 0.9:  # default value
            payload["generationConfig"]["temperature"] = temperature

        # สร้างเส้นทางไฟล์
        wav_path, mp3_path = determine_output_paths(
            output_folder, output_filename)

        # เรียก REST API
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise exception for HTTP errors

        # ประมวลผล response
        data = response.json()
        
        if (data.get("candidates") and 
            data["candidates"][0].get("content") and
            data["candidates"][0]["content"].get("parts") and
            data["candidates"][0]["content"]["parts"][0].get("inlineData")):
            
            # ดึงข้อมูลเสียงที่เป็น base64
            audio_base64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
            audio_data = base64.b64decode(audio_base64)

            # บันทึกไฟล์ WAV
            save_pcm_as_wav(wav_path, audio_data)

            # แปลงเป็น MP3
            convert_with_ffmpeg(ffmpeg_path, wav_path, mp3_path)

            # ลบไฟล์ temporary WAV
            if os.path.exists(wav_path):
                os.remove(wav_path)

            return mp3_path
        else:
            raise ValueError("No audio data received from the API.")

    except requests.exceptions.RequestException as e:
        raise ValueError(f"API Request Error: {str(e)}")
    except Exception as e:
        raise ValueError(f"Backend Error: {str(e)}")


def save_pcm_as_wav(filename, pcm_data, channels=1, rate=24000, sample_width=2):
    """บันทึก PCM data เป็นไฟล์ WAV"""
    import wave
    try:
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm_data)
    except Exception as e:
        # Fallback: ใช้วิธีสร้าง WAV header แบบเดิม
        wav_data = create_wav_header(pcm_data, channels, rate, sample_width) + pcm_data
        save_binary_file(filename, wav_data)


def create_wav_header(pcm_data, channels=1, rate=24000, sample_width=2):
    """สร้าง WAV header"""
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(pcm_data),
        b"WAVE",
        b"fmt ",
        16,  # PCM format size
        1,   # PCM format
        channels,
        rate,
        rate * channels * sample_width,
        channels * sample_width,
        sample_width * 8,
        b"data",
        len(pcm_data)
    )
    return header


def convert_with_ffmpeg(ffmpeg_path, wav_path, mp3_path):
    """แปลงไฟล์ WAV เป็น MP3 ด้วย ffmpeg"""
    try:
        command = [ffmpeg_path, '-i', wav_path, '-y',
                   '-acodec', 'libmp3lame', '-q:a', '2', mp3_path]
        result = subprocess.run(command, check=True,
                                capture_output=True, text=True)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"FFMPEG not found. Make sure '{ffmpeg_path}' is accessible.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"FFMPEG conversion failed:\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")


def determine_output_paths(folder, filename_base):
    """สร้างเส้นทางไฟล์ output"""
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
    """บันทึกไฟล์ binary"""
    with open(file_name, "wb") as f:
        f.write(data)


# เก็บฟังก์ชันเดิมไว้เป็น backup
def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """แปลงข้อมูลเสียงเป็นรูปแบบ WAV"""
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(audio_data),
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        sample_rate * (bits_per_sample // 8),
        (bits_per_sample // 8),
        bits_per_sample,
        b"data",
        len(audio_data)
    )

    return header + audio_data


def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    """แปลง mime type เป็นพารามิเตอร์เสียง"""
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
