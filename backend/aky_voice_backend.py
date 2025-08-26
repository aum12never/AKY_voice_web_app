# File: aky_voice_backend.py (Final, Corrected Version)
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
    ฟังก์ชันหลักที่รับการตั้งค่าทั้งหมดเข้ามา
    Returns: Path ของไฟล์ MP3 ที่สำเร็จ
    Raises: ValueError หากเกิดข้อผิดพลาด
    """
    try:
        genai.configure(api_key=api_key)

        # รูปแบบ prompt สำหรับ TTS คือ "text to be spoken"
        # เราจะรวม style และ main_text เข้าด้วยกัน
        # หมายเหตุ: API อาจไม่ตีความ "style" แยกต่างหาก แต่การรวมเข้าไปจะช่วยชี้นำโทนเสียงได้
        full_prompt = f"{style_instructions}. {main_text}"

        wav_path, mp3_path = determine_output_paths(
            output_folder, output_filename)

        # --- [แก้ไข] API สำหรับ Text-to-Speech โดยเฉพาะ ---
        response = genai.text_to_speech(
            text=full_prompt,
            voice=voice_name,
            # อุณหภูมิ (temperature) ไม่ใช่พารามิเตอร์โดยตรงสำหรับ API นี้
        )
        
        # ข้อมูลเสียงจะอยู่ใน attribute 'audio_data'
        audio_buffer = response.audio_data

        if audio_buffer:
            # ไม่จำเป็นต้องแปลงเป็น WAV แล้ว เพราะ API ส่งข้อมูลที่พร้อมใช้งานมาให้
            # เราจะบันทึกเป็น MP3 โดยตรง
            save_binary_file(mp3_path, audio_buffer)
            # ไม่จำเป็นต้องใช้ FFMPEG ในขั้นตอนนี้แล้ว
            return mp3_path
        else:
            raise ValueError("No audio data received from the API.")

    except Exception as e:
        raise ValueError(f"Backend Error: {e}")

# --- [ลบออก] ฟังก์ชันนี้ไม่จำเป็นอีกต่อไป ---
# def convert_with_ffmpeg(...):

# --- [ลบออก] ฟังก์ชันนี้ไม่จำเป็นอีกต่อไป ---
# def prepare_api_config(...):

def determine_output_paths(folder, filename_base):
    os.makedirs(folder, exist_ok=True)
    # --- [แก้ไข] ไม่ต้องสร้างโฟลเดอร์ MP3_Output ซ้อนแล้ว ---
    mp3_folder = folder
    
    mp3_base_path = os.path.join(mp3_folder, filename_base)
    mp3_output = f"{mp3_base_path}.mp3"
    counter = 1
    # --- [แก้ไข] ไม่ต้องจัดการกับ .wav ---
    while os.path.exists(mp3_output):
        mp3_output = f"{mp3_base_path} ({counter}).mp3"
        counter += 1
    # คืนค่า mp3 path ทั้งสองตำแหน่งเพื่อความเข้ากันได้
    return mp3_output, mp3_output

def save_binary_file(file_name, data):
    with open(file_name, "wb") as f:
        f.write(data)

# --- [ลบออก] ฟังก์ชันเกี่ยวกับ WAV ไม่จำเป็นอีกต่อไป ---
# def convert_to_wav(...):
# def parse_audio_mime_type(...):
