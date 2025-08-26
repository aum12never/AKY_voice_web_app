# File: aky_voice_backend.py (The Definitive, Stable Version)
# -*- coding: utf-8 -*-
import os
import google.generativeai as genai

def run_tts_generation(
    api_key: str, style_instructions: str, main_text: str, voice_name: str,
    output_folder: str, output_filename: str, temperature: float,
    ffmpeg_path: str
):
    """
    ฟังก์ชันหลักที่ใช้โมเดล TTS โดยเฉพาะเพื่อความเสถียร
    Returns: Path ของไฟล์ MP3 ที่สำเร็จ
    Raises: ValueError หากเกิดข้อผิดพลาด
    """
    try:
        genai.configure(api_key=api_key)

        # --- [แก้ไข] ใช้โมเดลที่สร้างมาเพื่อทำเสียงโดยเฉพาะ ---
        tts_model = genai.GenerativeModel(model_name="models/tts-1")

        # รวม prompt ทั้งหมดเข้าด้วยกัน
        full_prompt = f"{style_instructions}. {main_text}"

        # --- [แก้ไข] เรียกใช้ generate_content กับโมเดล TTS ---
        # API จะจัดการเรื่องเสียงให้เองจากชนิดของโมเดล
        response = tts_model.generate_content(
            full_prompt,
            stream=False
        )

        # --- [แก้ไข] วิธีการเข้าถึงข้อมูลเสียงสำหรับโมเดล TTS ---
        # ข้อมูลเสียงจะอยู่ใน Part แรกของ response ซึ่งเป็น blob
        audio_buffer = response.parts[0].data

        if audio_buffer:
            _, mp3_path = determine_output_paths(output_folder, output_filename)

            # บันทึกข้อมูลเสียงที่ได้มาเป็นไฟล์ MP3 โดยตรง
            save_binary_file(mp3_path, audio_buffer)

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
