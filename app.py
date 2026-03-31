import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import cv2
import numpy as np
import time
import datetime
import os
import streamlit.components.v1 as components

# --- Setup ---
st.set_page_config(page_title="Raasi AI Proctor", layout="wide")
SAVE_DIR = "malpractice_logs"
os.makedirs(SAVE_DIR, exist_ok=True)

# --- JavaScript for Browser-Side Audio ---
# This solves the "server cannot play sound" problem
def play_browser_beep():
    components.html(
        """
        <script>
        var context = new (window.AudioContext || window.webkitAudioContext)();
        var oscillator = context.createOscillator();
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(1000, context.currentTime);
        oscillator.connect(context.destination);
        oscillator.start();
        setTimeout(function(){ oscillator.stop(); }, 500);
        </script>
        """,
        height=0,
    )

# --- Improved Detection Logic ---
class ProctorProcessor(VideoTransformerBase):
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.inattention_start = None
        self.malpractice_confirmed = False
        self.last_snap_time = 0

    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

        if len(faces) == 1:
            # ✅ Status: Normal
            self.inattention_start = None
            self.malpractice_confirmed = False
            (x, y, w, h) = faces[0]
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(img, "STATUS: ACTIVE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
        elif len(faces) > 1:
            # ⚠️ Status: Multiple People (Malpractice)
            cv2.putText(img, "WARNING: MULTIPLE PEOPLE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            self._trigger_violation(img, "Multiple Persons")

        else:
            # ❌ Status: No Face / Looking Away
            if self.inattention_start is None:
                self.inattention_start = time.time()
            
            elapsed = time.time() - self.inattention_start
            
            if elapsed >= 2.0:
                self.malpractice_confirmed = True
                cv2.rectangle(img, (0, 0), (img.shape[1], img.shape[0]), (0, 0, 255), 15)
                cv2.putText(img, f"VIOLATION: {elapsed:.1f}s AWAY", (50, 240), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                self._trigger_violation(img, "Looking Away")
            else:
                cv2.putText(img, f"WARNING: {elapsed:.1f}s", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

        return img

    def _trigger_violation(self, img, reason):
        # Save snapshot once every 3 seconds during violation
        if time.time() - self.last_snap_time > 3:
            ts = datetime.datetime.now().strftime("%H-%M-%S")
            filename = f"{SAVE_DIR}/{ts}_{reason.replace(' ', '_')}.jpg"
            cv2.imwrite(filename, img)
            self.last_snap_time = time.time()
            # Note: We can't call st.write inside the transform thread, 
            # so we handle UI updates in the main loop.

# --- Main UI ---
st.title("🛡️ Raasi AI: Secure Proctoring")

col_vid, col_logs = st.columns([2, 1])

with col_vid:
    webrtc_ctx = webrtc_streamer(
        key="proctoring",
        video_processor_factory=ProctorProcessor,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"video": True, "audio": False},
    )

with col_logs:
    st.subheader("📊 Live Violation Log")
    
    # Check for violations to play sound
    if webrtc_ctx.video_processor:
        if webrtc_ctx.video_processor.malpractice_confirmed:
            st.error("Malpractice Detected!")
            play_browser_beep() # Trigger the JS sound

    # Display Snapshots
    st.divider()
    if st.button("Refresh Log"):
        files = sorted(os.listdir(SAVE_DIR), reverse=True)
        for f in files[:5]:
            st.image(f"{SAVE_DIR}/{f}", caption=f"Captured: {f}")
