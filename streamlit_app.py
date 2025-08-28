# File: streamlit_app.py
# -*- coding: utf-8 -*-
import streamlit as st
import os
import json
from backend.aky_voice_backend import run_tts_generation
import time
from typing import Dict, Any
from pathlib import Path

# --- Configuration ---
PROFILES_FILE = "profiles_data.json"

# --- Persistent Storage Functions ---


def load_profiles_from_file() -> Dict:
    """โหลดข้อมูล Profiles จากไฟล์ JSON"""
    try:
        if os.path.exists(PROFILES_FILE):
            with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
    except Exception as e:
        st.warning(f"Could not load profiles: {e}")

    # Return default if file doesn't exist or error
    return {
        'profiles': {
            'Default': {
                'style_instructions': '',
                'main_text': '',
                'voice': 'Achernar - Soft',
                'temperature': 0.9,
                'filename': 'my_voiceover'
            }
        },
        'last_profile': 'Default'
    }


def save_profiles_to_file(data: Dict):
    """บันทึกข้อมูล Profiles ลงไฟล์ JSON"""
    try:
        with open(PROFILES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Could not save profiles: {e}")
        return False

# --- Profile Management Functions ---


def initialize_profiles():
    """สร้าง Session State สำหรับเก็บข้อมูล Profiles"""
    # โหลดข้อมูลจากไฟล์
    saved_data = load_profiles_from_file()

    if 'profiles' not in st.session_state:
        st.session_state.profiles = saved_data['profiles']

    if 'current_profile' not in st.session_state:
        st.session_state.current_profile = saved_data.get(
            'last_profile', 'Default')

    # Initialize tracking for auto-save
    if 'last_saved_values' not in st.session_state:
        st.session_state.last_saved_values = {}

    # Flag to track if data needs saving
    if 'data_changed' not in st.session_state:
        st.session_state.data_changed = False


def get_current_profile_data() -> Dict[str, Any]:
    """ดึงข้อมูลของ Profile ปัจจุบัน"""
    return st.session_state.profiles.get(
        st.session_state.current_profile,
        st.session_state.profiles['Default']
    )


def save_to_current_profile(field: str, value: Any):
    """บันทึกค่าไปยัง Profile ปัจจุบันและบันทึกลงไฟล์"""
    if st.session_state.current_profile in st.session_state.profiles:
        st.session_state.profiles[st.session_state.current_profile][field] = value

        # บันทึกลงไฟล์ทันที
        data_to_save = {
            'profiles': st.session_state.profiles,
            'last_profile': st.session_state.current_profile
        }
        save_profiles_to_file(data_to_save)


def create_new_profile(profile_name: str) -> bool:
    """สร้าง Profile ใหม่"""
    if not profile_name or profile_name.strip() == '':
        return False

    profile_name = profile_name.strip()

    # ตรวจสอบว่าชื่อซ้ำหรือไม่
    if profile_name in st.session_state.profiles:
        return False

    # คัดลอกค่าจาก Profile ปัจจุบัน
    current_data = get_current_profile_data()
    st.session_state.profiles[profile_name] = current_data.copy()
    st.session_state.current_profile = profile_name

    # บันทึกลงไฟล์
    data_to_save = {
        'profiles': st.session_state.profiles,
        'last_profile': st.session_state.current_profile
    }
    save_profiles_to_file(data_to_save)

    return True


def delete_profile(profile_name: str) -> bool:
    """ลบ Profile (ห้ามลบ Default)"""
    if profile_name == 'Default' or profile_name not in st.session_state.profiles:
        return False

    del st.session_state.profiles[profile_name]

    # ถ้าลบ Profile ที่กำลังใช้อยู่ ให้กลับไป Default
    if st.session_state.current_profile == profile_name:
        st.session_state.current_profile = 'Default'

    # บันทึกลงไฟล์
    data_to_save = {
        'profiles': st.session_state.profiles,
        'last_profile': st.session_state.current_profile
    }
    save_profiles_to_file(data_to_save)

    return True


def switch_profile(profile_name: str):
    """สลับไปยัง Profile อื่น"""
    if profile_name in st.session_state.profiles:
        st.session_state.current_profile = profile_name

        # บันทึก profile ล่าสุดลงไฟล์
        data_to_save = {
            'profiles': st.session_state.profiles,
            'last_profile': st.session_state.current_profile
        }
        save_profiles_to_file(data_to_save)

# --- Auto-save Function ---


def auto_save_field(field_name: str, value: Any):
    """บันทึกค่าอัตโนมัติเมื่อมีการเปลี่ยนแปลง"""
    current_key = f"{st.session_state.current_profile}_{field_name}"

    # ตรวจสอบว่าค่าเปลี่ยนหรือไม่
    if st.session_state.last_saved_values.get(current_key) != value:
        save_to_current_profile(field_name, value)
        st.session_state.last_saved_values[current_key] = value

# --- Password Check Function ---


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


# --- Main App ---
st.set_page_config(page_title="Affiliate Voice Generator Pro", layout="wide")

st.title("🎙️ Affiliate Voice Generator Pro")
st.write("---")

# ตรวจสอบรหัสผ่านก่อนแสดงแอป
if check_password():

    # Initialize profiles system
    initialize_profiles()

    # ตรวจสอบว่าได้ตั้งค่า API Key ใน Secrets แล้วหรือยัง
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        if not api_key:
            st.error("❌ กรุณาตั้งค่า GOOGLE_API_KEY ใน Streamlit Secrets")
            st.stop()
    except KeyError:
        st.error("❌ ไม่พบ GOOGLE_API_KEY ในการตั้งค่า Secrets!")
        st.stop()

    # --- Profile Management UI ---
    with st.container(border=True):
        st.subheader("📁 Profile Management")

        col_profile1, col_profile2, col_profile3 = st.columns([3, 2, 1])

        with col_profile1:
            # Dropdown สำหรับเลือก Profile
            profile_options = list(st.session_state.profiles.keys())
            current_index = profile_options.index(
                st.session_state.current_profile) if st.session_state.current_profile in profile_options else 0

            selected_profile = st.selectbox(
                "Select Profile:",
                options=profile_options,
                index=current_index,
                key="profile_selector",
                on_change=lambda: switch_profile(
                    st.session_state.profile_selector)
            )

        with col_profile2:
            # ช่องใส่ชื่อ Profile ใหม่
            new_profile_name = st.text_input(
                "New Profile Name:",
                key="new_profile_input",
                placeholder="Enter profile name"
            )

        with col_profile3:
            st.write("")  # Spacer
            st.write("")  # Spacer
            # ปุ่มเพิ่ม Profile
            if st.button("➕ Add Profile", use_container_width=True):
                if create_new_profile(new_profile_name):
                    st.success(f"✅ Created profile: {new_profile_name}")
                    st.rerun()
                else:
                    st.error("Profile name is empty or already exists")

        # ปุ่มลบ Profile (ไม่ให้ลบ Default)
        if st.session_state.current_profile != 'Default':
            col_del1, col_del2, col_del3 = st.columns([1, 2, 1])
            with col_del2:
                if st.button(f"🗑️ Delete '{st.session_state.current_profile}' Profile",
                             type="secondary",
                             use_container_width=True):
                    if delete_profile(st.session_state.current_profile):
                        st.success("Profile deleted")
                        st.rerun()

    # ดึงข้อมูลจาก Profile ปัจจุบัน
    profile_data = get_current_profile_data()

    # --- Main UI ---
    with st.container(border=True):
        st.subheader("1. ใส่สคริปต์และคำสั่ง")

        # แสดงชื่อ Profile ที่กำลังใช้
        st.info(
            f"📌 Currently using profile: **{st.session_state.current_profile}**")

        col1, col2 = st.columns(2)
        with col1:
            style_instructions = st.text_area(
                "Style Instructions:",
                height=250,
                value=profile_data.get('style_instructions', ''),
                placeholder="ตัวอย่าง: พูดด้วยน้ำเสียงตื่นเต้น สดใส มีพลัง",
                key="style_input",
                on_change=lambda: auto_save_field(
                    'style_instructions', st.session_state.style_input)
            )
        with col2:
            main_text = st.text_area(
                "Main Text (Script):",
                height=250,
                value=profile_data.get('main_text', ''),
                placeholder="ใส่สคริปต์หลักของคุณที่นี่...",
                key="main_text_input",
                on_change=lambda: auto_save_field(
                    'main_text', st.session_state.main_text_input)
            )

    with st.container(border=True):
        st.subheader("2. ตั้งค่าเสียงและไฟล์")

        col3, col4 = st.columns(2)
        with col3:
            # รายชื่อเสียง
            gemini_voices_data = {
                "Zephyr": "Bright", "Puck": "Upbeat", "Charon": "Informative",
                "Kore": "Firm", "Fenrir": "Excitable", "Leda": "Youthful",
                "Orus": "Firm", "Aoede": "Breezy", "Callirrhoe": "Easy-going",
                "Autonoe": "Bright", "Enceladus": "Breathy", "Iapetus": "Clear",
                "Umbriel": "Easy-going", "Algieba": "Smooth", "Despina": "Smooth",
                "Erinome": "Clear", "Algenib": "Gravelly", "Rasalgethi": "Informative",
                "Laomedeia": "Upbeat", "Achernar": "Soft", "Alnilam": "Firm",
                "Schedar": "Even", "Gacrux": "Mature", "Pulcherrima": "Forward",
                "Achird": "Friendly", "Zubenelgenubi": "Casual", "Vindemiatrix": "Gentle",
                "Sadachbia": "Lively", "Sadaltager": "Knowledgeable", "Sulafat": "Warm"
            }
            voice_display_list = sorted(
                [f"{name} - {desc}" for name, desc in gemini_voices_data.items()])

            # หา index ของเสียงที่บันทึกไว้
            saved_voice = profile_data.get('voice', 'Achernar - Soft')
            voice_index = voice_display_list.index(
                saved_voice) if saved_voice in voice_display_list else 20

            selected_voice_display = st.selectbox(
                "เลือกเสียงพากย์:",
                options=voice_display_list,
                index=voice_index,
                key="voice_selector",
                on_change=lambda: auto_save_field(
                    'voice', st.session_state.voice_selector)
            )

            temperature = st.slider(
                "Temperature (ความสร้างสรรค์ของเสียง):",
                min_value=0.0,
                max_value=2.0,
                value=profile_data.get('temperature', 0.9),
                step=0.1,
                key="temp_slider",
                on_change=lambda: auto_save_field(
                    'temperature', st.session_state.temp_slider)
            )

        with col4:
            output_filename = st.text_input(
                "ตั้งชื่อไฟล์ (ไม่ต้องใส่นามสกุล .mp3):",
                value=profile_data.get('filename', 'my_voiceover'),
                key="filename_input",
                on_change=lambda: auto_save_field(
                    'filename', st.session_state.filename_input)
            )

            # แสดงสถานะการบันทึก
            st.caption("💾 ข้อมูลจะถูกบันทึกอัตโนมัติเมื่อมีการเปลี่ยนแปลง")

    st.write("---")

    # --- Generate Button ---
    if st.button("🚀 สร้างไฟล์เสียง (Generate Audio)", type="primary", use_container_width=True):

        # [แก้ไข] ตรวจสอบข้อมูลจาก profile_data โดยตรง
        if not profile_data.get('main_text', ''):
            st.warning("⚠️ กรุณาใส่สคริปต์ในช่อง Main Text")
        else:
            with st.spinner("⏳ กำลังสร้างไฟล์เสียง... กรุณารอสักครู่..."):
                try:
                    voice_name_for_api = profile_data.get('voice', 'Achernar - Soft').split(' - ')[0]
                    temp_output_folder = "temp_output"

                    # [แก้ไข] เรียกใช้ Backend โดยดึงข้อมูลจาก profile_data ทั้งหมด
                    final_mp3_path = run_tts_generation(
                        api_key=api_key,
                        style_instructions=profile_data.get('style_instructions', ''),
                        main_text=profile_data.get('main_text', ''),
                        voice_name=voice_name_for_api,
                        output_folder=temp_output_folder,
                        output_filename=profile_data.get('filename', 'my_voiceover'),
                        temperature=profile_data.get('temperature', 0.9),
                        ffmpeg_path="ffmpeg"
                    )

                    st.success("🎉 สร้างไฟล์เสียงสำเร็จ!")
                    st.audio(final_mp3_path, format='audio/mp3')

                    with open(final_mp3_path, "rb") as file:
                        st.download_button(
                            label="📥 ดาวน์โหลดไฟล์ MP3",
                            data=file,
                            file_name=os.path.basename(final_mp3_path),
                            mime="audio/mp3",
                            use_container_width=True
                        )

                except Exception as e:
                    st.error(f"❌ เกิดข้อผิดพลาด: {e}")

                    # แสดงข้อมูล Debug เพิ่มเติม
                    with st.expander("🔍 ดูรายละเอียด Error"):
                        st.code(str(e))
                        st.info("""
                        หากพบ Error เกี่ยวกับ API:
                        1. ตรวจสอบว่า API Key ถูกต้อง
                        2. ตรวจสอบ Quota ของ API
                        3. ลองใช้ text สั้นๆ ก่อนเพื่อทดสอบ
                        """)

    # --- Footer Info ---
    with st.expander("ℹ️ ข้อมูลเกี่ยวกับ Profile"):
        st.info("""
        **📁 ระบบ Profile:**
        - ข้อมูล Profile จะถูกบันทึกอัตโนมัติทุกครั้งที่มีการเปลี่ยนแปลง
        - ข้อมูลจะคงอยู่แม้ปิด Browser หรือ Refresh หน้า
        - สามารถสร้าง Profile ได้ไม่จำกัด
        - Profile 'Default' ไม่สามารถลบได้
        
        **🔒 ความปลอดภัย:**
        - API Key ถูกเก็บใน Streamlit Secrets (ไม่แสดงในโค้ด)
        - ข้อมูล Profile ไม่มี API Key หรือข้อมูลส่วนตัว
        - ต้องใส่รหัสผ่านเพื่อเข้าใช้งาน
        """)

        # Debug Information (ซ่อนได้)
        if st.checkbox("🔧 แสดงข้อมูล Debug"):
            col_debug1, col_debug2 = st.columns(2)
            with col_debug1:
                st.write("**Profiles ทั้งหมด:**")
                st.json(st.session_state.profiles)
            with col_debug2:
                st.write("**Profile ปัจจุบัน:**",
                         st.session_state.current_profile)
                st.write("**ข้อมูล Profile:**")
                st.json(profile_data)


