try:
    import cv2
except ImportError:
    print("[ERROR] 'cv2' module not found. Please install it using:")
    print("pip install opencv-python opencv-contrib-python")
    exit(1)
import os
import numpy as np
import json
import database  # Import our database module

# Directory to save face data
DATA_DIR = "face_data"
MODEL_FILE = "trainer.yml"
NAMES_FILE = "names.json"

def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def load_names():
    # Try file first
    if os.path.exists(NAMES_FILE):
        with open(NAMES_FILE, 'r') as f:
            try:
                names = {int(k):v for k,v in json.load(f).items()}
                print(f"[INFO] Loaded {len(names)} users from {NAMES_FILE}.")
                return names
            except Exception:
                pass
    # Fallback to DB if file missing or invalid
    try:
        users = database.get_all_users()
        if users:
            print(f"[INFO] Loaded {len(users)} users from database as fallback.")
            return users
    except Exception as e:
        print(f"[WARN] Could not load users from DB: {e}")
    return {}

def save_name(id, name):
    names = load_names()
    names[id] = name
    # Ensure JSON keys are strings for compatibility
    serializable = {str(k): v for k, v in names.items()}
    with open(NAMES_FILE, 'w') as f:
        json.dump(serializable, f)
    # Also save to DB
    database.add_user(id, name)

def register_face(face_id, name):
    # Try opening camera. On Windows, CAP_DSHOW can help in some setups.
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cam.isOpened():
        print("[ERROR] Unable to open camera. Check camera connection and permissions.")
        return
    # ensure data dir exists
    create_directory(DATA_DIR)
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    print(f"\n[INFO] Initializing face capture for user {name} (ID: {face_id}).")
    print("[INFO] Please look at the camera. Move your face slightly (left, right, up, down) to capture angles.")
    
    count = 0
    max_samples = 60
    
    while True:
        ret, img = cam.read()
        if not ret:
            print("[ERROR] Failed to read frame from camera")
            break

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = detector.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
            count += 1
            # Save face ROI only
            face_roi = gray[y:y+h, x:x+w]
            cv2.imwrite(os.path.join(DATA_DIR, f"User.{face_id}.{count}.jpg"), face_roi)

        # Always show the latest frame and capture count (even when no faces detected)
        cv2.putText(img, f"Captured: {count}/{max_samples}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow('Registering Face', img)

        # Use waitKey(1) for better responsiveness
        k = cv2.waitKey(1) & 0xff
        if k == 27:  # Press 'ESC' to stop
            break
        elif count >= max_samples:
            break

    print("\n[INFO] Capture complete.")
    cam.release()
    cv2.destroyAllWindows()
    train_model()

def train_model():
    print("\n[INFO] Training faces. Please wait...")
    path = DATA_DIR
    # Ensure data directory exists before training
    create_directory(path)
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    imagePaths = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('.jpg')]
    imagePaths.sort()
    faceSamples = []
    ids = []

    if not imagePaths:
        print("[ERROR] No training data found!")
        return

    for imagePath in imagePaths:
        img = cv2.imread(imagePath, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"[WARN] Skipping unreadable image: {imagePath}")
            continue
        try:
            id = int(os.path.split(imagePath)[-1].split(".")[1])
            faceSamples.append(img)
            ids.append(id)
        except Exception:
            print(f"[WARN] Could not parse id from filename: {imagePath}")
            continue

    if not ids:
        print("[ERROR] No valid training images found after scanning files.")
        return

    try:
        recognizer.train(faceSamples, np.array(ids))
    except Exception as e:
        print(f"[ERROR] Training failed: {e}")
        return
    recognizer.write(MODEL_FILE)
    print(f"\n[INFO] Success! {len(np.unique(ids))} faces trained.")

def recognize_faces(names_dict):
    # Create recognizer and check availability (opencv-contrib required)
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
    except Exception as e:
        print("[ERROR] OpenCV face recognizer not available. Install 'opencv-contrib-python'.")
        print(f"Details: {e}")
        return

    if not os.path.exists(MODEL_FILE):
        print("[ERROR] Model not found! Please register a face first.")
        return

    try:
        recognizer.read(MODEL_FILE)
    except Exception as e:
        print(f"[ERROR] Failed to load model '{MODEL_FILE}': {e}")
        return
    faceCascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml");

    font = cv2.FONT_HERSHEY_SIMPLEX
    # Try opening camera. On Windows, CAP_DSHOW can help in some setups.
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cam.isOpened():
        print("[ERROR] Unable to open camera for recognition. Check connection and permissions.")
        return
    
    print("\n[INFO] Starting Recognition. Press 'ESC' to exit.")

    while True:
        ret, img = cam.read()
        if not ret:
            break
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        faces = faceCascade.detectMultiScale( 
            gray,
            scaleFactor = 1.2,
            minNeighbors = 5,
            minSize = (int(0.1*cam.get(3)), int(0.1*cam.get(4))),
        )

        for(x,y,w,h) in faces:
            cv2.rectangle(img, (x,y), (x+w,y+h), (0,255,0), 2)
            id, confidence = recognizer.predict(gray[y:y+h,x:x+w])

            if (confidence < 65):
                name = names_dict.get(id, "Unknown")
                match_txt = f"{round(100 - confidence)}%"
                
                # Mark attendance in DB
                if name != "Unknown":
                    status = database.mark_attendance(id, name)
                    if status:
                        print(f"[ATTENDANCE] {status} for {name}")
                        # Visual feedback on screen
                        cv2.putText(img, status, (x, y-30), font, 0.7, (0, 255, 0), 2)
            else:
                name = "Unknown"
                match_txt = f"Low: {round(confidence)}"
            
            cv2.putText(img, str(name), (x+5,y-5), font, 1, (255,255,255), 2)
            cv2.putText(img, str(match_txt), (x+5,y+h-5), font, 1, (255,255,0), 1)  
        
        cv2.imshow('Face Recognition', img) 

        # Fix: Use waitKey(1) and check specifically for ESC (27)
        k = cv2.waitKey(1) & 0xff 
        if k == 27:
            print("\n[INFO] ESC pressed. Exiting...")
            break

    cam.release()
    cv2.destroyAllWindows()

def main():
    create_directory(DATA_DIR)
    # Initialize DB on startup
    database.init_db()
    
    while True:
        print("\n--- Face Recognition System (With Dashboard) ---")
        print("1. Register New Face")
        print("2. Start Recognition")
        print("3. Exit")
        choice = input("Enter choice: ")
        
        if choice == '1':
            try:
                face_id = int(input('\nEnter user id (numeric, e.g., 1): '))
                name = input('Enter user name: ')
                save_name(face_id, name)
                register_face(face_id, name)
            except ValueError:
                print("Invalid ID. Please enter a number.")
        elif choice == '2':
            names = load_names()
            if not names:
                print("No faces registered yet!")
            else:
                recognize_faces(names)
        elif choice == '3':
            break
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()
