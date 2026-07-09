import cv2
import os
import pandas as pd

harcascadePath = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
detector = cv2.CascadeClassifier(harcascadePath)

if detector.empty():
    print("[ERROR] Could not load Haar Cascade XML.")
    exit()

cam = cv2.VideoCapture(0)
if not cam.isOpened():
    print("[ERROR] Could not access the camera.")
    exit()

# ====== INPUT DETAILS ======
name = input('\nEnter your Name: ')
roll_number = input('Enter your Roll Number: ')
face_id = input('Enter user ID (numeric): ')

print("\n[INFO] Initializing face capture. Look at camera...")

count = 0
os.makedirs("dataset", exist_ok=True)

# ====== CREATE STUDENT DATABASE FILE ======
student_file = "students.xlsx"

if not os.path.exists(student_file):
    df = pd.DataFrame(columns=["ID", "Name", "Roll"])
    df.to_excel(student_file, index=False)

df = pd.read_excel(student_file)

# Prevent duplicate ID
if int(face_id) in df["ID"].values:
    print("ID already exists!")
else:
    new_row = {"ID": int(face_id), "Name": name, "Roll": roll_number}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_excel(student_file, index=False)
    print("Student details saved.")

# ====== FACE CAPTURE ======
while True:
    ret, img = cam.read()
    if not ret:
        break

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(gray, 1.3, 5)

    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x,y), (x+w,y+h), (255,0,0), 2)
        count += 1

        face_img = gray[y:y+h, x:x+w]
        filename = f"dataset/User.{face_id}.{count}.jpg"
        cv2.imwrite(filename, face_img)

    cv2.imshow('image', img)

    if cv2.waitKey(100) & 0xFF == ord('q'):
        break
    elif count >= 80:
        break

print("\n[INFO] Face Capture Completed")
cam.release()
cv2.destroyAllWindows()


#3.1.7 PYTHON CODE:-
import cv2
import pandas  as pd
import serial
import os
import time
from datetime import datetime

# ================= SERIAL =================
try:
    ser = serial.Serial('COM6', 9600, timeout=1)
    time.sleep(2)
    print("ESP32 Connected")
except:
    print("ESP32 Not Connected")
    ser = None

# ================= LOAD MODEL =================
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("trainer.yml")

faceCascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

students_df = pd.read_excel("students.xlsx")
attendance_file = "attendance.xlsx"

# ================= CREATE FILE IF NOT EXISTS =================
if not os.path.exists(attendance_file):
    df = pd.DataFrame(columns=["ID","Name","Roll","Date","Period","Time"])
    df.to_excel(attendance_file, index=False)

# =====================================================
def take_attendance():

    period = input("Enter Period (1-6): ")
    today = datetime.now().strftime("%Y-%m-%d")

    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("Camera not working!")
        return

    print("\nAttendance Mode Started (Press Q to Exit)\n")

    session_present = set()

    while True:

        ret, img = cam.read()
        if not ret:
            break

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = faceCascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:

            id, confidence = recognizer.predict(gray[y:y+h, x:x+w])

            if confidence < 50:

                student = students_df[students_df["ID"] == id]

                if not student.empty:

                    name = student.iloc[0]["Name"]
                    roll = student.iloc[0]["Roll"]
                    current_time = datetime.now().strftime("%H:%M:%S")

                    if id not in session_present:
                        print(f"{name} is PRESENT")
                        session_present.add(id)

                        # 🔹 Send to ESP32 (LCD will show PRESENT)
                        if ser:
                            message = f"PRESENT,{id},{name},{period}\n"
                            ser.write(message.encode())
                            time.sleep(0.5)

                    # ===== SAVE TO EXCEL =====
                    df = pd.read_excel(attendance_file)

                    already_marked = df[
                        (df["ID"] == id) &
                        (df["Date"] == today) &
                        (df["Period"].astype(str) == str(period))
                    ]

                    if already_marked.empty:
                        new_row = {
                            "ID": id,
                            "Name": name,
                            "Roll": roll,
                            "Date": today,
                            "Period": period,
                            "Time": current_time
                        }

                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        df.to_excel(attendance_file, index=False)

                    label = name
                else:
                    label = "UNKNOWN"
            else:
                label = "UNKNOWN"

            cv2.rectangle(img, (x, y), (x+w, y+h), (0,255,0), 2)
            cv2.putText(img, label, (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1, (255,255,255), 2)

        cv2.imshow("Attendance System", img)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()

    # ================= ABSENT CHECK =================
    df = pd.read_excel(attendance_file)

    present_ids = df[
        (df["Date"] == today) &
        (df["Period"].astype(str) == str(period))
    ]["ID"].tolist()

    print("\n===== ABSENT STUDENTS =====")

    for _, row in students_df.iterrows():

        if row["ID"] not in present_ids:

            print(f"{row['Name']} is ABSENT")

            # 🔹 Send ABSENT to ESP32 (LCD + SMS trigger)
            if ser:
                message = f"ABSENT,{row['ID']},{row['Name']},{period}\n"
                ser.write(message.encode())
                time.sleep(2)

    print("\nAttendance Mode Closed\n")

# =====================================================
def main():

    while True:
        print("========= FACE ATTENDANCE SYSTEM =========")
        print("1 - Take Attendance")
        print("2 - Exit")

        choice = input("Enter choice: ")

        if choice == '1':
            take_attendance()
        elif choice == '2':
            print("System Closed")
            break
        else:
            print("Invalid choice\n")

main()
