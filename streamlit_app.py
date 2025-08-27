# File: streamlit_app.py (พร้อมระบบโปรไฟล์)
# -*- coding: utf-8 -*-
import streamlit as st
import os
from backend.aky_voice_backend import run_tts_generation
import time

# --- ฟังก์ชันสำหรับตรวจสอบรหัสผ่าน (เหมือนเดิม) ---
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

# --- [ใหม่] ฟังก์ชันสำหรับบันทึกค่าลงในโปรไฟล์ปัจจุบัน ---
def save_current_profile_settings():
    """บันทึกค่าจาก UI inputs ทั้งหมดลงใน st.session_state ของโปรไฟล์ปัจจุบัน"""
    profile_name = st.session_state.current_profile
    if profile_name in st.session_state.profiles:
        st.session_state.profiles[profile_name]['style'] = st.session_state.ui_style_instructions
        st.session_state.profiles[profile_name]['script'] = st.session_state.ui_main_text
        st.session_state.profiles[profile_name]['voice'] = st.session_state.ui_voice_select
        st.session_state.profiles[profile_name]['temp'] = st.session_state.ui_temperature
        st.session_state.profiles[profile_name]['filename'] = st.session_state.ui_output_filename

#
