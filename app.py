from flask import Flask, render_template, Response, request, redirect, url_for, session, flash, jsonify
import cv2
import numpy as np
import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import time
import platform

app = Flask(__name__)
app.secret_key = 'test123'  # Simple secret key for testing

# --- FIX 1: Platform-Independent Sound ---
def play_beep():
    """Plays a beep sound. Works on Windows and attempts a terminal bell on Linux/Mac."""
    try:
        if platform.system() == "Windows":
            import winsound
            winsound.Beep(1000, 500)
        else:
            # Linux/Mac terminal bell
            print('\a') 
            os.system('echo -e "\a"')
    except Exception as e:
        print(f"Audio alert failed: {e}")

# --- FIX 2: Graceful Camera Initialization ---
# Note: VideoCapture(0) works on your LOCAL machine. 
# On Cloud servers, this will initialize but success will be False.
cap = cv2.VideoCapture(0)

# Use absolute path for cascade to prevent loading errors
cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(cascade_path)

# Create directories
SAVE_DIR = 'static/captured_images'
os.makedirs(SAVE_DIR, exist_ok=True)

# Database setup
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY,
                  password_hash TEXT NOT NULL)''')
    conn.commit()
    conn.close()

init_db()

# Session management
class_session = {
    'active': False,
    'start_time': None,
    'end_time': None,
    'session_stats': {
        'total_frames': 0,
        'attentive_frames': 0,
        'looking_away': 0
    },
    'inattention_start_time': None,
    'inattention_warned': False
}

def reset_stats():
    class_session['session_stats'] = {
        'total_frames': 0,
        'attentive_frames': 0,
        'looking_away': 0
    }
    class_session['inattention_start_time'] = None
    class_session['inattention_warned'] = False

def generate_frames():
    while True:
        if not class_session['active']:
            # Show a static "Idle" frame when session isn't active
            blank_frame = np.zeros((480, 640, 3), np.uint8)
            cv2.putText(blank_frame, "Exam Not Started", (150, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            ret, buffer = cv2.imencode('.jpg', blank_frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.1) # Prevent CPU spiking
            continue

        try:
            success, frame = cap.read()
            if not success:
                # If camera fails (common on cloud servers), show error message
                error_frame = np.zeros((480, 640, 3), np.uint8)
                cv2.putText(error_frame, "Camera Source Not Found", (120, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                ret, buffer = cv2.imencode('.jpg', error_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                time.sleep(1)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)

            class_session['session_stats']['total_frames'] += 1
            
            if len(faces) > 0:
                class_session['session_stats']['attentive_frames'] += 1
                cv2.putText(frame, "Attentive", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                class_session['inattention_start_time'] = None
                class_session['inattention_warned'] = False
            else:
                class_session['session_stats']['looking_away'] += 1
                cv2.putText(frame, "NOT ATTENTIVE!", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                
                if class_session['inattention_start_time'] is None:
                    class_session['inattention_start_time'] = time.time()
                
                inattention_duration = time.time() - class_session['inattention_start_time']
                
                if inattention_duration >= 3.0:
                    # Draw Warning Overlay
                    cv2.rectangle(frame, (50, 100), (590, 200), (0, 0, 255), 3)
                    cv2.putText(frame, "MALPRACTICE WARNING", (100, 150),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                    
                    if not class_session['inattention_warned']:
                        play_beep()
                        class_session['inattention_warned'] = True
                        
                        # Save Warning Image
                        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        image_path = os.path.join(SAVE_DIR, f'malpractice_{timestamp}.jpg')
                        cv2.imwrite(image_path, frame)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
        except Exception as e:
            print(f"Error in generate_frames: {e}")
            continue

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
        result = c.fetchone()
        conn.close()
        
        if result and check_password_hash(result[0], password):
            session['username'] = username
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password_hash = generate_password_hash(request.form['password'])
        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', 
                     (username, password_hash))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except:
            conn.close()
            flash('Username already exists')
    return render_template('register.html')

@app.route('/start_class')
def start_class():
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'})
    
    class_session['active'] = True
    class_session['start_time'] = datetime.datetime.now()
    reset_stats()
    return jsonify({'status': 'success'})

@app.route('/stop_class')
def stop_class():
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'})
    
    class_session['active'] = False
    class_session['end_time'] = datetime.datetime.now()
    return jsonify({
        'status': 'success',
        'stats': class_session['session_stats']
    })

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    images = []
    if os.path.exists(SAVE_DIR):
        for f in os.listdir(SAVE_DIR):
            if f.endswith('.jpg'):
                try:
                    # Simplified parsing for the dashboard
                    label = 'Malpractice Warning' if 'malpractice' in f else 'Inattentive'
                    images.append({
                        'path': f,
                        'label': label
                    })
                except:
                    continue
    
    images.sort(key=lambda x: x['path'], reverse=True)
    
    total_frames = class_session['session_stats']['total_frames']
    attention_rate = 0
    if total_frames > 0:
        attention_rate = (class_session['session_stats']['attentive_frames'] / total_frames * 100)
    
    session_data = {
        'total_frames': class_session['session_stats']['total_frames'],
        'attentive_frames': class_session['session_stats']['attentive_frames'],
        'looking_away': class_session['session_stats']['looking_away'],
        'attention_rate': round(attention_rate, 2)
    }
    
    return render_template('dashboard.html',
                         stats=session_data,
                         images=images,
                         class_active=class_session['active'])

@app.route('/logout')
def logout():
    if class_session['active']:
        class_session['active'] = False
    session.clear()
    return redirect(url_for('login'))

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Determine port for cloud compatibility
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
