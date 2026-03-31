import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import cv2
import numpy as np
import time
import datetime
import os
import base64

# --- 1. SETUP ---
st.set_page_config(page_title="AI Proctoring Dashboard", layout="wide")
SAVE_DIR = "malpractice_logs"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# --- 2. AUDIO TRIGGER LOGIC ---
def get_audio_html(file_path):
    """Returns an HTML string that plays the MP3 file immediately."""
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            return f"""
                <audio autoplay="true" style="display:none;">
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
            """
    return ""

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

        # MALPRACTICE LOGIC: Not exactly 1 face
        if len(faces) != 1:
            if len(faces) == 0:
                if self.inattention_start is None:
                    self.inattention_start = time.time()
                elapsed = time.time() - self.inattention_start
                if elapsed >= 2.0:
                    self.is_violating = True
                    self._draw_warning(img, f"ALERT: {int(elapsed)}s AWAY")
                else:
                    cv2.putText(img, f"Warning: {elapsed:.1f}s", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            else:
                self.is_violating = True
                self._draw_warning(img, "ALERT: MULTIPLE PEOPLE")
        else:
            self.inattention_start = None
            self.is_violating = False
            (x, y, w, h) = faces[0]
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(img, "STATUS: OK", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        # Snapshot logic
        if self.is_violating and (time.time() - self.last_snap_time > 3):
            ts = datetime.datetime.now().strftime("%H-%M-%S")
            cv2.imwrite(f"{SAVE_DIR}/{ts}_alert.jpg", img)
            self.last_snap_time = time.time()

        return img

    def _draw_warning(self, img, text):
        cv2.rectangle(img, (0, 0), (img.shape[1], img.shape[0]), (0, 0, 255), 20)
        cv2.putText(img, text, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 0, 255), 3)

# --- 4. MAIN UI ---
st.title("🛡️ AI Proctoring System")

# Button to unlock audio permissions in the browser
if "monitoring" not in st.session_state:
    st.session_state.monitoring = False

if not st.session_state.monitoring:
    if st.button("🚀 START MONITORING SESSION", use_container_width=True, type="primary"):
        st.session_state.monitoring = True
        st.rerun()
else:
    col_v, col_s = st.columns([2, 1])
    
    # We create a persistent placeholder for the audio tag
    audio_placeholder = st.empty()

    with col_v:
        ctx = webrtc_streamer(
            key="proctoring-v1",
            video_processor_factory=ProctorProcessor,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"video": True, "audio": False},
        )

    with col_s:
        st.subheader("Live Status")
        if ctx.video_processor:
            if ctx.video_processor.is_violating:
                st.error("❗ MALPRACTICE DETECTED")
                # Update the empty placeholder with the audio HTML
                audio_placeholder.markdown(get_audio_html("beep.mp3"), unsafe_allow_html=True)
            else:
                st.success("✅ Student Attentive")
                audio_placeholder.empty()

        st.divider()
        if st.button("Refresh Alerts"):
            files = sorted([f for f in os.listdir(SAVE_DIR) if f.endswith('.jpg')], reverse=True)
            for f in files[:2]:
                st.image(f"{SAVE_DIR}/{f}", caption=f"Time: {f}")
