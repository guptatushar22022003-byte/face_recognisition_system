from flask import Flask, render_template, jsonify, Response, request
import sqlite3
import datetime
import camera

app = Flask(__name__)
video_camera = None

def get_camera():
    global video_camera
    if video_camera is None:
        video_camera = camera.VideoCamera()
    return video_camera

def get_logs():
    conn = sqlite3.connect("attendance.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Check if table exists to avoid errors if run before init
    try:
        cursor.execute("SELECT name, date, time_in, time_out FROM daily_attendance ORDER BY date DESC, time_in DESC LIMIT 50")
        logs = [dict(row) for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        logs = []
    conn.close()
    return logs

@app.route('/')
def index():
    users = database.get_all_users()
    return render_template('index.html', users=users)

@app.route('/user/<int:user_id>')
def user_dashboard(user_id):
    users = database.get_all_users()
    name = users.get(user_id, "Unknown")
    logs = database.get_user_attendance(user_id)
    return render_template('user_dashboard.html', user_id=user_id, name=name, logs=logs)

@app.route('/api/logs')
def api_logs():
    logs = get_logs()
    return jsonify(logs)

@app.route('/api/control', methods=['POST'])
def control():
    data = request.json
    action = data.get('action')
    cam = get_camera()
    
    if action == 'register':
        user_id = data.get('id')
        name = data.get('name')
        if not user_id or not name:
            return jsonify({"status": "error", "message": "Missing ID or Name"}), 400
        cam.start_registration(user_id, name)
        return jsonify({"status": "success", "message": "Registration started"})
        
    elif action == 'recognize':
        if cam.start_recognition():
            return jsonify({"status": "success", "message": "Recognition started"})
        else:
            return jsonify({"status": "error", "message": "Model not found. Register a face first."}), 400
            
    elif action == 'stop':
        cam.stop_mode()
        return jsonify({"status": "success", "message": "Stopped"})
        
    return jsonify({"status": "error", "message": "Invalid action"}), 400

def gen(camera):
    while True:
        frame = camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen(get_camera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Initialize DB
    import database
    database.init_db()
    app.run(debug=True, port=5000)
