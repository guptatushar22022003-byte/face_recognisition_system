# Face Recognition System (Web Version)

This is the complete **Face Recognition & Attendance System** with a unified Web Interface.

## Setup

1.  **Install Dependencies**:
    ```bash
    py -3.11 -m pip install -r requirements.txt
    ```

## How to Run

You only need to run **one command** now:

```bash
py -3.11 app.py
```

Then open your browser and go to:
👉 **http://127.0.0.1:5000**

## How to Use the Dashboard

1.  **Register a Face**:
    *   Enter a User ID (e.g., `1`) and Name (e.g., `Alice`).
    *   Click **Start Registration**.
    *   Look at the camera preview on the screen.
    *   Wait until it says "Training Complete".

2.  **Start Recognition**:
    *   Click the green **Start Recognition** button.
    *   The system will now detect faces and mark attendance.
    *   Attendance logs will appear on the right side instantly.

3.  **Stop**:
    *   Click **Stop / Idle** to pause recognition.
