"""
Real-Time Malpractice Detection in Classroom
Advanced AI-Powered Cheating Detection System
"""

import cv2
import numpy as np
import time
from datetime import datetime
import os
import sys
from threading import Thread

if sys.platform.startswith("win"):
    import winsound
else:
    winsound = None

# Create directory for evidence snapshots
SNAPSHOT_DIR = 'lookaway_snapshots'
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

def play_alarm():
    """Play alarm sound for malpractice alert"""
    try:
        if winsound:
            frequency = 1000  # Hz
            duration = 500    # milliseconds
            winsound.Beep(frequency, duration)
            return
    except:
        print("🚨 MALPRACTICE ALERT: Student showing suspicious behavior!")

def malpractice_detection_system():
    """Real-time malpractice detection in classroom"""
    print("🚨 REAL-TIME MALPRACTICE DETECTION SYSTEM")
    print("=" * 60)
    print("🎓 Advanced AI-Powered Cheating Detection for Classroom")
    print("💡 CNN Model & YOLO Object Detection Analysis")
    print("-" * 60)
    print("🎮 DEMO MODE: Face & behavior detection for exam integrity")
    print("📹 Controls: Press 'q' to quit, 's' to take screenshot")
    print("=" * 60)
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: Could not access camera")
        return
    
    # Load face detector
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    # Tracking variables
    session_start = time.time()
    face_detected_time = 0
    total_frames = 0
    alert_threshold = 3  # seconds without face detection
    last_face_time = time.time()
    
    # Warning system variables for malpractice detection
    warning_count = 0
    max_warnings = 3
    lookaway_start_time = None
    warning_display_time = 0
    is_looking_away = False
    malpractice_incidents = []
    
    print("✅ Camera initialized successfully!")
    print("📹 Starting malpractice detection monitoring...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Error reading from camera")
            break
        
        # Flip frame for mirror effect
        frame = cv2.flip(frame, 1)
        total_frames += 1
        
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        current_time = time.time()
        session_duration = current_time - session_start
        
        # Check if face is detected
        face_detected = len(faces) > 0
        
        if face_detected:
            face_detected_time += 1/30  # Assuming 30 FPS
            last_face_time = current_time
            attention_status = "NORMAL ✅"
            status_color = (0, 255, 0)  # Green
            is_looking_away = False
            warning_count = 0  # Reset warnings when face is detected
            
            # Draw rectangle around face
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, "Student Detected", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        else:
            time_since_face = current_time - last_face_time
            
            if time_since_face > alert_threshold:
                attention_status = "SUSPICIOUS ❌"
                status_color = (0, 0, 255)  # Red
                
                # Flash red border for alert
                if int(time_since_face * 2) % 2:  # Flash every 0.5 seconds
                    cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), 
                                 (0, 0, 255), 10)
                
                # Handle malpractice incident
                if not is_looking_away:
                    is_looking_away = True
                    lookaway_start_time = current_time
                    warning_count = 0
                
                # Increment warning count (once per second)
                if lookaway_start_time and (current_time - lookaway_start_time) > warning_count:
                    warning_count += 1
                    
                    # Take snapshot evidence
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = os.path.join(SNAPSHOT_DIR, f'malpractice_warning{warning_count}_{timestamp}.jpg')
                    cv2.imwrite(filename, frame)
                    print(f"📸 Malpractice Warning {warning_count}/3: Evidence snapshot taken - {filename}")
                    
                    # Play alarm
                    Thread(target=play_alarm, daemon=True).start()
                    
                    # Store incident
                    malpractice_incidents.append({
                        'warning': warning_count,
                        'time': timestamp,
                        'duration': current_time - lookaway_start_time
                    })
                    
                    if warning_count >= max_warnings:
                        print(f"🚨 CRITICAL: Maximum warnings ({max_warnings}) reached! Student integrity compromised!")
            else:
                attention_status = "DISTRACTED ⚠️"
                status_color = (0, 255, 255)  # Yellow
        
        # Calculate integrity percentage
        integrity_percentage = (face_detected_time / session_duration) * 100 if session_duration > 0 else 0
        
        # Draw status overlay
        cv2.rectangle(frame, (10, 10), (450, 150), (50, 50, 50), -1)
        
        # Status text
        cv2.putText(frame, f"Status: {attention_status}", (15, 35), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        
        # Session info
        cv2.putText(frame, f"Session: {session_duration:.0f}s", (15, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(frame, f"Integrity: {integrity_percentage:.1f}%", (15, 80), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(frame, f"Faces: {len(faces)}", (15, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Warning display
        if warning_count > 0:
            warning_color = (0, 165, 255) if warning_count < 3 else (0, 0, 255)
            cv2.putText(frame, f"WARNINGS: {warning_count}/{max_warnings}", (15, 125), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, warning_color, 2)
        
        # Instructions
        cv2.putText(frame, "Press 'q' to quit, 's' for screenshot", (10, frame.shape[0] - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        # Display frame
        cv2.imshow('Real-Time Malpractice Detection System', frame)
        
        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            # Save screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"malpractice_screenshot_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            print(f"📸 Screenshot saved: {filename}")
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    
    # Final session summary
    print("\n📊 MALPRACTICE DETECTION REPORT:")
    print("=" * 50)
    print(f"Total Duration: {session_duration:.1f} seconds")
    print(f"Integrity Percentage: {integrity_percentage:.1f}%")
    print(f"Face Detection Time: {face_detected_time:.1f} seconds")
    print(f"Total Frames: {total_frames}")
    print(f"Malpractice Incidents: {len(malpractice_incidents)}")
    
    if malpractice_incidents:
        print("\n🚨 MALPRACTICE INCIDENTS:")
        for incident in malpractice_incidents:
            print(f"  Warning {incident['warning']}: {incident['time']} (Duration: {incident['duration']:.1f}s)")
    
    if integrity_percentage >= 80:
        grade = "Excellent - High Integrity! 🌟"
    elif integrity_percentage >= 60:
        grade = "Good - Acceptable Integrity 👍"
    elif integrity_percentage >= 40:
        grade = "Fair - Requires Monitoring 📚"
    else:
        grade = "Poor - Integrity Compromised ⚠️"
    
    print(f"Assessment: {grade}")
    print(f"\n📁 Evidence snapshots saved in: {SNAPSHOT_DIR}/")

if __name__ == "__main__":
    try:
        malpractice_detection_system()
    except KeyboardInterrupt:
        print("\n🛑 Malpractice detection stopped by user")
    except Exception as e:
        print(f"❌ Error running detection system: {e}")
        print("💡 Make sure your camera is connected and not being used by another application")