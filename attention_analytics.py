"""
Advanced Attention Logger with Detailed Analytics
Logs all attention events and generates comprehensive graphs
"""

import json
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import numpy as np
import os
from collections import defaultdict

class AttentionLogger:
    def __init__(self, db_path="attention_logs.db"):
        """Initialize the attention logger with SQLite database"""
        self.db_path = db_path
        self.current_session_id = None
        self.init_database()
        
        # Set up plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration_seconds REAL,
                total_attention_time REAL,
                attention_percentage REAL,
                total_look_aways INTEGER,
                avg_attention_score REAL,
                session_type TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Attention events table (detailed logs)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attention_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TIMESTAMP,
                event_type TEXT,
                attention_score REAL,
                face_detected BOOLEAN,
                eyes_detected INTEGER,
                head_pose_yaw REAL,
                head_pose_pitch REAL,
                look_away_duration REAL,
                alert_triggered BOOLEAN,
                notes TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        ''')
        
        # Look away incidents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS look_away_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration_seconds REAL,
                alert_triggered BOOLEAN,
                recovery_time REAL,
                cause TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        ''')
        
        # Daily summaries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_summaries (
                date DATE PRIMARY KEY,
                total_sessions INTEGER,
                total_study_time REAL,
                avg_attention_percentage REAL,
                total_look_aways INTEGER,
                best_session_attention REAL,
                worst_session_attention REAL,
                improvement_trend TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("📊 Attention logging database initialized")
    
    def start_session(self, session_type="study", notes=""):
        """Start a new attention tracking session"""
        self.current_session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sessions (session_id, start_time, session_type, notes)
            VALUES (?, ?, ?, ?)
        ''', (self.current_session_id, datetime.now(), session_type, notes))
        
        conn.commit()
        conn.close()
        
        print(f"📝 Started logging session: {self.current_session_id}")
        return self.current_session_id
    
    def log_attention_event(self, event_data):
        """Log a single attention event"""
        if not self.current_session_id:
            self.start_session()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO attention_events (
                session_id, timestamp, event_type, attention_score,
                face_detected, eyes_detected, head_pose_yaw, head_pose_pitch,
                look_away_duration, alert_triggered, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.current_session_id,
            datetime.now(),
            event_data.get('event_type', 'attention_check'),
            event_data.get('attention_score', 0),
            event_data.get('face_detected', False),
            event_data.get('eyes_detected', 0),
            event_data.get('head_pose_yaw', 0),
            event_data.get('head_pose_pitch', 0),
            event_data.get('look_away_duration', 0),
            event_data.get('alert_triggered', False),
            event_data.get('notes', '')
        ))
        
        conn.commit()
        conn.close()
    
    def log_look_away_incident(self, start_time, end_time, alert_triggered=False, cause=""):
        """Log a look away incident"""
        if not self.current_session_id:
            return
        
        duration = (end_time - start_time).total_seconds()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO look_away_incidents (
                session_id, start_time, end_time, duration_seconds,
                alert_triggered, cause
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            self.current_session_id, start_time, end_time,
            duration, alert_triggered, cause
        ))
        
        conn.commit()
        conn.close()
    
    def end_session(self, session_stats):
        """End current session and save summary statistics"""
        if not self.current_session_id:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE sessions SET
                end_time = ?,
                duration_seconds = ?,
                total_attention_time = ?,
                attention_percentage = ?,
                total_look_aways = ?,
                avg_attention_score = ?
            WHERE session_id = ?
        ''', (
            datetime.now(),
            session_stats.get('duration_seconds', 0),
            session_stats.get('total_attention_time', 0),
            session_stats.get('attention_percentage', 0),
            session_stats.get('total_look_aways', 0),
            session_stats.get('avg_attention_score', 0),
            self.current_session_id
        ))
        
        conn.commit()
        conn.close()
        
        # Update daily summary
        self.update_daily_summary()
        
        print(f"📊 Session ended: {self.current_session_id}")
        self.current_session_id = None
    
    def update_daily_summary(self):
        """Update daily summary statistics"""
        today = datetime.now().date()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get today's session stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total_sessions,
                SUM(duration_seconds) as total_study_time,
                AVG(attention_percentage) as avg_attention,
                SUM(total_look_aways) as total_look_aways,
                MAX(attention_percentage) as best_attention,
                MIN(attention_percentage) as worst_attention
            FROM sessions 
            WHERE DATE(start_time) = ?
        ''', (today,))
        
        stats = cursor.fetchone()
        
        # Calculate improvement trend (compare with yesterday)
        yesterday = today - timedelta(days=1)
        cursor.execute('''
            SELECT avg_attention_percentage 
            FROM daily_summaries 
            WHERE date = ?
        ''', (yesterday,))
        
        yesterday_avg = cursor.fetchone()
        trend = "stable"
        
        if yesterday_avg and stats[2]:  # avg_attention exists
            if stats[2] > yesterday_avg[0] + 5:
                trend = "improving"
            elif stats[2] < yesterday_avg[0] - 5:
                trend = "declining"
        
        # Insert or update daily summary
        cursor.execute('''
            INSERT OR REPLACE INTO daily_summaries (
                date, total_sessions, total_study_time, avg_attention_percentage,
                total_look_aways, best_session_attention, worst_session_attention,
                improvement_trend
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (today, stats[0], stats[1] or 0, stats[2] or 0, 
              stats[3] or 0, stats[4] or 0, stats[5] or 0, trend))
        
        conn.commit()
        conn.close()

