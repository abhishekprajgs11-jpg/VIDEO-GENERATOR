"""
run_cli.py — Headless runner for v5_engine.py (TXT2SHORTS V5)

Usage:
    python run_cli.py <input.txt or .html> <output_dir> [options]

Options (all optional, sensible defaults):
    --qpv N          questions per video          (default 5)
    --timer N        seconds per question timer   (default 10)
    --width N        video width                  (default 1080)
    --height N       video height                 (default 1920)
    --voice-idx N    SAPI voice index              (default 0)
    --speed F        playback speed 0.5-2.0        (default 1.0)
    --show-expl      include explanation slide     (flag)
    --workers N      parallel video workers        (default 2)

This is a 1:1 headless version of what the V5 GUI's "GO" button does —
same functions (parse_input_file, _process_question_group), just called
directly with no window / no manual click, so it can run unattended on
a CI runner (e.g. GitHub Actions windows-latest).

IMPORTANT: This must run on WINDOWS — v5_engine.py uses win32com (SAPI
text-to-speech) and ctypes.windll, which only exist on Windows.
"""

import argparse
import math
import os
import sys
import tempfile
import time
import concurrent.futures

import v5_engine as V5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_file")
    ap.add_argument("output_dir")
    ap.add_argument("--qpv", type=int, default=5)
    ap.add_argument("--timer", type=int, default=10)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--voice-idx", type=int, default=0)
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--show-expl", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    def log(msg):
        print(msg, flush=True)

    def cancelled():
        return False

    log(f"[CLI] Parsing: {args.input_file}")
    questions = V5.parse_input_file(args.input_file)
    if not questions:
        log("[CLI] ERROR: no questions parsed. Check the input file format.")
        sys.exit(1)
    log(f"[CLI] Parsed {len(questions)} questions.")

    portrait = args.height > args.width
    sapi_rate = max(-10, min(10, int((args.speed - 1.0) * 5)))

    n_groups = math.ceil(len(questions) / args.qpv)
    groups = [
        list(range(i * args.qpv, min((i + 1) * args.qpv, len(questions))))
        for i in range(n_groups)
    ]
    log(f"[CLI] {len(questions)} questions -> {n_groups} video(s), "
        f"{args.qpv} questions/video, {args.width}x{args.height}")

    ffmpeg_exe = V5._find_ffmpeg()
    log(f"[CLI] FFmpeg: {ffmpeg_exe}")

    with tempfile.TemporaryDirectory() as td_main:
        tick_wav = os.path.join(td_main, "tick_master.wav")
        V5.generate_ticking_audio(tick_wav, duration_sec=float(args.timer) + 1.0)

        start_t = time.time()
        ok_count = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(
                    V5._process_question_group,
                    gi, grp, questions,
                    args.width, args.height, portrait,
                    args.voice_idx, sapi_rate,
                    args.output_dir, tick_wav, ffmpeg_exe,
                    args.show_expl, args.timer,
                    log, cancelled,
                ): gi
                for gi, grp in enumerate(groups)
            }
            for fut in concurrent.futures.as_completed(futures):
                gi = futures[fut]
                try:
                    out_path, q_nums, elapsed = fut.result()
                    if out_path:
                        ok_count += 1
                        log(f"[CLI] Group {gi} done -> {out_path} ({elapsed:.1f}s)")
                    else:
                        log(f"[CLI] Group {gi} FAILED (questions {q_nums})")
                except Exception as e:
                    log(f"[CLI] Group {gi} EXCEPTION: {e}")

        total = time.time() - start_t
        log(f"[CLI] Done: {ok_count}/{n_groups} videos in {total:.1f}s -> {args.output_dir}")

    if ok_count == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
