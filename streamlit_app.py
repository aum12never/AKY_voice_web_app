# File: streamlit_app.py (แก้ไข Bug และปรับปรุง Profile ทั้งระบบ)
# -*- coding: utf-8 -*-
import streamlit as st
import os
from backend.aky_voice_backend import run_tts_generation
import time

# --- ฟังก์ชันสำหรับตรวจสอบรหัสผ่าน ---
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        if st.session_state.get("password") == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            if "password" in st.session_state:
                del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if not st.session_state.get("password_correct", False):
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        if not st.session_state.get("password_correct", False):
             st.error("😕 Password incorrect")
        return False
    return True

# --- ฟังก์ชันสำหรับ "โหลด" ค่าจากโปรไฟล์มาแสดงบน UI ---
def load_profile_to_ui():
    """โหลดค่าจากโปรไฟล์ที่เลือกมาใส่ใน State ของ UI"""
    profile_name = st.session_state.get('current_profile')
    if profile_name and profile_name in st.session_state.get('profiles', {}):
        profile_data = st.session_state.profiles[profile_name]
        st.session_state.ui_style_instructions = profile_data.get('style', '')
        st.session_state.ui_main_text = profile_data.get('script', '')
        st.session_state.ui_voice_select = profile_data.get('voice', 'Achernar - Soft')
        st.session_state.ui_temperature = profile_data.get('temp', 0.9)
        st.session_state.ui_output_filename = profile_data.get('filename', 'my_voiceover')
    else: # กรณีไม่มีโปรไฟล์หรือโปรไฟล์ที่เลือกไม่มีอยู่จริง
        st.session_state.ui_style_instructions = ""
        st.session_state.ui_main_text = ""
        st.session_state.ui_voice_select = "Achernar - Soft"
        st.session_state.ui_temperature = 0.9
        st.session_state.ui_output_filename = "new_voice"

# --- ฟังก์ชันสำหรับ "บันทึก" ค่าจาก UI กลับไปที่โปรไฟล์ ---
def save_ui_to_profile():
    """บันทึกค่าจาก State ของ UI กลับไปที่โปรไฟล์ที่กำลังเลือกอยู่"""
    profile_name = st.session_state.get('current_profile')
    if profile_name and profile_name in st.session_state.get('profiles', {}):
        st.session_state.profiles[profile_name]['style'] = st.session_state.ui_style_instructions
        st.session_state.profiles[profile_name]['script'] = st.session_state.ui_main_text
        st.session_state.profiles[profile_name]['voice'] = st.session_state.ui_voice_select
        st.session_state.profiles[profile_name]['temp'] = st.session_state.ui_temperature
        st.session_state.profiles[profile_name]['filename'] = st.session_state.ui_output_filename

# --- ส่วนแสดงผลหลักของแอป ---
st.set_page_config(page_title="Affiliate Voice Generator AKYYY", layout="wide")
st.title("🎙️ Affiliate Voice Generator Pro AKY VVVV")
st.write("---")

