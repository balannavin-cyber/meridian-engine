import json
from pathlib import Path
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates


INPUT_FILE = Path(r"C:\GammaEnginePython\data\ad_points_current_session.jsonl")
OUTPUT_FILE = Path(r"C:\GammaEnginePython\ad_session_chart.png")


def parse_ts(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def main() -> None:
    if not INPUT_FILE.exists():
        print(f"ERROR: File not found: {INPUT_FILE}")
        return

    times = []
    net_ad = []

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Skipping bad JSON on line {line_no}: {e}")
                continue

            ts_raw = row.get("ts") or row.get("timestamp")
            advances = row.get("advances")
            declines = row.get("declines")

            if ts_raw is None or advances is None or declines is None:
                print(f"Skipping line {line_no}: missing ts/timestamp or advances/declines")
                continue

            try:
                ts = parse_ts(str(ts_raw))
                adv = int(advances)
                dec = int(declines)
            except Exception as e:
                print(f"Skipping line {line_no}: {e}")
                continue

            times.append(ts)
            net_ad.append(adv - dec)

    if not times:
        print("ERROR: No valid data points found in the JSONL file.")
        return

    plt.figure(figsize=(12, 6))
    plt.plot(times, net_ad)
    plt.title("Current Session Net A/D")
    plt.xlabel("Time")
    plt.ylabel("Net A/D (Advances - Declines)")
    plt.grid(True)

    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    plt.xticks(rotation=45)
    plt.tight_layout()

    plt.savefig(OUTPUT_FILE, dpi=150)
    plt.close()

    print(f"Chart saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()