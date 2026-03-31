"""
Enhanced Attention Tracker with Advanced Logging and Real-time Analytics
Integrates comprehensive logging and graph generation
"""

import cv2
import numpy as np
import time
import pygame
import threading
from datetime import datetime, timedelta
import json
from attention_analytics import AttentionLogger, AttentionAnalytics

class EnhancedAttentionTracker:
    def __init__(self):
        """Initialize enhanced attention tracker with logging"""
        # Initialize camera
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Load face and eye cascades
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        
        # Initialize logging system
        self.logger = AttentionLogger()
        self.analytics = AttentionAnalytics()
        
        # Initialize pygame for sound
        try:
            pygame.mixer.init()
            self.sound_available = True
        except:
            self.sound_available = False
            print("Sound not available")
        
        # Tracking variables
        self.session_start = time.time()
        self.last_face_time = time.time()
        self.total_face_time = 0
        self.alert_active = False
        self.alert_threshold = 5  # seconds
        
        # Look away tracking
        self.look_away_start = None
        self.look_away_incidents = []
        self.current_incident_id = 0
        
        # Analytics data
        self.attention_scores = []
        self.frame_count = 0
        self.last_log_time = time.time()
        self.log_interval = 1.0  # Log every second
        
        # Performance tracking
        self.best_attention_streak = 0
        self.current_attention_streak = 0
        self.total_alerts = 0
        
        print("🎯 AI-POWERED STUDENT ATTENTION TRACKER - ENHANCED")
        print("=" * 70)
        print("🧠 Advanced Computer Vision Learning Analytics Platform")
        print("📊 Features: Real-time tracking + SQLite logging + ML Analytics")
        print("-" * 70)
        print("🎮 Controls: 'q'=Quit | 'r'=Report | 'g'=Graphs | 's'=Screenshot")
        print("=" * 70)
    
    def start_tracking_session(self, session_type="study", notes=""):
        """Start a new tracking session with logging"""
        self.session_id = self.logger.start_session(session_type, notes)
        print(f"📝 Started logged session: {session_type}")
        return self.session_id
    
    def detect_face_and_eyes(self, frame):
        """Enhanced face and eye detection with detailed logging"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        results = {
            'face_detected': len(faces) > 0,
            'faces': faces,
            'eyes_detected': 0,
            'attention_score': 0,
            'face_size': 0,
            'face_center': None,
            'head_pose_estimated': {'yaw': 0, 'pitch': 0}
        }
        
        if len(faces) > 0:
            # Process the largest face
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face
            
            results['face_size'] = w * h
            results['face_center'] = (x + w//2, y + h//2)
            
            # Estimate head pose based on face position
            frame_center_x = frame.shape[1] // 2
            frame_center_y = frame.shape[0] // 2
            
            yaw_offset = (results['face_center'][0] - frame_center_x) / frame_center_x * 45
            pitch_offset = (results['face_center'][1] - frame_center_y) / frame_center_y * 30
            
            results['head_pose_estimated'] = {
                'yaw': yaw_offset,
                'pitch': pitch_offset
            }
            
            # Detect eyes in face region
            roi_gray = gray[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 5)
            results['eyes_detected'] = len(eyes)
            
            # Draw visualizations
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Draw eyes
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(frame, (x+ex, y+ey), (x+ex+ew, y+ey+eh), (0, 0, 255), 2)
            
            # Calculate detailed attention score
            attention_score = self.calculate_advanced_attention_score(results)
            results['attention_score'] = attention_score
        
        return results, frame
    
    def calculate_advanced_attention_score(self, detection_results):
        """Calculate advanced attention score with multiple factors"""
        score = 0
        
        # Base score for face detection (30%)
        if detection_results['face_detected']:
            score += 0.3
        
        # Eye detection bonus (40%)
        eyes = detection_results['eyes_detected']
        if eyes >= 2:
            score += 0.4  # Both eyes visible
        elif eyes == 1:
            score += 0.2  # One eye visible
        
        # Face size factor (20%) - closer face = more attention
        face_size = detection_results['face_size']
        if face_size > 15000:  # Very close
            score += 0.2
        elif face_size > 8000:  # Moderate distance
            score += 0.15
        elif face_size > 3000:  # Far but acceptable
            score += 0.1
        
        # Head pose factor (10%)
        head_pose = detection_results['head_pose_estimated']
        if abs(head_pose['yaw']) < 15 and abs(head_pose['pitch']) < 15:
            score += 0.1  # Looking straight
        elif abs(head_pose['yaw']) < 30 and abs(head_pose['pitch']) < 25:
            score += 0.05  # Slightly off
        
        return min(score, 1.0)
    
    def update_attention_tracking(self, results):
        """Update attention tracking with incident logging"""
        current_time = time.time()
        is_attentive = results['attention_score'] > 0.5
        
        # Update look away tracking
        if is_attentive:
            # Student is paying attention
            if self.look_away_start is not None:
                # End of look away incident
                incident_duration = current_time - self.look_away_start
                
                # Log the incident
                self.logger.log_look_away_incident(
                    datetime.fromtimestamp(self.look_away_start),
                    datetime.now(),
                    alert_triggered=self.alert_active,
                    cause="distraction" if incident_duration > 3 else "brief_glance"
                )
                
                self.look_away_incidents.append({
                    'start': self.look_away_start,
                    'end': current_time,
                    'duration': incident_duration,
                    'alert_triggered': self.alert_active
                })
                
                self.look_away_start = None
                
                if self.alert_active:
                    self.stop_alert()
            
            # Update attention streak
            self.current_attention_streak += 1
            self.best_attention_streak = max(self.best_attention_streak, self.current_attention_streak)
            self.last_face_time = current_time
            self.total_face_time += 1/30  # Assuming 30 FPS
            
        else:
            # Student is not paying attention
            if self.look_away_start is None:
                # Start of new look away incident
                self.look_away_start = current_time
            
            self.current_attention_streak = 0
            
            # Check for alert trigger
            time_since_look_away = current_time - self.look_away_start
            if time_since_look_away > self.alert_threshold and not self.alert_active:
                self.trigger_alert()
        
        # Log attention event periodically
        if current_time - self.last_log_time >= self.log_interval:
            self.log_attention_event(results)
            self.last_log_time = current_time
    
    def log_attention_event(self, results):
        """Log current attention event to database"""
        event_data = {
            'event_type': 'attention_check',
            'attention_score': results['attention_score'],
            'face_detected': results['face_detected'],
            'eyes_detected': results.get('eyes_detected', 0),
            'head_pose_yaw': results.get('head_pose_estimated', {}).get('yaw', 0),
            'head_pose_pitch': results.get('head_pose_estimated', {}).get('pitch', 0),
            'look_away_duration': (time.time() - self.look_away_start) if self.look_away_start else 0,
            'alert_triggered': self.alert_active,
            'notes': f'Frame {self.frame_count}, Streak: {self.current_attention_streak}'
        }
        
        self.logger.log_attention_event(event_data)
        self.attention_scores.append(results['attention_score'])
    
    def trigger_alert(self):
        """Trigger attention alert with logging"""
        if self.alert_active:
            return
        
        self.alert_active = True
        self.total_alerts += 1
        
        print(f"🚨 ATTENTION ALERT #{self.total_alerts}: Please focus on the screen!")
        
        # Play sound alert
        if self.sound_available:
            alert_thread = threading.Thread(target=self.play_alert_sound)
            alert_thread.daemon = True
            alert_thread.start()
    
    def stop_alert(self):
        """Stop alert with logging"""
        if self.alert_active:
            self.alert_active = False
            print("✅ Good attention restored")
    
    def play_alert_sound(self):
        """Play alert sound"""
        try:
            duration = 0.5
            frequency = 800
            sample_rate = 22050
            frames = int(duration * sample_rate)
            
            arr = []
            for i in range(frames):
                wave = 4096 * (i // (sample_rate // frequency) % 2 - 0.5)
                arr.append([int(wave), int(wave)])
            
            sound = pygame.sndarray.make_sound(arr)
            sound.play()
        except:
            pass
    
    def draw_enhanced_interface(self, frame, results):
        """Draw enhanced interface with detailed statistics"""
        current_time = time.time()
        session_duration = current_time - self.session_start
        attention_percentage = (self.total_face_time / session_duration) * 100 if session_duration > 0 else 0
        
        # Main status panel
        panel_height = 180
        overlay = np.zeros((panel_height, frame.shape[1], 3), dtype=np.uint8)
        overlay.fill(40)  # Dark background
        
        # Determine status color and text
        if results['face_detected']:
            if results['attention_score'] >= 0.8:
                status_color = (0, 255, 0)  # Green
                status_text = "EXCELLENT FOCUS 🌟"
            elif results['attention_score'] >= 0.6:
                status_color = (0, 255, 255)  # Yellow
                status_text = "GOOD ATTENTION 👍"
            elif results['attention_score'] >= 0.4:
                status_color = (0, 165, 255)  # Orange
                status_text = "FAIR ATTENTION 📚"
            else:
                status_color = (0, 100, 255)  # Red-orange
                status_text = "POOR ATTENTION 😴"
        else:
            status_color = (0, 0, 255)  # Red
            status_text = "NO FACE DETECTED ❌"
        
        # Alert overlay
        if self.alert_active:
            time_since_look_away = current_time - (self.look_away_start or current_time)
            if int(time_since_look_away * 4) % 2:  # Flash 4 times per second
                cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[0]), (0, 0, 255), 15)
            
            status_text = f"⚠️ FOCUS REQUIRED! ({time_since_look_away:.1f}s)"
            status_color = (0, 0, 255)
        
        # Draw main status
        cv2.putText(overlay, status_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        
        # Session statistics
        cv2.putText(overlay, f"Session: {session_duration:.0f}s | Attention: {attention_percentage:.1f}%", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.putText(overlay, f"Score: {results['attention_score']:.3f} | Eyes: {results.get('eyes_detected', 0)} | Alerts: {self.total_alerts}", 
                   (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.putText(overlay, f"Current Streak: {self.current_attention_streak} | Best: {self.best_attention_streak}", 
                   (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.putText(overlay, f"Look Aways: {len(self.look_away_incidents)} | Frames: {self.frame_count}", 
                   (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Head pose info
        head_pose = results.get('head_pose_estimated', {})
        cv2.putText(overlay, f"Head: Yaw {head_pose.get('yaw', 0):.1f}° | Pitch {head_pose.get('pitch', 0):.1f}°", 
                   (10, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        # Instructions
        cv2.putText(overlay, "Controls: 'q'=Quit | 'r'=Report | 'g'=Graphs | 's'=Screenshot", 
                   (10, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        
        # Mini attention graph (last 60 scores)
        if len(self.attention_scores) > 1:
            recent_scores = self.attention_scores[-60:]  # Last 60 data points
            graph_width = 200
            graph_height = 50
            graph_x = frame.shape[1] - graph_width - 10
            graph_y = 10
            
            # Draw graph background
            cv2.rectangle(frame, (graph_x, graph_y), (graph_x + graph_width, graph_y + graph_height), 
                         (50, 50, 50), -1)
            
            # Draw score line
            if len(recent_scores) > 1:
                points = []
                for i, score in enumerate(recent_scores):
                    x = graph_x + int(i * graph_width / len(recent_scores))
                    y = graph_y + graph_height - int(score * graph_height)
                    points.append((x, y))
                
                # Draw line graph
                for i in range(1, len(points)):
                    cv2.line(frame, points[i-1], points[i], status_color, 2)
            
            # Graph labels
            cv2.putText(frame, "Attention", (graph_x, graph_y - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)
        
        # Combine overlay with frame
        frame[:panel_height] = overlay
        
        return frame
    
    def generate_session_report(self):
        """Generate and display session report"""
        if hasattr(self, 'session_id') and self.session_id:
            print("📊 Generating session report...")
            try:
                report_file = self.analytics.generate_session_report(self.session_id)
                print(f"✅ Report generated: {report_file}")
            except Exception as e:
                print(f"❌ Error generating report: {e}")
        else:
            print("⚠️ No active session to report on")
    
    def show_analytics_graphs(self):
        """Show comprehensive analytics graphs"""
        print("📈 Generating analytics graphs...")
        try:
            self.analytics.generate_daily_trends(7)
            self.analytics.generate_look_away_analysis()
            self.analytics.generate_comprehensive_dashboard()
            print("✅ All graphs generated successfully!")
        except Exception as e:
            print(f"❌ Error generating graphs: {e}")
    
    def save_screenshot(self, frame):
        """Save screenshot with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"attention_screenshot_{timestamp}.jpg"
        cv2.imwrite(filename, frame)
        print(f"📸 Screenshot saved: {filename}")
        return filename
    
    def end_session(self):
        """End current session and save all data"""
        current_time = time.time()
        session_duration = current_time - self.session_start
        attention_percentage = (self.total_face_time / session_duration) * 100 if session_duration > 0 else 0
        
        # Close any open look away incident
        if self.look_away_start is not None:
            self.logger.log_look_away_incident(
                datetime.fromtimestamp(self.look_away_start),
                datetime.now(),
                alert_triggered=self.alert_active,
                cause="session_end"
            )
        
        # Save session statistics
        session_stats = {
            'duration_seconds': session_duration,
            'total_attention_time': self.total_face_time,
            'attention_percentage': attention_percentage,
            'total_look_aways': len(self.look_away_incidents),
            'avg_attention_score': np.mean(self.attention_scores) if self.attention_scores else 0
        }
        
        if hasattr(self, 'session_id'):
            self.logger.end_session(session_stats)
        
        return session_stats
    
    def run(self):
        """Main enhanced tracking loop"""
        print("🚀 LAUNCHING AI ATTENTION ANALYSIS ENGINE...")
        print("📹 Position yourself clearly in front of the camera")
        print("🎯 Ready to monitor your learning focus and engagement!")
        
        # Start logging session
        self.start_tracking_session("enhanced_study", "Enhanced tracker with full logging")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("❌ Error: Cannot read from camera")
                break
            
            # Flip frame for mirror effect
            frame = cv2.flip(frame, 1)
            self.frame_count += 1
            
            # Detect face and eyes with enhanced analysis
            results, frame = self.detect_face_and_eyes(frame)
            
            # Update attention tracking and logging
            self.update_attention_tracking(results)
            
            # Draw enhanced interface
            frame = self.draw_enhanced_interface(frame, results)
            
            # Display frame
            cv2.imshow('Enhanced Student Attention Tracker', frame)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.generate_session_report()
            elif key == ord('g'):
                self.show_analytics_graphs()
            elif key == ord('s'):
                self.save_screenshot(frame)
        
        # Cleanup and final report
        self.cap.release()
        cv2.destroyAllWindows()
        
        # End session and get final statistics
        final_stats = self.end_session()
        
        # Display comprehensive final report
        print(f"\n{'='*60}")
        print(f"🎓 ENHANCED ATTENTION TRACKING SESSION COMPLETE")
        print(f"{'='*60}")
        print(f"📊 Session Duration: {final_stats['duration_seconds']:.1f} seconds")
        print(f"📈 Attention Percentage: {final_stats['attention_percentage']:.1f}%")
        print(f"⭐ Average Attention Score: {final_stats['avg_attention_score']:.3f}")
        print(f"👁️ Total Look Away Incidents: {final_stats['total_look_aways']}")
        print(f"🚨 Total Alerts Triggered: {self.total_alerts}")
        print(f"🔥 Best Attention Streak: {self.best_attention_streak}")
        print(f"🎯 Total Frames Processed: {self.frame_count}")
        
        # Performance grade
        attention_pct = final_stats['attention_percentage']
        if attention_pct >= 90:
            grade = "A+ (Outstanding! 🌟)"
        elif attention_pct >= 80:
            grade = "A (Excellent! 👏)"
        elif attention_pct >= 70:
            grade = "B+ (Very Good! 👍)"
        elif attention_pct >= 60:
            grade = "B (Good 📚)"
        elif attention_pct >= 50:
            grade = "C+ (Fair ⚡)"
        else:
            grade = "C (Needs Improvement 📖)"
        
        print(f"🎯 Performance Grade: {grade}")
        print(f"{'='*60}")
        
        # Generate final analytics
        print("\n📊 Generating final analytics...")
        try:
            self.generate_session_report()
            self.show_analytics_graphs()
            self.analytics.export_data_to_csv()
            print("✅ All analytics and data exports completed!")
        except Exception as e:
            print(f"⚠️ Some analytics generation failed: {e}")
        
        return final_stats

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Student Attention Tracker with Logging')
    parser.add_argument('--alert-threshold', type=float, default=5.0,
                       help='Seconds without attention before alert (default: 5.0)')
    parser.add_argument('--session-type', type=str, default='study',
                       help='Type of session: study, meeting, training (default: study)')
    parser.add_argument('--notes', type=str, default='',
                       help='Notes about this session')
    
    args = parser.parse_args()
    
    try:
        tracker = EnhancedAttentionTracker()
        tracker.alert_threshold = args.alert_threshold
        
        final_stats = tracker.run()
        
        print(f"\n🎓 Enhanced attention tracking completed!")
        print(f"📁 Check 'attention_graphs' folder for detailed analytics")
        print(f"🗄️ Session data saved to SQLite database: attention_logs.db")
        
    except KeyboardInterrupt:
        print("\n🛑 Tracking stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure your camera is connected and all packages are installed")