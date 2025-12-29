import cv2
import numpy as np
import requests
import time

# --- GLOBAL SCORE ---
red_score = 0
blue_score = 0
last_score_time = 0.0      # Cooldown to avoid multiple points in one go
GOAL_COOLDOWN_TIME = 5.0   # 5-second wait after a goal
GOAL_THRESHOLD_CM = 2.0    # Distance to register a goal: 2.0 cm
# ------------------------

# --- ESP32 IP ADDRESSES ---
RED_PLAYER_VIBRATOR_URL = "http://192.168.1.100/red/player" 
RED_GOAL_VIBRATOR_URL = "http://192.168.1.101/red/goal"     
BLUE_PLAYER_VIBRATOR_URL = "http://192.168.1.102/blue/player" 
BLUE_GOAL_VIBRATOR_URL = "http://192.168.1.103/blue/goal"     
# --------------------------------

# --- CALIBRATION AND COOLDOWN PARAMETERS ---
PIXELS_PER_CM = 25.0        
PLAYER_PROXIMITY_THRESHOLD_CM = 7.0   
GOAL_PROXIMITY_THRESHOLD_CM = 10.0   
PLAYER_COOLDOWN_TIME = 3.0      
GOAL_COOLDOWN_TIME_ALERT = 0.5         
last_player_alert_time = 0.0 
last_goal_alert_time = 0.0
MIN_DETECTION_AREA = 100 
# --- MORPHOLOGICAL FILTER ---
KERNEL_SIZE = 5 
# ---------------------------------------------

# --- COLOR RANGES (HSV) ---

# 🔴 RED (Player)
RED_Lower = np.array([0, 150, 50], np.uint8) 
RED_Upper = np.array([10, 255, 255], np.uint8)

# 🔵 BLUE (Player)
BLUE_Lower = np.array([105, 150, 80], np.uint8) 
BLUE_Upper = np.array([125, 255, 255], np.uint8)

# 🟡 YELLOW (Red Team Goal)
YELLOW_Lower = np.array([25, 100, 100], np.uint8) 
YELLOW_Upper = np.array([35, 255, 255], np.uint8)

# 🟢 NEON GREEN (Blue Team Goal) - EXPANDED RANGE
GREEN_GOAL_Lower = np.array([45, 150, 180], np.uint8)  
GREEN_GOAL_Upper = np.array([90, 255, 255], np.uint8)  

# 💎 BALL (CYAN/TURQUOISE)
CYAN_BALL_Lower = np.array([85, 120, 100], np.uint8) 
CYAN_BALL_Upper = np.array([105, 255, 255], np.uint8) 

# State and Drawing Variables
show_detailed_info = False 
player_distance_display = 0.0
red_goal_distance_display = 0.0
blue_goal_distance_display = 0.0
red_score_distance_display = 0.0 
blue_score_distance_display = 0.0 

# --- FUNCTIONS ---

def calculate_distance(p1, p2):
    """Calculates Euclidean distance between two points."""
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def calculate_vibration_intensity(distance_cm, threshold_cm):
    """Calculates intensity from 0 to 100: closer = higher intensity."""
    if distance_cm >= threshold_cm:
        return 0 
    
    normalized_distance = distance_cm / threshold_cm
    intensity = 100 - (normalized_distance * 100)
    
    return max(1, min(100, int(intensity)))

def send_alert(base_url, intensity, is_goal=False):
    """Sends HTTP request and handles console logging for alerts."""
    if intensity == 0:
        return

    if is_goal:
        team = "RED" if "red" in base_url else "BLUE"
        print(f"\n🎉🎉🎉 GOAL for {team} Team! 🎉🎉🎉")
    
    # Goal Alert (Movement proximity)
    elif "goal" in base_url and intensity > 0:
        team = "RED" if "red" in base_url else "BLUE"
        goal_color = "YELLOW" if "red" in base_url else "NEON GREEN" 
        print(f"🚨 GOAL ALERT ({team} -> {goal_color}): Intensity: {intensity}%")
        
    final_url = f"{base_url}?intensity={intensity}"
    try:
        requests.get(final_url, timeout=0.1)
    except requests.exceptions.RequestException:
        pass 
    except Exception:
        pass

def print_player_alert(base_url, intensity):
    """Handles console printing for player alerts (triggered at 100%)."""
    if intensity == 100:
        team = "RED" if "red" in base_url else "BLUE"
        print(f"⚠️ PLAYER ALERT: {team} Team activated (100% proximity).")
    
