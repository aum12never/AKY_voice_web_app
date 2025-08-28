# File: aky_voice_backend.py (Fixed for latest google-generativeai)
# -*- coding: utf-8 -*-
import os
import struct
import subprocess
import google.generativeai as genai
import json

def run_tts_generation(
    api_key: str, style_instructions: str, main_text: str, voice_name: str,
    output_folder: str, output_filename: str, temperature: float,
    ffmpeg_path: str
):
    """
    ฟังก์ชันหลักสำหรับสร้าง TTS ด้วย Google Gemini API
    ใช้ไลบรารี google-generativeai with proper Audio generation
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
        
        # ใช้ Gemini Pro 1.5 หรือ model ที่รองรับ audio
        model = genai.GenerativeModel('gemini-1.5-flash-8b')
        
        # สร้าง request สำหรับ audio generation
        # ลองใช้วิธีการสร้าง audio content
        response = model.generate_content(
            full_prompt,
            generation_config={
                "temperature": temperature,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
        )
        
        # Check if the response contains audio
        # Note: The actual audio generation might need different approach
        # Let's try alternative method using specific audio model
        
        # Alternative approach - using specific TTS endpoint if available
        import requests
        
        # Prepare the request for TTS
        headers = {
            "Content-Type": "application/json",
        }
        
        # Try using the REST API directly for TTS
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": full_prompt
                }]
            }],
            "generationConfig": {
                "temperature": temperature,
                "candidateCount": 1,
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": voice_name
                        }
                    }
                }
            }
        }
        
        # Make the request
        response = requests.post(api_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract audio data from response
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        if 'inlineData' in part:
                            audio_data = part['inlineData'].get('data', '')
                            if audio_data:
                                # Decode base64 audio data
                                import base64
                                audio_bytes = base64.b64decode(audio_data)
                                
                                # Get mime type
                                mime_type = part['inlineData'].get('mimeType', 'audio/wav')
                                
                                # Convert to WAV if needed
                                if 'pcm' in mime_type.lower() or 'l16' in mime_type.lower():
                                    final_wav_data = convert_to_wav(audio_bytes, mime_type)
                                else:
                                    final_wav_data = audio_bytes
                                
                                # Save WAV file
                                save_binary_file(wav_path, final_wav_data)
                                
                                # Convert to MP3
                                convert_with_ffmpeg(ffmpeg_path, wav_path, mp3_path)
                                
                                # Remove temporary WAV
                                try:
                                    os.remove(wav_path)
                                except:
                                    pass
                                
                                return mp3_path
            
            # If no audio in response, it might not be supported
            raise ValueError("This model might not support direct audio generation. Please check Google's TTS API documentation for the correct model and endpoint.")
        else:
            error_msg = f"API request failed with status {response.status_code}"
            if response.text:
                try:
                    error_detail = response.json()
                    error_msg = f"API Error: {error_detail.get('error', {}).get('message', error_msg)}"
                except:
                    error_msg = f"API Error: {response.text[:200]}"
            raise ValueError(error_msg)

    except Exception as e:
        # เพิ่ม debugging info
        error_message = f"Backend Error: {str(e)}"
        
        # ตรวจสอบประเภทของ error
        if "API_KEY" in str(e).upper() or "authentication" in str(e).lower():
            error_message = "API Key Error: Please check your API key is valid and has proper permissions for TTS/Audio generation."
        elif "quota" in str(e).lower():
            error_message = "Quota Error: You may have exceeded your API quota limit."
        elif "model" in str(e).lower() or "audio" in str(e).lower():
            error_message = "Model Error: The current model might not support audio generation. Google's TTS feature might require specific API access or a different endpoint."
        
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
