import cv2
import math
import time
import numpy as np
from ctypes import cast, POINTER

mp_hands = None
mp_draw = None

try:
    import mediapipe.python.solutions.hands as mp_hands
    import mediapipe.python.solutions.drawing_utils as mp_draw
except Exception:
    try:
        import mediapipe as mp
        mp_hands = mp.solutions.hands
        mp_draw = mp.solutions.drawing_utils
    except Exception:
        try:
            from mediapipe.python.solutions import hands as mp_hands
            from mediapipe.python.solutions import drawing_utils as mp_draw
        except Exception as e:
            print("خطا در بارگذاری MediaPipe:", e)

if mp_hands is None or mp_draw is None:
    print("❌ خطای اصلی: کتابخانه MediaPipe به درستی لود نشد.")
    print("لطفاً در ترمینال دستور زیر را اجرا کنید:")
    print("python -m pip install mediapipe --upgrade --force-reinstall")
    exit(1)

volume_control = None
has_sound = False

try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    devices = AudioUtilities.GetSpeakers()
    if hasattr(devices, 'EndpointVolume'):
        volume_control = devices.EndpointVolume
    else:
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume_control = cast(interface, POINTER(IAudioEndpointVolume))
    
    has_sound = True
    print("✅ سیستم کنترل صدای ویندوز با موفقیت متصل شد.")
except Exception as e:
    print(f"⚠️ هشدار سیستم صدا: {e} (برنامه در حالت شبیه‌سازی اجرا می‌شود)")

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

vol_bar = 400
vol_per = 0
p_time = 0

print("🚀 برنامه آماده اجراست. برای خروج دکمه 'q' یا 'ESC' را در پنجره تصویر فشار دهید.")

while cap.isOpened():
    success, img = cap.read()
    if not success:
        print("عدم دسترسی به دوربین!")
        break

    img = cv2.flip(img, 1)
    h, w, c = img.shape

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    lm_list = []
    if results.multi_hand_landmarks:
        for hand_lms in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_lms, mp_hands.HAND_CONNECTIONS)
            
            for id, lm in enumerate(hand_lms.landmark):
                cx, cy = int(lm.x * w), int(lm.y * h)
                lm_list.append([id, cx, cy])

    if len(lm_list) != 0:
        x1, y1 = lm_list[4][1], lm_list[4][2]
        x2, y2 = lm_list[8][1], lm_list[8][2]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        cv2.circle(img, (x1, y1), 10, (255, 0, 255), cv2.FILLED)
        cv2.circle(img, (x2, y2), 10, (255, 0, 255), cv2.FILLED)
        cv2.line(img, (x1, y1), (x2, y2), (255, 0, 255), 3)
        cv2.circle(img, (cx, cy), 8, (0, 255, 0), cv2.FILLED)

        length = math.hypot(x2 - x1, y2 - y1)

        vol_per = np.interp(length, [20, 180], [0, 100])
        vol_bar = np.interp(length, [20, 180], [400, 150])

        if has_sound and volume_control is not None:
            try:
                volume_control.SetMasterVolumeLevelScalar(vol_per / 100.0, None)
            except Exception:
                pass

        if length < 25:
            cv2.circle(img, (cx, cy), 10, (0, 0, 255), cv2.FILLED)

    cv2.rectangle(img, (50, 150), (85, 400), (0, 255, 0), 2)
    cv2.rectangle(img, (50, int(vol_bar)), (85, 400), (0, 255, 0), cv2.FILLED)
    cv2.putText(img, f'{int(vol_per)} %', (40, 440), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)

    c_time = time.time()
    fps = 1 / (c_time - p_time) if (c_time - p_time) > 0 else 0
    p_time = c_time
    cv2.putText(img, f'FPS: {int(fps)}', (40, 50), cv2.FONT_HERSHEY_COMPLEX, 0.8, (255, 0, 0), 2)

    cv2.imshow("Hand Gesture Volume Control", img)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q') or key == 27:  # q یا ESC
        break

cap.release()
cv2.destroyAllWindows()
