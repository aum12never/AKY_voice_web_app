# File: backend/aky_voice_backend.py (ฉบับปรับปรุง)
# -*- coding: utf-8 -*-
import os
import subprocess
import google.generativeai as genai

def run_tts_generation(
    api_key: str, style_instructions: str, main_text: str, voice_name: str,
    output_folder: str, output_filename: str, temperature: float,
    ffmpeg_path: str
):
    """
    ฟังก์ชันหลักสำหรับสร้าง TTS โดยใช้โมเดล 'models/text-to-speech' ที่ดีที่สุด
    """
    try:
        # 1. ตั้งค่า API Key
        genai.configure(api_key=api_key)
        
        # 2. [แก้ไข] สร้าง model โดยใช้ชื่อโมเดลสำหรับ TTS โดยเฉพาะ
        model = genai.GenerativeModel('models/text-to-speech')
        
        # 3. เตรียม prompt
        full_prompt = f"{style_instructions}\n\n{main_text}"
        
        # 4. สร้างเส้นทางไฟล์
        wav_path, mp3_path = determine_output_paths(output_folder, output_filename)
        
        # 5. [แก้ไข] เรียกใช้ API พร้อม config ที่ถูกต้องสำหรับโมเดล TTS
        response = model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                # ระบุว่าต้องการไฟล์เสียง WAV กลับมา
                response_mime_type="audio/wav", 
            ),
            # Speech config ยังคงเหมือนเดิม
            speech_config=genai.SpeechConfig(
                voice_config=genai.VoiceConfig(
                    prebuilt_voice_config=genai.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                )
            )
        )
        
        # 6. [แก้ไข] ดึงข้อมูลเสียงที่ตอนนี้เป็นไฟล์ WAV ที่สมบูรณ์แล้ว
        if response and response.candidates and hasattr(response.candidates[0].content.parts[0], 'inline_data'):
            # API ส่งไฟล์ WAV กลับมาโดยตรง ไม่ต้องแปลงเอง
            wav_audio_data = response.candidates[0].content.parts[0].inline_data.data
            
            # บันทึกไฟล์ WAV ชั่วคราว
            save_binary_file(wav_path, wav_audio_data)
            
            # แปลงเป็น MP3
            convert_with_ffmpeg(ffmpeg_path, wav_path, mp3_path)
            
            # ลบไฟล์ temporary WAV
            if os.path.exists(wav_path):
                os.remove(wav_path)
            
            return mp3_path
        
        raise ValueError("No audio data received from the API.")
        
    except Exception as e:
        raise ValueError(f"Backend Error: {str(e)}")


def convert_with_ffmpeg(ffmpeg_path, wav_path, mp3_path):
    """แปลงไฟล์ WAV เป็น MP3 ด้วย ffmpeg"""
    try:
        command = [ffmpeg_path, '-i', wav_path, '-y',
                   '-acodec', 'libmp3lame', '-q:a', '2', mp3_path]
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        raise FileNotFoundError(f"FFMPEG not found. Make sure '{ffmpeg_path}' is accessible.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFMPEG conversion failed:\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")


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

# [ลบออก] ฟังก์ชัน convert_to_wav และ parse_audio_mime_type ไม่จำเป็นต้องใช้อีกต่อไป
