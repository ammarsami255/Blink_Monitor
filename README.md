# Blink Monitor 👁️

Real-time eye blink tracking and eye strain detection using MediaPipe FaceMesh + PyQt6 dashboard.

---

## The Problem

A person blinks naturally **15–20 times/minute**. In front of a screen, that drops to **5–7 times/minute** without noticing.

**Effects of low blink rate:**
- Dry, burning eyes
- Blurry vision after extended use
- Headaches from eye muscle strain
- Long-term: corneal damage

This tool monitors your blink rate in real-time and warns you before symptoms start.

---

## Features

- Real-time EAR (Eye Aspect Ratio) calculation via MediaPipe FaceMesh
- Per-minute blink rate tracking with live status
- Color-coded warnings (Normal / Eye Strain / High Rate)
- Full PyQt6 dashboard with live camera feed
- Session statistics (total blinks, avg rate, avg EAR)
- Per-minute history log
- Export reports: JSON / CSV / TXT

---

## Project Structure

```
blink_monitor/
├── main.py              # PyQt6 GUI + CameraThread
├── eye_analyzer.py      # EyeAnalyzer + BlinkSession logic
├── report_generator.py  # JSON / CSV / TXT export
├── requirements.txt
└── reports/             # Auto-created on first export
```

---

## Requirements

- Python 3.10+
- Webcam

```
numpy<2
opencv-python>=4.8.0
mediapipe>=0.10.0
PyQt6>=6.4.0
```

---

## Installation

```bash
pip install -r requirements.txt
python main.py
```

---

## How It Works

1. **MediaPipe FaceMesh** detects 468 facial landmarks per frame
2. **EAR** (Eye Aspect Ratio) is calculated each frame:
   ```
   EAR = (||p1-p5|| + ||p2-p4||) / (2 * ||p0-p3||)
   ```
3. If EAR drops below **0.21** for **2+ consecutive frames** → blink detected
4. Every 60 seconds, blink count is recorded and rate is evaluated:
   - `< 12/min` → **Eye Strain Warning** 🔴
   - `12–20/min` → **Normal** 🟢
   - `> 20/min` → **High Blink Rate** 🟠

---

## Stack

| Tool | Usage |
|------|-------|
| Python | Core language |
| MediaPipe | Face landmark detection |
| OpenCV | Camera capture + frame processing |
| PyQt6 | GUI dashboard |
| NumPy | EAR math |

---

## Potential Applications

- Eye health monitoring for desk workers
- Driver drowsiness detection
- Medical research (Parkinson's, Dry Eye Disease)
- Attention/focus tracking systems
