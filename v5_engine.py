"""
TXT 2 SHORTS V5 — PREMIUM CINEMATIC ENGINE
==========================================
Built on V4's True Selenium-Free Pillow Renderer.

NEW IN V5:
  ✦ 55+ Premium Glowing Themes  (Cyber Blue, Neon Cyan, Emerald, Royal Purple,
    Crimson, Gold, Orange Fire, Ice Blue, Holographic, Glassmorphism, Matrix,
    Synthwave, Tron, Aurora, Quantum, Deep Ocean, Cosmic, Luxury Gold, ...)
  ✦ Random Cinematic Transition Engine (15 premium transitions)
  ✦ Dynamic Content Sizing — cards auto-resize to content
  ✦ Breathing Glow Animations — borders & shadows softly pulse
  ✦ Premium Intro + Outro Screens — cinematic, emoji-rich, gradient
  ✦ Video Uniqueness Engine — no two exports look identical

REQUIREMENTS:
  pip install pillow pywin32 static-ffmpeg numpy
"""

import os, re, time, wave, math, shutil, tempfile
import threading, subprocess, array, random
import concurrent.futures
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ctypes
from ctypes import wintypes

# ── Optional / guarded imports ─────────────────────────────────────────────────
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import pythoncom
    HAS_PYTHONCOM = True
except ImportError:
    HAS_PYTHONCOM = False


# ─── Windows Drag & Drop ──────────────────────────────────────────────────────
WM_DROPFILES = 0x0233
GWL_WNDPROC  = -4
shell32 = ctypes.windll.shell32
user32  = ctypes.windll.user32
DragAcceptFiles = shell32.DragAcceptFiles
DragQueryFileW  = shell32.DragQueryFileW
DragFinish      = shell32.DragFinish
DragQueryFileW.argtypes = [wintypes.HANDLE, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint]
DragQueryFileW.restype  = ctypes.c_uint

if ctypes.sizeof(ctypes.c_void_p) == 8:
    SetWindowLong  = user32.SetWindowLongPtrW
    SetWindowLong.argtypes  = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    SetWindowLong.restype   = ctypes.c_void_p
    CallWindowProc = user32.CallWindowProcW
    CallWindowProc.argtypes = [ctypes.c_void_p, wintypes.HWND, ctypes.c_uint,
                               wintypes.WPARAM, wintypes.LPARAM]
    CallWindowProc.restype  = ctypes.c_void_p
else:
    SetWindowLong  = user32.SetWindowLongW
    SetWindowLong.argtypes  = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    SetWindowLong.restype   = ctypes.c_long
    CallWindowProc = user32.CallWindowProcW
    CallWindowProc.argtypes = [ctypes.c_long, wintypes.HWND, ctypes.c_uint,
                               wintypes.WPARAM, wintypes.LPARAM]
    CallWindowProc.restype  = ctypes.c_long

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_void_p,
                             wintypes.HWND, ctypes.c_uint,
                             wintypes.WPARAM, wintypes.LPARAM)


class WinDropTarget:
    def __init__(self, widget, callback):
        self.widget = widget; self.callback = callback
        self.hwnd = widget.winfo_id()
        DragAcceptFiles(self.hwnd, True)
        self.new_wnd_proc = WNDPROC(self.wnd_proc)
        self.old_wnd_proc = SetWindowLong(self.hwnd, GWL_WNDPROC, self.new_wnd_proc)
        self.widget.bind("<Destroy>", self.on_destroy)

    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_DROPFILES:
            hDrop = wparam
            num   = DragQueryFileW(hDrop, 0xFFFFFFFF, None, 0)
            files = []
            for i in range(num):
                length = DragQueryFileW(hDrop, i, None, 0)
                buf    = ctypes.create_unicode_buffer(length + 1)
                DragQueryFileW(hDrop, i, buf, length + 1)
                files.append(buf.value)
            DragFinish(hDrop)
            if files:
                self.widget.after(10, self.callback, files[0])
            return 0
        return CallWindowProc(self.old_wnd_proc, hwnd, msg, wparam, lparam)

    def on_destroy(self, event):
        if hasattr(self, 'old_wnd_proc') and self.old_wnd_proc:
            SetWindowLong(self.hwnd, GWL_WNDPROC, self.old_wnd_proc)
            self.old_wnd_proc = None


# ─── Audio Helpers ────────────────────────────────────────────────────────────
CANONICAL_RATE     = 44100
CANONICAL_CHANNELS = 1
CANONICAL_WIDTH    = 2


