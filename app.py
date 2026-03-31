import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import cv2
import numpy as np
import time
import datetime
import os
import base64

# --- 1. SETUP ---
st.set_page_config(page_title="AI Proctoring System", layout="wide")
SAVE_DIR = "malpractice_logs"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# --- 2. AUDIO GENERATOR ---
def get_audio_html(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            return f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
    return ""

# --- 3. DETECTION ENGINE ---
class ProctorProcessor(VideoTransformerBase):
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.inattention_start = None
        self.last_snap_time = 0
        # Internal state flags
        self.is_violating = False
        self.violation_count = 0

    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

        # LOGIC: Check for 0 or 2+ faces
        if len(faces) != 1:
            if len(faces) == 0:
                if self.inattention_start is None:
                    self.inattention_start = time.time()
                elapsed = time.time() - self.inattention_start
                if elapsed >= 2.0:
                    self._trigger_malpractice(img, f"AWAY: {int(elapsed)}s")
            else:
                self._trigger_malpractice(img, "MULTIPLE PEOPLE")
        else:
            self.inattention_start = None
            self.is_violating = False
            (x, y, w, h) = faces[0]
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)

        return img

    def _trigger_malpractice(self, img, reason):
        self.is_violating = True
        cv2.rectangle(img, (0, 0), (img.shape[1], img.shape[0]), (0, 0, 255), 20)
        cv2.putText(img, reason, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        
        # Save snapshot and increment count every 3 seconds
        if time.time() - self.last_snap_time > 3:
            self.violation_count += 1
            ts = datetime.datetime.now().strftime("%H-%M-%S")
            cv2.imwrite(f"{SAVE_DIR}/{ts}_warning.jpg", img)
            self.last_snap_time = time.time()

# --- 4. MAIN UI ---
st.title("🛡️ Secure AI Proctoring")

if "start" not in st.session_state:
    st.session_state.start = False

if not st.session_state.start:
    if st.button("🚀 START EXAM SESSION", type="primary", use_container_width=True):
        st.session_state.start = True
        st.rerun()
else:
    col_vid, col_stat = st.columns([2, 1])
    
    # Placeholders for dynamic updates
    audio_area = st.empty()
    
    with col_vid:
        webrtc_ctx = webrtc_streamer(
            key="proctor-engine",
            video_processor_factory=ProctorProcessor,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"video": True, "audio": False},
        )

    with col_stat:
        st.subheader("📋 Session Live Status")
        
        # Pull data from the video thread
        if webrtc_ctx.video_processor:
            v_count = webrtc_ctx.video_processor.violation_count
            is_bad = webrtc_ctx.video_processor.is_violating
            
            # Status Box
            if is_bad:
                st.error(f"⚠️ MALPRACTICE DETECTED")
                audio_area.markdown(get_audio_html("beep.mp3"), unsafe_allow_html=True)
            else:
                st.success("✅ STUDENT ATTENTIVE")
                audio_area.empty()

            # Warning Counter
            st.metric("Total Warnings", v_count)

            # Auto-display Gallery
            st.divider()
            st.write("Recent Violation Captures:")
            files = sorted([f for f in os.listdir(SAVE_DIR) if f.endswith('.jpg')], reverse=True)
            if files:
                for f in files[:3]: # Shows top 3 latest images automatically
                    st.image(f"{SAVE_DIR}/{f}", use_container_width=True)
            else:
                st.info("No violations recorded yet.")
        
        # Force the UI to refresh to pick up thread changes
        time.sleep(0.5)
        st.rerun()