class AttentionAnalytics:
    def __init__(self, db_path="attention_logs.db"):
        """Initialize analytics engine"""
        self.db_path = db_path
        self.ensure_output_dir()
    
    def ensure_output_dir(self):
        """Create output directory for graphs"""
        self.output_dir = "attention_graphs"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def generate_session_report(self, session_id):
        """Generate detailed report for a specific session"""
        conn = sqlite3.connect(self.db_path)
        
        # Get session data
        session_df = pd.read_sql_query('''
            SELECT * FROM sessions WHERE session_id = ?
        ''', conn, params=(session_id,))
        
        # Get attention events
        events_df = pd.read_sql_query('''
            SELECT * FROM attention_events WHERE session_id = ?
            ORDER BY timestamp
        ''', conn, params=(session_id,))
        
        # Get look away incidents
        incidents_df = pd.read_sql_query('''
            SELECT * FROM look_away_incidents WHERE session_id = ?
            ORDER BY start_time
        ''', conn, params=(session_id,))
        
        conn.close()
        
        if session_df.empty:
            print(f"No session found with ID: {session_id}")
            return
        
        # Create comprehensive session report
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'Attention Analysis Report - {session_id}', fontsize=16, fontweight='bold')
        
        # 1. Attention Score Timeline
        if not events_df.empty:
            events_df['timestamp'] = pd.to_datetime(events_df['timestamp'])
            events_df['minutes'] = (events_df['timestamp'] - events_df['timestamp'].min()).dt.total_seconds() / 60
            
            axes[0, 0].plot(events_df['minutes'], events_df['attention_score'], 
                           linewidth=2, color='blue', alpha=0.7)
            axes[0, 0].fill_between(events_df['minutes'], events_df['attention_score'], 
                                   alpha=0.3, color='blue')
            axes[0, 0].axhline(y=0.8, color='green', linestyle='--', alpha=0.7, label='Excellent')
            axes[0, 0].axhline(y=0.5, color='orange', linestyle='--', alpha=0.7, label='Good')
            axes[0, 0].axhline(y=0.3, color='red', linestyle='--', alpha=0.7, label='Poor')
            axes[0, 0].set_title('Attention Score Over Time')
            axes[0, 0].set_xlabel('Time (minutes)')
            axes[0, 0].set_ylabel('Attention Score')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)
        
        # 2. Look Away Incidents
        if not incidents_df.empty:
            incidents_df['start_time'] = pd.to_datetime(incidents_df['start_time'])
            incidents_df['minutes'] = (incidents_df['start_time'] - events_df['timestamp'].min()).dt.total_seconds() / 60
            
            colors = ['red' if alert else 'orange' for alert in incidents_df['alert_triggered']]
            axes[0, 1].bar(range(len(incidents_df)), incidents_df['duration_seconds'], 
                          color=colors, alpha=0.7)
            axes[0, 1].set_title('Look Away Incidents')
            axes[0, 1].set_xlabel('Incident Number')
            axes[0, 1].set_ylabel('Duration (seconds)')
            axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Attention Distribution
        if not events_df.empty:
            attention_categories = []
            for score in events_df['attention_score']:
                if score >= 0.8:
                    attention_categories.append('Excellent')
                elif score >= 0.5:
                    attention_categories.append('Good')
                elif score >= 0.3:
                    attention_categories.append('Fair')
                else:
                    attention_categories.append('Poor')
            
            category_counts = pd.Series(attention_categories).value_counts()
            colors = ['green', 'lightgreen', 'orange', 'red']
            axes[1, 0].pie(category_counts.values, labels=category_counts.index, 
                          autopct='%1.1f%%', colors=colors[:len(category_counts)])
            axes[1, 0].set_title('Attention Quality Distribution')
        
        # 4. Session Statistics
        stats_text = f"""
Session Statistics:
Duration: {session_df['duration_seconds'].iloc[0]:.1f} seconds
Attention %: {session_df['attention_percentage'].iloc[0]:.1f}%
Look Aways: {session_df['total_look_aways'].iloc[0]}
Avg Score: {session_df['avg_attention_score'].iloc[0]:.3f}
Session Type: {session_df['session_type'].iloc[0]}
        """
        
        axes[1, 1].text(0.1, 0.5, stats_text, fontsize=12, 
                        verticalalignment='center', transform=axes[1, 1].transAxes)
        axes[1, 1].set_title('Session Summary')
        axes[1, 1].axis('off')
        
        plt.tight_layout()
        
        # Save the report
        filename = f"{self.output_dir}/session_report_{session_id}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"📊 Session report saved: {filename}")
        return filename
    
    def generate_daily_trends(self, days=7):
        """Generate daily attention trends graph"""
        conn = sqlite3.connect(self.db_path)
        
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        daily_df = pd.read_sql_query('''
            SELECT * FROM daily_summaries 
            WHERE date BETWEEN ? AND ?
            ORDER BY date
        ''', conn, params=(start_date, end_date))
        
        conn.close()
        
        if daily_df.empty:
            print("No daily data available")
            return
        
        # Create daily trends visualization
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle(f'Daily Attention Trends ({days} days)', fontsize=16, fontweight='bold')
        
        daily_df['date'] = pd.to_datetime(daily_df['date'])
        
        # 1. Attention Percentage Trend
        axes[0, 0].plot(daily_df['date'], daily_df['avg_attention_percentage'], 
                       marker='o', linewidth=2, markersize=8)
        axes[0, 0].set_title('Daily Average Attention %')
        axes[0, 0].set_ylabel('Attention Percentage')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # 2. Study Time Trend
        daily_df['study_hours'] = daily_df['total_study_time'] / 3600
        axes[0, 1].bar(daily_df['date'], daily_df['study_hours'], alpha=0.7, color='skyblue')
        axes[0, 1].set_title('Daily Study Time (Hours)')
        axes[0, 1].set_ylabel('Hours')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 3. Look Away Incidents
        axes[1, 0].plot(daily_df['date'], daily_df['total_look_aways'], 
                       marker='s', linewidth=2, markersize=8, color='red', alpha=0.7)
        axes[1, 0].set_title('Daily Look Away Incidents')
        axes[1, 0].set_ylabel('Total Look Aways')
        axes[1, 0].grid(True, alpha=0.3)
        axes[1, 0].tick_params(axis='x', rotation=45)
        
        # 4. Improvement Trend
        trend_counts = daily_df['improvement_trend'].value_counts()
        colors = {'improving': 'green', 'stable': 'orange', 'declining': 'red'}
        pie_colors = [colors.get(trend, 'gray') for trend in trend_counts.index]
        
        axes[1, 1].pie(trend_counts.values, labels=trend_counts.index, 
                      autopct='%1.1f%%', colors=pie_colors)
        axes[1, 1].set_title('Overall Improvement Trend')
        
        plt.tight_layout()
        
        # Save the graph
        filename = f"{self.output_dir}/daily_trends_{days}days.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"📈 Daily trends saved: {filename}")
        return filename
    
    def generate_look_away_analysis(self):
        """Generate detailed look away pattern analysis"""
        conn = sqlite3.connect(self.db_path)
        
        incidents_df = pd.read_sql_query('''
            SELECT * FROM look_away_incidents 
            ORDER BY start_time DESC
            LIMIT 100
        ''', conn)
        
        conn.close()
        
        if incidents_df.empty:
            print("No look away data available")
            return
        
        # Create look away analysis
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('Look Away Pattern Analysis', fontsize=16, fontweight='bold')
        
        # 1. Duration Distribution
        axes[0, 0].hist(incidents_df['duration_seconds'], bins=20, alpha=0.7, color='orange')
        axes[0, 0].set_title('Look Away Duration Distribution')
        axes[0, 0].set_xlabel('Duration (seconds)')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. Alert vs Non-Alert Incidents
        alert_counts = incidents_df['alert_triggered'].value_counts()
        axes[0, 1].pie(alert_counts.values, 
                      labels=['No Alert', 'Alert Triggered'], 
                      autopct='%1.1f%%', 
                      colors=['lightblue', 'red'])
        axes[0, 1].set_title('Alert Trigger Rate')
        
        # 3. Time of Day Analysis
        incidents_df['start_time'] = pd.to_datetime(incidents_df['start_time'])
        incidents_df['hour'] = incidents_df['start_time'].dt.hour
        
        hourly_counts = incidents_df['hour'].value_counts().sort_index()
        axes[1, 0].bar(hourly_counts.index, hourly_counts.values, alpha=0.7, color='purple')
        axes[1, 0].set_title('Look Away Incidents by Hour of Day')
        axes[1, 0].set_xlabel('Hour (24h format)')
        axes[1, 0].set_ylabel('Number of Incidents')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Duration vs Alert Relationship
        alert_durations = incidents_df[incidents_df['alert_triggered'] == True]['duration_seconds']
        no_alert_durations = incidents_df[incidents_df['alert_triggered'] == False]['duration_seconds']
        
        axes[1, 1].boxplot([no_alert_durations, alert_durations], 
                          labels=['No Alert', 'Alert'])
        axes[1, 1].set_title('Duration Comparison: Alert vs No Alert')
        axes[1, 1].set_ylabel('Duration (seconds)')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save the analysis
        filename = f"{self.output_dir}/look_away_analysis.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"👁️ Look away analysis saved: {filename}")
        return filename
    
    def generate_comprehensive_dashboard(self):
        """Generate a comprehensive attention dashboard"""
        conn = sqlite3.connect(self.db_path)
        
        # Get overall statistics
        stats_query = '''
            SELECT 
                COUNT(*) as total_sessions,
                SUM(duration_seconds)/3600 as total_hours,
                AVG(attention_percentage) as avg_attention,
                SUM(total_look_aways) as total_look_aways
            FROM sessions
        '''
        
        overall_stats = pd.read_sql_query(stats_query, conn).iloc[0]
        
        # Get recent sessions
        recent_sessions = pd.read_sql_query('''
            SELECT * FROM sessions 
            ORDER BY start_time DESC 
            LIMIT 10
        ''', conn)
        
        conn.close()
        
        # Create dashboard
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
        
        # Title
        fig.suptitle('Comprehensive Attention Dashboard', fontsize=20, fontweight='bold')
        
        # Overall Statistics Panel
        ax_stats = fig.add_subplot(gs[0, :2])
        stats_text = f"""
📊 OVERALL STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Sessions: {overall_stats['total_sessions']:.0f}
Total Study Time: {overall_stats['total_hours']:.1f} hours
Average Attention: {overall_stats['avg_attention']:.1f}%
Total Look Aways: {overall_stats['total_look_aways']:.0f}

Performance Grade: {self.get_performance_grade(overall_stats['avg_attention'])}
        """
        
        ax_stats.text(0.05, 0.5, stats_text, fontsize=14, 
                     verticalalignment='center', transform=ax_stats.transAxes,
                     bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
        ax_stats.set_title('Summary Statistics', fontsize=16, fontweight='bold')
        ax_stats.axis('off')
        
        # Recent Performance Trend
        if not recent_sessions.empty:
            ax_trend = fig.add_subplot(gs[0, 2:])
            recent_sessions['session_num'] = range(len(recent_sessions), 0, -1)
            ax_trend.plot(recent_sessions['session_num'], recent_sessions['attention_percentage'], 
                         marker='o', linewidth=3, markersize=8, color='blue')
            ax_trend.set_title('Recent Session Performance', fontsize=14, fontweight='bold')
            ax_trend.set_xlabel('Sessions (Most Recent →)')
            ax_trend.set_ylabel('Attention %')
            ax_trend.grid(True, alpha=0.3)
        
        # Generate additional dashboard components
        self.generate_daily_trends(7)
        self.generate_look_away_analysis()
        
        # Save dashboard
        filename = f"{self.output_dir}/comprehensive_dashboard.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"📊 Comprehensive dashboard saved: {filename}")
        return filename
    
    def get_performance_grade(self, attention_percentage):
        """Get performance grade based on attention percentage"""
        if attention_percentage >= 90:
            return "A+ (Outstanding)"
        elif attention_percentage >= 80:
            return "A (Excellent)"
        elif attention_percentage >= 70:
            return "B+ (Very Good)"
        elif attention_percentage >= 60:
            return "B (Good)"
        elif attention_percentage >= 50:
            return "C+ (Fair)"
        elif attention_percentage >= 40:
            return "C (Needs Improvement)"
        else:
            return "D (Poor - Review Study Environment)"
    
    def export_data_to_csv(self):
        """Export all data to CSV files for external analysis"""
        conn = sqlite3.connect(self.db_path)
        
        # Export tables
        tables = ['sessions', 'attention_events', 'look_away_incidents', 'daily_summaries']
        
        for table in tables:
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            filename = f"{self.output_dir}/{table}_export.csv"
            df.to_csv(filename, index=False)
            print(f"📁 Exported {table} to {filename}")
        
        conn.close()
        return f"{self.output_dir}/"

# Test the logging system
if __name__ == "__main__":
    print("🧪 Testing Attention Logger and Analytics...")
    
    # Initialize logger
    logger = AttentionLogger()
    analytics = AttentionAnalytics()
    
    # Test session creation
    session_id = logger.start_session("test_session", "Testing the logging system")
    
    # Simulate some attention events
    import random
    from datetime import datetime, timedelta
    
    current_time = datetime.now()
    look_away_start = None
    
    for i in range(100):  # Simulate 100 data points
        # Generate realistic attention data
        base_attention = 0.7 + 0.2 * np.sin(i / 10)  # Cyclical pattern
        noise = random.uniform(-0.2, 0.2)
        attention_score = max(0, min(1, base_attention + noise))
        
        face_detected = attention_score > 0.3
        eyes_detected = 2 if face_detected and attention_score > 0.5 else (1 if face_detected else 0)
        
        # Simulate look away incidents
        if attention_score < 0.4 and look_away_start is None:
            look_away_start = current_time
        elif attention_score >= 0.4 and look_away_start is not None:
            logger.log_look_away_incident(
                look_away_start, 
                current_time, 
                alert_triggered=random.choice([True, False]),
                cause="distraction"
            )
            look_away_start = None
        
        # Log attention event
        event_data = {
            'event_type': 'attention_check',
            'attention_score': attention_score,
            'face_detected': face_detected,
            'eyes_detected': eyes_detected,
            'head_pose_yaw': random.uniform(-30, 30),
            'head_pose_pitch': random.uniform(-20, 20),
            'look_away_duration': 0 if face_detected else random.uniform(1, 5),
            'alert_triggered': attention_score < 0.3,
            'notes': f'Test data point {i}'
        }
        
        logger.log_attention_event(event_data)
        current_time += timedelta(seconds=1)
    
    # End session with statistics
    session_stats = {
        'duration_seconds': 100,
        'total_attention_time': 70,
        'attention_percentage': 70,
        'total_look_aways': 5,
        'avg_attention_score': 0.65
    }
    
    logger.end_session(session_stats)
    
    # Generate analytics
    print("\n📊 Generating analytics...")
    
    try:
        analytics.generate_session_report(session_id)
        analytics.generate_daily_trends(7)
        analytics.generate_look_away_analysis()
        analytics.generate_comprehensive_dashboard()
        analytics.export_data_to_csv()
        
        print("\n✅ All analytics generated successfully!")
        print(f"📁 Check the 'attention_graphs' folder for all visualizations")
        
    except Exception as e:
        print(f"❌ Error generating analytics: {e}")
    
    print("\n🎯 Attention Logger and Analytics system ready for production use!")