"""
send_to_telegram.py — uploads every .mp4 in a folder to a Telegram chat.

Reads BOT_TOKEN and CHAT_ID from environment variables (set as GitHub
Actions secrets / workflow inputs so the token is never committed to
the repo).
"""
import os
import sys
import glob
import requests

def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "out"
    token = os.environ["BOT_TOKEN"]
    chat_id = os.environ["CHAT_ID"]

    videos = sorted(glob.glob(os.path.join(folder, "*.mp4")))
    if not videos:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": "Koi video nahi bana — kuch गलत hua. Logs check karein."},
        )
        sys.exit(1)

    for v in videos:
        with open(v, "rb") as f:
            r = requests.post(
                f"https://api.telegram.org/bot{token}/sendVideo",
                data={"chat_id": chat_id, "caption": os.path.basename(v)},
                files={"video": f},
                timeout=300,
            )
        print(v, "->", r.status_code, r.text[:200])

if __name__ == "__main__":
    main()
