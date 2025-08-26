# File: aky_voice_backend.py (Final Version for google-generativeai >= 0.9.0)
# -*- coding: utf-8 -*-
import os
import google.generativeai as genai

def run_tts_generation(
    api_key: str, style_instructions: str, main_text: str, voice_name: str,
    output_folder: str, output_filename: str, temperature: float, # temperature is unused in this API but kept for compatibility
    ffmpeg_path: str # ffmpeg_path is unused in this API but kept for compatibility
):
    """
    ฟังก์ชันหลักที่รับการตั้งค่าทั้งหมดเข้ามา
    Returns: Path ของไฟล์ MP3 ที่สำเร็จ
    Raises: ValueError หากเกิดข้อผิดพลาด
    """
    try:
        genai.configure(api_key=api_key)

        full_prompt = f"{style_instructions}. {main_text}"

        # API สำหรับ Text-to-Speech โดยเฉพาะ
        response = genai.text_to_speech(
            text=full_prompt,
            voice_name=voice_name,
        )

        # ข้อมูลเสียงจะอยู่ใน attribute 'audio_data'
        audio_buffer = response.audio_data

        if audio_buffer:
            # กำหนด path ของไฟล์ MP3 ที่จะบันทึก
            _, mp3_path = determine_output_paths(output_folder, output_filename)

            # บันทึกเป็น MP3 โดยตรง
            save_binary_file(mp3_path, audio_buffer)

            # ไม่จำเป็นต้องใช้ FFMPEG ในขั้นตอนนี้แล้ว
            return mp3_path
        else:
            raise ValueError("No audio data received from the API.")

    except Exception as e:
        raise ValueError(f"Backend Error: {e}")

def determine_output_paths(folder, filename_base):
    os.makedirs(folder, exist_ok=True)
    mp3_folder = folder

    mp3_base_path = os.path.join(mp3_folder, filename_base)
    mp3_output = f"{mp3_base_path}.mp3"
    counter = 1

    while os.path.exists(mp3_output):
        mp3_output = f"{mp3_base_path} ({counter}).mp3"
        counter += 1

    return mp3_output, mp3_output

def save_binary_file(file_name, data):
    with open(file_name, "wb") as f:
        f.write(data)
