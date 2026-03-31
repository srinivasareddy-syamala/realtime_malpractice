import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import cv2
import numpy as np
import time
import datetime
import os
import base64
import streamlit.components.v1 as components

# --- 1. SETUP & DIRECTORIES ---
st.set_page_config(page_title="AI Proctor", layout="wide")
SAVE_DIR = "malpractice_logs"
os.makedirs(SAVE_DIR, exist_ok=True)

# --- 2. AUDIO LOGIC (Browser-Side MP3) ---
def play_local_mp3(file_path):
    """Encodes local MP3 to Base64 and triggers browser autoplay."""
    try:
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                data = f.read()
                b64 = base64.b64encode(data).decode()
                # HTML snippet to trigger audio in the student's browser
                audio_html = f"""
                    <audio autoplay="true">
                        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                    </audio>
                """
                components.html(audio_html, height=0)
    except Exception as e:
        st.error(f"Audio Error: {e}")

# --- 3. DETECTION ENGINE ---
class ProctorProcessor(VideoTransformerBase):
    def __init__(self):
        # Load the pre-trained face detection model
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.inattention_start = None
        self.is_violating = False  # The 'Master Flag' for UI/Sound
        self.last_snap_time = 0

    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1) # Mirror view for the student
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect all faces in the frame
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)

        # SCENARIO A: MULTIPLE PEOPLE DETECTED
        if len(faces) > 1:
            self.is_violating = True
            self._draw_ui(img, "MALPRACTICE: MULTIPLE PEOPLE", (0, 0, 255))
            self._take_snapshot(img, "Multiple_People")

        # SCENARIO B: NO FACE DETECTED (LOOKING AWAY)
        elif len(faces) == 0:
            if self.inattention_start is None:
                self.inattention_start = time.time()
            
            elapsed = time.time() - self.inattention_start
            
            if elapsed >= 2.0:
                self.is_violating = True
                self._draw_ui(img, f"MALPRACTICE: {int(elapsed)}s AWAY", (0, 0, 255))
                self._take_snapshot(img, "Looking_Away")
            else:
                # Early warning before 2 seconds
                self._draw_ui(img, f"Warning: {elapsed:.1f}s", (0, 165, 255))
        
        # SCENARIO C: NORMAL (EXACTLY 1 PERSON)
        else:
            self.inattention_start = None
            self.is_violating = False
            (x, y, w, h) = faces[0]
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            self._draw_ui(img, "STATUS: ACTIVE", (0, 255, 0))

        return img

    def _draw_ui(self, img, text, color):
        # Draw red border if violating
        if self.is_violating:
            cv2.rectangle(img, (0, 0), (img.shape[1], img.shape[0]), (0, 0, 255), 20)
        
        cv2.putText(img, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    def _take_snapshot(self, img, reason):
        # Log a snapshot once every 3 seconds to avoid filling up disk space
        if time.time() - self.last_snap_time > 3:
            ts = datetime.datetime.now().strftime("%H-%M-%S")
            cv2.imwrite(f"{SAVE_DIR}/{ts}_{reason}.jpg", img)
            self.last_snap_time = time.time()

# --- 4. MAIN STREAMLIT UI ---
st.title("🛡️ AI: Secure Proctoring System")
st.markdown("Monitoring for **Multiple People** and **Extended Absence (2s+)**.")

col_vid, col_logs = st.columns([2, 1])

with col_vid:
    # WebRTC Component handles browser camera permissions automatically
    webrtc_ctx = webrtc_streamer(
        key="proctoring-engine",
        video_processor_factory=ProctorProcessor,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"video": True, "audio": False},
    )

with col_logs:
    st.subheader("📊 Session Control")
    
    # Sync UI with the detection engine's violation flag
    if webrtc_ctx.video_processor:
        if webrtc_ctx.video_processor.is_violating:
            st.error("⚠️ MALPRACTICE DETECTED")
            # Trigger the MP3 file playback in the browser
            play_local_mp3("beep.mp3") 
        else:
            st.success("✅ Student Attentive")

    # Display Logs
    st.divider()
    st.write("Recent Malpractice Logs:")
    if st.button("Refresh Snapshots"):
        # Get list of .jpg files sorted by time
        files = sorted([f for f in os.listdir(SAVE_DIR) if f.endswith('.jpg')], reverse=True)
        if files:
            for f in files[:4]:
                st.image(f"{SAVE_DIR}/{f}", caption=f"Captured at {f.split('_')[0]}")
        else:
            st.info("No violations recorded yet.")
