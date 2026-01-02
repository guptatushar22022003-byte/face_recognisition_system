import sqlite3
import datetime

DB_NAME = "attendance.db"



def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Table for Users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Table for Daily Attendance (Time In / Time Out)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            date TEXT,
            time_in TEXT,
            time_out TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Keep old table for backward compatibility if needed, or we can ignore it.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            date TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def add_user(user_id, name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO users (id, name) VALUES (?, ?)", (user_id, name))
        conn.commit()
    except Exception as e:
        print(f"Error adding user: {e}")
    finally:
        conn.close()

def mark_attendance(user_id, name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    # Check if there is a record for this user TODAY (Get the latest one)
    cursor.execute("SELECT * FROM daily_attendance WHERE user_id = ? AND date = ? ORDER BY id DESC LIMIT 1", (user_id, date_str))
    record = cursor.fetchone()
    
    status_message = ""
    
    if not record:
        # No record -> Mark Time IN
        cursor.execute("INSERT INTO daily_attendance (user_id, name, date, time_in, last_updated) VALUES (?, ?, ?, ?, ?)", 
                       (user_id, name, date_str, time_str, now))
        conn.commit()
        status_message = f"Time In: {time_str}"
        conn.close()
        return status_message
    else:
        # Record exists. Check if we should mark Time OUT.
        # record structure: id, user_id, name, date, time_in, time_out, last_updated
        # indices: 0, 1, 2, 3, 4, 5, 6
        
        last_updated_str = record[6]
        # Parse last_updated to check cooldown (e.g. 1 minute)
        try:
            last_updated = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
             # Fallback formats if milliseconds are missing
            try:
                last_updated = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
            except:
                last_updated = now # Should not happen usually

        diff = (now - last_updated).total_seconds()
        

        if diff < 60: # 1 Minute Cooldown
            conn.close()
            return None # Too soon to toggle
            
        # If cooldown passed:
        # If Time Out is NULL -> Set Time Out (Check Out)
        # If Time Out is SET -> Create NEW record (Check In again)
        
        if record[5]: # time_out is not None, so they are already checked out.
             # Create NEW Session (Time In)
            cursor.execute("INSERT INTO daily_attendance (user_id, name, date, time_in, last_updated) VALUES (?, ?, ?, ?, ?)", 
                           (user_id, name, date_str, time_str, now))
            conn.commit()
            status_message = f"Time In: {time_str}"
        else:
            # Still checked in, so Check Out
            cursor.execute("UPDATE daily_attendance SET time_out = ?, last_updated = ? WHERE id = ?", 
                           (time_str, now, record[0]))
            conn.commit()
            status_message = f"Time Out: {time_str}"
            
        conn.close()
        return status_message

def get_attendance_logs():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT name, date, time_in, time_out FROM daily_attendance ORDER BY date DESC, time_in DESC LIMIT 50")
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs

def get_user_attendance(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT date, time_in, time_out 
        FROM daily_attendance 
        WHERE user_id = ? 
        ORDER BY date DESC, time_in DESC
    """, (user_id,))
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return logs

def get_all_users():
    """Return a dict of all users in the DB as {id: name}.
    This is used as a fallback when names.json is missing.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, name FROM users")
        rows = cursor.fetchall()
        return {row[0]: row[1] for row in rows}
    except Exception as e:
        print(f"Error fetching users: {e}")
        return {}
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
