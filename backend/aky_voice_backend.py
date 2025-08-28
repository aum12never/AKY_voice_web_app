# File: aky_voice_backend.py (Fixed for google-generativeai library)
# -*- coding: utf-8 -*-
import os
import struct
import subprocess
import google.generativeai as genai
import time

def run_tts_generation(
    api_key: str, style_instructions: str, main_text: str, voice_name: str,
    output_folder: str, output_filename: str, temperature: float,
    ffmpeg_path: str
):
    """
    ฟังก์ชันหลักสำหรับสร้าง TTS ด้วย Google Gemini API
    ใช้ไลบรารี google-generativeai อย่างถูกต้อง
    """
    try:
        # Configure API
        genai.configure(api_key=api_key)
        
        # เตรียม prompt
        full_prompt = f"""
        {style_instructions}
        
        {main_text}
        """
        
        # สร้างเส้นทางไฟล์
        wav_path, mp3_path = determine_output_paths(
            output_folder, output_filename)
        
        # ใช้ Gemini 2.0 Flash Experimental สำหรับ TTS
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        
        # สร้าง content พร้อม speech config
        result = model.generate_content(
            [full_prompt],
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                response_modalities=["AUDIO"],
                speech_config={
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": voice_name
                        }
                    }
                }
            ),
        )
        
        # ตรวจสอบและดึงข้อมูลเสียง
        if result and result.candidates:
            candidate = result.candidates[0]
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        if hasattr(part.inline_data, 'data'):
                            audio_data = part.inline_data.data
                            
                            # ตรวจสอบ mime_type
                            mime_type = getattr(part.inline_data, 'mime_type', 'audio/wav')
                            
                            # แปลงเป็น WAV format ถ้าจำเป็น
                            if 'pcm' in mime_type.lower() or 'l16' in mime_type.lower():
                                final_wav_data = convert_to_wav(audio_data, mime_type)
                            else:
                                final_wav_data = audio_data
                            
                            # บันทึกไฟล์ WAV
                            save_binary_file(wav_path, final_wav_data)
                            
                            # แปลงเป็น MP3
                            convert_with_ffmpeg(ffmpeg_path, wav_path, mp3_path)
                            
                            # ลบไฟล์ temporary WAV
                            try:
                                os.remove(wav_path)
                            except:
                                pass
                            
                            return mp3_path
        
        # ถ้าไม่พบข้อมูลเสียง ให้ลองดู error message
        error_msg = "No audio data received from the API."
        if result and hasattr(result, 'prompt_feedback'):
            feedback = result.prompt_feedback
            if hasattr(feedback, 'block_reason'):
                error_msg = f"Content was blocked: {feedback.block_reason}"
        
        raise ValueError(error_msg)

    except Exception as e:
        # เพิ่ม debugging info
        error_message = f"Backend Error: {str(e)}"
        
        # ตรวจสอบประเภทของ error
        if "API_KEY" in str(e).upper() or "authentication" in str(e).lower():
            error_message = "API Key Error: Please check your API key is valid and has proper permissions."
        elif "quota" in str(e).lower():
            error_message = "Quota Error: You may have exceeded your API quota limit."
        elif "model" in str(e).lower():
            error_message = "Model Error: The model name might be incorrect or unavailable."
        
        raise ValueError(error_message)

def convert_with_ffmpeg(ffmpeg_path, wav_path, mp3_path):
    """แปลงไฟล์ WAV เป็น MP3 ด้วย ffmpeg"""
    try:
        # สำหรับ Streamlit Cloud จะใช้ ffmpeg ที่ติดตั้งผ่าน packages.txt
        if not os.path.exists(ffmpeg_path) and ffmpeg_path == "ffmpeg":
            # Try system ffmpeg
            ffmpeg_path = "ffmpeg"
        
        command = [ffmpeg_path, '-i', wav_path, '-y',
                   '-acodec', 'libmp3lame', '-q:a', '2', mp3_path]
        
        result = subprocess.run(command, check=True,
                                capture_output=True, text=True)
        
        if not os.path.exists(mp3_path):
            raise RuntimeError("MP3 file was not created successfully")
            
    except FileNotFoundError:
        raise FileNotFoundError(
            f"FFMPEG not found. Make sure '{ffmpeg_path}' is accessible.")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"FFMPEG conversion failed:\nCommand: {' '.join(command)}\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")

def determine_output_paths(folder, filename_base):
    """สร้างเส้นทางไฟล์ output"""
    os.makedirs(folder, exist_ok=True)
    mp3_folder = os.path.join(folder, "MP3_Output")
    os.makedirs(mp3_folder, exist_ok=True)

    # Clean filename
    filename_base = "".join(c for c in filename_base if c.isalnum() or c in (' ', '-', '_')).rstrip()
    if not filename_base:
        filename_base = "output"

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
    try:
        with open(file_name, "wb") as f:
            f.write(data)
        
        # Verify file was written
        if not os.path.exists(file_name) or os.path.getsize(file_name) == 0:
            raise IOError(f"Failed to write file: {file_name}")
            
    except Exception as e:
        raise IOError(f"Error saving file {file_name}: {str(e)}")

def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """แปลงข้อมูลเสียงเป็นรูปแบบ WAV"""
    # Default parameters
    bits_per_sample = 16
    sample_rate = 24000
    num_channels = 1
    
    # Parse mime type for parameters
    mime_lower = mime_type.lower()
    
    # Check for sample rate
    if "rate=" in mime_lower:
        try:
            rate_part = mime_lower.split("rate=")[1].split(";")[0].split(",")[0]
            sample_rate = int(rate_part)
        except:
            pass
    
    # Check for bit depth
    if "l16" in mime_lower:
        bits_per_sample = 16
    elif "l24" in mime_lower:
        bits_per_sample = 24
    elif "l32" in mime_lower:
        bits_per_sample = 32
    
    # Calculate sizes
    bytes_per_sample = bits_per_sample // 8
    byte_rate = sample_rate * num_channels * bytes_per_sample
    block_align = num_channels * bytes_per_sample
    
    # Create WAV header
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",                    # ChunkID
        36 + len(audio_data),       # ChunkSize
        b"WAVE",                    # Format
        b"fmt ",                    # Subchunk1ID
        16,                         # Subchunk1Size (PCM)
        1,                          # AudioFormat (PCM=1)
        num_channels,               # NumChannels
        sample_rate,                # SampleRate
        byte_rate,                  # ByteRate
        block_align,                # BlockAlign
        bits_per_sample,            # BitsPerSample
        b"data",                    # Subchunk2ID
        len(audio_data)             # Subchunk2Size
    )
    
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict:
    """แปลง mime type เป็นพารามิเตอร์เสียง (Legacy function for compatibility)"""
    bits_per_sample = 16
    rate = 24000

    for param in mime_type.split(";"):
        param = param.strip().lower()
        if param.startswith("rate="):
            try:
                rate = int(param.split("=", 1)[1])
            except:
                pass
        elif param.startswith("audio/l"):
            try:
                bits_per_sample = int(param.split("l", 1)[1])
            except:
                pass

    return {"bits_per_sample": bits_per_sample, "rate": rate}
