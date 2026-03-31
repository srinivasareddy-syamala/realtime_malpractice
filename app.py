import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import cv2
import numpy as np
import time
import datetime
import os
import streamlit.components.v1 as components

# --- Setup ---
st.set_page_config(page_title=" AI Proctor", layout="wide")
SAVE_DIR = "malpractice_logs"
os.makedirs(SAVE_DIR, exist_ok=True)

# --- JavaScript for Browser-Side Audio ---
# This injects a small script to play a 1000Hz beep for 500ms
def play_browser_beep():
    components.html(
        """
        <script>
        var context = new (window.AudioContext || window.webkitAudioContext)();
        var oscillator = context.createOscillator();
        oscillator.type = 'square'; // 'square' is louder and more "beepy"
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
        self.is_violating = False  # Flag for the UI to play sound
        self.last_snap_time = 0

    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

        # 1. CHECK FOR MULTIPLE PEOPLE
        if len(faces) > 1:
            self.is_violating = True
            self._draw_warning(img, "MALPRACTICE: MULTIPLE PEOPLE")
            self._take_snapshot(img, "Multiple_People")

        # 2. CHECK FOR LOOKING AWAY (No face detected)
        elif len(faces) == 0:
            if self.inattention_start is None:
                self.inattention_start = time.time()
            
            elapsed = time.time() - self.inattention_start
            
            if elapsed >= 2.0:
                self.is_violating = True
                self._draw_warning(img, f"MALPRACTICE: {int(elapsed)}s AWAY")
                self._take_snapshot(img, "Looking_Away")
            else:
                cv2.putText(img, f"Warning: {elapsed:.1f}s", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        
        # 3. NORMAL STATE (Exactly 1 face)
        else:
            self.inattention_start = None
            self.is_violating = False
            (x, y, w, h) = faces[0]
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(img, "STATUS: ACTIVE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return img

    def _draw_warning(self, img, text):
        # Draw thick red border and large warning text
        cv2.rectangle(img, (0, 0), (img.shape[1], img.shape[0]), (0, 0, 255), 20)
        cv2.putText(img, text, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

    def _take_snapshot(self, img, reason):
        # Prevent spamming: only take a snapshot every 3 seconds
        if time.time() - self.last_snap_time > 3:
            ts = datetime.datetime.now().strftime("%H-%M-%S")
            cv2.imwrite(f"{SAVE_DIR}/{ts}_{reason}.jpg", img)
            self.last_snap_time = time.time()

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
    st.subheader("📊 Session Control")
    
    # This block checks the 'is_violating' flag from the video thread
    if webrtc_ctx.video_processor:
        if webrtc_ctx.video_processor.is_violating:
            st.error("⚠️ MALPRACTICE DETECTED")
            play_browser_beep() # This plays the sound in the browser
        else:
            st.success("✅ Monitoring Active")

    # Display Snapshots Log
    st.divider()
    st.write("Recent Violations:")
    if st.button("Refresh Snapshots"):
        files = sorted([f for f in os.listdir(SAVE_DIR) if f.endswith('.jpg')], reverse=True)
        for f in files[:4]:
            st.image(f"{SAVE_DIR}/{f}", caption=f"Time: {f.split('_')[0]}")