if check_password():
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except KeyError:
        st.error("❌ ไม่พบ GOOGLE_API_KEY ในการตั้งค่า Secrets!")
        st.stop()

    # --- [แก้ไข] ตรวจสอบและสร้าง State ทั้งหมดให้มั่นใจว่ามีอยู่จริง ---
    if 'ui_style_instructions' not in st.session_state:
        st.session_state.profiles = {}
        st.session_state.current_profile = None
        # ตั้งค่าเริ่มต้นให้ State ของ UI
        load_profile_to_ui()

    # --- [ปรับปรุง] ตรรกะการเลือกโปรไฟล์หลังการสร้าง ---
    if 'just_created_profile' in st.session_state:
        st.session_state.current_profile = st.session_state.just_created_profile
        del st.session_state.just_created_profile
        load_profile_to_ui()

    with st.sidebar:
        st.header("👤 Profile Management")
        st.write("---")
        st.subheader("Select Profile")

        col1, col2 = st.columns([0.8, 0.2])
        
        with col1:
            profile_options = list(st.session_state.profiles.keys())
            if not profile_options:
                st.caption("No profiles yet.")
            else:
                st.selectbox(
                    "Select Profile:", options=profile_options, key='current_profile',
                    on_change=load_profile_to_ui, label_visibility="collapsed"
                )
        
        with col2:
            if st.session_state.current_profile:
                if st.button("🗑️", key="delete_profile", help=f"Delete profile '{st.session_state.current_profile}'"):
                    profile_to_delete = st.session_state.current_profile
                    del st.session_state.profiles[profile_to_delete]
                    
                    remaining_profiles = list(st.session_state.profiles.keys())
                    st.session_state.current_profile = remaining_profiles[0] if remaining_profiles else None
                    
                    st.success(f'ลบ Profile "{profile_to_delete}" แล้ว')
                    load_profile_to_ui()
                    st.rerun()

        st.write("---")
        st.subheader("Create New Profile")
        new_profile_name = st.text_input("New profile name:", key="new_profile_name_input")
        
        if st.button("Create and Save Current Settings"):
            if new_profile_name and new_profile_name not in st.session_state.profiles:
                # บันทึกค่าปัจจุบันจาก UI ลงโปรไฟล์ใหม่
                st.session_state.profiles[new_profile_name] = {
                    'style': st.session_state.ui_style_instructions,
                    'script': st.session_state.ui_main_text,
                    'voice': st.session_state.ui_voice_select,
                    'temp': st.session_state.ui_temperature,
                    'filename': st.session_state.ui_output_filename
                }
                # [ปรับปรุง] ตั้งค่าสถานะเพื่อให้แอปเลือโปรไฟล์นี้ในรอบถัดไป
                st.session_state.just_created_profile = new_profile_name
                st.success(f"Profile '{new_profile_name}' created!")
                st.rerun()
            else:
                st.warning("Please enter a unique profile name.")
    
    # --- ส่วน UI หลัก ---
    with st.container(border=True):
        st.subheader("1. ใส่สคริปต์และคำสั่ง")
        col1, col2 = st.columns(2)
        with col1:
            st.text_area("Style Instructions:", height=250, key='ui_style_instructions', on_change=save_ui_to_profile)
        with col2:
            st.text_area("Main Text (Script):", height=250, key='ui_main_text', on_change=save_ui_to_profile)

    with st.container(border=True):
        st.subheader("2. ตั้งค่าเสียงและไฟล์")
        col3, col4 = st.columns(2)
        with col3:
            gemini_voices_data = {"Zephyr": "Bright", "Puck": "Upbeat", "Charon": "Informative", "Kore": "Firm", "Fenrir": "Excitable", "Leda": "Youthful", "Orus": "Firm", "Aoede": "Breezy", "Callirrhoe": "Easy-going", "Autonoe": "Bright", "Enceladus": "Breathy", "Iapetus": "Clear", "Umbriel": "Easy-going", "Algieba": "Smooth", "Despina": "Smooth", "Erinome": "Clear", "Algenib": "Gravelly", "Rasalgethi": "Informative", "Laomedeia": "Upbeat", "Achernar": "Soft", "Alnilam": "Firm", "Schedar": "Even", "Gacrux": "Mature", "Pulcherrima": "Forward", "Achird": "Friendly", "Zubenelgenubi": "Casual", "Vindemiatrix": "Gentle", "Sadachbia": "Lively", "Sadaltager": "Knowledgeable", "Sulafat": "Warm"}
            voice_display_list = sorted([f"{name} - {desc}" for name, desc in gemini_voices_data.items()])
            try:
                voice_index = voice_display_list.index(st.session_state.ui_voice_select)
            except ValueError:
                voice_index = 20
            st.selectbox("เลือกเสียงพากย์:", options=voice_display_list, index=voice_index, key='ui_voice_select', on_change=save_ui_to_profile)
            st.slider("Temperature:", min_value=0.0, max_value=2.0, step=0.1, key='ui_temperature', on_change=save_ui_to_profile)
        with col4:
            st.text_input("ตั้งชื่อไฟล์ (ไม่ต้องใส่นามสกุล .mp3):", key='ui_output_filename', on_change=save_ui_to_profile)

    st.write("---")

    if st.button("🚀 สร้างไฟล์เสียง (Generate Audio)", type="primary", use_container_width=True):
        if not st.session_state.ui_main_text:
            st.warning("กรุณาใส่สคริปต์ในช่อง Main Text ก่อนครับ")
        else:
            with st.spinner("⏳ กำลังสร้างไฟล์เสียง..."):
                try:
                    voice_name_for_api = st.session_state.ui_voice_select.split(' - ')[0]
                    final_mp3_path = run_tts_generation(
                        api_key=api_key, style_instructions=st.session_state.ui_style_instructions,
                        main_text=st.session_state.ui_main_text, voice_name=voice_name_for_api,
                        output_folder="temp_output", output_filename=st.session_state.ui_output_filename,
                        temperature=st.session_state.ui_temperature, ffmpeg_path="ffmpeg"
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
