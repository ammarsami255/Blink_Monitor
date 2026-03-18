import sys
import cv2
import numpy as np
import time
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QMessageBox,
    QProgressBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QFont, QColor, QPalette

from eye_analyzer import EyeAnalyzer
from report_generator import ReportGenerator


DARK_BG    = "#0d1117"
CARD_BG    = "#161b22"
BORDER     = "#30363d"
TEXT_PRI   = "#e6edf3"
TEXT_SEC   = "#8b949e"
ACCENT     = "#58a6ff"
GREEN      = "#3fb950"
RED        = "#f85149"
ORANGE     = "#d29922"


class CameraThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    stats_ready = pyqtSignal(dict)

    def __init__(self, analyzer: EyeAnalyzer):
        super().__init__()
        self.analyzer = analyzer
        self._running = True

    def run(self):
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        while self._running:
            ret, frame = cap.read()
            if not ret:
                continue
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            summary = self.analyzer.process(rgb, w, h)
            self.frame_ready.emit(frame)
            self.stats_ready.emit(summary)
            self.msleep(16)
        cap.release()

    def stop(self):
        self._running = False
        self.wait()


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "—", unit: str = ""):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background: {CARD_BG};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        self._title = QLabel(title)
        self._title.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; font-weight: 600; border: none;")

        self._value = QLabel(value)
        self._value.setStyleSheet(f"color: {TEXT_PRI}; font-size: 26px; font-weight: 700; border: none;")

        self._unit = QLabel(unit)
        self._unit.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; border: none;")

        layout.addWidget(self._title)
        layout.addWidget(self._value)
        layout.addWidget(self._unit)

    def update_value(self, value: str, color: str = TEXT_PRI):
        self._value.setText(value)
        self._value.setStyleSheet(f"color: {color}; font-size: 26px; font-weight: 700; border: none;")


class StatusBadge(QLabel):
    def __init__(self):
        super().__init__("● Monitoring")
        self.setStyleSheet(f"""
            color: {ACCENT};
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            background: rgba(88, 166, 255, 0.1);
            border: 1px solid rgba(88, 166, 255, 0.3);
            border-radius: 10px;
        """)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_status(self, status: str, color: str):
        self.setText(f"● {status}")
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        self.setStyleSheet(f"""
            color: {color};
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            background: rgba({r}, {g}, {b}, 0.1);
            border: 1px solid rgba({r}, {g}, {b}, 0.3);
            border-radius: 10px;
        """)


class BlinkMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.analyzer = EyeAnalyzer()
        self.reporter = ReportGenerator()
        self._session_start = time.time()
        self._last_summary = {}

        self.setWindowTitle("Blink Monitor")
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(f"background-color: {DARK_BG}; color: {TEXT_PRI};")

        self._build_ui()

        self.cam_thread = CameraThread(self.analyzer)
        self.cam_thread.frame_ready.connect(self._update_frame)
        self.cam_thread.stats_ready.connect(self._update_stats)
        self.cam_thread.start()

        self._timer = QTimer()
        self._timer.timeout.connect(self._update_elapsed)
        self._timer.start(1000)

    def _btn(self, text: str, color: str = ACCENT) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(88,166,255,0.08);
                color: {color};
                border: 1px solid {color};
                border-radius: 6px;
                padding: 8px 18px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: rgba(88,166,255,0.18);
            }}
            QPushButton:pressed {{
                background: rgba(88,166,255,0.28);
            }}
        """)
        return btn

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("Blink Monitor")
        title.setStyleSheet(f"color: {TEXT_PRI}; font-size: 18px; font-weight: 700;")
        self._status_badge = StatusBadge()
        self._elapsed_label = QLabel("00:00:00")
        self._elapsed_label.setStyleSheet(f"color: {TEXT_SEC}; font-size: 13px;")
        header.addWidget(title)
        header.addWidget(self._status_badge)
        header.addStretch()
        header.addWidget(self._elapsed_label)
        root.addLayout(header)

        # Main content
        content = QHBoxLayout()
        content.setSpacing(16)

        # Left: camera
        left = QVBoxLayout()
        left.setSpacing(10)
        self._cam_label = QLabel()
        self._cam_label.setFixedSize(640, 480)
        self._cam_label.setStyleSheet(f"background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px;")
        self._cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(self._cam_label)

        # EAR bar
        ear_row = QHBoxLayout()
        ear_lbl = QLabel("EAR")
        ear_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; font-weight: 600;")
        self._ear_bar = QProgressBar()
        self._ear_bar.setRange(0, 100)
        self._ear_bar.setTextVisible(False)
        self._ear_bar.setFixedHeight(8)
        self._ear_bar.setStyleSheet(f"""
            QProgressBar {{ background: {BORDER}; border-radius: 4px; border: none; }}
            QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}
        """)
        self._ear_val = QLabel("0.00")
        self._ear_val.setStyleSheet(f"color: {TEXT_PRI}; font-size: 12px; min-width: 35px;")
        ear_row.addWidget(ear_lbl)
        ear_row.addWidget(self._ear_bar)
        ear_row.addWidget(self._ear_val)
        left.addLayout(ear_row)
        content.addLayout(left)

        # Right: stats + controls
        right = QVBoxLayout()
        right.setSpacing(12)

        # Stat cards grid
        grid = QGridLayout()
        grid.setSpacing(10)
        self._card_total   = StatCard("TOTAL BLINKS", "0", "blinks")
        self._card_rate    = StatCard("BLINKS / MIN", "—", "last minute")
        self._card_avg_ear = StatCard("AVG EAR", "0.000", "eye aspect ratio")
        self._card_avg_rate = StatCard("AVG RATE", "0.0", "blinks/min overall")
        grid.addWidget(self._card_total,    0, 0)
        grid.addWidget(self._card_rate,     0, 1)
        grid.addWidget(self._card_avg_ear,  1, 0)
        grid.addWidget(self._card_avg_rate, 1, 1)
        right.addLayout(grid)

        # Minute history
        hist_frame = QFrame()
        hist_frame.setStyleSheet(f"background: {CARD_BG}; border: 1px solid {BORDER}; border-radius: 8px;")
        hist_layout = QVBoxLayout(hist_frame)
        hist_layout.setContentsMargins(16, 12, 16, 12)
        hist_lbl = QLabel("Per-Minute History")
        hist_lbl.setStyleSheet(f"color: {TEXT_SEC}; font-size: 11px; font-weight: 600; border: none;")
        self._hist_label = QLabel("No data yet")
        self._hist_label.setStyleSheet(f"color: {TEXT_PRI}; font-size: 13px; border: none;")
        self._hist_label.setWordWrap(True)
        hist_layout.addWidget(hist_lbl)
        hist_layout.addWidget(self._hist_label)
        right.addWidget(hist_frame)

        right.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        self._btn_reset  = self._btn("Reset Session", ORANGE)
        self._btn_json   = self._btn("Export JSON", GREEN)
        self._btn_csv    = self._btn("Export CSV", GREEN)
        self._btn_txt    = self._btn("Export TXT", GREEN)
        self._btn_reset.clicked.connect(self._reset)
        self._btn_json.clicked.connect(lambda: self._export("json"))
        self._btn_csv.clicked.connect(lambda: self._export("csv"))
        self._btn_txt.clicked.connect(lambda: self._export("txt"))
        for b in [self._btn_reset, self._btn_json, self._btn_csv, self._btn_txt]:
            btn_row.addWidget(b)
        right.addLayout(btn_row)

        content.addLayout(right)
        root.addLayout(content)

    def _update_frame(self, frame: np.ndarray):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame.shape
        img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self._cam_label.setPixmap(QPixmap.fromImage(img).scaled(
            640, 480, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

    def _update_stats(self, summary: dict):
        self._last_summary = summary
        total  = summary["total_blinks"]
        rate   = self.analyzer.current_rate
        ear    = self.analyzer.current_ear
        avg_r  = summary["avg_blinks_per_min"]
        avg_e  = summary["avg_ear"]
        status = self.analyzer.session.status(rate)
        color  = self.analyzer.session.status_color(rate)

        self._card_total.update_value(str(total))
        self._card_rate.update_value(str(rate) if rate > 0 else "—", color if rate > 0 else TEXT_PRI)
        self._card_avg_ear.update_value(f"{avg_e:.3f}")
        self._card_avg_rate.update_value(f"{avg_r:.1f}")

        self._ear_bar.setValue(int(min(ear / 0.4 * 100, 100)))
        self._ear_val.setText(f"{ear:.2f}")

        self._status_badge.set_status(status, color)

        rates = summary["minute_rates"]
        if rates:
            parts = []
            for i, r in enumerate(rates[-6:], max(1, len(rates) - 5)):
                c = GREEN if 12 <= r <= 20 else (RED if r < 12 else ORANGE)
                parts.append(f'<span style="color:{c}">Min {i}: {r}</span>')
            self._hist_label.setText("  |  ".join(parts))

    def _update_elapsed(self):
        s = int(time.time() - self._session_start)
        self._elapsed_label.setText(f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}")

    def _reset(self):
        self.analyzer.reset_session()
        self._session_start = time.time()
        self._card_total.update_value("0")
        self._card_rate.update_value("—")
        self._card_avg_ear.update_value("0.000")
        self._card_avg_rate.update_value("0.0")
        self._hist_label.setText("No data yet")

    def _export(self, fmt: str):
        if not self._last_summary:
            QMessageBox.warning(self, "No Data", "No session data to export yet.")
            return
        path = getattr(self.reporter, f"save_{fmt}")(self._last_summary)
        QMessageBox.information(self, "Exported", f"Report saved:\n{path}")

    def closeEvent(self, event):
        self.cam_thread.stop()
        self.analyzer.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    win = BlinkMonitorApp()
    win.show()
    sys.exit(app.exec())