def generate_ticking_audio(filepath, duration_sec=10.0, sample_rate=CANONICAL_RATE):
    n = int(sample_rate * duration_sec)
    if HAS_NUMPY:
        t    = np.arange(n, dtype=np.float64) / sample_rate
        sf   = t - np.floor(t)
        beat = (np.floor(t).astype(np.int32) % 2 == 0).astype(np.float64)
        freq = 1500.0 * beat + 1100.0 * (1.0 - beat)
        env  = np.exp(-sf * 110.0) * (sf < 0.048)
        tick = (0.80 * np.sin(2.0 * np.pi * freq * t) +
                0.55 * np.sin(       np.pi * freq * t)) * env
        drone = 0.07 * np.sin(2.0 * np.pi * 120.0 * t)
        raw   = (np.clip(tick + drone, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
    else:
        buf = array.array('h', [0] * n)
        for i in range(n):
            t_  = i / sample_rate
            sf_ = t_ - int(t_)
            tick_ = 0.0
            if sf_ < 0.048:
                freq_ = 1500.0 if int(t_) % 2 == 0 else 1100.0
                env_  = math.exp(-sf_ * 110.0)
                tick_ = (0.80 * math.sin(2*math.pi*freq_*t_) +
                         0.55 * math.sin(math.pi*freq_*t_)) * env_
            drone_ = 0.07 * math.sin(2*math.pi*120.0*t_)
            buf[i] = int(max(-1.0, min(1.0, tick_+drone_)) * 32767)
        raw = buf.tobytes()
    with wave.open(filepath, 'w') as wf:
        wf.setnchannels(CANONICAL_CHANNELS)
        wf.setsampwidth(CANONICAL_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(raw)


def generate_silent_wav(filepath, duration_sec=1.0, sample_rate=CANONICAL_RATE):
    n = int(sample_rate * duration_sec)
    with wave.open(filepath, 'w') as wf:
        wf.setnchannels(CANONICAL_CHANNELS)
        wf.setsampwidth(CANONICAL_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(b'\x00\x00' * n)


def wav_duration(filepath, minimum=1.0):
    try:
        with wave.open(filepath, 'r') as wf:
            return max(minimum, wf.getnframes() / float(wf.getframerate()))
    except Exception:
        return minimum


def _normalize_wav(src_path, dst_path,
                   out_rate=CANONICAL_RATE,
                   out_channels=CANONICAL_CHANNELS,
                   out_width=CANONICAL_WIDTH):
    try:
        with wave.open(src_path, 'r') as wf:
            in_channels = wf.getnchannels()
            in_width    = wf.getsampwidth()
            in_rate     = wf.getframerate()
            n_frames    = wf.getnframes()
            raw_bytes   = wf.readframes(n_frames)

        total_samples = n_frames * in_channels
        if in_width == 1:
            samples = array.array('b', raw_bytes)
            samples = array.array('h', [s << 8 for s in samples])
        elif in_width == 2:
            samples = array.array('h')
            samples.frombytes(raw_bytes)
        elif in_width == 4:
            samples32 = array.array('i')
            samples32.frombytes(raw_bytes)
            samples = array.array('h', [s >> 16 for s in samples32])
        else:
            samples = array.array('h', [0] * total_samples)

        if in_channels > 1:
            mono = array.array('h', [0] * n_frames)
            for i in range(n_frames):
                s = sum(samples[i*in_channels + c] for c in range(in_channels))
                mono[i] = max(-32768, min(32767, s // in_channels))
            samples = mono

        if in_rate != out_rate:
            ratio      = in_rate / out_rate
            out_frames = int(n_frames / ratio)
            resampled  = array.array('h', [0] * out_frames)
            for i in range(out_frames):
                src_f = i * ratio
                src_i = int(src_f)
                frac  = src_f - src_i
                s0    = samples[min(src_i,     n_frames-1)]
                s1    = samples[min(src_i + 1, n_frames-1)]
                resampled[i] = int(s0 + frac * (s1 - s0))
            samples = resampled

        with wave.open(dst_path, 'w') as wf:
            wf.setnchannels(out_channels)
            wf.setsampwidth(out_width)
            wf.setframerate(out_rate)
            wf.writeframes(samples.tobytes())

    except Exception:
        shutil.copy2(src_path, dst_path)


# ─── Text Helpers ─────────────────────────────────────────────────────────────
def clean_text(text):
    if not text: return ""
    t = re.sub(r'www\.\S+', '', text, flags=re.IGNORECASE)
    t = re.sub(r'@\S+', '', t)
    t = re.sub(r'https?://\S+', '', t)
    t = re.sub(r'pakexampoint[^\n]*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'PowerUp\s+Prelims[^\n]*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'No part of this document[^\n]*', '', t, flags=re.IGNORECASE)
    t = re.sub(r'[ \t]+', ' ', t).strip()
    return t


# ─── Parser ───────────────────────────────────────────────────────────────────
def parse_input_file(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    raw_blocks = re.split(r'(?=\bQ\d+[\.\s\:\)])', content)
    questions  = []

    for block in raw_blocks:
        block = block.strip()
        if not block: continue
        hm = re.match(r'^Q(\d+)[\.\s\:\)]\s*(.*)', block, re.DOTALL)
        if not hm: continue
        q_num = int(hm[1])
        rest  = hm[2].strip()

        em = re.search(r'\n\s*(?:Ex|Explanation)\s*:\s*(.*)', rest,
                       re.DOTALL | re.IGNORECASE)
        if em:
            q_and_opts  = rest[:em.start()].strip()
            explanation = em.group(1).strip()
        else:
            q_and_opts  = rest
            explanation = ""

        explanation = clean_text(explanation)
        lines = [l.strip() for l in q_and_opts.split('\n') if l.strip()]
        lines = [l for l in lines if l not in ['😂','😊','👍','🙏']]

        opts, correct_idx = [], 0
        ans_m    = re.search(r'\bAnsw\s*er\s*:\s*([a-d])\b', explanation, re.IGNORECASE)
        explicit = ord(ans_m.group(1).lower()) - ord('a') if ans_m else -1

        if len(lines) >= 5:
            possible = lines[-4:]; q_lines = lines[:-4]
            for i, ol in enumerate(possible):
                correct = ('✅' in ol) or (explicit == i)
                clean_o = ol.replace('✅', '').strip()
                clean_o = re.sub(r'^(?:[a-dA-D][\.\)]|[1-4][\.\)])\s*', '',
                                 clean_o).strip()
                opts.append(clean_text(clean_o))
                if correct: correct_idx = i
        else:
            q_lines = lines
            opts    = ["Option A", "Option B", "Option C", "Option D"]

        q_text = clean_text("\n".join(q_lines).strip())
        first  = q_lines[0] if q_lines else f"Question {q_num}"
        title  = first[:50] + "..." if len(first) > 50 else first

        questions.append({
            "number": q_num, "title": title,
            "questionText": q_text, "options": opts,
            "correctIndex": correct_idx, "explanation": explanation
        })

    return questions


# ─── 55+ PREMIUM GLOWING THEMES ───────────────────────────────────────────────
# Each theme has:
#   bg/bg2: gradient background colors
#   card: card fill color
#   border: crisp border color
#   glow: glow halo color (usually = border or accent)
#   title: primary text color
#   badge_bg/badge_fg: badge pill colors
#   accent: highlight/secondary color
#   correct: correct-answer highlight color
#   gradient: 'vertical'|'radial'|'diagonal'|'solid'
#   glow_intensity: 0.5–1.0
#   particle: dot-grid color
THEMES = [
    # ── CYBER / TECH ──────────────────────────────────────────────────────────
    {   # 0 Cyber Blue
        "name":"Cyber Blue",
        "bg":"#06101e","bg2":"#091426","card":"#0d1e30",
        "border":"#00D8FF","glow":"#00D8FF","title":"#00EEFF",
        "badge_bg":"#00D8FF","badge_fg":"#06101e",
        "accent":"#FFD700","correct":"#00FF88",
        "gradient":"diagonal","glow_intensity":0.90,"particle":"#00D8FF",
    },
    {   # 1 Neon Cyan
        "name":"Neon Cyan",
        "bg":"#040c10","bg2":"#071318","card":"#0a1a20",
        "border":"#00FFF0","glow":"#00FFF0","title":"#00FFF0",
        "badge_bg":"#00FFF0","badge_fg":"#040c10",
        "accent":"#FF6B35","correct":"#00FF88",
        "gradient":"radial","glow_intensity":1.0,"particle":"#00E5D4",
    },
    {   # 2 Matrix
        "name":"Matrix",
        "bg":"#010d05","bg2":"#011a08","card":"#031a09",
        "border":"#00FF41","glow":"#00FF41","title":"#00FF41",
        "badge_bg":"#00FF41","badge_fg":"#010d05",
        "accent":"#39FF14","correct":"#00FF41",
        "gradient":"vertical","glow_intensity":0.95,"particle":"#00FF41",
    },
    {   # 3 Tron Blue
        "name":"Tron",
        "bg":"#03080f","bg2":"#040d18","card":"#081220",
        "border":"#3BFCFD","glow":"#3BFCFD","title":"#7FFFFF",
        "badge_bg":"#3BFCFD","badge_fg":"#03080f",
        "accent":"#FF8C00","correct":"#00FF88",
        "gradient":"diagonal","glow_intensity":0.85,"particle":"#3BFCFD",
    },
    {   # 4 Quantum
        "name":"Quantum",
        "bg":"#050915","bg2":"#080e20","card":"#0c1630",
        "border":"#4488FF","glow":"#4488FF","title":"#88BBFF",
        "badge_bg":"#4488FF","badge_fg":"#050915",
        "accent":"#FF44AA","correct":"#44FF88",
        "gradient":"radial","glow_intensity":0.88,"particle":"#4488FF",
    },
    {   # 5 Electric Purple
        "name":"Electric Purple",
        "bg":"#0b0518","bg2":"#120825","card":"#180a30",
        "border":"#BF5FFF","glow":"#BF5FFF","title":"#D580FF",
        "badge_bg":"#BF5FFF","badge_fg":"#0b0518",
        "accent":"#00D8FF","correct":"#00FF88",
        "gradient":"vertical","glow_intensity":0.92,"particle":"#9040CC",
    },
    {   # 6 Hacker Green
        "name":"Hacker",
        "bg":"#010a04","bg2":"#010e06","card":"#021508",
        "border":"#39FF14","glow":"#39FF14","title":"#7FFF00",
        "badge_bg":"#39FF14","badge_fg":"#010a04",
        "accent":"#00FFCC","correct":"#39FF14",
        "gradient":"solid","glow_intensity":0.95,"particle":"#39FF14",
    },
    {   # 7 Synthwave
        "name":"Synthwave",
        "bg":"#120024","bg2":"#200040","card":"#1e003a",
        "border":"#FF2D78","glow":"#FF2D78","title":"#FF88CC",
        "badge_bg":"#FF2D78","badge_fg":"#120024",
        "accent":"#00F0FF","correct":"#00FF88",
        "gradient":"radial","glow_intensity":0.93,"particle":"#CC0066",
    },
    # ── WARM / FIRE ───────────────────────────────────────────────────────────
    {   # 8 Orange Fire
        "name":"Orange Fire",
        "bg":"#120500","bg2":"#1f0900","card":"#1e0a00",
        "border":"#FF6B00","glow":"#FF6B00","title":"#FF9A3C",
        "badge_bg":"#FF6B00","badge_fg":"#120500",
        "accent":"#FFD700","correct":"#00FF88",
        "gradient":"vertical","glow_intensity":0.90,"particle":"#FF4400",
    },
    {   # 9 Crimson
        "name":"Crimson",
        "bg":"#140006","bg2":"#200009","card":"#220008",
        "border":"#FF1744","glow":"#FF1744","title":"#FF6680",
        "badge_bg":"#FF1744","badge_fg":"#140006",
        "accent":"#FFD700","correct":"#00FF88",
        "gradient":"diagonal","glow_intensity":0.88,"particle":"#CC0022",
    },
    {   # 10 Luxury Gold
        "name":"Luxury Gold",
        "bg":"#0d0900","bg2":"#180e00","card":"#1a1000",
        "border":"#FFD700","glow":"#FFD700","title":"#FFE566",
        "badge_bg":"#FFD700","badge_fg":"#0d0900",
        "accent":"#FF8C00","correct":"#00FF88",
        "gradient":"vertical","glow_intensity":0.95,"particle":"#CC9900",
    },
    {   # 11 Magma
        "name":"Magma",
        "bg":"#0f0300","bg2":"#1a0500","card":"#1c0600",
        "border":"#FF3D00","glow":"#FF3D00","title":"#FF6333",
        "badge_bg":"#FF3D00","badge_fg":"#0f0300",
        "accent":"#FFB300","correct":"#00FF88",
        "gradient":"radial","glow_intensity":0.92,"particle":"#CC2800",
    },
    {   # 12 Solar
        "name":"Solar",
        "bg":"#100a00","bg2":"#1c1100","card":"#1e1200",
        "border":"#FFC107","glow":"#FFC107","title":"#FFD740",
        "badge_bg":"#FFC107","badge_fg":"#100a00",
        "accent":"#FF5722","correct":"#00FF88",
        "gradient":"diagonal","glow_intensity":0.85,"particle":"#FFA000",
    },
    {   # 13 Neon Pink
        "name":"Neon Pink",
        "bg":"#14000a","bg2":"#200012","card":"#22001a",
        "border":"#FF0080","glow":"#FF0080","title":"#FF66B2",
        "badge_bg":"#FF0080","badge_fg":"#14000a",
        "accent":"#00F0FF","correct":"#00FF88",
        "gradient":"radial","glow_intensity":0.93,"particle":"#CC0066",
    },
    {   # 14 Rose Gold
        "name":"Rose Gold",
        "bg":"#130008","bg2":"#1e000e","card":"#200010",
        "border":"#FF6B9D","glow":"#FF6B9D","title":"#FFB3D1",
        "badge_bg":"#FF6B9D","badge_fg":"#130008",
        "accent":"#FFD700","correct":"#00FF88",
        "gradient":"vertical","glow_intensity":0.80,"particle":"#CC4477",
    },
    # ── COOL / ICE ────────────────────────────────────────────────────────────
    {   # 15 Ice Blue
        "name":"Ice Blue",
        "bg":"#050d18","bg2":"#081525","card":"#0c1c30",
        "border":"#7EC8E3","glow":"#7EC8E3","title":"#B3E0F0",
        "badge_bg":"#7EC8E3","badge_fg":"#050d18",
        "accent":"#E0F7FF","correct":"#00FF88",
        "gradient":"vertical","glow_intensity":0.75,"particle":"#5AABC4",
    },
    {   # 16 Deep Ocean
        "name":"Deep Ocean",
        "bg":"#020c1a","bg2":"#041528","card":"#061e35",
        "border":"#0088CC","glow":"#00AAFF","title":"#44CCFF",
        "badge_bg":"#0088CC","badge_fg":"#020c1a",
        "accent":"#00F0C8","correct":"#00FF88",
        "gradient":"radial","glow_intensity":0.87,"particle":"#005588",
    },
    {   # 17 Sapphire
        "name":"Sapphire",
        "bg":"#040b1c","bg2":"#061428","card":"#091b35",
        "border":"#1E90FF","glow":"#1E90FF","title":"#6AB4FF",
        "badge_bg":"#1E90FF","badge_fg":"#040b1c",
        "accent":"#00F0FF","correct":"#00FF88",
        "gradient":"diagonal","glow_intensity":0.90,"particle":"#1166CC",
    },
    {   # 18 Arctic
        "name":"Arctic",
        "bg":"#06101c","bg2":"#0a1828","card":"#0f2035",
        "border":"#A8D8EA","glow":"#A8D8EA","title":"#D4EEF7",
        "badge_bg":"#A8D8EA","badge_fg":"#06101c",
        "accent":"#FFD700","correct":"#00FF88",
        "gradient":"vertical","glow_intensity":0.70,"particle":"#80B8CC",
    },
    {   # 19 Storm
        "name":"Storm",
        "bg":"#080c14","bg2":"#0d1220","card":"#121828",
        "border":"#5B8CFF","glow":"#5B8CFF","title":"#8CB0FF",
        "badge_bg":"#5B8CFF","badge_fg":"#080c14",
        "accent":"#FF6B35","correct":"#00FF88",
        "gradient":"radial","glow_intensity":0.85,"particle":"#3355CC",
    },
    # ── NATURE / ORGANIC ──────────────────────────────────────────────────────
    {   # 20 Emerald
        "name":"Emerald",
        "bg":"#020e07","bg2":"#031608","card":"#051c0c",
        "border":"#00E676","glow":"#00E676","title":"#66FF99",
        "badge_bg":"#00E676","badge_fg":"#020e07",
        "accent":"#FFEB3B","correct":"#00E676",
        "gradient":"vertical","glow_intensity":0.90,"particle":"#00BB55",
    },
    {   # 21 Forest
        "name":"Forest",
        "bg":"#041208","bg2":"#071c0c","card":"#092010",
        "border":"#4CAF50","glow":"#4CAF50","title":"#A5D6A7",
        "badge_bg":"#4CAF50","badge_fg":"#041208",
        "accent":"#CDDC39","correct":"#4CAF50",
        "gradient":"diagonal","glow_intensity":0.80,"particle":"#2E7D32",
    },
    {   # 22 Bioluminescent
        "name":"Bioluminescent",
        "bg":"#020a08","bg2":"#031410","card":"#051c15",
        "border":"#00FFCC","glow":"#00FFCC","title":"#66FFEE",
        "badge_bg":"#00FFCC","badge_fg":"#020a08",
        "accent":"#80FF00","correct":"#00FFCC",
        "gradient":"radial","glow_intensity":1.0,"particle":"#00CC99",
    },
    {   # 23 Jade
        "name":"Jade",
        "bg":"#031410","bg2":"#051e18","card":"#072620",
        "border":"#00BFA5","glow":"#00BFA5","title":"#66D9C8",
        "badge_bg":"#00BFA5","badge_fg":"#031410",
        "accent":"#FFCA28","correct":"#00BFA5",
        "gradient":"vertical","glow_intensity":0.82,"particle":"#008875",
    },
    {   # 24 Mint
        "name":"Mint",
        "bg":"#031412","bg2":"#061e1a","card":"#082422",
        "border":"#00E5CC","glow":"#00E5CC","title":"#88FFF0",
        "badge_bg":"#00E5CC","badge_fg":"#031412",
        "accent":"#FF8A80","correct":"#00E5CC",
        "gradient":"diagonal","glow_intensity":0.78,"particle":"#00B8A0",
    },
    # ── PREMIUM / LUXURY ──────────────────────────────────────────────────────
    {   # 25 Royal Purple
        "name":"Royal Purple",
        "bg":"#0d0520","bg2":"#170830","card":"#200a40",
        "border":"#9C27B0","glow":"#CE93D8","title":"#E1BEE7",
        "badge_bg":"#9C27B0","badge_fg":"#0d0520",
        "accent":"#FFD700","correct":"#00FF88",
        "gradient":"radial","glow_intensity":0.88,"particle":"#6A1B9A",
    },
    {   # 26 Holographic
        "name":"Holographic",
        "bg":"#08080f","bg2":"#12101a","card":"#1a1825",
        "border":"#CC88FF","glow":"#FF88CC","title":"#FFBBEE",
        "badge_bg":"#CC88FF","badge_fg":"#08080f",
        "accent":"#88FFFF","correct":"#88FF88",
        "gradient":"diagonal","glow_intensity":0.95,"particle":"#9944CC",
    },
    {   # 27 Glassmorphism
        "name":"Glassmorphism",
        "bg":"#0a1628","bg2":"#112235","card":"#162a40",
        "border":"#88CCFF","glow":"#AADDFF","title":"#CCEEFF",
        "badge_bg":"#3388CC","badge_fg":"#0a1628",
        "accent":"#FFD700","correct":"#00FF88",
        "gradient":"diagonal","glow_intensity":0.72,"particle":"#4488AA",
    },
    {   # 28 Velvet
        "name":"Velvet",
        "bg":"#100018","bg2":"#1a0028","card":"#240035",
        "border":"#AA44FF","glow":"#CC66FF","title":"#EEB0FF",
        "badge_bg":"#AA44FF","badge_fg":"#100018",
        "accent":"#FF88CC","correct":"#00FF88",
        "gradient":"vertical","glow_intensity":0.85,"particle":"#7722BB",
    },
    {   # 29 Diamond
        "name":"Diamond",
        "bg":"#07101c","bg2":"#0d1a28","card":"#122230",
        "border":"#B0E0FF","glow":"#D0EEFF","title":"#E8F4FF",
        "badge_bg":"#7BBCDD","badge_fg":"#07101c",
        "accent":"#FFD700","correct":"#00FF88",
        "gradient":"radial","glow_intensity":0.80,"particle":"#4488AA",
    },
    # ── ARTISTIC / SPECIAL ────────────────────────────────────────────────────
    {   # 30 Aurora
        "name":"Aurora",
        "bg":"#030e10","bg2":"#051820","card":"#082028",
        "border":"#00FFAA","glow":"#00FFAA","title":"#88FFD4",
        "badge_bg":"#00FFAA","badge_fg":"#030e10",
        "accent":"#AA44FF","correct":"#00FFAA",
        "gradient":"diagonal","glow_intensity":0.93,"particle":"#00CC88",
    },
    {   # 31 Cosmic
        "name":"Cosmic",
        "bg":"#060410","bg2":"#0c0820","card":"#120c30",
        "border":"#8844FF","glow":"#AA66FF","title":"#CC99FF",
        "badge_bg":"#6622CC","badge_fg":"#060410",
        "accent":"#FF44AA","correct":"#00FF88",
        "gradient":"radial","glow_intensity":0.90,"particle":"#5511AA",
    },
    {   # 32 Galaxy
        "name":"Galaxy",
        "bg":"#050308","bg2":"#0c0715","card":"#130b20",
        "border":"#7755EE","glow":"#9977FF","title":"#BBAAFF",
        "badge_bg":"#5533BB","badge_fg":"#050308",
        "accent":"#FF66CC","correct":"#00FF88",
        "gradient":"radial","glow_intensity":0.88,"particle":"#4422AA",
    },
    {   # 33 Neon Tokyo
        "name":"Neon Tokyo",
        "bg":"#0a0010","bg2":"#14001a","card":"#1a0022",
        "border":"#FF00FF","glow":"#FF44FF","title":"#FF99FF",
        "badge_bg":"#CC00CC","badge_fg":"#0a0010",
        "accent":"#00FFFF","correct":"#00FF88",
        "gradient":"vertical","glow_intensity":0.95,"particle":"#AA00AA",
    },
    {   # 34 Sunrise
        "name":"Sunrise",
        "bg":"#0e0800","bg2":"#200e00","card":"#1e1200",
        "border":"#FF7043","glow":"#FF7043","title":"#FFAB91",
        "badge_bg":"#FF7043","badge_fg":"#0e0800",
        "accent":"#FFC107","correct":"#00FF88",
        "gradient":"vertical","glow_intensity":0.82,"particle":"#CC4400",
    },
    {   # 35 Indigo Night
        "name":"Indigo Night",
        "bg":"#080a20","bg2":"#0d0f30","card":"#121540",
        "border":"#5C6BC0","glow":"#7986CB","title":"#9FA8DA",
        "badge_bg":"#3F51B5","badge_fg":"#080a20",
        "accent":"#FF4081","correct":"#00FF88",
        "gradient":"diagonal","glow_intensity":0.82,"particle":"#283593",
    },
    {   # 36 Cyber Green V2
        "name":"Cyber Green",
        "bg":"#040d06","bg2":"#071508","card":"#0a1e0c",
        "border":"#00FF66","glow":"#00FF66","title":"#66FFA0",
        "badge_bg":"#00CC44","badge_fg":"#040d06",
        "accent":"#FFFF00","correct":"#00FF66",
        "gradient":"diagonal","glow_intensity":0.92,"particle":"#00BB33",
    },
    {   # 37 Blood Moon
        "name":"Blood Moon",
        "bg":"#150004","bg2":"#220006","card":"#2a0008",
        "border":"#CC0000","glow":"#FF2222","title":"#FF8888",
        "badge_bg":"#990000","badge_fg":"#150004",
        "accent":"#FF8800","correct":"#FF4444",
        "gradient":"radial","glow_intensity":0.90,"particle":"#880000",
    },
    {   # 38 Cyber Orange
        "name":"Cyber Orange",
        "bg":"#0f0600","bg2":"#190a00","card":"#1e0d00",
        "border":"#FF8C00","glow":"#FF8C00","title":"#FFBB55",
        "badge_bg":"#E65C00","badge_fg":"#0f0600",
        "accent":"#00D4FF","correct":"#00FF88",
        "gradient":"vertical","glow_intensity":0.88,"particle":"#CC5500",
    },
    {   # 39 Deep Violet
        "name":"Deep Violet",
        "bg":"#0c0520","bg2":"#160830","card":"#1e0c40",
        "border":"#7B1FA2","glow":"#AB47BC","title":"#CE93D8",
        "badge_bg":"#6A1B9A","badge_fg":"#0c0520",
        "accent":"#FF80AB","correct":"#00FF88",
        "gradient":"radial","glow_intensity":0.85,"particle":"#4A0072",
    },
    {   # 40 Electric Lime
        "name":"Electric Lime",
        "bg":"#080d00","bg2":"#0e1600","card":"#121c00",
        "border":"#AAFF00","glow":"#CCFF33","title":"#DDFF77",
        "badge_bg":"#88CC00","badge_fg":"#080d00",
        "accent":"#FF4400","correct":"#AAFF00",
        "gradient":"diagonal","glow_intensity":0.90,"particle":"#77AA00",
    },
    {   # 41 Ocean Glow
        "name":"Ocean Glow",
        "bg":"#030c18","bg2":"#051525","card":"#081e35",
        "border":"#00BCD4","glow":"#00E5FF","title":"#80DEEA",
        "badge_bg":"#0097A7","badge_fg":"#030c18",
        "accent":"#FF6D00","correct":"#00FF88",
        "gradient":"vertical","glow_intensity":0.87,"particle":"#00688B",
    },
    {   # 42 Raspberry
        "name":"Raspberry",
        "bg":"#160008","bg2":"#22000e","card":"#2a0014",
        "border":"#E91E63","glow":"#F48FB1","title":"#FCE4EC",
        "badge_bg":"#C2185B","badge_fg":"#160008",
        "accent":"#FFD740","correct":"#00FF88",
        "gradient":"diagonal","glow_intensity":0.87,"particle":"#880033",
    },
    {   # 43 Cyber Amber
        "name":"Cyber Amber",
        "bg":"#0f0900","bg2":"#1a1000","card":"#1e1500",
        "border":"#FFAB00","glow":"#FFAB00","title":"#FFD54F",
        "badge_bg":"#FF8F00","badge_fg":"#0f0900",
        "accent":"#00E5FF","correct":"#00FF88",
        "gradient":"vertical","glow_intensity":0.88,"particle":"#CC8800",
    },
    {   # 44 Plasma
        "name":"Plasma",
        "bg":"#0a0518","bg2":"#140a28","card":"#1a1035",
        "border":"#FF44BB","glow":"#FF44BB","title":"#FF99DD",
        "badge_bg":"#CC1188","badge_fg":"#0a0518",
        "accent":"#44FFDD","correct":"#00FF88",
        "gradient":"radial","glow_intensity":0.93,"particle":"#AA0077",
    },
    {   # 45 Arctic Blue
        "name":"Arctic Blue",
        "bg":"#050e18","bg2":"#081520","card":"#0c1c2c",
        "border":"#64B5F6","glow":"#90CAF9","title":"#BBDEFB",
        "badge_bg":"#1976D2","badge_fg":"#050e18",
        "accent":"#FF8A65","correct":"#00FF88",
        "gradient":"vertical","glow_intensity":0.78,"particle":"#1565C0",
    },
    {   # 46 Phantom
        "name":"Phantom",
        "bg":"#060610","bg2":"#0a0a18","card":"#0f0f22",
        "border":"#9999FF","glow":"#BBBBFF","title":"#DDDDFF",
        "badge_bg":"#5555CC","badge_fg":"#060610",
        "accent":"#FF8844","correct":"#00FF88",
        "gradient":"radial","glow_intensity":0.82,"particle":"#4444AA",
    },
    {   # 47 Inferno
        "name":"Inferno",
        "bg":"#100200","bg2":"#1e0400","card":"#280600",
        "border":"#FF4500","glow":"#FF6600","title":"#FF9966",
        "badge_bg":"#CC2200","badge_fg":"#100200",
        "accent":"#FFD700","correct":"#FF4500",
        "gradient":"radial","glow_intensity":0.95,"particle":"#AA1100",
    },
    {   # 48 Midnight
        "name":"Midnight",
        "bg":"#050510","bg2":"#080818","card":"#0c0c20",
        "border":"#4455AA","glow":"#6677CC","title":"#99AADD",
        "badge_bg":"#334488","badge_fg":"#050510",
        "accent":"#FF9933","correct":"#00FF88",
        "gradient":"solid","glow_intensity":0.70,"particle":"#223366",
    },
    {   # 49 Sakura
        "name":"Sakura",
        "bg":"#140010","bg2":"#200018","card":"#280020",
        "border":"#FF80AB","glow":"#FFAAC8","title":"#FFDDE8",
        "badge_bg":"#E91E63","badge_fg":"#140010",
        "accent":"#FFD700","correct":"#00FF88",
        "gradient":"diagonal","glow_intensity":0.80,"particle":"#CC3377",
    },
    {   # 50 Neon Violet
        "name":"Neon Violet",
        "bg":"#0d0020","bg2":"#160030","card":"#1e0040",
        "border":"#CC00FF","glow":"#DD44FF","title":"#EE88FF",
        "badge_bg":"#AA00CC","badge_fg":"#0d0020",
        "accent":"#00FFAA","correct":"#00FF88",
        "gradient":"vertical","glow_intensity":0.95,"particle":"#8800AA",
    },
    {   # 51 Copper
        "name":"Copper",
        "bg":"#0e0600","bg2":"#180a00","card":"#1e0e00",
        "border":"#B87333","glow":"#D4884F","title":"#FFCC99",
        "badge_bg":"#8B5A2B","badge_fg":"#0e0600",
        "accent":"#FFD700","correct":"#00FF88",
        "gradient":"vertical","glow_intensity":0.78,"particle":"#7A4520",
    },
    {   # 52 Chrome
        "name":"Chrome",
        "bg":"#080c12","bg2":"#0e1420","card":"#141c28",
        "border":"#AABBCC","glow":"#CCDDEE","title":"#E8EEF4",
        "badge_bg":"#778899","badge_fg":"#080c12",
        "accent":"#FF6B35","correct":"#00FF88",
        "gradient":"diagonal","glow_intensity":0.75,"particle":"#5577AA",
    },
    {   # 53 Vaporwave
        "name":"Vaporwave",
        "bg":"#0f0020","bg2":"#180030","card":"#220040",
        "border":"#FF71CE","glow":"#FF71CE","title":"#FFB3E8",
        "badge_bg":"#B455F0","badge_fg":"#0f0020",
        "accent":"#01CDFE","correct":"#05FFA1",
        "gradient":"radial","glow_intensity":0.93,"particle":"#9900CC",
    },
    {   # 54 Biotech
        "name":"Biotech",
        "bg":"#020e08","bg2":"#031610","card":"#052018",
        "border":"#00FFB2","glow":"#00FFB2","title":"#66FFD4",
        "badge_bg":"#00CC88","badge_fg":"#020e08",
        "accent":"#BBFF00","correct":"#00FFB2",
        "gradient":"vertical","glow_intensity":0.93,"particle":"#009966",
    },
]


# ─── Color Utilities ─────────────────────────────────────────────────────────
def _rgb(hex_color):
    h = hex_color.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _lighten(rgb, amount=30):
    return tuple(min(255, c + amount) for c in rgb)


def _darken(rgb, amount=20):
    return tuple(max(0, c - amount) for c in rgb)


def _alpha_blend(base_rgb, overlay_rgb, alpha):
    return tuple(int(b*(1-alpha) + o*alpha) for b, o in zip(base_rgb, overlay_rgb))


def _hex_alpha(hex_color, alpha_0_255):
    """Return RGBA tuple from hex color + alpha int 0-255."""
    r, g, b = _rgb(hex_color)
    return (r, g, b, alpha_0_255)


# ─── Font Loading ─────────────────────────────────────────────────────────────
_FONT_CACHE = {}

def _load_font(size, bold=True, heavy=False):
    key = (size, bold, heavy)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    win = r"C:\Windows\Fonts"
    if heavy:
        candidates = ["seguibl.ttf", "segoeuib.ttf", "arialbd.ttf", "calibrib.ttf"]
    elif bold:
        candidates = ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf", "segoeui.ttf"]
    else:
        candidates = ["segoeui.ttf", "arial.ttf", "calibri.ttf"]
    for name in candidates:
        path = os.path.join(win, name)
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                _FONT_CACHE[key] = font
                return font
            except Exception:
                continue
    font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def _load_emoji_font(size):
    """Try to load Segoe UI Emoji for better emoji rendering."""
    win = r"C:\Windows\Fonts"
    for name in ["seguiemj.ttf", "seguisym.ttf", "segoeuib.ttf"]:
        path = os.path.join(win, name)
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return _load_font(size, bold=True)


# ─── Text Utilities ───────────────────────────────────────────────────────────
def _tw(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0]


def _th(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[3] - bb[1]


def _wrap(draw, text, font, max_w):
    words = text.split()
    if not words:
        return [""]
    lines, cur = [], []
    for word in words:
        test = ' '.join(cur + [word])
        if _tw(draw, test, font) <= max_w:
            cur.append(word)
        else:
            if cur:
                lines.append(' '.join(cur))
            cur = [word]
    if cur:
        lines.append(' '.join(cur))
    return lines or [""]


def _fit_text(draw, text, max_w, max_h, size_max, size_min, bold=True, heavy=False):
    text = text.strip() or " "
    step = 2
    for sz in range(size_max, size_min - 1, -step):
        font = _load_font(sz, bold=bold, heavy=heavy)
        lh   = sz + max(8, sz // 5)
        lines = _wrap(draw, text, font, max_w)
        if len(lines) * lh <= max_h:
            return font, lines, lh
    font = _load_font(size_min, bold=bold, heavy=heavy)
    lh   = size_min + max(8, size_min // 5)
    lines = _wrap(draw, text, font, max_w)
    return font, lines, lh


def _draw_text_block(draw, lines, font, lh, cx, y, fill, align='center', max_w=None):
    for line in lines:
        w = _tw(draw, line, font)
        if align == 'center':
            x = cx - w // 2
            if max_w is not None:
                x = max(cx - max_w // 2, x)
            draw.text((x, y), line, font=font, fill=fill)
        else:
            draw.text((cx, y), line, font=font, fill=fill)
        y += lh
    return y


# ─── Glow Drawing Engine ─────────────────────────────────────────────────────
def _draw_glow_rect(img_rgba, x1, y1, x2, y2, glow_rgb, intensity=0.85,
                    blur_r=14, corner_r=28):
    """Draw a soft glowing halo around a rounded rectangle on an RGBA image."""
    try:
        glow_layer = Image.new('RGBA', img_rgba.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)
        r, g, b = glow_rgb
        for offset in range(blur_r, 0, -1):
            a = int(intensity * 220 * (offset / blur_r) ** 0.6)
            a = min(200, a)
            color = (r, g, b, a)
            expand = offset
            try:
                gd.rounded_rectangle(
                    [x1 - expand, y1 - expand, x2 + expand, y2 + expand],
                    radius=max(1, corner_r + expand // 2),
                    outline=color, width=2
                )
            except (AttributeError, TypeError):
                gd.rectangle(
                    [x1 - expand, y1 - expand, x2 + expand, y2 + expand],
                    outline=color, width=2
                )
        blurred = glow_layer.filter(ImageFilter.GaussianBlur(radius=blur_r // 3))
        img_rgba.alpha_composite(blurred)
    except Exception:
        pass  # Graceful fallback — no glow


def _draw_glow_ellipse(img_rgba, cx, cy, r, glow_rgb, intensity=0.85, blur_r=12):
    """Draw a glowing halo around a circle on an RGBA image."""
    try:
        glow_layer = Image.new('RGBA', img_rgba.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)
        rv, gv, bv = glow_rgb
        for offset in range(blur_r, 0, -1):
            a = int(intensity * 200 * (offset / blur_r) ** 0.7)
            a = min(200, a)
            color = (rv, gv, bv, a)
            ex = offset
            gd.ellipse([cx - r - ex, cy - r - ex, cx + r + ex, cy + r + ex],
                       outline=color, width=2)
        blurred = glow_layer.filter(ImageFilter.GaussianBlur(radius=blur_r // 3))
        img_rgba.alpha_composite(blurred)
    except Exception:
        pass


# ─── Gradient Background Maker ────────────────────────────────────────────────
def _make_gradient_bg(W, H, theme, glow_phase=0.0):
    """Create gradient background + dot grid. Returns RGB image."""
    bg1 = _rgb(theme['bg'])
    bg2 = _rgb(theme.get('bg2', theme['bg']))
    gradient = theme.get('gradient', 'solid')
    glow_intensity = theme.get('glow_intensity', 0.85)
    # Breathing phase modulates bg2 slightly
    breath = 0.85 + 0.15 * (math.sin(glow_phase) * 0.5 + 0.5)

    if HAS_NUMPY:
        bg1a = np.array(bg1, dtype=np.float32)
        bg2a = np.array(bg2, dtype=np.float32) * breath

        if gradient == 'vertical':
            t = np.linspace(0, 1, H, dtype=np.float32).reshape(-1, 1, 1)
            rgb = np.clip((1 - t) * bg1a + t * bg2a, 0, 255).astype(np.uint8)
            rgb = np.broadcast_to(rgb, (H, W, 3)).copy()

        elif gradient == 'radial':
            cx_f, cy_f = W / 2.0, H / 2.0
            y_arr, x_arr = np.mgrid[0:H, 0:W]
            r_arr = np.sqrt((x_arr - cx_f) ** 2 + (y_arr - cy_f) ** 2)
            max_r = math.sqrt(cx_f ** 2 + cy_f ** 2)
            t = np.clip(r_arr / max_r, 0, 1).reshape(H, W, 1).astype(np.float32)
            rgb = np.clip((1 - t) * bg1a + t * bg2a, 0, 255).astype(np.uint8)

        elif gradient == 'diagonal':
            x_t = np.linspace(0, 1, W, dtype=np.float32).reshape(1, W, 1)
            y_t = np.linspace(0, 1, H, dtype=np.float32).reshape(H, 1, 1)
            t = ((x_t + y_t) / 2).astype(np.float32)
            rgb = np.clip((1 - t) * bg1a + t * bg2a, 0, 255).astype(np.uint8)

        else:  # solid
            rgb = np.full((H, W, 3), bg1, dtype=np.uint8)

        img = Image.fromarray(rgb, 'RGB')
    else:
        # Pure-Python fallback: vertical row loop
        img = Image.new('RGB', (W, H), bg1)
        d = ImageDraw.Draw(img)
        for y in range(H):
            t = y / H if H > 1 else 0
            c = tuple(int(bg1[i] * (1 - t) + bg2[i] * t * breath) for i in range(3))
            d.line([(0, y), (W-1, y)], fill=c)

    # Add subtle dot grid overlay
    img = img.convert('RGBA')
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(ov)
    dot_rgb = _rgb(theme.get('particle', theme['border']))
    dot_a = int(20 * glow_intensity)
    dot_c = (*dot_rgb, dot_a)
    spacing = 30
    for gy in range(0, H + spacing, spacing):
        for gx in range(0, W + spacing, spacing):
            odraw.ellipse([gx - 2, gy - 2, gx + 2, gy + 2], fill=dot_c)

    result = Image.alpha_composite(img, ov)
    return result.convert('RGBA')  # Keep RGBA for glow compositing


# ─── Drawing Primitives ───────────────────────────────────────────────────────
def _rounded_rect(draw, x1, y1, x2, y2, radius, fill=None, outline=None, width=3):
    try:
        draw.rounded_rectangle([x1, y1, x2, y2], radius=radius,
                               fill=fill, outline=outline, width=width)
    except (AttributeError, TypeError):
        draw.rectangle([x1, y1, x2, y2], fill=fill, outline=outline, width=width)


def _draw_card(img_rgba, draw, x, y, x2, y2, theme, accent_border=False,
               radius=28, glow_phase=0.0, extra_glow=False):
    """Draw a premium card with glow on an RGBA image."""
    glow_intensity = theme.get('glow_intensity', 0.85)
    breath = 0.6 + 0.4 * (math.sin(glow_phase) * 0.5 + 0.5)
    effective_glow = glow_intensity * breath

    border_hex = theme['accent'] if accent_border else theme['border']
    glow_hex   = theme.get('glow', theme['border'])
    border_rgb = _rgb(border_hex)
    glow_rgb   = _rgb(glow_hex)
    card_rgb   = _rgb(theme['card'])
    shadow_rgb = _darken(_rgb(theme['bg']), 25)

    # Shadow
    _rounded_rect(draw, x + 5, y + 5, x2 + 5, y2 + 5,
                  radius=radius, fill=(*shadow_rgb, 160))
    # Card fill
    _rounded_rect(draw, x, y, x2, y2,
                  radius=radius, fill=(*card_rgb, 240))
    # Glow halo (breathing)
    blur_r = 18 if extra_glow else 14
    _draw_glow_rect(img_rgba, x, y, x2, y2, glow_rgb,
                    intensity=effective_glow, blur_r=blur_r, corner_r=radius)
    # Crisp border
    _rounded_rect(draw, x, y, x2, y2,
                  radius=radius, outline=(*border_rgb, 255), width=3)


def _draw_badge(img_rgba, draw, W, y, text, theme, is_portrait,
                badge_style='pill', glow_phase=0.0):
    """Draw a premium glowing pill badge. Returns badge bottom y."""
    size   = 26 if is_portrait else 22
    font   = _load_font(size, bold=True, heavy=True)
    tw     = _tw(draw, text, font)
    th     = _th(draw, text, font)
    pad_x  = 40
    pad_y  = 14
    bw     = tw + 2 * pad_x
    bh     = th + 2 * pad_y
    bx     = (W - bw) // 2
    by     = y

    glow_rgb   = _rgb(theme.get('glow', theme['border']))
    badge_bg   = _rgb(theme['badge_bg'])
    badge_fg   = _rgb(theme['badge_fg'])
    glow_intensity = theme.get('glow_intensity', 0.85)
    breath = 0.7 + 0.3 * (math.sin(glow_phase) * 0.5 + 0.5)

    # Glow halo
    _draw_glow_rect(img_rgba, bx, by, bx + bw, by + bh,
                    glow_rgb, intensity=glow_intensity * breath,
                    blur_r=12, corner_r=bh // 2)
    # Shadow
    _rounded_rect(draw, bx + 3, by + 3, bx + bw + 3, by + bh + 3,
                  radius=bh // 2, fill=(*_darken(_rgb(theme['bg']), 30), 160))
    # Fill
    _rounded_rect(draw, bx, by, bx + bw, by + bh,
                  radius=bh // 2, fill=(*badge_bg, 255))
    # Text
    draw.text((bx + pad_x, by + pad_y), text, font=font, fill=(*badge_fg, 255))

    return by + bh


def _draw_footer(img_rgba, draw, W, H, theme, glow_phase=0.0):
    """Draw the premium glowing LIKE SHARE SUBSCRIBE footer."""
    text    = "* LIKE, SHARE AND SUBSCRIBE *"
    fsize   = 28
    font    = _load_font(fsize, bold=True, heavy=True)
    tw      = _tw(draw, text, font)
    pill_w  = tw + 100
    pill_h  = 60
    footer_y = H - 90
    px = (W - pill_w) // 2
    py = footer_y + (90 - pill_h) // 2

    border_rgb = _rgb(theme['border'])
    glow_rgb   = _rgb(theme.get('glow', theme['border']))
    bg_rgb     = _rgb(theme['bg'])
    glow_intensity = theme.get('glow_intensity', 0.85)
    breath = 0.65 + 0.35 * (math.sin(glow_phase + math.pi * 0.3) * 0.5 + 0.5)

    # Glow halo
    _draw_glow_rect(img_rgba, px, py, px + pill_w, py + pill_h,
                    glow_rgb, intensity=glow_intensity * breath,
                    blur_r=16, corner_r=pill_h // 2)
    # Shadow
    _rounded_rect(draw, px + 4, py + 4, px + pill_w + 4, py + pill_h + 4,
                  radius=pill_h // 2, fill=(*_darken(bg_rgb, 30), 160))
    # Pill background
    _rounded_rect(draw, px, py, px + pill_w, py + pill_h,
                  radius=pill_h // 2, fill=(*bg_rgb, 230),
                  outline=(*border_rgb, 255), width=3)
    # Text
    th2 = _th(draw, text, font)
    draw.text((px + 50, py + (pill_h - th2) // 2), text,
              font=font, fill=(*border_rgb, 255))


def _draw_option_row(img_rgba, draw, x, y, w, h, letter, text, theme,
                     correct=False, is_portrait=True, glow_phase=0.0):
    """Draw one MCQ option row with glow on correct answer."""
    radius = 20
    glow_rgb   = _rgb(theme.get('glow', theme['border']))
    correct_rgb = _rgb(theme['correct'])
    border_dim  = _darken(_rgb(theme['border']), 40)

    if correct:
        fill_c   = _alpha_blend(_rgb(theme['card']), correct_rgb, 0.30)
        border_c = correct_rgb
        # Glow on correct answer
        breath = 0.7 + 0.3 * (math.sin(glow_phase + math.pi) * 0.5 + 0.5)
        _draw_glow_rect(img_rgba, x, y, x + w, y + h, correct_rgb,
                        intensity=0.80 * breath, blur_r=10, corner_r=radius)
    else:
        fill_c   = _rgb(theme['card'])
        border_c = border_dim

    _rounded_rect(draw, x, y, x + w, y + h, radius=radius,
                  fill=(*fill_c, 240), outline=(*border_c, 200), width=3)

    # Letter badge circle
    badge_d  = 52 if is_portrait else 44
    badge_x  = x + 22
    badge_cx = badge_x + badge_d // 2
    badge_cy = y + h // 2

    if correct:
        badge_fill = correct_rgb
        badge_fg   = (255, 255, 255)
    else:
        badge_fill = _rgb(theme['badge_bg'])
        badge_fg   = _rgb(theme['badge_fg'])

    if correct:
        _draw_glow_ellipse(img_rgba, badge_cx, badge_cy, badge_d // 2,
                           correct_rgb, intensity=0.75, blur_r=8)

    draw.ellipse([badge_x, badge_cy - badge_d // 2,
                  badge_x + badge_d, badge_cy + badge_d // 2],
                 fill=(*badge_fill, 255), outline=(255, 255, 255, 200), width=2)

    lf = _load_font(22 if is_portrait else 18, bold=True, heavy=True)
    lw = _tw(draw, letter, lf)
    lh = _th(draw, letter, lf)
    draw.text((badge_cx - lw // 2, badge_cy - lh // 2), letter,
              font=lf, fill=(*badge_fg, 255))

    # Option text — dynamic sizing
    text_x = badge_x + badge_d + 18
    text_w = w - (text_x - x) - 18
    text_cx = text_x + text_w // 2

    display = text + "  \u2713" if correct else text

    sz_max = 30 if is_portrait else 24
    sz_min = 16
    font2, lines2, lh2 = _fit_text(draw, display, text_w, h - 20, sz_max, sz_min)
    block_h = len(lines2) * lh2
    ty = y + (h - block_h) // 2
    _draw_text_block(draw, lines2, font2, lh2, text_cx, ty,
                     (255, 255, 255, 255), align='center', max_w=text_w)


# ─── Dynamic Option Height ────────────────────────────────────────────────────
def _measure_option_height(draw, opt_text, opt_w, is_portrait):
    """Return the card height needed to fit the option text."""
    badge_d = 52 if is_portrait else 44
    text_w  = opt_w - badge_d - 80   # badge + margins
    sz_max  = 30 if is_portrait else 24
    sz_min  = 16
    font, lines, lh = _fit_text(draw, opt_text, text_w, 400, sz_max, sz_min)
    content_h = len(lines) * lh
    return max(70, content_h + 36)   # 36 px vertical padding


# ──────────────────────────────────────────────────────────────────────────────
#  PREMIUM SLIDE RENDERERS
# ──────────────────────────────────────────────────────────────────────────────

def _render_hook(W, H, theme, num_q, timer_secs, is_portrait, glow_phase=0.0):
    """Premium cinematic Intro Screen."""
    img_rgba = _make_gradient_bg(W, H, theme, glow_phase)
    draw = ImageDraw.Draw(img_rgba)
    _draw_footer(img_rgba, draw, W, H, theme, glow_phase)

    mg = 44 if is_portrait else 36
    cx = W // 2
    footer_top = H - 118

    # ── Top badge row ──────────────────────────────────────────────────────
    badge_texts = ["\u26a1 QUIZ TIME \u26a1", "\U0001f3af BRAIN CHALLENGE \U0001f3af",
                   "\U0001f525 IQ TEST \U0001f525", "\U0001f9e0 THINK FAST \u23f1\ufe0f",
                   "\u2b50 CHALLENGE YOURSELF \u2b50"]
    badge_text = badge_texts[abs(hash(str(num_q) + str(timer_secs))) % len(badge_texts)]
    badge_bot = _draw_badge(img_rgba, draw, W, mg, badge_text, theme, is_portrait, glow_phase=glow_phase)
    y = badge_bot + 18

    # ── Main central card ──────────────────────────────────────────────────
    content_zone = footer_top - y - 20
    card_pad_top = 24
    card_pad_side = 50

    # Estimate text heights to size card properly
    dummy_draw = ImageDraw.Draw(Image.new('RGBA', (W, H)))
    inner_w = W - 2 * mg - 2 * card_pad_side

    # Line 1: IQ Test header
    line1 = "\U0001f3af IQ Test \u2014 Are You Smarter Than 90%?"
    f1, ls1, lh1 = _fit_text(dummy_draw, line1, inner_w, 140, 42 if is_portrait else 34, 26, heavy=True)
    b1h = len(ls1) * lh1

    # Line 2: challenge hook
    if num_q > 1:
        line2 = f"\U0001f525 Can You Get All {num_q} Questions Right? \U0001f525"
    else:
        line2 = "\U0001f92f This Question Trips Everyone Up! \U0001f92f"
    f2, ls2, lh2 = _fit_text(dummy_draw, line2, inner_w, 160, 48 if is_portrait else 40, 28, heavy=True)
    b2h = len(ls2) * lh2

    # Line 3: timer
    line3 = f"\u23f1\ufe0f Guess in {timer_secs} Seconds!"
    f3, ls3, lh3 = _fit_text(dummy_draw, line3, inner_w, 120, 40 if is_portrait else 32, 24, heavy=True)
    b3h = len(ls3) * lh3

    gap = 30
    total_text_h = b1h + gap + b2h + gap + b3h
    card_h = total_text_h + card_pad_top * 3
    card_h = max(200, min(card_h, int(content_zone * 0.82)))

    card_x  = mg
    card_x2 = W - mg
    card_y  = y
    card_y2 = card_y + card_h

    # Draw main card with strong glow
    _draw_card(img_rgba, draw, card_x, card_y, card_x2, card_y2, theme,
               radius=40, glow_phase=glow_phase, extra_glow=True)

    # Draw text inside card
    ty = card_y + card_pad_top + (card_h - total_text_h - card_pad_top) // 2

    _draw_text_block(draw, ls1, f1, lh1, cx, ty, (255, 255, 255, 255))
    ty += b1h + gap

    _draw_text_block(draw, ls2, f2, lh2, cx, ty, (*_rgb(theme['accent']), 255))
    ty += b2h + gap

    _draw_text_block(draw, ls3, f3, lh3, cx, ty, (*_rgb(theme['border']), 255))

    # ── Decorative accent dots at corners ─────────────────────────────────
    dot_c  = _rgb(theme.get('glow', theme['border']))
    dot_a  = int(160 * theme.get('glow_intensity', 0.85))
    for (dx, dy) in [(card_x + 20, card_y + 20), (card_x2 - 20, card_y + 20),
                     (card_x + 20, card_y2 - 20), (card_x2 - 20, card_y2 - 20)]:
        draw.ellipse([dx - 6, dy - 6, dx + 6, dy + 6], fill=(*dot_c, dot_a))

    # ── CTA area below main card ───────────────────────────────────────────
    remaining = footer_top - card_y2
    if remaining > 80:
        cta_text = "\U0001f44c Like \u2022 \u2197\ufe0f Share \u2022 \U0001f514 Subscribe"
        cta_font = _load_font(24 if is_portrait else 20, bold=True, heavy=True)
        cta_w    = _tw(draw, cta_text, cta_font)
        cta_h    = _th(draw, cta_text, cta_font)
        cta_y    = card_y2 + (remaining - cta_h) // 2
        draw.text((cx - cta_w // 2, cta_y), cta_text,
                  font=cta_font, fill=(*_rgb(theme['accent']), 220))

    return img_rgba.convert('RGB')


def _render_mcq(W, H, theme, question, slide_type, timer_secs, is_portrait,
                glow_phase=0.0):
    """Render entrance, timer, or answer slide — with dynamic sizing."""
    img_rgba = _make_gradient_bg(W, H, theme, glow_phase)
    draw = ImageDraw.Draw(img_rgba)
    _draw_footer(img_rgba, draw, W, H, theme, glow_phase)

    mg   = 44 if is_portrait else 30
    cx   = W // 2
    cw   = W - 2 * mg

    q_text = question['questionText']
    opts   = question['options']
    ci     = question['correctIndex']
    L      = ['A', 'B', 'C', 'D']

    # ── Badge ─────────────────────────────────────────────────────────────
    if slide_type == 'entrance':
        badge_text = "\U0001f4dd QUIZ QUESTION"
    elif slide_type == 'timer':
        badge_text = "\u23f1\ufe0f THINK FAST!"
    else:
        badge_text = "\u2705 ANSWER REVEAL"

    badge_bot = _draw_badge(img_rgba, draw, W, mg, badge_text, theme, is_portrait,
                            glow_phase=glow_phase)
    y = badge_bot + 18

    # ── Dynamic option heights ─────────────────────────────────────────────
    n_opts    = min(4, len(opts))
    opt_gap   = 16 if is_portrait else 12
    opt_heights = [_measure_option_height(draw, opts[i] if i < len(opts) else '', cw,
                                          is_portrait)
                   for i in range(n_opts)]

    # ── Layout: work from bottom up ────────────────────────────────────────
    footer_top = H - 118
    timer_h    = 120 if is_portrait else 100
    timer_gap  = 16

    if slide_type == 'timer':
        opts_bottom = footer_top - timer_gap - timer_h - timer_gap
    else:
        opts_bottom = footer_top - opt_gap

    opts_section_h = sum(opt_heights) + (n_opts - 1) * opt_gap
    opts_top       = opts_bottom - opts_section_h
    qbox_gap       = 16
    qbox_available = opts_top - y - qbox_gap

    # ── Question box (dynamic height) ─────────────────────────────────────
    q_inner_w = cw - 80
    ql        = len(q_text)
    sz_max    = 46 if is_portrait else 38
    sz_min    = 20
    if ql > 280: sz_max = 32 if is_portrait else 26
    elif ql > 140: sz_max = 38 if is_portrait else 32

    q_font, q_lines, q_lh = _fit_text(draw, q_text, q_inner_w,
                                       max(60, qbox_available) - 40, sz_max, sz_min)
    actual_q_text_h = len(q_lines) * q_lh
    qbox_h = max(80, actual_q_text_h + 44)  # dynamic: fits content + padding
    qbox_h = min(qbox_h, qbox_available)

    _draw_card(img_rgba, draw, mg, y, W - mg, y + qbox_h, theme,
               radius=28, glow_phase=glow_phase)

    qy = y + (qbox_h - actual_q_text_h) // 2
    _draw_text_block(draw, q_lines, q_font, q_lh, mg + 40 + (cw - 80) // 2,
                     qy, (255, 255, 255, 255), max_w=q_inner_w)

    # ── Options ───────────────────────────────────────────────────────────
    oy = y + qbox_h + 8
    for i in range(n_opts):
        oh = opt_heights[i]
        is_correct = (slide_type == 'answer') and (i == ci)
        opt_txt = opts[i] if i < len(opts) else ""
        _draw_option_row(img_rgba, draw, mg, oy, cw, oh, L[i], opt_txt,
                         theme, correct=is_correct, is_portrait=is_portrait,
                         glow_phase=glow_phase)
        oy += oh + opt_gap

    # ── Timer box (timer slide only) ──────────────────────────────────────
    if slide_type == 'timer':
        tb_y  = opts_bottom + timer_gap
        tb_y2 = tb_y + timer_h
        if tb_y2 > footer_top - 4:
            tb_y2 = footer_top - 4
            tb_y  = tb_y2 - timer_h

        _draw_card(img_rgba, draw, mg, tb_y, W - mg, tb_y2, theme,
                   accent_border=True, radius=22, glow_phase=glow_phase + math.pi,
                   extra_glow=True)

        # Ring circle with glow
        ring_cx = mg + 68
        ring_cy = (tb_y + tb_y2) // 2
        ring_r  = 36
        ring_rgb = _rgb(theme['accent'])

        _draw_glow_ellipse(img_rgba, ring_cx, ring_cy, ring_r + 4,
                           ring_rgb, intensity=0.85, blur_r=10)

        draw.arc([ring_cx - ring_r, ring_cy - ring_r,
                  ring_cx + ring_r, ring_cy + ring_r],
                 start=0, end=360, fill=(*_darken(ring_rgb, 60), 255), width=7)
        draw.arc([ring_cx - ring_r, ring_cy - ring_r,
                  ring_cx + ring_r, ring_cy + ring_r],
                 start=-90, end=270, fill=(*ring_rgb, 255), width=7)

        nf = _load_font(34, bold=True, heavy=True)
        ns = str(timer_secs)
        nw = _tw(draw, ns, nf); nh = _th(draw, ns, nf)
        draw.text((ring_cx - nw // 2, ring_cy - nh // 2), ns, font=nf,
                  fill=(*ring_rgb, 255))

        lf2 = _load_font(26 if is_portrait else 22, bold=True, heavy=True)
        lbl = "GUESS THE ANSWER!"
        lw = _tw(draw, lbl, lf2); lh_ = _th(draw, lbl, lf2)
        draw.text((ring_cx + ring_r + 24, (tb_y + tb_y2) // 2 - lh_ // 2),
                  lbl, font=lf2, fill=(*ring_rgb, 255))

    return img_rgba.convert('RGB')


def _render_explanation(W, H, theme, sentences, is_portrait, glow_phase=0.0):
    img_rgba = _make_gradient_bg(W, H, theme, glow_phase)
    draw = ImageDraw.Draw(img_rgba)
    _draw_footer(img_rgba, draw, W, H, theme, glow_phase)

    mg = 44 if is_portrait else 30
    cx = W // 2
    cw = W - 2 * mg

    # Explanation header badge
    badge_bot = _draw_badge(img_rgba, draw, W, mg,
                            "\U0001f4a1 EXPLANATION", theme, is_portrait,
                            glow_phase=glow_phase)
    y = badge_bot + 18

    footer_top = H - 118
    available_h = footer_top - y
    n        = max(1, len(sentences))
    item_gap = 14 if is_portrait else 10
    item_h   = (available_h - (n - 1) * item_gap) // n
    item_h   = max(80, min(item_h, 320 if is_portrait else 240))

    accent_rgb = _rgb(theme['accent'])
    border_rgb = _rgb(theme['border'])

    for sent in sentences:
        _draw_card(img_rgba, draw, mg, y, W - mg, y + item_h, theme,
                   radius=22, glow_phase=glow_phase)

        # Premium bullet: glowing diamond
        bf   = _load_font(26 if is_portrait else 20, bold=True)
        bul  = "\u25c6"  # diamond bullet
        bw   = _tw(draw, bul, bf)
        bh   = _th(draw, bul, bf)
        draw.text((mg + 20, y + (item_h - bh) // 2), bul,
                  font=bf, fill=(*accent_rgb, 255))

        txt_x = mg + 20 + bw + 16
        txt_w = (W - mg) - txt_x - 18
        sf, sl, slh = _fit_text(draw, sent, txt_w, item_h - 24,
                                 30 if is_portrait else 24, 16)
        block_h = len(sl) * slh
        ty = y + (item_h - block_h) // 2
        _draw_text_block(draw, sl, sf, slh, txt_x + txt_w // 2, ty,
                         (240, 248, 255, 255))
        y += item_h + item_gap

    return img_rgba.convert('RGB')


def _render_end(W, H, theme, is_portrait, glow_phase=0.0):
    """Premium cinematic Outro / End Screen."""
    img_rgba = _make_gradient_bg(W, H, theme, glow_phase)
    draw = ImageDraw.Draw(img_rgba)
    _draw_footer(img_rgba, draw, W, H, theme, glow_phase)

    mg  = 44 if is_portrait else 36
    cx  = W // 2
    footer_top = H - 118
    content_h  = footer_top - mg

    glow_rgb   = _rgb(theme.get('glow', theme['border']))
    accent_rgb = _rgb(theme['accent'])
    border_rgb = _rgb(theme['border'])

    # ── Top celebration badge ──────────────────────────────────────────────
    badge_bot = _draw_badge(img_rgba, draw, W, mg,
                            "\U0001f3c6 QUIZ COMPLETE \U0001f3c6",
                            theme, is_portrait, glow_phase=glow_phase)
    y = badge_bot + 16

    # ── Main card ─────────────────────────────────────────────────────────
    card_x  = mg + 20
    card_x2 = W - mg - 20
    card_inner_w = card_x2 - card_x - 80
    card_h  = int(content_h * 0.68)
    card_y  = y
    card_y2 = card_y + card_h

    _draw_card(img_rgba, draw, card_x, card_y, card_x2, card_y2, theme,
               accent_border=True, radius=44, glow_phase=glow_phase,
               extra_glow=True)

    # ── Trophy / star symbol ──────────────────────────────────────────────
    trophy_text = "\U0001f3c6"   # trophy emoji
    trophy_font = _load_emoji_font(80 if is_portrait else 64)
    tw = _tw(draw, trophy_text, trophy_font)
    th = _th(draw, trophy_text, trophy_font)
    trophy_y = card_y + 28
    draw.text((cx - tw // 2, trophy_y), trophy_text,
              font=trophy_font, fill=(*accent_rgb, 255))

    inner_y = trophy_y + th + 20

    # ── Main call-to-action text ──────────────────────────────────────────
    lines_cfg = [
        ("FOLLOW FOR DAILY QUIZ!", 50 if is_portrait else 42, (255, 255, 255)),
        ("Every day new questions!", 30 if is_portrait else 24, (*accent_rgb,)),
    ]

    for (txt, sz_max, color) in lines_cfg:
        f_, ls_, lh_ = _fit_text(draw, txt, card_inner_w,
                                  card_y2 - inner_y - 80, sz_max, max(20, sz_max - 12),
                                  heavy=True)
        bh_ = len(ls_) * lh_
        _draw_text_block(draw, ls_, f_, lh_, cx, inner_y,
                         (*color[:3], 255) if len(color) == 3 else color)
        inner_y += bh_ + 16

    # ── Social action row ─────────────────────────────────────────────────
    remaining_card = card_y2 - inner_y - 20
    if remaining_card > 50:
        actions = [("\U0001f44d Like", accent_rgb),
                   ("\u2197\ufe0f Share", border_rgb),
                   ("\U0001f514 Subscribe", accent_rgb),
                   ("\u2764\ufe0f Follow", border_rgb)]
        action_font = _load_font(26 if is_portrait else 22, bold=True, heavy=True)
        total_w = sum(_tw(draw, a[0], action_font) + 30 for a in actions) - 30
        ax = cx - total_w // 2
        ay = inner_y + (remaining_card - _th(draw, actions[0][0], action_font)) // 2

        for (atxt, acolor) in actions:
            aw = _tw(draw, atxt, action_font)
            draw.text((ax, ay), atxt, font=action_font, fill=(*acolor, 255))
            ax += aw + 30

    # ── Second smaller card with channel message ───────────────────────────
    remaining = footer_top - card_y2
    if remaining > 70:
        c2_h  = min(remaining - 20, 90 if is_portrait else 70)
        c2_y  = card_y2 + (remaining - c2_h) // 2
        c2_x  = mg + 40
        c2_x2 = W - mg - 40
        _draw_card(img_rgba, draw, c2_x, c2_y, c2_x2, c2_y + c2_h, theme,
                   radius=22, glow_phase=glow_phase + math.pi * 0.5)
        sub_text = "\U0001f514 Turn on notifications for more quizzes!"
        sub_font = _load_font(22 if is_portrait else 18, bold=True)
        sw = _tw(draw, sub_text, sub_font)
        sh = _th(draw, sub_text, sub_font)
        draw.text((cx - sw // 2, c2_y + (c2_h - sh) // 2), sub_text,
                  font=sub_font, fill=(*border_rgb, 230))

    return img_rgba.convert('RGB')


def render_slide(slide_data, W, H, is_portrait):
    """Top-level dispatcher: returns a Pillow RGB Image for the given slide dict."""
    t         = slide_data['type']
    theme_idx = slide_data.get('theme_idx', 0) % len(THEMES)
    theme     = THEMES[theme_idx]
    ts        = slide_data.get('timer_secs', 10)
    gp        = slide_data.get('glow_phase', 0.0)

    if t == 'hook':
        return _render_hook(W, H, theme, slide_data.get('num_q', 1), ts,
                            is_portrait, glow_phase=gp)
    elif t in ('entrance', 'timer', 'answer'):
        return _render_mcq(W, H, theme, slide_data['q'], t, ts, is_portrait,
                           glow_phase=gp)
    elif t == 'explanation':
        return _render_explanation(W, H, theme, slide_data.get('sentences', []),
                                   is_portrait, glow_phase=gp)
    elif t == 'end':
        return _render_end(W, H, theme, is_portrait, glow_phase=gp)
    else:
        img = _make_gradient_bg(W, H, theme, gp)
        d   = ImageDraw.Draw(img)
        _draw_footer(img, d, W, H, theme, gp)
        return img.convert('RGB')


# ─── Cinematic Transition Engine ─────────────────────────────────────────────
# Allowed premium transitions (no cube, no star wipe, no PowerPoint effects)
PREMIUM_TRANSITIONS = [
    'fade',          # smooth opacity blend
    'slide_up',      # curr enters from bottom
    'slide_down',    # curr enters from top
    'fade_up',       # blend + slight upward drift
    'fade_down',     # blend + slight downward drift
    'soft_dissolve', # very gentle cross-dissolve
    'scale_fade',    # curr zooms from 110% while fading in
    'zoom_out',      # prev gently zooms out as curr fades in
    'wipe_up',       # curtain wipe from bottom to top
    'wipe_down',     # curtain wipe from top to bottom
    'content_morph', # luminance-boosted dissolve
    'perspective_drift',  # subtle horizontal drift + blend
    'layered_fade',  # double-exposure style
    'opacity_transform',  # eased opacity blend
    'cinematic_reveal',   # slide_up with ease-out curve
]

# Transition timing
_N_TRANS_FRAMES   = 10      # frames per transition
_TRANS_FRAME_DUR  = 0.04    # seconds per frame (25 fps = 0.04s)
_TRANS_TOTAL_DUR  = _N_TRANS_FRAMES * _TRANS_FRAME_DUR  # 0.40 s


def _ease_out(t):
    """Ease-out cubic: fast start, slow end."""
    return 1.0 - (1.0 - t) ** 3


def _ease_in_out(t):
    """Smooth S-curve easing."""
    return t * t * (3 - 2 * t)


def _render_transition_frames(prev_rgb, curr_rgb, transition_type, n=_N_TRANS_FRAMES):
    """
    Generate n transition frames blending from prev_rgb to curr_rgb.
    Both images must be PIL RGB with the same W×H.
    Returns list of PIL RGB images.
    """
    frames = []
    W, H = curr_rgb.size

    for i in range(n):
        raw_t = (i + 1) / (n + 1)  # 0 < raw_t < 1

        try:
            if transition_type == 'fade':
                t = _ease_in_out(raw_t)
                frame = Image.blend(prev_rgb, curr_rgb, alpha=t)

            elif transition_type == 'slide_up':
                t     = _ease_out(raw_t)
                offset = int(H * (1.0 - t))
                frame  = prev_rgb.copy()
                frame.paste(curr_rgb, (0, offset))

            elif transition_type == 'slide_down':
                t     = _ease_out(raw_t)
                offset = int(-H * (1.0 - t))
                frame  = prev_rgb.copy()
                frame.paste(curr_rgb, (0, offset))

            elif transition_type == 'fade_up':
                t      = _ease_in_out(raw_t)
                drift  = int(H * 0.04 * (1.0 - raw_t))
                shifted = Image.new('RGB', (W, H), (0, 0, 0))
                shifted.paste(curr_rgb, (0, -drift))
                frame  = Image.blend(prev_rgb, shifted, alpha=t)

            elif transition_type == 'fade_down':
                t     = _ease_in_out(raw_t)
                drift = int(H * 0.04 * (1.0 - raw_t))
                shifted = Image.new('RGB', (W, H), (0, 0, 0))
                shifted.paste(curr_rgb, (0, drift))
                frame = Image.blend(prev_rgb, shifted, alpha=t)

            elif transition_type in ('soft_dissolve', 'layered_fade',
                                     'opacity_transform'):
                t     = _ease_in_out(raw_t)
                frame = Image.blend(prev_rgb, curr_rgb, alpha=t)

            elif transition_type == 'scale_fade':
                t     = _ease_out(raw_t)
                scale = 1.0 + 0.10 * (1.0 - raw_t)
                nw    = int(W * scale)
                nh    = int(H * scale)
                scaled = curr_rgb.resize((nw, nh), Image.BILINEAR)
                ox    = (nw - W) // 2
                oy    = (nh - H) // 2
                cropped = scaled.crop((ox, oy, ox + W, oy + H))
                frame = Image.blend(prev_rgb, cropped, alpha=t)

            elif transition_type == 'zoom_out':
                t     = _ease_out(raw_t)
                scale = 1.0 + 0.08 * raw_t
                nw    = int(W * scale)
                nh    = int(H * scale)
                scaled_prev = prev_rgb.resize((nw, nh), Image.BILINEAR)
                ox   = (nw - W) // 2
                oy   = (nh - H) // 2
                cropped_prev = scaled_prev.crop((ox, oy, ox + W, oy + H))
                frame = Image.blend(cropped_prev, curr_rgb, alpha=t)

            elif transition_type == 'wipe_up':
                wipe_start = int(H * (1.0 - raw_t))
                frame = prev_rgb.copy()
                if wipe_start < H:
                    patch = curr_rgb.crop((0, wipe_start, W, H))
                    frame.paste(patch, (0, wipe_start))

            elif transition_type == 'wipe_down':
                wipe_end = int(H * raw_t)
                frame = prev_rgb.copy()
                if wipe_end > 0:
                    patch = curr_rgb.crop((0, 0, W, wipe_end))
                    frame.paste(patch, (0, 0))

            elif transition_type == 'content_morph':
                t     = _ease_in_out(raw_t)
                frame = Image.blend(prev_rgb, curr_rgb, alpha=t)
                if HAS_NUMPY and 0.3 < raw_t < 0.7:
                    brightness = 1.0 + 0.12 * math.sin(raw_t * math.pi)
                    arr  = np.array(frame, dtype=np.float32)
                    arr  = np.clip(arr * brightness, 0, 255).astype(np.uint8)
                    frame = Image.fromarray(arr)

            elif transition_type == 'perspective_drift':
                t     = _ease_in_out(raw_t)
                drift = int(W * 0.025 * (1.0 - raw_t))
                drifted = Image.new('RGB', (W, H), (0, 0, 0))
                drifted.paste(curr_rgb, (drift, 0))
                frame = Image.blend(prev_rgb, drifted, alpha=t)

            elif transition_type == 'cinematic_reveal':
                # Ease-out slide_up variant
                t     = _ease_out(raw_t) ** 0.7
                offset = int(H * (1.0 - t))
                frame  = prev_rgb.copy()
                frame.paste(curr_rgb, (0, offset))

            else:
                t     = _ease_in_out(raw_t)
                frame = Image.blend(prev_rgb, curr_rgb, alpha=t)

        except Exception:
            frame = Image.blend(prev_rgb, curr_rgb, alpha=raw_t)

        frames.append(frame.convert('RGB'))

    return frames


# ─── Slide Builder ────────────────────────────────────────────────────────────
def _build_inner_slides(question, show_explanation, timer_seconds,
                        theme_idx, rng):
    slides = []
    L  = ['A', 'B', 'C', 'D']
    ci = question['correctIndex']
    cl = L[ci] if ci < 4 else 'A'
    ct = question['options'][ci] if ci < len(question['options']) else ''

    # Unique glow phase for each slide
    def _gp():
        return rng.uniform(0, 2 * math.pi)

    slides.append({'type': 'entrance', 'q': question, 'theme_idx': theme_idx,
                   'speak': '', 'is_tick': False, 'fixed_dur': 3.5,
                   'timer_secs': timer_seconds, 'glow_phase': _gp()})

    slides.append({'type': 'timer', 'q': question, 'theme_idx': theme_idx,
                   'speak': '', 'is_tick': True,
                   'fixed_dur': float(timer_seconds),
                   'timer_secs': timer_seconds, 'glow_phase': _gp()})

    slides.append({'type': 'answer', 'q': question, 'theme_idx': theme_idx,
                   'speak': f"The correct answer is Option {cl}: {ct}.",
                   'is_tick': False, 'fixed_dur': None, 'min_dur': 3.0,
                   'timer_secs': timer_seconds, 'glow_phase': _gp()})

    expl = question.get('explanation', '').strip()
    if show_explanation and expl:
        sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', expl)
                 if s.strip() and len(s.strip()) > 12]
        chunk = 4
        for i in range(0, max(1, len(sents)), chunk):
            group = sents[i:i + chunk]
            if not group:
                continue
            slides.append({'type': 'explanation', 'sentences': group,
                           'theme_idx': theme_idx,
                           'speak': ' '.join(group),
                           'is_tick': False, 'fixed_dur': None, 'min_dur': 3.0,
                           'timer_secs': timer_seconds, 'glow_phase': _gp()})

    return slides


def _pick_themes_no_repeat(rng, n_themes_total, n_slots):
    """Pick n_slots theme indices with no consecutive repeats."""
    result = []
    last   = -1
    for _ in range(n_slots):
        pool = [t for t in range(n_themes_total) if t != last]
        idx  = rng.choice(pool)
        result.append(idx)
        last = idx
    return result


def build_video_slides(group_questions, show_explanation, timer_seconds,
                       hook_theme, q_themes, rng):
    slides = []
    num_q  = len(group_questions)

    def _gp():
        return rng.uniform(0, 2 * math.pi)

    slides.append({'type': 'hook', 'num_q': num_q, 'theme_idx': hook_theme,
                   'speak': 'Welcome! Test your knowledge with this quiz!',
                   'is_tick': False, 'fixed_dur': None, 'min_dur': 2.5,
                   'timer_secs': timer_seconds, 'glow_phase': _gp()})

    for qi, q in enumerate(group_questions):
        slides.extend(_build_inner_slides(q, show_explanation, timer_seconds,
                                          q_themes[qi], rng))

    slides.append({'type': 'end', 'theme_idx': hook_theme,
                   'speak': 'Follow for daily quizzes. Like, share and subscribe!',
                   'is_tick': False, 'fixed_dur': None, 'min_dur': 2.5,
                   'timer_secs': timer_seconds, 'glow_phase': _gp()})

    return slides


# ─── TTS Worker ───────────────────────────────────────────────────────────────
def tts_worker(text, wav_path, voice_idx, sapi_rate, result_dict, key):
    if HAS_PYTHONCOM:
        pythoncom.CoInitialize()
    try:
        import win32com.client
        sp     = win32com.client.Dispatch("SAPI.SpVoice")
        voices = sp.GetVoices()
        if voice_idx < voices.Count:
            sp.Voice = voices.Item(voice_idx)
        sp.Rate = sapi_rate
        fs = win32com.client.Dispatch("SAPI.SpFileStream")
        fs.Open(wav_path, 3, False)
        sp.AudioOutputStream = fs
        sp.Speak(text if text.strip() else " ")
        fs.Close()
        result_dict[key] = wav_path
    except Exception:
        generate_silent_wav(wav_path, 1.5)
        result_dict[key] = wav_path
    finally:
        if HAS_PYTHONCOM:
            try: pythoncom.CoUninitialize()
            except: pass


# ─── WAV Merge ────────────────────────────────────────────────────────────────
def _merge_wavs(wav_paths, out_path):
    tmp_dir   = tempfile.mkdtemp(prefix="wmerge_")
    init_done = False
    try:
        with wave.open(out_path, 'w') as out_wf:
            for idx, wp in enumerate(wav_paths):
                if not os.path.exists(wp):
                    continue
                try:
                    with wave.open(wp, 'r') as probe:
                        src_rate     = probe.getframerate()
                        src_channels = probe.getnchannels()
                        src_width    = probe.getsampwidth()

                    needs_norm = (src_rate     != CANONICAL_RATE     or
                                  src_channels != CANONICAL_CHANNELS or
                                  src_width    != CANONICAL_WIDTH)

                    if needs_norm:
                        norm_path = os.path.join(tmp_dir, f"n{idx}.wav")
                        _normalize_wav(wp, norm_path)
                        read_path = norm_path
                    else:
                        read_path = wp

                    with wave.open(read_path, 'r') as wf:
                        if not init_done:
                            out_wf.setnchannels(wf.getnchannels())
                            out_wf.setsampwidth(wf.getsampwidth())
                            out_wf.setframerate(wf.getframerate())
                            init_done = True
                        out_wf.writeframes(wf.readframes(wf.getnframes()))

                except Exception:
                    pass

        if not init_done:
            generate_silent_wav(out_path, 1.0)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ─── FFmpeg helpers ───────────────────────────────────────────────────────────
def _find_ffmpeg():
    try:
        import static_ffmpeg
        paths = static_ffmpeg.add_paths()
        if paths and os.path.exists(paths[0]):
            return paths[0]
    except Exception:
        pass
    found = shutil.which("ffmpeg")
    if found:
        return found
    return "ffmpeg"


def _ffmpeg_assemble(ffmpeg_exe, imgs, durs, merged_wav, W, H, out_path):
    list_path = out_path + ".concat.txt"
    try:
        with open(list_path, 'w', encoding='utf-8') as lf:
            lf.write("ffconcat version 1.0\n")
            for img, dur in zip(imgs, durs):
                safe = img.replace("\\", "/")
                lf.write(f"file '{safe}'\n")
                lf.write(f"duration {dur:.4f}\n")
            if imgs:
                lf.write(f"file '{imgs[-1].replace(chr(92), '/')}'\n")

        cmd = [
            ffmpeg_exe, "-y",
            "-f", "concat", "-safe", "0", "-i", list_path,
            "-i", merged_wav,
            "-vf", f"scale={W}:{H}",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-tune", "fastdecode",
            "-c:a", "aac", "-b:a", "128k",
            "-af", "apad",
            "-movflags", "+faststart",
            "-threads", "0",
            "-shortest",
            out_path
        ]
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    finally:
        try: os.remove(list_path)
        except: pass


# ─── V5 Per-Group Video Worker ────────────────────────────────────────────────
def _process_question_group(
    group_idx, group_q_indices, all_questions,
    W, H, portrait, vi, sapi_rate, out_dir,
    tick_wav_master, ffmpeg_exe,
    show_explanation, timer_seconds, log_fn, cancel_fn
):
    """
    V5 engine — adds:
    • Random premium theme selection (no consecutive repeats)
    • Per-slide breathing glow phase
    • Cinematic transitions between slides
    • Audio-sync-preserving transition timing
    """
    n_themes    = len(THEMES)
    q_nums      = [all_questions[idx]["number"] for idx in group_q_indices]
    group_start = time.time()

    # ── Uniqueness Engine: fresh RNG seeded from os.urandom ────────────────
    seed = int.from_bytes(os.urandom(4), 'little')
    rng  = random.Random(seed)

    # Theme selection: random, no consecutive repeats
    all_slots   = 1 + len(group_q_indices)  # hook + one per question
    slot_themes = _pick_themes_no_repeat(rng, n_themes, all_slots)
    hook_theme  = slot_themes[0]
    q_themes    = slot_themes[1:]

    try:
        group_questions = [all_questions[idx] for idx in group_q_indices]
        slides = build_video_slides(group_questions, show_explanation,
                                    timer_seconds, hook_theme, q_themes, rng)

        with tempfile.TemporaryDirectory() as td:
            # ── STEP 1: generate all audio in parallel ─────────────────
            audio_files  = {}
            tts_results  = {}
            tts_threads  = []

            for i, s in enumerate(slides):
                wav_path = os.path.join(td, f"a{i}.wav")
                if s['is_tick']:
                    shutil.copy2(tick_wav_master, wav_path)
                    audio_files[i] = wav_path
                elif s.get('fixed_dur') and not s.get('speak', '').strip():
                    generate_silent_wav(wav_path, float(s['fixed_dur']))
                    audio_files[i] = wav_path
                else:
                    speak_text = s.get('speak', '') or ' '
                    t = threading.Thread(
                        target=tts_worker,
                        args=(speak_text, wav_path, vi, sapi_rate, tts_results, i),
                        daemon=True)
                    tts_threads.append(t)
                    t.start()

            for t in tts_threads:
                t.join(timeout=30)

            for i, wav_path in tts_results.items():
                audio_files[i] = wav_path

            if cancel_fn():
                return None, q_nums, 0

            # ── STEP 2: render images + transitions ────────────────────
            # Pre-select a unique transition for each slide boundary
            n_transitions = len(slides)
            trans_per_slide = [rng.choice(PREMIUM_TRANSITIONS)
                               for _ in range(n_transitions)]

            imgs      = []
            durs      = []
            prev_img  = None
            frame_idx = 0

            for i, s in enumerate(slides):
                if cancel_fn():
                    break

                wav_path = audio_files.get(i, os.path.join(td, f"a{i}.wav"))
                if not os.path.exists(wav_path):
                    generate_silent_wav(wav_path, 1.5)

                dur = wav_duration(wav_path, 1.5)
                if s['is_tick']:
                    dur = max(dur, float(timer_seconds))
                min_dur = s.get('min_dur', 0.0)
                if min_dur and dur < min_dur:
                    padded_path = os.path.join(td, f"a{i}_padded.wav")
                    pad_secs    = min_dur - dur
                    try:
                        with wave.open(wav_path, 'r') as src_wf:
                            src_frames = src_wf.readframes(src_wf.getnframes())
                            src_rate   = src_wf.getframerate()
                            src_ch     = src_wf.getnchannels()
                            src_sw     = src_wf.getsampwidth()
                        pad_bytes = int(src_rate * pad_secs) * src_ch * src_sw
                        with wave.open(padded_path, 'w') as dst_wf:
                            dst_wf.setnchannels(src_ch)
                            dst_wf.setsampwidth(src_sw)
                            dst_wf.setframerate(src_rate)
                            dst_wf.writeframes(src_frames)
                            dst_wf.writeframes(b'\x00' * pad_bytes)
                        audio_files[i] = padded_path
                        wav_path       = padded_path
                        dur            = wav_duration(padded_path, min_dur)
                    except Exception:
                        dur = max(dur, min_dur)

                # Render main slide image
                slide_img = render_slide(s, W, H, portrait)

                # ── Cinematic transition into this slide ───────────────
                if prev_img is not None and dur > _TRANS_TOTAL_DUR * 2.0:
                    trans_type   = trans_per_slide[i]
                    trans_frames = _render_transition_frames(
                        prev_img, slide_img, trans_type, _N_TRANS_FRAMES
                    )
                    for j, tf in enumerate(trans_frames):
                        tf_path = os.path.join(td, f"tr{i}_{j}.jpg")
                        tf.save(tf_path, 'JPEG', quality=88)
                        imgs.append(tf_path)
                        durs.append(_TRANS_FRAME_DUR)
                    # Subtract transition time from this slide's still duration
                    dur = max(0.3, dur - _TRANS_TOTAL_DUR)

                img_path = os.path.join(td, f"s{i}.jpg")
                slide_img.save(img_path, 'JPEG', quality=92)
                imgs.append(img_path)
                durs.append(dur)

                prev_img = slide_img

            if cancel_fn():
                return None, q_nums, 0

            # ── STEP 3: merge WAVs ─────────────────────────────────────
            ordered_wavs = [audio_files.get(i, os.path.join(td, f"a{i}.wav"))
                            for i in range(len(slides))]
            merged_wav = os.path.join(td, "merged_audio.wav")
            _merge_wavs(ordered_wavs, merged_wav)

            # ── STEP 4: output filename ────────────────────────────────
            if len(q_nums) == 1:
                out_path = os.path.join(out_dir, f"Question_{q_nums[0]}_video.mp4")
            else:
                out_path = os.path.join(out_dir,
                    f"Quiz_Q{q_nums[0]}_to_Q{q_nums[-1]}_video.mp4")

            # ── STEP 5: FFmpeg ─────────────────────────────────────────
            result  = _ffmpeg_assemble(ffmpeg_exe, imgs, durs, merged_wav,
                                       W, H, out_path)
            elapsed = time.time() - group_start
            label   = (f"Q{q_nums[0]}" if len(q_nums) == 1
                       else f"Q{q_nums[0]}-Q{q_nums[-1]}")

            if result.returncode == 0:
                log_fn(f"[OK] {label} done in {elapsed:.1f}s  "
                       f"({len(slides)} slides + transitions)"
                       f"  -> {os.path.basename(out_path)}")
                return out_path, q_nums, elapsed
            else:
                err = result.stderr[-400:].decode(errors='ignore')
                log_fn(f"[ERROR] {label} FFmpeg failed ({elapsed:.1f}s): {err}")
                return None, q_nums, elapsed

    except Exception as e:
        log_fn(f"[ERROR] Group {q_nums} crashed: {e}")
        import traceback
        log_fn(traceback.format_exc())
        return None, q_nums, time.time() - group_start


# ─── Scrollable Frame ─────────────────────────────────────────────────────────
class ScrollableFrame(tk.Frame):
    def __init__(self, parent, bg="#0B0F19", **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self._canvas    = tk.Canvas(self, bg=bg, highlightthickness=0)
        self._scrollbar = tk.Scrollbar(self, orient="vertical",
                                       command=self._canvas.yview,
                                       bg="#1E293B", troughcolor="#0B0F19")
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.inner   = tk.Frame(self._canvas, bg=bg)
        self._win_id = self._canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",   self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind("<Enter>",  self._bind_wheel)
        self._canvas.bind("<Leave>",  self._unbind_wheel)

    def _on_inner_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._win_id, width=event.width)

    def _bind_wheel(self, event):
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_wheel(self, event):
        self._canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ─── Main Application ─────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()

        if not HAS_PIL:
            messagebox.showerror(
                "Pillow Missing",
                "Please install Pillow:\n\n  pip install pillow\n\nThen restart.")
            self.destroy()
            return

        self.title(
            "TXT 2 SHORTS V5  \u2605 PREMIUM CINEMATIC ENGINE  |  "
            "55+ Themes \u2022 Transitions \u2022 Glow \u2022 Unique Videos"
        )
        self.geometry("1080x860")
        self.configure(bg="#0B0F19")
        self.minsize(920, 720)

        self.html_file_path   = tk.StringVar()
        self.output_dir_path  = tk.StringVar()
        self.selected_voice   = tk.StringVar()
        self.playback_speed   = tk.DoubleVar(value=1.0)
        self.video_resolution = tk.StringVar(value="1080x1920 (Portrait 9:16 Shorts)")
        self.max_workers_var  = tk.IntVar(value=2)

        self.show_explanation_var    = tk.BooleanVar(value=True)
        self.questions_per_video_var = tk.IntVar(value=1)
        self._qpv_custom             = tk.StringVar()
        self.timer_seconds_var       = tk.StringVar(value="10")
        self._timer_custom           = tk.StringVar()

        self.questions_count = 0
        self.questions_list  = []
        self.is_cancelling   = False

        import win32com.client
        self._com   = win32com.client.Dispatch("SAPI.SpVoice")
        self.voices = self._com.GetVoices()
        self.voice_names = [self.voices.Item(i).GetDescription()
                            for i in range(self.voices.Count)]
        if self.voice_names:
            self.selected_voice.set(self.voice_names[0])

        self._setup_ui()
        self._setup_dd()

    # ─── UI ──────────────────────────────────────────────────────────────────
    def _setup_ui(self):
        hf = tk.Frame(self, bg="#0B0F19")
        hf.pack(fill=tk.X, padx=24, pady=(14, 8))

        tk.Label(
            hf,
            text="TXT 2 SHORTS V5  \u2605  PREMIUM CINEMATIC ENGINE",
            fg="#00CEC9", bg="#0B0F19",
            font=("Segoe UI", 17, "bold")
        ).pack(anchor="w")

        tk.Label(
            hf,
            text=(
                "55+ Glowing Themes  \u2022  Cinematic Transitions  \u2022  "
                "Breathing Glow  \u2022  Dynamic Sizing  \u2022  Unique Every Export"
            ),
            fg="#94A3B8", bg="#0B0F19",
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(2, 0))

        body = tk.Frame(self, bg="#0B0F19")
        body.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 14))

        lc_outer = tk.Frame(body, bg="#0B0F19")
        lc_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))

        self.drop_c = tk.Canvas(lc_outer, bg="#151B2C", highlightthickness=2,
                                highlightbackground="#1E293B", height=110)
        self.drop_c.pack(fill=tk.X, pady=(0, 8))
        self.drop_c.bind("<Enter>",
                         lambda e: self.drop_c.config(highlightbackground="#00CEC9"))
        self.drop_c.bind("<Leave>",
                         lambda e: self.drop_c.config(highlightbackground="#1E293B"))
        self.drop_c.bind("<Button-1>", lambda e: self._browse_in())
        self._dtid = self.drop_c.create_text(
            200, 55,
            text="Drag & Drop .txt file here\nor Click to Browse",
            fill="#94A3B8", font=("Segoe UI", 11, "bold"), justify=tk.CENTER)
        self.drop_c.bind("<Configure>",
            lambda e: self.drop_c.coords(self._dtid, e.width / 2, e.height / 2))

        sc = tk.Frame(lc_outer, bg="#1E293B", padx=10, pady=7)
        sc.pack(fill=tk.X, pady=(0, 8))
        self.lbl_fn = tk.Label(sc, text="No file loaded", fg="#F8FAFC",
                               bg="#1E293B", font=("Segoe UI", 10, "bold"), anchor="w")
        self.lbl_fn.pack(fill=tk.X)
        self.lbl_qc = tk.Label(sc, text="0 questions parsed", fg="#94A3B8",
                               bg="#1E293B", font=("Segoe UI", 9), anchor="w")
        self.lbl_qc.pack(fill=tk.X, pady=(2, 0))

        scroll_frame = ScrollableFrame(lc_outer, bg="#0B0F19")
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        sf_parent = scroll_frame.inner

        sf = tk.LabelFrame(sf_parent, text=" Settings ", fg="#00CEC9",
                           bg="#151B2C", font=("Segoe UI", 10, "bold"),
                           padx=12, pady=10, bd=1, relief="solid")
        sf.pack(fill=tk.X, pady=(0, 8))

        tk.Label(sf, text="Output Directory:", fg="#F8FAFC", bg="#151B2C",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        od = tk.Frame(sf, bg="#151B2C"); od.pack(fill=tk.X, pady=(3, 9))
        tk.Entry(od, textvariable=self.output_dir_path, bg="#0B0F19",
                 fg="#F8FAFC", insertbackground="#F8FAFC", relief="flat",
                 font=("Segoe UI", 9), bd=5).pack(
                     side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        tk.Button(od, text="Browse", bg="#1E293B", fg="#F8FAFC", relief="flat",
                  font=("Segoe UI", 9),
                  command=self._browse_out).pack(side=tk.RIGHT)

        tk.Label(sf, text="Voice Language (SAPI5 Offline):", fg="#F8FAFC",
                 bg="#151B2C", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Combobox(sf, textvariable=self.selected_voice,
                     values=self.voice_names, state="readonly",
                     font=("Segoe UI", 9)).pack(fill=tk.X, pady=(3, 9))

        tk.Label(sf, text="Speech Speed:", fg="#F8FAFC", bg="#151B2C",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Scale(sf, from_=0.5, to=2.5, resolution=0.1, orient=tk.HORIZONTAL,
                 variable=self.playback_speed, bg="#151B2C", fg="#F8FAFC",
                 highlightthickness=0, troughcolor="#0B0F19",
                 activebackground="#00CEC9").pack(fill=tk.X, pady=(3, 9))

        tk.Label(sf, text="Aspect Ratio / Resolution:", fg="#F8FAFC",
                 bg="#151B2C", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Combobox(sf, textvariable=self.video_resolution,
                     values=["1080x1920 (Portrait 9:16 Shorts)",
                             "1920x1080 (Landscape 16:9)",
                             "1280x720 (Landscape 16:9)"],
                     state="readonly",
                     font=("Segoe UI", 9)).pack(fill=tk.X, pady=(3, 9))

        wf = tk.Frame(sf, bg="#151B2C"); wf.pack(fill=tk.X, pady=(0, 4))
        tk.Label(wf, text="Parallel Workers (more = faster, uses more RAM):",
                 fg="#FDCB6E", bg="#151B2C",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        wf2 = tk.Frame(wf, bg="#151B2C"); wf2.pack(fill=tk.X, pady=(3, 0))
        for n, label in [(1, "1 — Safe"), (2, "2 — Fast"),
                         (4, "4 — Turbo"), (6, "6 — Max")]:
            tk.Radiobutton(wf2, text=label, variable=self.max_workers_var,
                           value=n, bg="#151B2C", fg="#F8FAFC",
                           selectcolor="#0B0F19", activebackground="#151B2C",
                           activeforeground="#00CEC9",
                           font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 10))

        # ── Feature panels ─────────────────────────────────────────────────
        nf = tk.LabelFrame(sf_parent, text=" Features ", fg="#A855F7",
                           bg="#151B2C", font=("Segoe UI", 10, "bold"),
                           padx=12, pady=10, bd=1, relief="solid")
        nf.pack(fill=tk.X, pady=(0, 8))

        # V5 feature info banner
        v5_banner = tk.Frame(nf, bg="#0B0F19", padx=8, pady=6)
        v5_banner.pack(fill=tk.X, pady=(0, 10))
        tk.Label(v5_banner,
                 text="\u2728 V5 ACTIVE: 55+ Themes \u2022 Transitions \u2022 "
                      "Breathing Glow \u2022 Unique Every Export",
                 fg="#00CEC9", bg="#0B0F19",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")

        # Explanation
        tk.Label(nf, text="Feature 1 \u2014 Explanation Slides:", fg="#C084FC",
                 bg="#151B2C", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Radiobutton(nf, text="Show Explanations",
                       variable=self.show_explanation_var, value=True,
                       bg="#151B2C", fg="#F8FAFC", selectcolor="#0B0F19",
                       activebackground="#151B2C", activeforeground="#A855F7",
                       font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 2))
        tk.Radiobutton(nf, text="Hide Explanations",
                       variable=self.show_explanation_var, value=False,
                       bg="#151B2C", fg="#F8FAFC", selectcolor="#0B0F19",
                       activebackground="#151B2C", activeforeground="#A855F7",
                       font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 10))

        tk.Frame(nf, bg="#2D3748", height=1).pack(fill=tk.X, pady=(0, 10))

        # Questions per video
        tk.Label(nf, text="Feature 2 \u2014 Questions per Video:", fg="#C084FC",
                 bg="#151B2C", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        f2b = tk.Frame(nf, bg="#151B2C"); f2b.pack(fill=tk.X, pady=(6, 4))
        for n, label in [(1,"1 Q"), (3,"3 Qs"), (5,"5 Qs"),
                         (10,"10 Qs"), (15,"15 Qs"), (20,"20 Qs")]:
            tk.Radiobutton(f2b, text=label,
                           variable=self.questions_per_video_var, value=n,
                           bg="#151B2C", fg="#F8FAFC", selectcolor="#0B0F19",
                           activebackground="#151B2C", activeforeground="#A855F7",
                           font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))
        f2c = tk.Frame(nf, bg="#151B2C"); f2c.pack(fill=tk.X, pady=(2, 10))
        tk.Label(f2c, text="Custom:", fg="#94A3B8", bg="#151B2C",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        tk.Entry(f2c, textvariable=self._qpv_custom, bg="#0B0F19", fg="#F8FAFC",
                 insertbackground="#F8FAFC", relief="flat", width=6,
                 font=("Segoe UI", 9), bd=4).pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(f2c, text="Set", bg="#1E293B", fg="#A855F7", relief="flat",
                  font=("Segoe UI", 9),
                  command=self._apply_custom_qpv).pack(side=tk.LEFT, padx=(6, 0))
        tk.Label(f2c, text="(1\u2013200)", fg="#475569", bg="#151B2C",
                 font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(6, 0))
        self.lbl_qpv = tk.Label(nf, text="Currently: 1 question per video",
                                fg="#A855F7", bg="#151B2C", font=("Segoe UI", 9))
        self.lbl_qpv.pack(anchor="w", pady=(0, 0))
        self.questions_per_video_var.trace_add("write", self._refresh_qpv_label)

        tk.Frame(nf, bg="#2D3748", height=1).pack(fill=tk.X, pady=(10, 10))

        # Timer
        tk.Label(nf, text="Feature 3 \u2014 Timer Duration (seconds):", fg="#C084FC",
                 bg="#151B2C", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        f3b = tk.Frame(nf, bg="#151B2C"); f3b.pack(fill=tk.X, pady=(6, 4))
        for secs, label in [(5,"5s"), (7,"7s"), (10,"10s"),
                            (15,"15s"), (20,"20s"), (30,"30s")]:
            tk.Radiobutton(f3b, text=label,
                           variable=self.timer_seconds_var, value=str(secs),
                           bg="#151B2C", fg="#F8FAFC", selectcolor="#0B0F19",
                           activebackground="#151B2C", activeforeground="#A855F7",
                           font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))
        f3c = tk.Frame(nf, bg="#151B2C"); f3c.pack(fill=tk.X, pady=(2, 6))
        tk.Label(f3c, text="Custom seconds:", fg="#94A3B8", bg="#151B2C",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        tk.Entry(f3c, textvariable=self._timer_custom, bg="#0B0F19", fg="#F8FAFC",
                 insertbackground="#F8FAFC", relief="flat", width=6,
                 font=("Segoe UI", 9), bd=4).pack(side=tk.LEFT, padx=(6, 0))
        tk.Button(f3c, text="Set", bg="#1E293B", fg="#A855F7", relief="flat",
                  font=("Segoe UI", 9),
                  command=self._apply_custom_timer).pack(side=tk.LEFT, padx=(6, 0))
        tk.Label(f3c, text="(3\u2013120)", fg="#475569", bg="#151B2C",
                 font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(6, 0))
        self.lbl_timer = tk.Label(nf, text="Currently: 10 seconds",
                                  fg="#A855F7", bg="#151B2C", font=("Segoe UI", 9))
        self.lbl_timer.pack(anchor="w")
        self.timer_seconds_var.trace_add("write", self._refresh_timer_label)

        # ── Start / Cancel buttons ──────────────────────────────────────────
        btn_frame = tk.Frame(lc_outer, bg="#0B0F19")
        btn_frame.pack(fill=tk.X, pady=(8, 0))
        self.btn_go = tk.Button(
            btn_frame,
            text="\u2728  Start V5  PREMIUM  Video Creation",
            bg="#00CEC9", fg="#0B0F19",
            font=("Segoe UI", 11, "bold"),
            relief="flat", padx=14, pady=10,
            activebackground="#81ECEC",
            command=self._start)
        self.btn_go.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.btn_stop = tk.Button(
            btn_frame, text="Cancel",
            bg="#EF4444", fg="#F8FAFC",
            font=("Segoe UI", 11, "bold"),
            relief="flat", padx=14, pady=10,
            state=tk.DISABLED, command=self._cancel)
        self.btn_stop.pack(side=tk.RIGHT)

        # ── Right panel ─────────────────────────────────────────────────────
        rc = tk.Frame(body, bg="#0B0F19", width=480)
        rc.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(12, 0))
        rc.pack_propagate(False)

        pf = tk.LabelFrame(rc, text=" Progress Dashboard ", fg="#00CEC9",
                           bg="#151B2C", font=("Segoe UI", 10, "bold"),
                           padx=12, pady=12, bd=1, relief="solid")
        pf.pack(fill=tk.X, pady=(0, 10))
        self.lbl_status = tk.Label(pf, text="Status: Idle", fg="#F8FAFC",
                                   bg="#151B2C", font=("Segoe UI", 10, "bold"),
                                   anchor="w")
        self.lbl_status.pack(fill=tk.X)
        self.prog_c = tk.Canvas(pf, bg="#0B0F19", height=14, highlightthickness=0)
        self.prog_c.pack(fill=tk.X, pady=7)
        self._prog(0)
        self.lbl_done = tk.Label(pf, text="Completed: 0 / 0 videos",
                                 fg="#94A3B8", bg="#151B2C",
                                 font=("Segoe UI", 9), anchor="w")
        self.lbl_done.pack(fill=tk.X)
        self.lbl_time = tk.Label(pf, text="Elapsed: 00:00:00  |  ETA: --:--:--",
                                 fg="#94A3B8", bg="#151B2C",
                                 font=("Segoe UI", 9), anchor="w")
        self.lbl_time.pack(fill=tk.X)
        self.lbl_speed = tk.Label(pf, text="Speed: --",
                                  fg="#00CEC9", bg="#151B2C",
                                  font=("Segoe UI", 9, "bold"), anchor="w")
        self.lbl_speed.pack(fill=tk.X, pady=(3, 0))
        self.lbl_settings_summary = tk.Label(pf, text="",
                                             fg="#A855F7", bg="#151B2C",
                                             font=("Segoe UI", 9), anchor="w")
        self.lbl_settings_summary.pack(fill=tk.X, pady=(3, 0))

        lf_frame = tk.LabelFrame(rc, text=" Console Logs ", fg="#00CEC9",
                                 bg="#151B2C", font=("Segoe UI", 10, "bold"),
                                 padx=8, pady=8, bd=1, relief="solid")
        lf_frame.pack(fill=tk.BOTH, expand=True)
        self.log_txt = tk.Text(lf_frame, bg="#0B0F19", fg="#F8FAFC",
                               font=("Consolas", 9),
                               insertbackground="#F8FAFC", relief="flat",
                               wrap=tk.WORD, state=tk.DISABLED)
        self.log_txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scr = tk.Scrollbar(lf_frame, command=self.log_txt.yview,
                           bg="#151B2C", troughcolor="#0B0F19")
        scr.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_txt.configure(yscrollcommand=scr.set)

        self._log("[V5] \u2728 TXT 2 SHORTS V5  \u2014  PREMIUM CINEMATIC ENGINE Ready!")
        self._log(f"[V5] {len(THEMES)} premium themes loaded.")
        self._log(f"[V5] {len(PREMIUM_TRANSITIONS)} cinematic transitions available.")
        self._log("[V5] Breathing glow, dynamic sizing, unique video engine: ACTIVE")
        self._log("[V5] Drop your .txt file, configure settings, then hit Start!")

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _refresh_qpv_label(self, *_):
        n = self.questions_per_video_var.get()
        self.lbl_qpv.configure(
            text=f"Currently: {n} question{'s' if n > 1 else ''} per video")

    def _refresh_timer_label(self, *_):
        self.lbl_timer.configure(
            text=f"Currently: {self.timer_seconds_var.get()} seconds")

    def _apply_custom_qpv(self):
        val = self._qpv_custom.get().strip()
        if val.isdigit() and 1 <= int(val) <= 200:
            self.questions_per_video_var.set(int(val))
        else:
            messagebox.showwarning("Invalid", "Enter a number between 1 and 200.")

    def _apply_custom_timer(self):
        val = self._timer_custom.get().strip()
        if val.isdigit() and 3 <= int(val) <= 120:
            self.timer_seconds_var.set(val)
        else:
            messagebox.showwarning("Invalid", "Enter a number between 3 and 120.")

    def _log(self, msg):
        self.log_txt.configure(state=tk.NORMAL)
        self.log_txt.insert(tk.END, msg + "\n")
        self.log_txt.see(tk.END)
        self.log_txt.configure(state=tk.DISABLED)

    def _prog(self, r):
        self.prog_c.delete("all")
        w = self.prog_c.winfo_width() or 400
        self.prog_c.create_rectangle(0, 0, w, 14, fill="#1E293B", outline="")
        if r > 0.01:
            self.prog_c.create_rectangle(0, 0, w * r, 14, fill="#00CEC9", outline="")

    def _setup_dd(self):
        try:
            self._ddt = WinDropTarget(self, self._dropped)
            self._log("[SYSTEM] Drag & drop ready.")
        except Exception as e:
            self._log(f"[WARNING] Drag & drop unavailable: {e}")

    def _dropped(self, fp):
        if not fp.lower().endswith((".txt", ".html")):
            messagebox.showerror("Invalid File", "Please drop a .txt file.")
            return
        self._load(fp)

    def _browse_in(self):
        fp = filedialog.askopenfilename(
            filetypes=[("Text/HTML", "*.txt;*.html"), ("All", "*.*")])
        if fp: self._load(fp)

    def _browse_out(self):
        d = filedialog.askdirectory()
        if d: self.output_dir_path.set(d)

    def _load(self, fp):
        self.html_file_path.set(fp)
        self.lbl_fn.configure(text=os.path.basename(fp))
        self._log(f"[SYSTEM] Loading: {fp}")
        try:
            qs = parse_input_file(fp)
            self.questions_list  = qs
            self.questions_count = len(qs)
            self.lbl_qc.configure(text=f"{self.questions_count} questions parsed.")
            self._log(f"[INFO] Parsed {self.questions_count} questions.")
            self.output_dir_path.set(os.path.join(os.path.dirname(fp), "videos"))
        except Exception as e:
            self.questions_count = 0
            self.lbl_qc.configure(text="Error parsing questions.")
            self._log(f"[ERROR] {e}")
            messagebox.showerror("Parse Error", str(e))

    def _cancel(self):
        self.is_cancelling = True
        self.lbl_status.configure(text="Status: Cancelling...")
        self._log("[SYSTEM] Cancel requested...")
        self.btn_stop.configure(state=tk.DISABLED)

    def _get_timer_seconds(self):
        try: return max(3, min(120, int(self.timer_seconds_var.get())))
        except: return 10

    def _start(self):
        if not self.html_file_path.get():
            messagebox.showerror("No Input", "Please select a .txt file first.")
            return
        if not self.questions_count:
            messagebox.showerror("No Questions", "No valid questions found.")
            return
        if not self.output_dir_path.get():
            messagebox.showerror("No Output", "Please choose an output directory.")
            return
        self.btn_go.configure(state=tk.DISABLED)
        self.btn_stop.configure(state=tk.NORMAL)
        self.is_cancelling = False
        self._prog(0)
        threading.Thread(target=self._run, daemon=True).start()

    # ── Core processing ───────────────────────────────────────────────────────
    def _run(self):
        out_dir = self.output_dir_path.get()
        os.makedirs(out_dir, exist_ok=True)

        vi = (self.voice_names.index(self.selected_voice.get())
              if self.selected_voice.get() in self.voice_names else 0)

        speed      = self.playback_speed.get()
        sapi_rate  = max(-10, min(10, int((speed - 1.0) * 5)))

        res_str    = self.video_resolution.get()
        parts      = res_str.split('x')
        W          = int(parts[0].strip())
        H          = int(parts[1].split()[0].strip())
        portrait   = H > W

        qpv         = self.questions_per_video_var.get()
        show_expl   = self.show_explanation_var.get()
        timer_secs  = self._get_timer_seconds()
        max_workers = self.max_workers_var.get()

        qs          = self.questions_list
        n_groups    = math.ceil(len(qs) / qpv)
        groups      = [list(range(i * qpv, min((i + 1) * qpv, len(qs))))
                       for i in range(n_groups)]

        self.lbl_settings_summary.configure(
            text=f"V5: {len(THEMES)} themes \u2022 {len(PREMIUM_TRANSITIONS)} transitions "
                 f"\u2022 {qpv}Q/video \u2022 {W}\u00d7{H}"
        )
        self._log(f"[V5] Starting: {len(qs)} questions \u2192 {n_groups} videos "
                  f"| {W}\u00d7{H} | {qpv}Q/video | timer={timer_secs}s "
                  f"| expl={show_expl} | workers={max_workers}")

        # Pre-generate master tick wav
        with tempfile.TemporaryDirectory() as td_main:
            tick_wav = os.path.join(td_main, "tick_master.wav")
            generate_ticking_audio(tick_wav, duration_sec=float(timer_secs) + 1.0)
            ffmpeg_exe = _find_ffmpeg()
            self._log(f"[V5] FFmpeg: {ffmpeg_exe}")

            start_t   = time.time()
            done_count = 0
            ok_count   = 0

            def _update_ui():
                elapsed = time.time() - start_t
                eh, em = divmod(int(elapsed), 3600)
                em, es = divmod(em, 60)
                elapsed_str = f"{eh:02d}:{em:02d}:{es:02d}"
                if done_count > 0:
                    eta_s = elapsed * (n_groups - done_count) / done_count
                    etah, etam = divmod(int(eta_s), 3600)
                    etam, etas = divmod(etam, 60)
                    eta_str = f"{etah:02d}:{etam:02d}:{etas:02d}"
                else:
                    eta_str = "--:--:--"
                spd = f"{done_count / elapsed:.2f} vid/s" if elapsed > 0 else "--"
                self.after(0, lambda: [
                    self.lbl_time.configure(
                        text=f"Elapsed: {elapsed_str}  |  ETA: {eta_str}"),
                    self.lbl_speed.configure(text=f"Speed: {spd}"),
                    self.lbl_done.configure(
                        text=f"Completed: {done_count} / {n_groups} videos"),
                    self._prog(done_count / n_groups),
                ])

            self.after(0, lambda: self.lbl_status.configure(
                text=f"Status: Running... 0/{n_groups}"))

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {
                    pool.submit(
                        _process_question_group,
                        gi, grp, qs, W, H, portrait, vi, sapi_rate,
                        out_dir, tick_wav, ffmpeg_exe,
                        show_expl, timer_secs,
                        self._log, lambda: self.is_cancelling
                    ): gi
                    for gi, grp in enumerate(groups)
                }

                for fut in concurrent.futures.as_completed(futures):
                    if self.is_cancelling:
                        break
                    try:
                        out_path, q_nums, elapsed = fut.result()
                        ok_count  += 1 if out_path else 0
                    except Exception as e:
                        self._log(f"[ERROR] Future exception: {e}")
                    done_count += 1
                    n_done = done_count
                    self.after(0, lambda nd=n_done: self.lbl_status.configure(
                        text=f"Status: Running... {nd}/{n_groups}"))
                    _update_ui()

        total_elapsed = time.time() - start_t
        th, tm = divmod(int(total_elapsed), 3600)
        tm, ts = divmod(tm, 60)
        msg = (f"[V5] Done! {ok_count}/{n_groups} videos created "
               f"in {th:02d}:{tm:02d}:{ts:02d}  \u2192  {out_dir}")
        self._log(msg)
        self.after(0, lambda: [
            self.lbl_status.configure(
                text=f"Status: Done! {ok_count}/{n_groups} videos"),
            self._prog(1.0),
            self.btn_go.configure(state=tk.NORMAL),
            self.btn_stop.configure(state=tk.DISABLED),
            messagebox.showinfo(
                "V5 Complete",
                f"{ok_count} of {n_groups} videos created.\n\nSaved to:\n{out_dir}"
            ),
        ])


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
