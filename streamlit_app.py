# File: streamlit_app.py (UI ลบโปรไฟล์แบบใหม่)
# -*- coding: utf-8 -*-
import streamlit as st
import os
from backend.aky_voice_backend import run_tts_generation
import time

# --- ฟังก์ชันสำหรับตรวจสอบรหัสผ่าน ---
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        return True

# --- ฟังก์ชันสำหรับบันทึกค่าลงในโปรไฟล์ปัจจุบัน ---
def save_current_profile_settings():
    """บันทึกค่าจาก UI inputs ทั้งหมดลงใน st.session_state ของโปรไฟล์ปัจจุบัน"""
    profile_name = st.session_state.current_profile
    if profile_name and profile_name in st.session_state.profiles:
        st.session_state.profiles[profile_name]['style'] = st.session_state.ui_style_instructions
        st.session_state.profiles[profile_name]['script'] = st.session_state.ui_main_text
        st.session_state.profiles[profile_name]['voice'] = st.session_state.ui_voice_select
        st.session_state.profiles[profile_name]['temp'] = st.session_state.ui_temperature
        st.session_state.profiles[profile_name]['filename'] = st.session_state.ui_output_filename

# --- ส่วนแสดงผลหลักของแอป ---
st.set_page_config(page_title="Affiliate Voice Generator AKYYY", layout="wide")

st.title("🎙️ Affiliate Voice Generator Pro AKY VVVV")
st.write("---")

