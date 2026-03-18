import numpy as np
import mediapipe as mp
import time
from collections import deque
from dataclasses import dataclass, field


LEFT_EYE  = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33,  160, 158, 133, 153, 144]

EAR_THRESHOLD   = 0.21
CONSEC_FRAMES   = 2
STRAIN_LOW      = 12
STRAIN_HIGH     = 20


@dataclass
class BlinkSession:
    start_time: float = field(default_factory=time.time)
    blink_timestamps: list = field(default_factory=list)
    ear_history: deque = field(default_factory=lambda: deque(maxlen=300))
    minute_rates: list = field(default_factory=list)

    def add_blink(self):
        self.blink_timestamps.append(time.time())

    def elapsed(self) -> float:
        return time.time() - self.start_time

    def blinks_in_last_n_seconds(self, n: float) -> int:
        cutoff = time.time() - n
        return sum(1 for t in self.blink_timestamps if t >= cutoff)

    def avg_ear(self) -> float:
        return float(np.mean(self.ear_history)) if self.ear_history else 0.0

    def status(self, rate: int) -> str:
        if rate == 0:
            return "Monitoring"
        if rate < STRAIN_LOW:
            return "Eye Strain Warning"
        if rate > STRAIN_HIGH:
            return "High Blink Rate"
        return "Normal"

    def status_color(self, rate: int) -> str:
        s = self.status(rate)
        return {"Normal": "#00e676", "Eye Strain Warning": "#ff1744",
                "High Blink Rate": "#ff9100", "Monitoring": "#40c4ff"}[s]

    def export_summary(self) -> dict:
        total = len(self.blink_timestamps)
        elapsed = self.elapsed()
        return {
            "duration_seconds": round(elapsed, 1),
            "total_blinks": total,
            "avg_blinks_per_min": round(total / (elapsed / 60), 1) if elapsed > 0 else 0,
            "avg_ear": round(self.avg_ear(), 4),
            "minute_rates": self.minute_rates,
        }


class EyeAnalyzer:
    def __init__(self):
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        )
        self.session = BlinkSession()
        self._closed_frames = 0
        self._last_minute_ts = time.time()
        self._minute_blink_count = 0
        self.current_rate = 0
        self.current_ear = 0.0
        self.face_detected = False

    def _ear(self, landmarks, eye_idx, w, h) -> float:
        p = [np.array([landmarks[i].x * w, landmarks[i].y * h]) for i in eye_idx]
        A = np.linalg.norm(p[1] - p[5])
        B = np.linalg.norm(p[2] - p[4])
        C = np.linalg.norm(p[0] - p[3])
        return (A + B) / (2.0 * C)

    def process(self, frame_rgb, w, h):
        result = self._face_mesh.process(frame_rgb)
        self.face_detected = result.multi_face_landmarks is not None

        if self.face_detected:
            lm = result.multi_face_landmarks[0].landmark
            left  = self._ear(lm, LEFT_EYE,  w, h)
            right = self._ear(lm, RIGHT_EYE, w, h)
            avg   = (left + right) / 2.0
            self.current_ear = avg
            self.session.ear_history.append(avg)

            if avg < EAR_THRESHOLD:
                self._closed_frames += 1
            else:
                if self._closed_frames >= CONSEC_FRAMES:
                    self.session.add_blink()
                    self._minute_blink_count += 1
                self._closed_frames = 0

        now = time.time()
        if now - self._last_minute_ts >= 60:
            self.current_rate = self._minute_blink_count
            self.session.minute_rates.append(self._minute_blink_count)
            self._minute_blink_count = 0
            self._last_minute_ts = now

        return self.session.export_summary()

    def reset_session(self):
        self.session = BlinkSession()
        self._closed_frames = 0
        self._minute_blink_count = 0
        self._last_minute_ts = time.time()
        self.current_rate = 0

    def close(self):
        self._face_mesh.close()
