# File: aky_voice_backend.py (แก้ไขสำหรับ Streamlit)
# -*- coding: utf-8 -*-
import os
import struct
import subprocess
import google.generativeai as genai
from google.generativeai.types import GenerationConfig, SpeechConfig, VoiceConfig, PrebuiltVoiceConfig, Content, Part

def run_tts_generation(
   api_key: str,
   style_instructions: str, main_text: str, voice_name: str,
   output_folder: str, output_filename: str, temperature: float,
   ffmpeg_path: str
):
    """
    ฟังก์ชันหลักที่ปรับปรุงให้ทำงานกับ google-generativeai เวอร์ชันล่าสุด
    """
    try:
        # --- 1. ตั้งค่า API Key ด้วยวิธีที่ถูกต้อง ---
        genai.configure(api_key=api_key)

        # --- 2. สร้าง Model object ---
        # ชื่อ model 'gemini-2.5-pro-preview-tts' ไม่ถูกต้องตามเอกสารปัจจุบัน
        # เราจะใช้ชื่อ model ที่เป็นทางการคือ 'models/text-to-speech'
        model = genai.GenerativeModel('models/text-to-speech')

        # --- 3. สร้าง Prompt ที่จะส่งไป ---
        # ไม่ต้องสร้างเป็น List ของ Content object แล้ว
        prompt = f"Style instructions: {style_instructions}\n\nMain text: {main_text}"

        # --- 4. สร้าง Config object ที่ถูกต้อง ---
        # โครงสร้าง config คล้ายเดิม แต่รวมไว้ใน GenerationConfig
        config = GenerationConfig(
            temperature=temperature,
            # response_modalities ถูกเปลี่ยนเป็น response_mime_type สำหรับ TTS
            response_mime_type="audio/wav",
            speech_config=SpeechConfig(
                voice_config=VoiceConfig(
                    prebuilt_voice_config=PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )

        wav_path, mp3_path = determine_output_paths(output_folder, output_filename)

        # --- 5. เรียกใช้ .generate_content (ไม่ใช่ stream) สำหรับ TTS ---
        # API สำหรับ TTS จะส่งข้อมูลเสียงกลับมาในครั้งเดียว
        response = model.generate_content(
            contents=prompt,
            generation_config=config
        )
        
        # เข้าถึงข้อมูลเสียงจาก response.candidates
        audio_buffer = response.candidates[0].content.parts[0].inline_data.data

        if audio_buffer:
            # ไม่จำเป็นต้อง convert_to_wav เพราะ API ส่ง wav มาให้โดยตรงแล้ว
            save_binary_file(wav_path, audio_buffer)
            convert_with_ffmpeg(ffmpeg_path, wav_path, mp3_path)
            os.remove(wav_path)
            return mp3_path
        else:
            raise ValueError("No audio data received from the API.")

    except Exception as e:
        # ส่งต่อ error ที่ชัดเจนขึ้น
        raise ValueError(f"Backend Error: {e}")


def convert_with_ffmpeg(ffmpeg_path, wav_path, mp3_path):
    try:
        command = [ffmpeg_path, '-i', wav_path, '-y',
                   '-acodec', 'libmp3lame', '-q:a', '2', mp3_path]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise FileNotFoundError(f"FFMPEG not found. Make sure '{ffmpeg_path}' is accessible in the system PATH.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFMPEG conversion failed:\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")

def determine_output_paths(folder, filename_base):
   os.makedirs(folder, exist_ok=True)
   # ใน Streamlit เราจะสร้างไฟล์ MP3 ในโฟลเดอร์ชั่วคราวเลย ไม่ต้องสร้างโฟลเดอร์ย่อย
   file_base_path = os.path.join(folder, filename_base)
   wav_output = f"{file_base_path}.wav"
   mp3_output = f"{file_base_path}.mp3"
   counter = 1
   while os.path.exists(mp3_output):
       wav_output = f"{file_base_path} ({counter}).wav"
       mp3_output = f"{file_base_path} ({counter}).mp3"
       counter += 1
   return wav_output, mp3_output

def save_binary_file(file_name, data):
    with open(file_name, "wb") as f:
        f.write(data)

# ฟังก์ชัน convert_to_wav และ parse_audio_mime_type ไม่จำเป็นต้องใช้อีกต่อไป
# เนื่องจาก API ของ 'models/text-to-speech' ส่งไฟล์ WAV ที่สมบูรณ์กลับมาให้โดยตรง
