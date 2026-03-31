import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import cv2
import numpy as np
import time
import datetime
import os
import base64
import streamlit.components.v1 as components

# --- 1. SETUP ---
st.set_page_config(page_title="AI Proctoring System", layout="wide")
SAVE_DIR = "malpractice_logs"
os.makedirs(SAVE_DIR, exist_ok=True)

# --- 2. SIMPLE AUDIO LOGIC (Base64) ---
def play_alarm(file_path):
    """Converts MP3 to Base64 to play in the user's browser."""
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            # The 'autoplay' attribute triggers the sound in the browser
            audio_html = f"""
                <audio autoplay="true" style="display:none;">
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
            """
            components.html(audio_html, height=0)
    else:
        st.error(f"Error: {file_path} not found in repository.")

# --- 3. DETECTION ENGINE ---
class ProctorProcessor(VideoTransformerBase):
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.inattention_start = None
        self.is_violating = False
        self.last_snap_time = 0

    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

        # Logic: Malpractice if 0 faces OR > 1 face
        if len(faces) != 1:
            if len(faces) == 0:
                if self.inattention_start is None:
                    self.inattention_start = time.time()
                
                elapsed = time.time() - self.inattention_start
                if elapsed >= 2.0:
                    self.is_violating = True
                    self._warn_ui(img, f"WARNING: {int(elapsed)}s AWAY")
                    self._save_log(img, "Away")
                else:
                    cv2.putText(img, f"Focus: {elapsed:.1f}s", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            
            else: # Multiple people detected
                self.is_violating = True
                self._warn_ui(img, "WARNING: MULTIPLE PEOPLE")
                self._save_log(img, "Multiple_People")
        
        else: # Normal: Exactly 1 face
            self.inattention_start = None
            self.is_violating = False
            (x, y, w, h) = faces[0]
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(img, "STATUS: OK", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return img

    def _warn_ui(self, img, text):
        cv2.rectangle(img, (0, 0), (img.shape[1], img.shape[0]), (0, 0, 255), 20)
        cv2.putText(img, text, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 3)

    def _save_log(self, img, reason):
        if time.time() - self.last_snap_time > 3:
            ts = datetime.datetime.now().strftime("%H-%M-%S")
            cv2.imwrite(f"{SAVE_DIR}/{ts}_{reason}.jpg", img)
            self.last_snap_time = time.time()

# --- 4. MAIN INTERFACE ---
st.title("🛡️ AI Proctoring Dashboard")

# Browser Interaction Check (Critical for Audio)
if "active" not in st.session_state:
    st.session_state.active = False

if not st.session_state.active:
    st.info("To enable the proctoring alarm, please click the button below.")
    if st.button("🚀 START MONITORING", type="primary", use_container_width=True):
        st.session_state.active = True
        st.rerun()
else:
    col_left, col_right = st.columns([2, 1])

    with col_left:
        webrtc_ctx = webrtc_streamer(
            key="proctor",
            video_processor_factory=ProctorProcessor,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"video": True, "audio": False},
        )

    with col_right:
        st.subheader("System Status")
        if webrtc_ctx.video_processor:
            if webrtc_ctx.video_processor.is_violating:
                st.error("❗ MALPRACTICE ALERT")
                play_alarm("beep.mp3") 
            else:
                st.success("✅ System Normal")

        st.divider()
        st.write("Violation Screenshots:")
        if st.button("Refresh Logs"):
            files = sorted([f for f in os.listdir(SAVE_DIR) if f.endswith('.jpg')], reverse=True)
            for f in files[:3]:
                st.image(f"{SAVE_DIR}/{f}", caption=f"Alert: {f}")
