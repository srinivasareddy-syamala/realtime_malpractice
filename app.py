import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import cv2
import numpy as np
import time
import datetime
import os
import base64

# --- 1. SETUP ---
st.set_page_config(page_title="Raasi AI Proctor", layout="wide")
SAVE_DIR = "malpractice_logs"
os.makedirs(SAVE_DIR, exist_ok=True)

# --- 2. AUDIO HELPER ---
def play_audio_file(file_path):
    """Plays the MP3 file using a hidden auto-playing HTML tag."""
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            # This HTML snippet forces the browser to play the audio data
            audio_html = f"""
                <audio autoplay="true" style="display:none;">
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
            """
            st.components.v1.html(audio_html, height=0)
    else:
        st.error(f"File {file_path} not found in GitHub repository!")

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

        # VIOLATION LOGIC: 0 faces OR > 1 face
        if len(faces) != 1:
            if len(faces) == 0:
                if self.inattention_start is None:
                    self.inattention_start = time.time()
                
                elapsed = time.time() - self.inattention_start
                if elapsed >= 2.0:
                    self.is_violating = True
                    self._draw_warning(img, f"MALPRACTICE: {int(elapsed)}s AWAY")
                    self._capture(img, "Away")
                else:
                    cv2.putText(img, f"Warning: {elapsed:.1f}s", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            
            else: # Multiple people
                self.is_violating = True
                self._draw_warning(img, "MALPRACTICE: MULTIPLE PEOPLE")
                self._capture(img, "Multiple_People")
        
        else: # Exactly 1 face (Normal)
            self.inattention_start = None
            self.is_violating = False
            (x, y, w, h) = faces[0]
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(img, "STATUS: ACTIVE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return img

    def _draw_warning(self, img, text):
        cv2.rectangle(img, (0, 0), (img.shape[1], img.shape[0]), (0, 0, 255), 20)
        cv2.putText(img, text, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 3)

    def _capture(self, img, reason):
        if time.time() - self.last_snap_time > 3:
            ts = datetime.datetime.now().strftime("%H-%M-%S")
            cv2.imwrite(f"{SAVE_DIR}/{ts}_{reason}.jpg", img)
            self.last_snap_time = time.time()

# --- 4. UI INTERFACE ---
st.title("🛡️ Raasi AI Proctoring System")

# STEP 1: Browser Interaction (Required for Audio)
if "session_unlocked" not in st.session_state:
    st.session_state.session_unlocked = False

if not st.session_state.session_unlocked:
    st.info("👋 Welcome! To enable the audio alarm and camera, please click the button below.")
    if st.button("🚀 START EXAM MONITORING", type="primary", use_container_width=True):
        st.session_state.session_unlocked = True
        st.rerun()
else:
    col_vid, col_logs = st.columns([2, 1])

    with col_vid:
        webrtc_ctx = webrtc_streamer(
            key="proctoring",
            video_processor_factory=ProctorProcessor,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"video": True, "audio": False},
        )

    with col_logs:
        st.subheader("📊 Live Status")
        
        if webrtc_ctx.video_processor:
            if webrtc_ctx.video_processor.is_violating:
                st.error("⚠️ VIOLATION DETECTED")
                # Trigger the beep.mp3 from your GitHub root
                play_audio_file("beep.mp3") 
            else:
                st.success("✅ Student is Attentive")

        st.divider()
        st.write("Recent Alerts:")
        if st.button("Refresh Logs"):
            files = sorted([f for f in os.listdir(SAVE_DIR) if f.endswith('.jpg')], reverse=True)
            for f in files[:3]:
                st.image(f"{SAVE_DIR}/{f}", caption=f"Violation: {f}")
