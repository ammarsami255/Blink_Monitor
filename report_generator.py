import json
import csv
import os
from datetime import datetime


class ReportGenerator:
    def __init__(self, output_dir: str = "reports"):
        os.makedirs(output_dir, exist_ok=True)
        self.output_dir = output_dir

    def _filename(self, ext: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.output_dir, f"blink_report_{ts}.{ext}")

    def save_json(self, summary: dict) -> str:
        path = self._filename("json")
        summary["generated_at"] = datetime.now().isoformat()
        with open(path, "w") as f:
            json.dump(summary, f, indent=2)
        return path

    def save_csv(self, summary: dict) -> str:
        path = self._filename("csv")
        rows = [
            ["Metric", "Value"],
            ["Duration (s)", summary["duration_seconds"]],
            ["Total Blinks", summary["total_blinks"]],
            ["Avg Blinks/Min", summary["avg_blinks_per_min"]],
            ["Avg EAR", summary["avg_ear"]],
            ["Generated At", datetime.now().isoformat()],
        ]
        if summary["minute_rates"]:
            rows.append([])
            rows.append(["Minute", "Blink Rate"])
            for i, r in enumerate(summary["minute_rates"], 1):
                rows.append([i, r])
        with open(path, "w", newline="") as f:
            csv.writer(f).writerows(rows)
        return path

    def save_txt(self, summary: dict) -> str:
        path = self._filename("txt")
        lines = [
            "=" * 40,
            "     BLINK MONITOR REPORT",
            "=" * 40,
            f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration  : {summary['duration_seconds']}s",
            f"Total Blinks     : {summary['total_blinks']}",
            f"Avg Blinks/Min   : {summary['avg_blinks_per_min']}",
            f"Avg EAR          : {summary['avg_ear']}",
            "",
            "Per-Minute Breakdown:",
        ]
        for i, r in enumerate(summary["minute_rates"], 1):
            status = "Normal" if 12 <= r <= 20 else ("Low" if r < 12 else "High")
            lines.append(f"  Minute {i:02d}: {r:3d} blinks  [{status}]")
        lines.append("=" * 40)
        with open(path, "w") as f:
            f.write("\n".join(lines))
        return path
