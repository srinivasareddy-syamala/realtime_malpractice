from flask import Flask, render_template, Response, request, redirect, url_for, session, flash, jsonify
import cv2
import numpy as np
import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import winsound
import time

app = Flask(__name__)
app.secret_key = 'test123'  # Simple secret key for testing

# Initialize OpenCV
cap = cv2.VideoCapture(0)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

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

def play_beep():
    try:
        winsound.Beep(1000, 500)
    except:
        try:
            os.system('echo -e "\a"')
        except:
            pass

def generate_frames():
    while True:
        if not class_session['active']:
            blank_frame = np.zeros((480, 640, 3), np.uint8)
            cv2.putText(blank_frame, "Exam Not Started", (150, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            ret, buffer = cv2.imencode('.jpg', blank_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                  b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            continue

        try:
            success, frame = cap.read()
            if not success:
                break

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
                cv2.putText(frame, "Not Attentive!", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                
                if class_session['inattention_start_time'] is None:
                    class_session['inattention_start_time'] = time.time()
                
                inattention_duration = time.time() - class_session['inattention_start_time']
                
                if inattention_duration >= 3.0 and not class_session['inattention_warned']:
                    cv2.rectangle(frame, (50, 100), (590, 200), (0, 0, 255), 3)
                    cv2.putText(frame, "MALPRACTICE WARNING", (100, 150),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                    
                    play_beep()
                    class_session['inattention_warned'] = True
                    
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                    image_path = os.path.join(SAVE_DIR, f'malpractice_warning_{timestamp}.jpg')
                    cv2.imwrite(image_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                elif inattention_duration >= 3.0:
                    cv2.rectangle(frame, (50, 100), (590, 200), (0, 0, 255), 3)
                    cv2.putText(frame, "MALPRACTICE WARNING", (100, 150),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
                else:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    image_path = os.path.join(SAVE_DIR, f'inattentive_{timestamp}.jpg')
                    cv2.imwrite(image_path, frame)

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
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
    for f in os.listdir(SAVE_DIR):
        if f.endswith('.jpg'):
            try:
                if f.startswith('malpractice_warning_'):
                    timestamp = f.replace('malpractice_warning_', '').replace('.jpg', '')
                    label = 'Malpractice Warning'
                else:
                    timestamp = f.replace('inattentive_', '').replace('.jpg', '')
                    label = 'Inattentive'
                formatted_time = datetime.datetime.strptime(timestamp, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
                images.append({
                    'path': f,
                    'time': formatted_time,
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
    app.run(debug=True)
