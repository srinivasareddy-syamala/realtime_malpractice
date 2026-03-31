import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase
import cv2
import numpy as np
import time
import datetime
import os

# --- Page Configuration ---
st.set_page_config(page_title="Raasi AI Proctor", layout="wide")
st.title("🛡️ Real-time Malpractice Detection")

# Create directory for logs
SAVE_DIR = 'captured_alerts'
os.makedirs(SAVE_DIR, exist_ok=True)

# --- Proctored Logic Class ---
class VideoProcessor(VideoTransformerBase):
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.inattention_start = None
        self.last_warn_time = 0
        self.is_malpractice = False

    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1) # Mirror view
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)

        if len(faces) > 0:
            # User is Attentive
            self.inattention_start = None
            self.is_malpractice = False
            for (x, y, w, h) in faces:
                cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(img, "ATTENTIVE", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        else:
            # User is looking away
            if self.inattention_start is None:
                self.inattention_start = time.time()
            
            duration = time.time() - self.inattention_start
            
            if duration >= 3.0:
                self.is_malpractice = True
                # Red Warning Overlay
                cv2.rectangle(img, (0, 0), (img.shape[1], img.shape[0]), (0, 0, 255), 10)
                cv2.putText(img, "WARNING: LOOK AT SCREEN", (50, 200), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                
                # Auto-save alert image every 5 seconds during malpractice
                if time.time() - self.last_warn_time > 5:
                    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    cv2.imwrite(f"{SAVE_DIR}/alert_{ts}.jpg", img)
                    self.last_warn_time = time.time()
            else:
                cv2.putText(img, "NOT ATTENTIVE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

        return img

# --- UI Layout ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Live Proctoring Feed")
    # This component handles the browser camera permissions and encryption
    ctx = webrtc_streamer(
        key="proctor",
        video_processor_factory=VideoProcessor,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"video": True, "audio": False},
    )

with col2:
    st.subheader("Session Status")
    if ctx.state.playing:
        st.success("Exam Session: ACTIVE")
        st.info("System is monitoring eye contact and face presence.")
    else:
        st.warning("Exam Session: IDLE")
    
    st.divider()
    if st.button("View Alert Logs"):
        files = os.listdir(SAVE_DIR)
        if files:
            st.write(f"Found {len(files)} malpractice alerts.")
            for f in files[-3:]: # Show last 3
                st.image(f"{SAVE_DIR}/{f}", caption=f"Alert: {f}")
        else:
            st.write("No alerts recorded yet.")