def putText_stroke(frame, text, org, font, fontScale, color, thickness, stroke_color=(0, 0, 0), stroke_thickness=3):
    """Draws text with an outline to improve readability over different backgrounds."""
    cv2.putText(frame, text, org, font, fontScale, stroke_color, stroke_thickness, cv2.LINE_AA)
    cv2.putText(frame, text, org, font, fontScale, color, thickness, cv2.LINE_AA)

def detect_object_shape(mask_original, bgr_color):
    """Detects contour, centroid, and bounding box using morphological filtering."""
    
    kernel = np.ones((KERNEL_SIZE, KERNEL_SIZE), np.uint8)
    filtered_mask = cv2.morphologyEx(mask_original, cv2.MORPH_OPEN, kernel)
    
    contours, _ = cv2.findContours(filtered_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        
        if cv2.contourArea(largest_contour) > MIN_DETECTION_AREA:
            (x, y, w, h) = cv2.boundingRect(largest_contour)
            center = (x + w // 2, y + h // 2)
            
            cv2.rectangle(frame, (x, y), (x + w, y + h), bgr_color, 2)
            cv2.circle(frame, center, 5, bgr_color, -1)
            
            return center, (x, y, w, h)
            
    return None, None


def distance_point_to_rect(point, rect):
    """Calculates minimum distance between a point (ball/player) and a rectangle (goal)."""
    px, py = point
    rx, ry, rw, rh = rect
    
    closest_x = max(rx, min(px, rx + rw))
    closest_y = max(ry, min(py, ry + rh))
    
    return calculate_distance((px, py), (closest_x, closest_y))

# --- CAMERA INITIALIZATION ---
try:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise IOError("Cannot open webcam.")
except Exception as e:
    print(f"FATAL ERROR starting camera: {e}")
    exit()

## 🔄 Main Loop
while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        continue

    current_time = time.time()
    goal_cooldown_active = (current_time - last_score_time) < GOAL_COOLDOWN_TIME
    
    try:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # --- 1. DETECTION OF ALL COLORS AND SHAPES ---
        detections = {}
        
        color_map = {
            'red_player': ((RED_Lower, RED_Upper), (0, 0, 255)),
            'blue_player': ((BLUE_Lower, BLUE_Upper), (255, 0, 0)),
            'yellow_goal': ((YELLOW_Lower, YELLOW_Upper), (0, 255, 255)), 
            'green_goal': ((GREEN_GOAL_Lower, GREEN_GOAL_Upper), (0, 255, 0)), 
            'cyan_ball': ((CYAN_BALL_Lower, CYAN_BALL_Upper), (255, 255, 0)), 
        }

        for color_key, ((lower, upper), bgr) in color_map.items():
            mask = cv2.inRange(hsv, lower, upper)
            center, rect = detect_object_shape(mask, bgr) 
            if center is not None:
                detections[color_key] = {'center': center, 'rect': rect}
        
        # --- 2. GOAL LOGIC (BALL vs GOALS) ---
        
        if 'cyan_ball' not in detections or goal_cooldown_active: 
            red_score_distance_display = 0.0 
            blue_score_distance_display = 0.0 
        
        if 'cyan_ball' in detections and not goal_cooldown_active: 
            ball_center = detections['cyan_ball']['center'] 
            
            # Red Team Goal (Ball vs Yellow Goal)
            if 'yellow_goal' in detections:
                rect = detections['yellow_goal']['rect']
                dist_pix = distance_point_to_rect(ball_center, rect)
                dist_cm = dist_pix / PIXELS_PER_CM if PIXELS_PER_CM else 0.0
                red_score_distance_display = round(dist_cm, 1) 
                
                if dist_cm <= GOAL_THRESHOLD_CM:
                    red_score += 1
                    last_score_time = current_time
                    send_alert(RED_GOAL_VIBRATOR_URL, 100, is_goal=True) 
                    print(f"SCORE: Red {red_score} - {blue_score} Blue")
                    continue

            # Blue Team Goal (Ball vs Green Goal)
            if 'green_goal' in detections: 
                rect = detections['green_goal']['rect'] 
                dist_pix = distance_point_to_rect(ball_center, rect)
                dist_cm = dist_pix / PIXELS_PER_CM if PIXELS_PER_CM else 0.0
                blue_score_distance_display = round(dist_cm, 1)
                
                if dist_cm <= GOAL_THRESHOLD_CM:
                    blue_score += 1
                    last_score_time = current_time
                    send_alert(BLUE_GOAL_VIBRATOR_URL, 100, is_goal=True) 
                    print(f"SCORE: Red {red_score} - {blue_score} Blue")
                    continue 
        
        # --- 3. PLAYER PROXIMITY LOGIC (Red vs Blue) ---
        if 'red_player' in detections and 'blue_player' in detections:
            c_red = detections['red_player']['center']
            c_blue = detections['blue_player']['center']
            dist_cm = calculate_distance(c_red, c_blue) / PIXELS_PER_CM
            player_distance_display = round(dist_cm, 1) 
            
            if dist_cm <= PLAYER_PROXIMITY_THRESHOLD_CM:
                if (current_time - last_player_alert_time) >= PLAYER_COOLDOWN_TIME:
                    last_player_alert_time = current_time 
                    print_player_alert(RED_PLAYER_VIBRATOR_URL, 100)
                    send_alert(RED_PLAYER_VIBRATOR_URL, 100)
                    send_alert(BLUE_PLAYER_VIBRATOR_URL, 100)
        
        # --- 4. GOAL PROXIMITY ALERTS (Proportional Vibration) ---
        if (current_time - last_goal_alert_time) >= GOAL_COOLDOWN_TIME_ALERT:
            last_goal_alert_time = current_time 
            
            # Red Team vs Yellow Goal
            if 'red_player' in detections and 'yellow_goal' in detections:
                dist_cm = distance_point_to_rect(detections['red_player']['center'], detections['yellow_goal']['rect']) / PIXELS_PER_CM
                red_goal_distance_display = round(dist_cm, 1) 
                intensity = calculate_vibration_intensity(dist_cm, GOAL_PROXIMITY_THRESHOLD_CM)
                send_alert(RED_GOAL_VIBRATOR_URL, intensity)
            
            # Blue Team vs Green Goal
            if 'blue_player' in detections and 'green_goal' in detections: 
                dist_cm = distance_point_to_rect(detections['blue_player']['center'], detections['green_goal']['rect']) / PIXELS_PER_CM
                blue_goal_distance_display = round(dist_cm, 1) 
                intensity = calculate_vibration_intensity(dist_cm, GOAL_PROXIMITY_THRESHOLD_CM)
                send_alert(BLUE_GOAL_VIBRATOR_URL, intensity)
        
    except Exception as e:
        print(f"Error during main processing: {e}")

    # --- 5. PROFESSIONAL HUD AND SCOREBOARD ---
    
    # 5a. Scoreboard (Always Visible)
    scoreboard_text = f"RED {red_score} | BLUE {blue_score}"
    text_color = (0, 0, 255) if red_score > blue_score else (255, 0, 0)
    if red_score == blue_score: text_color = (255, 255, 255)
    
    font = cv2.FONT_HERSHEY_DUPLEX
    (w_t, h_t), base = cv2.getTextSize(scoreboard_text, font, 1.0, 2)
    
    # Draw Background Panel
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 5), (w_t + 30, h_t + 25), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    putText_stroke(frame, scoreboard_text, (20, 35), font, 1.0, text_color, 2, (255, 255, 255), 3)
    
    # 5b. Info Toggle Button
    info_text = "INFO (i)"
    btn_color = (0, 255, 0) if not show_detailed_info else (0, 0, 255)
    putText_stroke(frame, info_text, (frame.shape[1] - 120, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, btn_color, 2)
    
    # 5c. Detailed Info Panel (Toggleable)
    if show_detailed_info:
        panel_y = 60
        overlay = frame.copy()
        cv2.rectangle(overlay, (15, panel_y), (415, panel_y + 220), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        y = panel_y + 30
        cv2.putText(frame, "PROXIMITY DATA", (30, y), font, 0.7, (0, 255, 255), 2)
        y += 30
        cv2.putText(frame, f"Players (R-B): {player_distance_display} cm", (30, y), 1, 1.2, (255,255,255), 1)
        y += 30
        cv2.putText(frame, f"Red -> Yellow Goal: {red_goal_distance_display} cm", (30, y), 1, 1.2, (0,255,255), 1)
        y += 30
        cv2.putText(frame, f"Blue -> Green Goal: {blue_goal_distance_display} cm", (30, y), 1, 1.2, (0,255,0), 1)
        y += 30
        cv2.putText(frame, f"Ball -> Red Goal: {red_score_distance_display} cm", (30, y), 1, 1.2, (255,255,0), 1)
        y += 30
        cv2.putText(frame, f"Ball -> Blue Goal: {blue_score_distance_display} cm", (30, y), 1, 1.2, (255,255,0), 1)

    cv2.imshow('Batsense - Vision System', frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break
    if key == ord('i'): show_detailed_info = not show_detailed_info

cap.release()
cv2.destroyAllWindows()
print("System closed. Resources released.")
