import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import cv2
import numpy as np
import time
import datetime
import os

# --- 1. SETUP ---
st.set_page_config(page_title="AI Proctor", layout="wide")
SAVE_DIR = "malpractice_logs"
os.makedirs(SAVE_DIR, exist_ok=True)

# --- 2. DETECTION ENGINE ---
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

        # Violation: Multiple People OR No People
        if len(faces) != 1:
            if len(faces) == 0:
                if self.inattention_start is None: self.inattention_start = time.time()
                elapsed = time.time() - self.inattention_start
                if elapsed >= 2.0:
                    self.is_violating = True
                    self._warn(img, f"MALPRACTICE: {int(elapsed)}s AWAY")
                else:
                    cv2.putText(img, f"Warning: {elapsed:.1f}s", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
            else: # Multiple people
                self.is_violating = True
                self._warn(img, "MALPRACTICE: MULTIPLE PEOPLE")
        else:
            self.inattention_start = None
            self.is_violating = False
            (x, y, w, h) = faces[0]
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(img, "STATUS: ACTIVE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return img

    def _warn(self, img, text):
        cv2.rectangle(img, (0, 0), (img.shape[1], img.shape[0]), (0, 0, 255), 20)
        cv2.putText(img, text, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
        if time.time() - self.last_snap_time > 3:
            ts = datetime.datetime.now().strftime("%H-%M-%S")
            cv2.imwrite(f"{SAVE_DIR}/{ts}_violation.jpg", img)
            self.last_snap_time = time.time()

# --- 3. MAIN UI ---
st.title("🛡️ AI: Secure Proctoring")

# CRITICAL: This button "unlocks" the browser's audio permission
if "exam_started" not in st.session_state:
    st.session_state.exam_started = False

if not st.session_state.exam_started:
    if st.button("🚀 CLICK HERE TO START EXAM", use_container_width=True, type="primary"):
        st.session_state.exam_started = True
        st.rerun()
    st.warning("You must click the button above to enable the Malpractice Alarm.")
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
        st.subheader("📊 Session Control")
        if webrtc_ctx.video_processor:
            if webrtc_ctx.video_processor.is_violating:
                st.error("⚠️ MALPRACTICE DETECTED")
                # Using the NEW native Streamlit autoplay (Added in v1.34.0)
                st.audio("beep.mp3", autoplay=True) 
            else:
                st.success("✅ Student Attentive")

        st.divider()
        if st.button("Refresh Snapshots"):
            files = sorted([f for f in os.listdir(SAVE_DIR) if f.endswith('.jpg')], reverse=True)
            for f in files[:3]:
                st.image(f"{SAVE_DIR}/{f}", caption=f"Violation: {f}")