# ตรวจสอบรหัสผ่านก่อนแสดงแอป
if check_password():

    # ตรวจสอบ API Key
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        if not api_key:
            st.error("❌ กรุณาตั้งค่า GOOGLE_API_KEY ใน Streamlit Secrets ก่อนครับ")
            st.stop()
    except KeyError:
        st.error("❌ ไม่พบ GOOGLE_API_KEY ในการตั้งค่า Secrets!")
        st.stop()

    # --- [แก้ไข] ตั้งค่าเริ่มต้นสำหรับระบบโปรไฟล์ (ไม่มี Default) ---
    if 'profiles' not in st.session_state:
        st.session_state.profiles = {}
        st.session_state.current_profile = None

    # --- [แก้ไข] ส่วนจัดการโปรไฟล์ใน Sidebar ---
    with st.sidebar:
        st.header("👤 Profile Management")
        st.write("---")

        # --- [ใหม่] UI สำหรับเลือกและลบโปรไฟล์ ---
        st.subheader("Select Profile")
        profile_options = list(st.session_state.profiles.keys())

        if not profile_options:
            st.caption("No profiles found. Please create one below.")

        for profile_name in profile_options:
            col1, col2 = st.columns([0.8, 0.2])
            
            # ปุ่มสำหรับเลือกโปรไฟล์
            button_type = "primary" if st.session_state.current_profile == profile_name else "secondary"
            if col1.button(profile_name, use_container_width=True, type=button_type):
                st.session_state.current_profile = profile_name
                st.rerun()

            # ปุ่มสำหรับลบโปรไฟล์
            if col2.button(f"🗑️", key=f"delete_{profile_name}", use_container_width=True):
                profile_to_delete = profile_name
                del st.session_state.profiles[profile_to_delete]
                
                # ถ้าโปรไฟล์ที่ลบคือโปรไฟล์ที่กำลังเลือกอยู่ ให้เลือกโปรไฟล์อื่นแทน
                if st.session_state.current_profile == profile_to_delete:
                    remaining_profiles = list(st.session_state.profiles.keys())
                    st.session_state.current_profile = remaining_profiles[0] if remaining_profiles else None
                
                st.success(f'ลบ Profile "{profile_to_delete}" แล้ว')
                st.rerun()

        st.write("---")
        st.subheader("Create New Profile")
        new_profile_name = st.text_input("New profile name:", key="new_profile_name_input")
        if st.button("Create and Save Current Settings"):
            if new_profile_name and new_profile_name not in st.session_state.profiles:
                st.session_state.profiles[new_profile_name] = {
                    "style": st.session_state.ui_style_instructions,
                    "script": st.session_state.ui_main_text,
                    "voice": st.session_state.ui_voice_select,
                    "temp": st.session_state.ui_temperature,
                    "filename": st.session_state.ui_output_filename
                }
                # หลังจากสร้าง ให้เลือกเป็นโปรไฟล์ปัจจุบันเลย
                st.session_state.current_profile = new_profile_name
                st.success(f"Profile '{new_profile_name}' created!")
                st.rerun()
            else:
                st.warning("Please enter a unique profile name.")
    
    # --- [แก้ไข] จัดการกรณีที่ไม่มีโปรไฟล์ ---
    if st.session_state.current_profile and st.session_state.current_profile in st.session_state.profiles:
        current_settings = st.session_state.profiles[st.session_state.current_profile]
    else:
        # สร้างโปรไฟล์ว่างๆ เพื่อไม่ให้แอปพัง
        current_settings = {
            "style": "", "script": "", "voice": "Achernar - Soft", "temp": 0.9, "filename": "new_voice"
        }

    # --- เริ่มส่วน UI หลักของแอป ---
    with st.container(border=True):
        st.subheader("1. ใส่สคริปต์และคำสั่ง")

        col1, col2 = st.columns(2)
        with col1:
            style_instructions = st.text_area(
                "Style Instructions:", height=250, value=current_settings.get('style', ''),
                key='ui_style_instructions', on_change=save_current_profile_settings
            )
        with col2:
            main_text = st.text_area(
                "Main Text (Script):", height=250, value=current_settings.get('script', ''),
                key='ui_main_text', on_change=save_current_profile_settings
            )

    with st.container(border=True):
        st.subheader("2. ตั้งค่าเสียงและไฟล์")

        col3, col4 = st.columns(2)
        with col3:
            gemini_voices_data = {"Zephyr": "Bright", "Puck": "Upbeat", "Charon": "Informative", "Kore": "Firm", "Fenrir": "Excitable", "Leda": "Youthful", "Orus": "Firm", "Aoede": "Breezy", "Callirrhoe": "Easy-going", "Autonoe": "Bright", "Enceladus": "Breathy", "Iapetus": "Clear", "Umbriel": "Easy-going", "Algieba": "Smooth", "Despina": "Smooth", "Erinome": "Clear", "Algenib": "Gravelly", "Rasalgethi": "Informative", "Laomedeia": "Upbeat", "Achernar": "Soft", "Alnilam": "Firm", "Schedar": "Even", "Gacrux": "Mature", "Pulcherrima": "Forward", "Achird": "Friendly", "Zubenelgenubi": "Casual", "Vindemiatrix": "Gentle", "Sadachbia": "Lively", "Sadaltager": "Knowledgeable", "Sulafat": "Warm"}
            voice_display_list = sorted([f"{name} - {desc}" for name, desc in gemini_voices_data.items()])
            
            try:
                voice_index = voice_display_list.index(current_settings.get('voice', 'Achernar - Soft'))
            except ValueError:
                voice_index = 20

            selected_voice_display = st.selectbox(
                "เลือกเสียงพากย์:", options=voice_display_list, index=voice_index,
                key='ui_voice_select', on_change=save_current_profile_settings
            )
            temperature = st.slider(
                "Temperature (ความสร้างสรรค์ของเสียง):", min_value=0.0, max_value=2.0,
                value=current_settings.get('temp', 0.9), step=0.1,
                key='ui_temperature', on_change=save_current_profile_settings
            )
        with col4:
            output_filename = st.text_input(
                "ตั้งชื่อไฟล์ (ไม่ต้องใส่นามสกุล .mp3):", value=current_settings.get('filename', 'my_voiceover'),
                key='ui_output_filename', on_change=save_current_profile_settings
            )

    st.write("---")

    # ปุ่ม Generate และส่วนแสดงผลลัพธ์
    if st.button("🚀 สร้างไฟล์เสียง (Generate Audio)", type="primary", use_container_width=True):
        if not main_text:
            st.warning("กรุณาใส่สคริปต์ในช่อง Main Text ก่อนครับ")
        else:
            with st.spinner("⏳ กำลังสร้างไฟล์เสียง... กรุณารอสักครู่..."):
                try:
                    voice_name_for_api = selected_voice_display.split(' - ')[0]
                    temp_output_folder = "temp_output"
                    ffmpeg_executable = "ffmpeg"
                    final_mp3_path = run_tts_generation(
                        api_key=api_key, style_instructions=style_instructions, main_text=main_text,
                        voice_name=voice_name_for_api, output_folder=temp_output_folder,
                        output_filename=output_filename, temperature=temperature, ffmpeg_path=ffmpeg_executable
                    )
                    st.success("🎉 สร้างไฟล์เสียงสำเร็จ!")
                    st.audio(final_mp3_path, format='audio/mp3')
                    with open(final_mp3_path, "rb") as file:
                        st.download_button(
                            label="📥 ดาวน์โหลดไฟล์ MP3", data=file,
                            file_name=os.path.basename(final_mp3_path), mime="audio/mp3",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
