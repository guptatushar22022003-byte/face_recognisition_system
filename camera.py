import cv2
import os
import numpy as np
import database
import json

class VideoCamera:
    def __init__(self):
        self.video = cv2.VideoCapture(0)
        self.mode = "idle"  # idle, register, recognize
        self.face_detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        
        self.data_dir = "face_data"
        self.model_file = "trainer.yml"
        self.names_file = "names.json"
        
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        self.load_resources()
        
        # Registration state
        self.reg_id = None
        self.reg_name = None
        self.reg_count = 0
        self.reg_max = 60

    def __del__(self):
        self.video.release()

    def load_resources(self):
        self.names = {}
        if os.path.exists(self.names_file):
            with open(self.names_file, 'r') as f:
                self.names = {int(k):v for k,v in json.load(f).items()}
        
        if os.path.exists(self.model_file):
            self.recognizer.read(self.model_file)

    def start_registration(self, user_id, name):
        self.reg_id = int(user_id)
        self.reg_name = name
        self.reg_count = 0
        self.mode = "register"
        
        # Save name mapping immediately
        self.names[self.reg_id] = name
        with open(self.names_file, 'w') as f:
            json.dump(self.names, f)
        database.add_user(self.reg_id, name)

    def start_recognition(self):
        self.load_resources() # Reload in case of updates
        if not os.path.exists(self.model_file):
            print("Model not found")
            return False
        self.mode = "recognize"
        return True

    def stop_mode(self):
        self.mode = "idle"

    def train_model(self):
        print("Training model...")
        path = self.data_dir
        imagePaths = [os.path.join(path,f) for f in os.listdir(path) if f.endswith('.jpg')]     
        faceSamples=[]
        ids = []

        for imagePath in imagePaths:
            try:
                PIL_img = cv2.imread(imagePath, cv2.IMREAD_GRAYSCALE)
                id = int(os.path.split(imagePath)[-1].split(".")[1])
                faceSamples.append(PIL_img)
                ids.append(id)
            except:
                continue
        
        if ids:
            self.recognizer.train(faceSamples, np.array(ids))
            self.recognizer.write(self.model_file)
            print("Training complete.")

    def get_frame(self):
        success, image = self.video.read()
        if not success:
            return None

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = self.face_detector.detectMultiScale(gray, 1.3, 5)

        if self.mode == "register":
            for (x, y, w, h) in faces:
                cv2.rectangle(image, (x, y), (x+w, y+h), (255, 0, 0), 2)
                self.reg_count += 1
                
                cv2.imwrite(f"{self.data_dir}/User.{self.reg_id}.{self.reg_count}.jpg", gray[y:y+h,x:x+w])
                cv2.putText(image, f"Capturing: {self.reg_count}/{self.reg_max}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if self.reg_count >= self.reg_max:
                self.mode = "idle"
                self.train_model()
                cv2.putText(image, "Training Complete!", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        elif self.mode == "recognize":
            for (x, y, w, h) in faces:
                try:
                    id, confidence = self.recognizer.predict(gray[y:y+h,x:x+w])
                    
                    # Lower threshold for stricter matching (0 is perfect, 100 is bad)
                    # 50 is a good balance. If still false positive, lower to 40.
                    if confidence < 50: 
                        name = self.names.get(id, "Unknown")
                        conf_text = f"{round(100 - confidence)}%"
                        color = (0, 255, 0) # Green for match
                        
                        if name != "Unknown":
                            if database.mark_attendance(id, name):
                                print(f"Marked: {name}")
                    else:
                        name = "Unknown"
                        conf_text = f"Low: {round(confidence)}"
                        color = (0, 0, 255) # Red for unknown

                    cv2.rectangle(image, (x, y), (x+w, y+h), color, 2)
                    cv2.putText(image, str(name), (x+5,y-5), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
                    cv2.putText(image, str(conf_text), (x+5,y+h-5), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,0), 1)
                except:
                    pass

        else: # Idle
            cv2.putText(image, "System Ready", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        ret, jpeg = cv2.imencode('.jpg', image)
        return jpeg.tobytes()
