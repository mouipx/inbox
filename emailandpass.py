#!/usr/bin/env python3
# ep_viewer_retro_cyber.py

import tkinter as tk
import tkinter.font as tkfont
import math
import ssl
import imaplib
import email
import email.utils
import sys
from email.header import decode_header
import re
import threading
import queue
from datetime import datetime
from tkinter import messagebox
from pathlib import Path
import random
import webbrowser
try:
    from tkinterweb import HtmlFrame
    HTML_RENDER_AVAILABLE = True
except ImportError:
    HTML_RENDER_AVAILABLE = False

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parent
    BUNDLE_DIR = APP_DIR

DATA_FILE = (APP_DIR / "emailsandpass.txt") if (APP_DIR / "emailsandpass.txt").exists() else (BUNDLE_DIR / "emailsandpass.txt")
GUI_DIR = BUNDLE_DIR / "guithings"
IMAP_SERVER = "imap.firstmail.ltd"
IMAP_PORT = 993
IMAP_TIMEOUT_SECONDS = 12
INBOX_MESSAGE_LIMIT = 20
MICROSOFT_SEARCH_SENDER = "account-security-noreply@accountprotection.microsoft.com"
MICROSOFT_CODE_PATTERNS = [
    re.compile(r"Your single-?use code is:\s*([0-9]{6})", flags=re.IGNORECASE),
    re.compile(
        r"To verify your email address use this security code:\s*([0-9]{6})",
        flags=re.IGNORECASE,
    ),
]
CHATGPT_CODE_PATTERNS = [
    re.compile(r"Your ChatGPT code is[:\s]*([0-9]{6})", re.IGNORECASE),
    re.compile(
        r"Enter\s+this\s+temporary\s+verification\s+code\s+to\s+continue[:\s]*([0-9]{6})",
        re.IGNORECASE | re.DOTALL
    ),
    re.compile(
        r"temporary\s+verification\s+code.*?([0-9]{6})",
        re.IGNORECASE | re.DOTALL
    ),
    re.compile(
        r"temporary\s+ChatGPT\s+login\s+code.*?([0-9]{6})",
        re.IGNORECASE | re.DOTALL
    ),
    re.compile(r"\b([0-9]{6})\b", re.IGNORECASE)
]
RECENT_MESSAGE_SCAN_LIMIT = 40


# ═══════════════════════════════════════════════════
#  CANVAS
# ═══════════════════════════════════════════════════
class CyberCanvas(tk.Canvas):
    def __init__(self, parent, bg, **kwargs):
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("bd", 0)
        super().__init__(parent, bg=bg, **kwargs)


# ═══════════════════════════════════════════════════
#  CYBER FRAME
# ═══════════════════════════════════════════════════
class CyberFrame(tk.Frame):
    def __init__(self, parent, border_color="#2a5a2a", glow_color="#5a8f5a",
                 corner_size=10, bg="#0a0f0a", show_corners=True,
                 show_notches=True, **kwargs):
        super().__init__(parent, bg=bg, **kwargs)
        self.border_color = border_color
        self.glow_color = glow_color
        self.corner_size = corner_size
        self.frame_bg = bg
        self.show_corners = show_corners
        self.show_notches = show_notches

        self._deco_canvas = CyberCanvas(self, bg=bg, width=0, height=0)
        self._deco_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._deco_canvas.tk.call("lower", self._deco_canvas._w)

        self.bind("<Configure>", self._redraw_border)

    def _redraw_border(self, event=None):
        c = self._deco_canvas
        c.delete("border")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return

        cs = self.corner_size
        pad = 1

        c.create_line(pad + cs, pad, w - pad - cs, pad,
                      fill=self.border_color, width=1, tags="border")
        c.create_line(w - pad, pad + cs, w - pad, h - pad - cs,
                      fill=self.border_color, width=1, tags="border")
        c.create_line(w - pad - cs, h - pad, pad + cs, h - pad,
                      fill=self.border_color, width=1, tags="border")
        c.create_line(pad, h - pad - cs, pad, pad + cs,
                      fill=self.border_color, width=1, tags="border")

        c.create_line(pad, pad + cs, pad + cs, pad,
                      fill=self.glow_color, width=2, tags="border")
        c.create_line(w - pad - cs, pad, w - pad, pad + cs,
                      fill=self.glow_color, width=2, tags="border")
        c.create_line(w - pad, h - pad - cs, w - pad - cs, h - pad,
                      fill=self.glow_color, width=2, tags="border")
        c.create_line(pad + cs, h - pad, pad, h - pad - cs,
                      fill=self.glow_color, width=2, tags="border")

        if self.show_corners:
            dot_r = 2
            for (dx, dy) in [(pad + cs, pad), (w - pad - cs, pad),
                             (w - pad, pad + cs), (w - pad, h - pad - cs),
                             (w - pad - cs, h - pad), (pad + cs, h - pad),
                             (pad, h - pad - cs), (pad, pad + cs)]:
                c.create_oval(dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r,
                              fill=self.glow_color, outline="", tags="border")


# ═══════════════════════════════════════════════════
#  GLITCH LABEL
# ═══════════════════════════════════════════════════
class GlitchLabel(tk.Canvas):
    def __init__(self, parent, text="", font=("Consolas", 10, "bold"),
                 fg="#9adf9a", bg="#0a0f0a", glitch_interval=3000,
                 glitch_chars="@#$%&!?░▒▓█", **kwargs):
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("bd", 0)
        super().__init__(parent, bg=bg, **kwargs)
        self._text = text
        self._font = font
        self._fg = fg
        self._bg = bg
        self._glitch_interval = glitch_interval
        self._glitch_chars = glitch_chars
        self._is_glitching = False

        self.bind("<Configure>", self._redraw)
        self._schedule_glitch()

    def set_text(self, text):
        self._text = text
        self._redraw()

    def _redraw(self, event=None):
        self.delete("all")
        w = self.winfo_width() or 100
        h = self.winfo_height() or 20
        self.create_text(w // 2, h // 2, text=self._text,
                         fill=self._fg, font=self._font, tags="text")

    def _schedule_glitch(self):
        delay = self._glitch_interval + random.randint(-500, 1500)
        self.after(max(500, delay), self._do_glitch)

    def _do_glitch(self):
        if not self.winfo_exists():
            return
        if self._is_glitching:
            self._schedule_glitch()
            return

        self._is_glitching = True
        original = self._text
        glitch_count = random.randint(2, 4)

        def glitch_step(n):
            if not self.winfo_exists():
                return
            if n <= 0:
                self.set_text(original)
                self._is_glitching = False
                self._schedule_glitch()
                return
            chars = list(original)
            num_glitch = random.randint(1, max(1, len(chars) // 3))
            for _ in range(num_glitch):
                idx = random.randint(0, max(0, len(chars) - 1))
                chars[idx] = random.choice(self._glitch_chars)
            self.set_text("".join(chars))
            self.after(60, lambda: glitch_step(n - 1))

        glitch_step(glitch_count)


# ═══════════════════════════════════════════════════
#  PROGRESS BAR
# ═══════════════════════════════════════════════════
class CyberProgressBar(tk.Canvas):
    def __init__(self, parent, bg="#0a0f0a", bar_color="#3a6a3a",
                 glow_color="#9adf9a", height=4, **kwargs):
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("bd", 0)
        super().__init__(parent, bg=bg, height=height, **kwargs)
        self._bar_color = bar_color
        self._glow_color = glow_color
        self._pos = 0
        self._running = True
        self._animate()

    def _animate(self):
        if not self._running:
            return
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        self.delete("bar")
        w = self.winfo_width() or 200
        h = self.winfo_height() or 4

        seg_width = 3
        gap = 2
        total = seg_width + gap
        num_segs = w // total + 2
        self._pos = (self._pos + 2) % (w + 60)

        for i in range(num_segs):
            x = i * total
            dist = abs(x - self._pos)
            if dist < 30:
                intensity = 1.0 - (dist / 30.0)
                if intensity > 0.7:
                    color = self._glow_color
                elif intensity > 0.3:
                    color = self._bar_color
                else:
                    color = "#1a3a1a"
                self.create_rectangle(
                    x, 1, x + seg_width, h - 1,
                    fill=color, outline="", tags="bar"
                )
            else:
                if random.random() > 0.85:
                    self.create_rectangle(
                        x, 1, x + seg_width, h - 1,
                        fill="#0d1a0d", outline="", tags="bar"
                    )

        self.after(40, self._animate)

    def stop(self):
        self._running = False


# ═══════════════════════════════════════════════════
#  LOADING SPLASH SCREEN
# ═══════════════════════════════════════════════════
class LoadingSplash:
    def __init__(self, root, on_complete):
        self.root = root
        self.on_complete = on_complete
        self.width = 500
        self.height = 280
        self._closed = False

        # Colors
        self.bg = "#050a05"
        self.panel_bg = "#0a150a"
        self.border = "#2a5a2a"
        self.accent = "#3a6a3a"
        self.accent_glow = "#9adf9a"
        self.accent_bright = "#bfffbf"
        self.text = "#c8dfc8"
        self.text_dim = "#3d5a3d"
        self.text_muted = "#2a4a2a"
        self.code_green = "#7fff7f"

        # Configure root
        self.root.title("")
        self.root.configure(bg=self.bg)
        self.root.overrideredirect(True)  # Remove titlebar for splash
        self.root.attributes("-topmost", True)

        # Center on screen
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - self.width) // 2
        y = (sh - self.height) // 2
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

        self._font_mono = self._pick_font("Consolas", "Courier New")
        self._font_title = self._pick_font("Courier New", "Consolas")

        self._build()
        self._boot_lines = []
        self._current_line = 0
        self._progress = 0

        self._loading_messages = [
            ("BOOT", "Initializing kernel..."),
            ("SYS", "Loading credential matrix..."),
            ("CRYPT", "AES-256-GCM handshake OK"),
            ("NET", "Establishing IMAP tunnel..."),
            ("AUTH", "Verifying certificates..."),
            ("DATA", "Mounting encrypted store..."),
            ("SCAN", "Priming code scanners..."),
            ("READY", "System nominal ░ ONLINE"),
        ]

        self.root.after(100, self._start_boot_sequence)

    def _pick_font(self, *candidates):
        available = set(tkfont.families(self.root))
        for name in candidates:
            if name in available:
                return name
        return "TkDefaultFont"

    def _build(self):
        # Outer shell canvas for border
        self.shell = tk.Canvas(self.root, bg=self.bg,
                               highlightthickness=0, bd=0,
                               width=self.width, height=self.height)
        self.shell.pack(fill="both", expand=True)

        # Draw decorative border with cut corners
        self._draw_border()

        # Content frame
        self.content = tk.Frame(self.shell, bg=self.bg)
        self.shell.create_window(4, 4, window=self.content, anchor="nw",
                                 width=self.width - 8, height=self.height - 8)

        self.content.grid_rowconfigure(0, weight=0)
        self.content.grid_rowconfigure(1, weight=0)
        self.content.grid_rowconfigure(2, weight=1)
        self.content.grid_rowconfigure(3, weight=0)
        self.content.grid_rowconfigure(4, weight=0)
        self.content.grid_columnconfigure(0, weight=1)

        # ── LOGO / TITLE ──
        header = tk.Frame(self.content, bg=self.bg)
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 4))

        tk.Label(header, text="╔═══════════════════════════════════╗",
                 bg=self.bg, fg=self.accent,
                 font=(self._font_mono, 8)).pack()

        title_row = tk.Frame(header, bg=self.bg)
        title_row.pack(pady=(4, 0))

        tk.Label(title_row, text="◈", bg=self.bg, fg=self.accent_bright,
                 font=(self._font_mono, 16, "bold")).pack(side="left")
        tk.Label(title_row, text=" CRED-MATRIX ", bg=self.bg,
                 fg=self.accent_glow,
                 font=(self._font_title, 20, "bold")).pack(side="left")
        tk.Label(title_row, text="◈", bg=self.bg, fg=self.accent_bright,
                 font=(self._font_mono, 16, "bold")).pack(side="left")

        tk.Label(header, text="[ v3.0 ░ SECURE CREDENTIAL VAULT ]",
                 bg=self.bg, fg=self.text_dim,
                 font=(self._font_mono, 7, "bold")).pack(pady=(2, 0))

        tk.Label(header, text="╚═══════════════════════════════════╝",
                 bg=self.bg, fg=self.accent,
                 font=(self._font_mono, 8)).pack(pady=(2, 0))

        # ── BOOT LOG AREA ──
        log_border = tk.Frame(self.content, bg=self.accent, padx=1, pady=1)
        log_border.grid(row=2, column=0, sticky="nsew", padx=20, pady=8)

        log_inner = tk.Frame(log_border, bg="#020602")
        log_inner.pack(fill="both", expand=True)

        # Terminal header
        term_head = tk.Frame(log_inner, bg=self.panel_bg, height=16)
        term_head.pack(fill="x")
        term_head.pack_propagate(False)

        tk.Label(term_head, text=" ● ● ● ", bg=self.panel_bg,
                 fg=self.accent, font=(self._font_mono, 6)).pack(side="left")
        tk.Label(term_head, text="[boot.log]", bg=self.panel_bg,
                 fg=self.text_dim,
                 font=(self._font_mono, 6, "bold")).pack(side="left", padx=4)

        # Log text
        self.log_frame = tk.Frame(log_inner, bg="#020602")
        self.log_frame.pack(fill="both", expand=True, padx=8, pady=4)

        # ── PROGRESS BAR ──
        progress_row = tk.Frame(self.content, bg=self.bg)
        progress_row.grid(row=3, column=0, sticky="ew", padx=20, pady=(4, 4))

        self.progress_label = tk.Label(progress_row, text="INITIALIZING...",
                                        bg=self.bg, fg=self.accent_glow,
                                        font=(self._font_mono, 7, "bold"))
        self.progress_label.pack(side="left")

        self.progress_pct = tk.Label(progress_row, text="0%",
                                      bg=self.bg, fg=self.text_dim,
                                      font=(self._font_mono, 7, "bold"))
        self.progress_pct.pack(side="right")

        # Progress bar canvas
        pb_border = tk.Frame(self.content, bg=self.accent, padx=1, pady=1)
        pb_border.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 20))

        self.progress_canvas = tk.Canvas(pb_border, bg="#020602",
                                          height=12,
                                          highlightthickness=0, bd=0)
        self.progress_canvas.pack(fill="x")

    def _draw_border(self):
        c = self.shell
        w = self.width
        h = self.height
        pad = 2
        corner = 14

        # Main outer border lines
        c.create_line(pad + corner, pad, w - pad - corner, pad,
                      fill=self.border, width=1)
        c.create_line(w - pad, pad + corner, w - pad, h - pad - corner,
                      fill=self.border, width=1)
        c.create_line(w - pad - corner, h - pad, pad + corner, h - pad,
                      fill=self.border, width=1)
        c.create_line(pad, h - pad - corner, pad, pad + corner,
                      fill=self.border, width=1)

        # Angled corners with glow
        c.create_line(pad, pad + corner, pad + corner, pad,
                      fill=self.accent_glow, width=2)
        c.create_line(w - pad - corner, pad, w - pad, pad + corner,
                      fill=self.accent_glow, width=2)
        c.create_line(w - pad, h - pad - corner, w - pad - corner, h - pad,
                      fill=self.accent_glow, width=2)
        c.create_line(pad + corner, h - pad, pad, h - pad - corner,
                      fill=self.accent_glow, width=2)

        # Corner dots
        dot_r = 3
        for (cx, cy) in [
            (pad + corner, pad), (w - pad - corner, pad),
            (w - pad, pad + corner), (w - pad, h - pad - corner),
            (w - pad - corner, h - pad), (pad + corner, h - pad),
            (pad, h - pad - corner), (pad, pad + corner)
        ]:
            c.create_oval(cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r,
                          fill=self.accent, outline=self.accent_glow, width=1)

    def _start_boot_sequence(self):
        self._show_next_boot_line()

    def _show_next_boot_line(self):
        if self._closed:
            return

        if self._current_line >= len(self._loading_messages):
            self.root.after(300, self._finish)
            return

        tag, msg = self._loading_messages[self._current_line]

        # Update progress label
        self.progress_label.config(text=f">> {msg.upper()}")

        # Add line to log
        line_frame = tk.Frame(self.log_frame, bg="#020602")
        line_frame.pack(fill="x", anchor="w")

        # Timestamp
        ts = datetime.now().strftime("%H:%M:%S")
        tk.Label(line_frame, text=f"[{ts}]", bg="#020602",
                 fg=self.text_muted,
                 font=(self._font_mono, 7)).pack(side="left")

        # Tag
        tag_colors = {
            "BOOT": self.accent_glow,
            "SYS": "#5aafaf",
            "CRYPT": "#8a6abf",
            "NET": self.accent_glow,
            "AUTH": self.accent_bright,
            "DATA": "#5aafaf",
            "SCAN": self.accent_glow,
            "READY": self.code_green,
        }
        tag_color = tag_colors.get(tag, self.accent_glow)

        tk.Label(line_frame, text=f" [{tag}]", bg="#020602",
                 fg=tag_color,
                 font=(self._font_mono, 7, "bold")).pack(side="left")

        # Message
        tk.Label(line_frame, text=f" {msg}", bg="#020602",
                 fg=self.text,
                 font=(self._font_mono, 7)).pack(side="left")

        # OK status
        ok_color = self.code_green if tag == "READY" else self.accent_glow
        ok_text = "  [OK]" if tag != "READY" else "  [◈]"
        tk.Label(line_frame, text=ok_text, bg="#020602",
                 fg=ok_color,
                 font=(self._font_mono, 7, "bold")).pack(side="right")

        self._current_line += 1

        # Update progress
        target_pct = int((self._current_line / len(self._loading_messages)) * 100)
        self._animate_progress_to(target_pct)

        # Next line
        delay = random.randint(180, 320)
        self.root.after(delay, self._show_next_boot_line)

    def _animate_progress_to(self, target):
        if self._closed:
            return
        if self._progress < target:
            self._progress += 1
            self._draw_progress()
            self.root.after(15, lambda: self._animate_progress_to(target))
        else:
            self._draw_progress()

    def _draw_progress(self):
        if self._closed:
            return
        c = self.progress_canvas
        try:
            if not c.winfo_exists():
                return
        except Exception:
            return
        c.delete("all")
        w = c.winfo_width() or 440
        h = 12

        # Background segments
        seg_w = 6
        gap = 2
        total_seg = seg_w + gap
        num_segs = w // total_seg
        filled_segs = int((self._progress / 100.0) * num_segs)

        for i in range(num_segs):
            x = i * total_seg + 1
            if i < filled_segs:
                # Filled
                if i < filled_segs - 3:
                    color = self.accent
                elif i < filled_segs - 1:
                    color = self.accent_glow
                else:
                    color = self.accent_bright
                c.create_rectangle(x, 2, x + seg_w, h - 2,
                                   fill=color, outline="")
            else:
                # Empty
                c.create_rectangle(x, 3, x + seg_w, h - 3,
                                   fill="#0a150a", outline="")

        # Percentage label
        self.progress_pct.config(text=f"{self._progress}%")

    def _finish(self):
        if self._closed:
            return
        self._closed = True
        for child in self.root.winfo_children():
            child.destroy()
        self.on_complete()


# ═══════════════════════════════════════════════════
#  CUSTOM CYBERPUNK TITLEBAR
# ═══════════════════════════════════════════════════
class CyberTitlebar(tk.Frame):
    def __init__(self, parent, root, title="CRED-MATRIX v3.0",
                 on_close=None, **kwargs):
        self.parent = parent
        self.root = root
        self.title_text = title
        self.on_close_callback = on_close

        # Colors
        self.bg = "#0a150a"
        self.bg_hover = "#122a12"
        self.border = "#2a5a2a"
        self.accent = "#3a6a3a"
        self.accent_glow = "#9adf9a"
        self.text = "#c8dfc8"
        self.text_dim = "#3d5a3d"
        self.close_bg = "#200a0a"
        self.close_hover = "#8a2020"
        self.close_fg = "#cf5a5a"
        self.min_bg = "#0a1520"
        self.min_hover = "#1a3040"
        self.min_fg = "#5aafaf"

        mono = self._pick_font("Consolas", "Courier New")
        title_font = self._pick_font("Courier New", "Consolas")

        super().__init__(parent, bg=self.bg, height=28, **kwargs)
        self.pack_propagate(False)

        # Bottom accent border
        tk.Frame(self, bg=self.border, height=1).pack(
            side="bottom", fill="x")

        # Left icon area
        left_frame = tk.Frame(self, bg=self.bg)
        left_frame.pack(side="left", padx=(10, 0))

        tk.Label(left_frame, text="◈", bg=self.bg, fg=self.accent_glow,
                 font=(mono, 10, "bold")).pack(side="left")

        tk.Label(left_frame, text=" " + title, bg=self.bg,
                 fg=self.accent_glow,
                 font=(title_font, 9, "bold")).pack(side="left")

        tk.Label(left_frame, text="  ░  SECURE",
                 bg=self.bg, fg=self.text_dim,
                 font=(mono, 7, "bold")).pack(side="left")

        # Right buttons area
        right_frame = tk.Frame(self, bg=self.bg)
        right_frame.pack(side="right", padx=(0, 4))

        # Minimize button
        self.min_btn = tk.Label(
            right_frame, text="  ─  ",
            bg=self.min_bg, fg=self.min_fg,
            font=(mono, 9, "bold"),
            padx=8, pady=2, cursor="hand2"
        )
        self.min_btn.pack(side="left", padx=(0, 2))

        def min_enter(e):
            self.min_btn.config(bg=self.min_hover, fg="#bfefff")

        def min_leave(e):
            self.min_btn.config(bg=self.min_bg, fg=self.min_fg)

        self.min_btn.bind("<Enter>", min_enter)
        self.min_btn.bind("<Leave>", min_leave)
        self.min_btn.bind("<Button-1>", self._minimize)

        # Close button
        self.close_btn = tk.Label(
            right_frame, text="  ×  ",
            bg=self.close_bg, fg=self.close_fg,
            font=(mono, 10, "bold"),
            padx=8, pady=2, cursor="hand2"
        )
        self.close_btn.pack(side="left")

        def close_enter(e):
            self.close_btn.config(bg=self.close_hover, fg="#ffffff")

        def close_leave(e):
            self.close_btn.config(bg=self.close_bg, fg=self.close_fg)

        self.close_btn.bind("<Enter>", close_enter)
        self.close_btn.bind("<Leave>", close_leave)
        self.close_btn.bind("<Button-1>", self._close)

        # Make the titlebar draggable
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        for widget in [self, left_frame] + list(left_frame.winfo_children()):
            widget.bind("<Button-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._on_drag)

    def _pick_font(self, *candidates):
        available = set(tkfont.families(self.root))
        for name in candidates:
            if name in available:
                return name
        return "TkDefaultFont"

    def _start_drag(self, event):
        self._drag_offset_x = event.x_root - self.root.winfo_x()
        self._drag_offset_y = event.y_root - self.root.winfo_y()

    def _on_drag(self, event):
        x = event.x_root - self._drag_offset_x
        y = event.y_root - self._drag_offset_y
        self.root.geometry(f"+{x}+{y}")

    def _minimize(self, event=None):
        self.root.iconify()

    def _on_restore(self, event=None):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _close(self, event=None):
        if self.on_close_callback:
            self.on_close_callback()
        else:
            self.root.destroy()


# ═══════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════
class EPViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("CRED-MATRIX v3.0")
        self.root.configure(bg="#030803")

        # Keep a normal Windows taskbar entry so minimize and restore work.
        self.root.overrideredirect(False)
        self.root.attributes("-topmost", False)

        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass

        self.entries = self.load_entries()
        self.index = 0
        self.code_queue = queue.Queue()
        self.code_poll_job = None
        self.code_poll_interval_ms = 2000
        self.current_lookup_id = 0
        self.latest_code_result = None
        self.lookup_in_flight = False
        self.app_closing = False
        self.current_lookup_entry = None
        self.last_notified_message_key = None
        self.toast_window = None
        self.toast_hide_job = None
        self.code_notification_recent_seconds = 120
        self._blink_state = True
        self._ticker_pos = 0
        self._pulse_phase = 0
        self._progress_bars = []

        self._search_has_focus = False
        self._search_placeholder = "search email..."
        self._search_dropdown = None
        self._search_results = []

        self.setup_theme()
        self.load_images()
        self.build_ui()

        # Fixed compact HORIZONTAL size
        self.fixed_width = 1000
        self.fixed_height = 408  # +28 for titlebar
        self.position_side_right(self.fixed_width, self.fixed_height)
        self.root.minsize(self.fixed_width, self.fixed_height)
        self.root.maxsize(self.fixed_width, self.fixed_height)
        self.root.resizable(False, False)

        self.root.bind("<Configure>", self.on_resize)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind_mouse_wheel()
        self.show_current()
        self.schedule_code_poll(immediate=True)
        self.animate_blink()
        self.animate_ticker()
        self.animate_pulse()
        self.animate_decorations()

    # ═══════════════════════════════════════════════
    #  THEME
    # ═══════════════════════════════════════════════
    def setup_theme(self):
        self.ui_font = self.pick_font("Courier New", "Consolas", "Lucida Console")
        self.mono_font = self.pick_font("Consolas", "Courier New", "Lucida Console")
        self.title_font = self.pick_font("Courier New", "Consolas", "Terminal")

        self.window_bg = "#030803"
        self.app_bg = "#060c06"
        self.panel_bg = "#0a150a"
        self.panel_bg_2 = "#0c1a0c"
        self.panel_bg_3 = "#0e1f0e"
        self.card_bg = "#091209"
        self.card_bg_hover = "#0f220f"
        self.sidebar_bg = "#050a05"
        self.input_bg = "#070e07"

        self.text = "#c8dfc8"
        self.text_soft = "#8aab8a"
        self.text_dim = "#3d5a3d"
        self.text_bright = "#e8ffe8"
        self.text_muted = "#2a4a2a"

        self.accent_1 = "#4a7a4a"
        self.accent_2 = "#6aaf6a"
        self.accent_3 = "#3a6a3a"
        self.accent_glow = "#9adf9a"
        self.accent_bright = "#bfffbf"
        self.accent_warn = "#b5a642"
        self.accent_danger = "#7a2a2a"
        self.accent_danger_bright = "#cf5a5a"
        self.accent_code = "#7fff7f"
        self.accent_dim_code = "#2a5f2a"
        self.accent_cyan = "#5aafaf"
        self.accent_cyan_dim = "#2a6a6a"
        self.accent_purple = "#8a6abf"
        self.accent_purple_dim = "#4a3a6a"

        self.border_1 = "#162016"
        self.border_2 = "#1e3a1e"
        self.border_bright = "#2a5a2a"
        self.border_dim = "#0f1a0f"

        self.button_nav_bg = "#0a1e0a"
        self.button_nav_hover = "#122a12"
        self.button_act_bg = "#0a1520"
        self.button_act_hover = "#122035"
        self.button_del_bg = "#200a0a"
        self.button_del_hover = "#351515"

    def pick_font(self, *candidates):
        available = set(tkfont.families(self.root))
        for name in candidates:
            if name in available:
                return name
        return "TkDefaultFont"

    # ═══════════════════════════════════════════════
    #  DATA
    # ═══════════════════════════════════════════════
    def load_entries(self):
        if not DATA_FILE.exists():
            return []
        lines = DATA_FILE.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines:
            s = line.strip()
            if not s:
                continue
            if ":" in s:
                em, pwd = s.split(":", 1)
            else:
                em, pwd = s, ""
            out.append((em.strip(), pwd.strip()))
        return out

    def save_entries(self):
        lines = [f"{e}:{p}" for e, p in self.entries]
        DATA_FILE.write_text("\n".join(lines), encoding="utf-8")

    # ═══════════════════════════════════════════════
    #  IMAGES
    # ═══════════════════════════════════════════════
    def load_button_image(self, filename, fallback_text):
        path = GUI_DIR / filename
        try:
            img = tk.PhotoImage(file=str(path))
            img = self.crop_transparent_bounds(img)
            return self.fit_icon_image(img, max_w=16, max_h=16)
        except Exception:
            return fallback_text

    def fit_icon_image(self, img, max_w=16, max_h=16):
        w = max(1, img.width())
        h = max(1, img.height())
        scale = max(w / max_w, h / max_h, 1.0)
        divisor = max(1, math.ceil(scale))
        if divisor > 1:
            img = img.subsample(divisor, divisor)
        return img

    def crop_transparent_bounds(self, img):
        w = img.width()
        h = img.height()
        min_x, min_y = w, h
        max_x, max_y = -1, -1
        try:
            for y in range(h):
                for x in range(w):
                    px = img.get(x, y)
                    if isinstance(px, tuple):
                        r, g, b = px
                    else:
                        r = g = b = 0
                    if (r + g + b) > 18:
                        min_x = x if x < min_x else min_x
                        min_y = y if y < min_y else min_y
                        max_x = x if x > max_x else max_x
                        max_y = y if y > max_y else max_y
        except Exception:
            return img
        if max_x < min_x or max_y < min_y:
            return img
        cropped = tk.PhotoImage()
        cropped.tk.call(str(cropped), "copy", str(img),
                        "-from", min_x, min_y, max_x + 1, max_y + 1)
        return cropped

    def load_images(self):
        self.img_back = self.load_button_image("back.png", "◀")
        self.img_next = self.load_button_image("next.png", "▶")
        self.img_email = self.load_button_image("email.png", "@")
        self.img_password = self.load_button_image("password.png", "#")
        self.img_delete = self.load_button_image("delete.png", "X")
        self.img_all = self.load_button_image("all.png", ">>")

    # ═══════════════════════════════════════════════
    #  UI BUILD
    # ═══════════════════════════════════════════════
    def build_ui(self):
        self.root.grid_rowconfigure(0, weight=0)  # titlebar
        self.root.grid_rowconfigure(1, weight=1)  # main content
        self.root.grid_columnconfigure(0, weight=1)

        # Custom titlebar
        self.titlebar = CyberTitlebar(
            self.root, self.root,
            title="CRED-MATRIX v3.0",
            on_close=self.on_close
        )
        self.titlebar.grid(row=0, column=0, sticky="ew")

        self.outer = tk.Frame(self.root, bg=self.window_bg, bd=0)
        self.outer.grid(row=1, column=0, sticky="nsew", padx=3, pady=(0, 3))
        self.outer.grid_rowconfigure(0, weight=1)
        self.outer.grid_columnconfigure(0, weight=1)

        self.shell_canvas = CyberCanvas(self.outer, bg=self.window_bg)
        self.shell_canvas.grid(row=0, column=0, sticky="nsew")

        self.content = tk.Frame(self.shell_canvas, bg=self.app_bg)
        self.content_window = self.shell_canvas.create_window(
            (0, 0), window=self.content, anchor="nw"
        )

        self.content.grid_rowconfigure(0, weight=0)
        self.content.grid_rowconfigure(1, weight=0)
        self.content.grid_rowconfigure(2, weight=0)
        self.content.grid_rowconfigure(3, weight=0)
        self.content.grid_rowconfigure(4, weight=1)
        self.content.grid_rowconfigure(5, weight=0)
        self.content.grid_rowconfigure(6, weight=0)
        self.content.grid_rowconfigure(7, weight=0)
        self.content.grid_columnconfigure(0, weight=1)

        self.build_top_accent()
        self.build_header()
        self.build_header_progress()
        self.build_ticker()
        self.build_cards_row()
        self.build_action_bar()
        self.build_footer_progress()
        self.build_footer()
        self.redraw_shell()

    # ─── TOP ACCENT ──────────────────────────────
    def build_top_accent(self):
        accent_frame = tk.Frame(self.content, bg=self.app_bg, height=2)
        accent_frame.grid(row=0, column=0, sticky="ew")
        accent_frame.grid_propagate(False)

        self.top_accent_canvas = CyberCanvas(accent_frame, bg=self.app_bg, height=2)
        self.top_accent_canvas.pack(fill="x", expand=True)
        self.top_accent_canvas.bind("<Configure>", self._draw_top_accent)

    def _draw_top_accent(self, event=None):
        c = self.top_accent_canvas
        c.delete("accent")
        w = c.winfo_width() or 800
        mid = w // 2
        c.create_line(0, 1, w, 1, fill=self.border_1, width=1, tags="accent")
        spread = min(300, w // 3)
        c.create_line(mid - spread, 1, mid + spread, 1,
                      fill=self.accent_3, width=1, tags="accent")
        c.create_line(mid - 40, 1, mid + 40, 1,
                      fill=self.accent_glow, width=1, tags="accent")

    # ─── HEADER ──────────────────────────────────
    def build_header(self):
        self.header_frame = CyberFrame(
            self.content, bg=self.panel_bg,
            border_color=self.border_2,
            glow_color=self.accent_3,
            corner_size=8,
            show_notches=False,
            show_corners=True,
            height=42
        )
        self.header_frame.grid(row=1, column=0, sticky="ew", padx=4, pady=(2, 0))
        self.header_frame.grid_propagate(False)
        self.header_frame.grid_columnconfigure(2, weight=1)

        title_frame = tk.Frame(self.header_frame, bg=self.panel_bg)
        title_frame.grid(row=0, column=0, padx=(10, 6), pady=8, sticky="w")

        tk.Label(title_frame, text="◈", bg=self.panel_bg,
                 fg=self.accent_glow,
                 font=(self.mono_font, 9, "bold")).pack(side="left")

        self.header_glitch = GlitchLabel(
            title_frame,
            text="CRED-MATRIX",
            font=(self.title_font, 10, "bold"),
            fg=self.accent_glow,
            bg=self.panel_bg,
            glitch_interval=4000,
            width=110, height=18
        )
        self.header_glitch.pack(side="left", padx=(4, 0))

        rec_frame = tk.Frame(self.header_frame, bg=self.panel_bg)
        rec_frame.grid(row=0, column=1, padx=(4, 10), pady=8, sticky="w")

        tk.Label(rec_frame, text="REC", bg=self.panel_bg, fg=self.accent_3,
                 font=(self.mono_font, 8, "bold")).pack(side="left")
        self.entry_big = tk.Label(
            rec_frame, text="[0000/0000]",
            bg=self.panel_bg, fg=self.accent_glow,
            font=(self.mono_font, 9, "bold")
        )
        self.entry_big.pack(side="left", padx=(4, 0))
        self.cursor_label = tk.Label(
            rec_frame, text="█",
            bg=self.panel_bg, fg=self.accent_glow,
            font=(self.mono_font, 9, "bold")
        )
        self.cursor_label.pack(side="left")

        self.search_frame = tk.Frame(self.header_frame, bg=self.panel_bg)
        self.search_frame.grid(row=0, column=2, padx=4, pady=6, sticky="ew")

        search_border = tk.Frame(self.search_frame, bg=self.accent_3, padx=1, pady=1)
        search_border.pack(fill="x", expand=True)

        search_inner = tk.Frame(search_border, bg=self.input_bg)
        search_inner.pack(fill="x")
        search_inner.grid_columnconfigure(1, weight=1)

        tk.Label(search_inner, text="◈", bg=self.input_bg,
                 fg=self.accent_dim_code,
                 font=(self.mono_font, 7, "bold")).grid(
            row=0, column=0, padx=(4, 2), pady=3, sticky="w")

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            search_inner,
            textvariable=self.search_var,
            bg=self.input_bg,
            fg=self.text,
            insertbackground=self.accent_glow,
            selectbackground=self.accent_3,
            selectforeground=self.text_bright,
            relief="flat", bd=0,
            highlightthickness=0,
            font=(self.mono_font, 8),
        )
        self.search_entry.grid(row=0, column=1, padx=2, pady=3, sticky="ew")
        self.search_entry.bind("<Return>", self.perform_search)
        self.search_entry.bind("<KP_Enter>", self.perform_search)
        self.search_entry.bind("<FocusIn>", self._search_focus_in)
        self.search_entry.bind("<FocusOut>", self._search_focus_out)
        self.search_entry.insert(0, self._search_placeholder)
        self.search_entry.config(fg=self.text_dim)
        self.search_var.trace_add("write", self._on_search_typing)

        search_btn_border = tk.Frame(search_inner, bg=self.accent_3, padx=1, pady=1)
        search_btn_border.grid(row=0, column=2, padx=(2, 2), pady=2, sticky="e")
        self.search_btn = tk.Button(
            search_btn_border, text="►",
            command=self.perform_search,
            bg=self.button_nav_bg, fg=self.accent_glow,
            activebackground=self.button_nav_hover,
            activeforeground=self.text_bright,
            relief="flat", bd=0, highlightthickness=0,
            font=(self.mono_font, 7, "bold"),
            cursor="hand2", padx=4, pady=0
        )
        self.search_btn.pack()
        self.search_btn.bind("<Enter>",
            lambda e: self.search_btn.config(bg=self.button_nav_hover, fg=self.text_bright))
        self.search_btn.bind("<Leave>",
            lambda e: self.search_btn.config(bg=self.button_nav_bg, fg=self.accent_glow))

        clear_btn_border = tk.Frame(search_inner, bg=self.border_2, padx=1, pady=1)
        clear_btn_border.grid(row=0, column=3, padx=(0, 3), pady=2, sticky="e")
        self.clear_btn = tk.Button(
            clear_btn_border, text="×",
            command=self.clear_search,
            bg=self.button_del_bg, fg=self.accent_danger_bright,
            activebackground=self.button_del_hover,
            activeforeground=self.text_bright,
            relief="flat", bd=0, highlightthickness=0,
            font=(self.mono_font, 7, "bold"),
            cursor="hand2", padx=3, pady=0
        )
        self.clear_btn.pack()
        self.clear_btn.bind("<Enter>",
            lambda e: self.clear_btn.config(bg=self.button_del_hover, fg=self.text_bright))
        self.clear_btn.bind("<Leave>",
            lambda e: self.clear_btn.config(bg=self.button_del_bg, fg=self.accent_danger_bright))

        self.search_result_lbl = tk.Label(
            search_inner, text="",
            bg=self.input_bg, fg=self.text_dim,
            font=(self.mono_font, 6)
        )
        self.search_result_lbl.grid(row=0, column=4, padx=(0, 4), pady=3, sticky="e")

        right_frame = tk.Frame(self.header_frame, bg=self.panel_bg)
        right_frame.grid(row=0, column=3, padx=(4, 10), pady=8, sticky="e")

        self.sys_dot = tk.Label(right_frame, text="◆", bg=self.panel_bg,
                                fg=self.accent_glow, font=(self.mono_font, 7))
        self.sys_dot.pack(side="left", padx=1)
        self.net_dot = tk.Label(right_frame, text="◆", bg=self.panel_bg,
                                fg=self.accent_warn, font=(self.mono_font, 7))
        self.net_dot.pack(side="left", padx=1)
        self.enc_dot = tk.Label(right_frame, text="◆", bg=self.panel_bg,
                                fg=self.accent_cyan, font=(self.mono_font, 7))
        self.enc_dot.pack(side="left", padx=(1, 6))

        count_border = tk.Frame(right_frame, bg=self.accent_3, padx=1, pady=1)
        count_border.pack(side="left")
        count_inner_f = tk.Frame(count_border, bg=self.panel_bg_3)
        count_inner_f.pack()
        self.count_label = tk.Label(
            count_inner_f, text="000",
            bg=self.panel_bg_3, fg=self.accent_glow,
            font=(self.mono_font, 7, "bold"), padx=6, pady=2
        )
        self.count_label.pack()

    def build_header_progress(self):
        self.header_progress = CyberProgressBar(
            self.content, bg=self.app_bg,
            bar_color=self.accent_3, glow_color=self.accent_glow,
            height=3
        )
        self.header_progress.grid(row=2, column=0, sticky="ew", padx=4)
        self._progress_bars.append(self.header_progress)

    def build_ticker(self):
        self.ticker_outer = tk.Frame(self.content, bg=self.border_dim, height=16)
        self.ticker_outer.grid(row=3, column=0, sticky="ew", padx=4, pady=(1, 0))
        self.ticker_outer.grid_propagate(False)

        self.ticker_frame = tk.Frame(self.ticker_outer, bg=self.sidebar_bg)
        self.ticker_frame.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(self.ticker_frame, text=" ◈", bg=self.sidebar_bg,
                 fg=self.accent_3, font=(self.mono_font, 6, "bold")).pack(side="left")

        self.entry_sub = tk.Label(
            self.ticker_frame, text="ACTIVE ",
            bg=self.sidebar_bg, fg=self.text_dim,
            font=(self.mono_font, 6, "bold"))
        self.entry_sub.pack(side="left", padx=(4, 4))

        tk.Label(self.ticker_frame, text="│", bg=self.sidebar_bg,
                 fg=self.border_2, font=(self.mono_font, 6)).pack(side="left")

        self.ticker_label = tk.Label(
            self.ticker_frame, text="",
            bg=self.sidebar_bg, fg=self.accent_dim_code,
            font=(self.mono_font, 6), anchor="w"
        )
        self.ticker_label.pack(side="left", fill="x", expand=True, padx=(4, 0))

        self.ticker_time = tk.Label(
            self.ticker_frame, text="",
            bg=self.sidebar_bg, fg=self.text_dim,
            font=(self.mono_font, 6)
        )
        self.ticker_time.pack(side="right", padx=4)

        self.update_clock()

    def update_clock(self):
        if self.app_closing:
            return
        self.root.after(1000, self.update_clock)

    def animate_ticker(self):
        if self.app_closing:
            return
        messages = [
            ">>> IMAP ACTIVE ",
            ">>> STORE LOADED ",
            ">>> AES-256-GCM ",
            ">>> MONITORING ",
            ">>> STABLE ",
            ">>> SCANNING ",
        ]
        full = "  ░░░  ".join(messages) + "   "
        self._ticker_pos = (self._ticker_pos + 1) % len(full)
        display = (full + full)[self._ticker_pos:self._ticker_pos + 100]
        self.ticker_label.config(text=display)
        now = datetime.now().strftime("%H:%M:%S")
        self.ticker_time.config(text=f"[{now}]")
        self.root.after(50, self.animate_ticker)

    def animate_blink(self):
        if self.app_closing:
            return
        self._blink_state = not self._blink_state
        color = self.accent_glow if self._blink_state else self.panel_bg
        self.cursor_label.config(fg=color)
        self.root.after(530, self.animate_blink)

    def animate_pulse(self):
        if self.app_closing:
            return
        self._pulse_phase = (self._pulse_phase + 1) % 20
        if self._pulse_phase < 10:
            self.sys_dot.config(fg=self.accent_glow)
        else:
            self.sys_dot.config(fg=self.accent_1)
        self.root.after(150, self.animate_pulse)

    def animate_decorations(self):
        if self.app_closing:
            return
        if random.random() > 0.92:
            self.enc_dot.config(fg=self.accent_bright)
            self.root.after(100, lambda: self.enc_dot.config(
                fg=self.accent_cyan) if not self.app_closing else None)
        self.root.after(200, self.animate_decorations)

    def build_cards_row(self):
        self.cards_area = tk.Frame(self.content, bg=self.app_bg)
        self.cards_area.grid(row=4, column=0, sticky="nsew", padx=4, pady=(2, 2))
        self.cards_area.grid_rowconfigure(0, weight=1)
        self.cards_area.grid_columnconfigure(0, weight=3)
        self.cards_area.grid_columnconfigure(1, weight=2)

        left_col = tk.Frame(self.cards_area, bg=self.app_bg)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        left_col.grid_rowconfigure(0, weight=1)
        left_col.grid_rowconfigure(1, weight=1)
        left_col.grid_columnconfigure(0, weight=1)

        self.email_card = self._build_data_card(
            left_col,
            slot_label="S01",
            title="EMAIL",
            accent=self.accent_cyan,
            accent_dim=self.accent_cyan_dim,
            icon_text="@",
            click_fn=self.copy_mail
        )
        self.email_card.grid(row=0, column=0, sticky="nsew", pady=(0, 2))

        self.pass_card = self._build_data_card(
            left_col,
            slot_label="S02",
            title="PASS",
            accent=self.accent_purple,
            accent_dim=self.accent_purple_dim,
            icon_text="#",
            click_fn=self.copy_pass
        )
        self.pass_card.grid(row=1, column=0, sticky="nsew", pady=(2, 0))

        self.code_card_outer = self._build_code_card(self.cards_area)
        self.code_card_outer.grid(row=0, column=1, sticky="nsew", padx=(3, 0))

    def _build_data_card(self, parent, slot_label, title, accent,
                         accent_dim, icon_text, click_fn):
        outer = tk.Frame(parent, bg=accent_dim, padx=1, pady=1)
        inner = tk.Frame(outer, bg=self.card_bg)
        inner.pack(fill="both", expand=True)
        inner.grid_rowconfigure(2, weight=1)
        inner.grid_columnconfigure(0, weight=1)

        top_bar = tk.Frame(inner, bg=self.panel_bg_3, height=18)
        top_bar.grid(row=0, column=0, sticky="ew")
        top_bar.grid_propagate(False)
        top_bar.grid_columnconfigure(2, weight=1)

        tk.Label(top_bar, text="●", bg=self.panel_bg_3, fg=accent,
                 font=(self.mono_font, 5)).grid(
            row=0, column=0, padx=(6, 2), pady=3, sticky="w")
        tk.Label(top_bar, text=slot_label, bg=self.panel_bg_3, fg=self.text_dim,
                 font=(self.mono_font, 6, "bold")).grid(
            row=0, column=1, pady=3, sticky="w")
        tk.Label(top_bar, text=f"{title} ═╣", bg=self.panel_bg_3, fg=accent,
                 font=(self.mono_font, 6, "bold")).grid(
            row=0, column=3, padx=(0, 6), pady=3, sticky="e")

        tk.Frame(inner, bg=accent, height=1).grid(row=1, column=0, sticky="ew")

        value_outer = tk.Frame(inner, bg=self.border_1, padx=1, pady=1)
        value_outer.grid(row=2, column=0, sticky="nsew", padx=6, pady=(4, 4))

        value_bg = tk.Frame(value_outer, bg=self.input_bg)
        value_bg.pack(fill="both", expand=True)

        prompt_row = tk.Frame(value_bg, bg=self.input_bg)
        prompt_row.pack(fill="x", padx=6, pady=(4, 0))
        tk.Label(prompt_row, text="$>", bg=self.input_bg, fg=accent_dim,
                 font=(self.mono_font, 7, "bold")).pack(side="left")
        tk.Label(prompt_row, text=f" {icon_text}", bg=self.input_bg,
                 fg=accent, font=(self.mono_font, 7, "bold")).pack(side="left")

        value_label = tk.Label(
            value_bg, text="",
            bg=self.input_bg, fg=self.text,
            font=(self.mono_font, 10),
            anchor="w", justify="left",
            wraplength=520, cursor="hand2"
        )
        value_label.pack(fill="both", expand=True, padx=8, pady=(2, 4))

        click_widgets = [outer, inner, top_bar, value_outer, value_bg,
                         prompt_row, value_label]

        def on_click(_=None):
            click_fn()

        def on_enter(_=None):
            outer.config(bg=accent)
            inner.config(bg=self.card_bg_hover)

        def on_leave(_=None):
            outer.config(bg=accent_dim)
            inner.config(bg=self.card_bg)

        for w in click_widgets:
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

        outer.value_label = value_label
        outer.inner = inner
        outer.accent = accent
        return outer

    def _build_code_card(self, parent):
        outer = tk.Frame(parent, bg=self.accent_3, padx=1, pady=1)
        inner = tk.Frame(outer, bg=self.card_bg)
        inner.pack(fill="both", expand=True)
        inner.grid_rowconfigure(3, weight=1)
        inner.grid_columnconfigure(0, weight=1)

        top_bar = tk.Frame(inner, bg=self.panel_bg_3, height=18)
        top_bar.grid(row=0, column=0, sticky="ew")
        top_bar.grid_propagate(False)
        top_bar.grid_columnconfigure(2, weight=1)

        tk.Label(top_bar, text="●", bg=self.panel_bg_3, fg=self.accent_glow,
                 font=(self.mono_font, 5)).grid(
            row=0, column=0, padx=(6, 2), pady=3, sticky="w")
        tk.Label(top_bar, text="S03  AUTH CODE", bg=self.panel_bg_3,
                 fg=self.accent_glow, font=(self.mono_font, 6, "bold")).grid(
            row=0, column=1, pady=3, sticky="w")

        self.code_time_lbl = tk.Label(
            top_bar, text="[NO_MSG]",
            bg=self.panel_bg_3, fg=self.text_dim,
            font=(self.mono_font, 6))
        self.code_time_lbl.grid(row=0, column=3, padx=(0, 6), pady=3, sticky="e")

        tk.Frame(inner, bg=self.accent_glow, height=1).grid(
            row=1, column=0, sticky="ew")

        signal_frame = tk.Frame(inner, bg=self.card_bg)
        signal_frame.grid(row=2, column=0, sticky="ew", padx=6, pady=(3, 0))
        self.signal_dots = []
        tk.Label(signal_frame, text="SIG:", bg=self.card_bg, fg=self.text_dim,
                 font=(self.mono_font, 6, "bold")).pack(side="left")
        for i in range(8):
            dot = tk.Label(signal_frame, text="▮", bg=self.card_bg,
                           fg=self.border_1, font=(self.mono_font, 6))
            dot.pack(side="left")
            self.signal_dots.append(dot)

        code_outer = tk.Frame(inner, bg=self.accent_3, padx=1, pady=1)
        code_outer.grid(row=3, column=0, sticky="nsew", padx=6, pady=(3, 4))

        code_bg = tk.Frame(code_outer, bg=self.input_bg)
        code_bg.pack(fill="both", expand=True)

        self.code_value_lbl = tk.Label(
            code_bg, text="- - - - - -",
            bg=self.input_bg, fg=self.accent_code,
            font=(self.mono_font, 24, "bold"),
            anchor="center", cursor="hand2"
        )
        self.code_value_lbl.pack(fill="both", expand=True, pady=(4, 0))

        self.code_hint_lbl = tk.Label(
            code_bg, text="[ AWAITING_SIGNAL ]",
            bg=self.input_bg, fg=self.text_dim,
            font=(self.mono_font, 7), anchor="center"
        )
        self.code_hint_lbl.pack(fill="x", pady=(0, 4))

        # ═══════════════════════════════════════════════
        #  NEW INBOX BUTTON (under code, on theme)
        # ═══════════════════════════════════════════════
        inbox_frame = tk.Frame(code_bg, bg=self.accent_3, padx=1, pady=1)
        inbox_frame.pack(fill="x", padx=6, pady=(4, 6))

        inbox_btn_inner = tk.Frame(inbox_frame, bg=self.button_nav_bg)
        inbox_btn_inner.pack(fill="x")

        self.inbox_btn = tk.Button(
            inbox_btn_inner,
            text="◈ OPEN INBOX",
            command=self.open_inbox,
            bg=self.button_nav_bg,
            fg=self.accent_glow,
            activebackground=self.accent_2,
            activeforeground=self.text_bright,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=(self.mono_font, 9, "bold"),
            cursor="hand2",
            padx=6,
            pady=3
        )
        self.inbox_btn.pack(fill="x")
        self.inbox_btn.bind("<Enter>", lambda e: self.inbox_btn.config(
            bg=self.accent_3, fg=self.text_bright))
        self.inbox_btn.bind("<Leave>", lambda e: self.inbox_btn.config(
            bg=self.button_nav_bg, fg=self.accent_glow))

        self.scan_bar = CyberProgressBar(
            inner, bg=self.card_bg,
            bar_color=self.accent_3, glow_color=self.accent_glow, height=4)
        self.scan_bar.grid(row=4, column=0, sticky="ew", padx=6, pady=(0, 2))
        self._progress_bars.append(self.scan_bar)

        for w in [outer, inner, code_outer, code_bg, self.code_value_lbl]:
            w.bind("<Button-1>", self.copy_code)

        outer.inner = inner
        return outer

    def update_signal_dots(self, level=0):
        for i, dot in enumerate(self.signal_dots):
            if i < level:
                if i < 3:
                    dot.config(fg=self.accent_danger_bright)
                elif i < 6:
                    dot.config(fg=self.accent_warn)
                else:
                    dot.config(fg=self.accent_glow)
            else:
                dot.config(fg=self.border_1)

    def build_action_bar(self):
        action_border = tk.Frame(self.content, bg=self.border_2, padx=1, pady=1)
        action_border.grid(row=5, column=0, sticky="ew", padx=4, pady=(2, 0))

        action_bar = tk.Frame(action_border, bg=self.panel_bg_2)
        action_bar.pack(fill="x")

        inner_bar = tk.Frame(action_bar, bg=self.panel_bg_2)
        inner_bar.pack(fill="x", padx=4, pady=4)

        nav_group = tk.Frame(inner_bar, bg=self.panel_bg_2)
        nav_group.pack(side="left")

        tk.Label(nav_group, text="◈ NAV:", bg=self.panel_bg_2,
                 fg=self.text_dim,
                 font=(self.mono_font, 6, "bold")).pack(side="left", padx=(0, 4))

        self.btn_prev = self._cyber_button(
            nav_group, "◄ PREV", self.prev_entry,
            bg=self.button_nav_bg, fg=self.accent_2,
            border_color=self.accent_3, hover_bg=self.button_nav_hover)
        self.btn_prev.pack(side="left", padx=1)

        self.btn_next = self._cyber_button(
            nav_group, "NEXT ►", self.next_entry,
            bg=self.button_nav_bg, fg=self.accent_2,
            border_color=self.accent_3, hover_bg=self.button_nav_hover)
        self.btn_next.pack(side="left", padx=1)

        tk.Frame(inner_bar, bg=self.border_2, width=1).pack(
            side="left", fill="y", padx=8, pady=2)

        copy_group = tk.Frame(inner_bar, bg=self.panel_bg_2)
        copy_group.pack(side="left")

        tk.Label(copy_group, text="◈ COPY:", bg=self.panel_bg_2,
                 fg=self.text_dim,
                 font=(self.mono_font, 6, "bold")).pack(side="left", padx=(0, 4))

        self.btn_copy_email = self._cyber_button(
            copy_group, "[@] EMAIL", self.copy_mail,
            bg=self.button_act_bg, fg=self.accent_cyan,
            border_color=self.accent_cyan_dim, hover_bg=self.button_act_hover,
            indicator_color=self.accent_cyan)
        self.btn_copy_email.pack(side="left", padx=1)

        self.btn_copy_pass = self._cyber_button(
            copy_group, "[#] PASS", self.copy_pass,
            bg=self.button_act_bg, fg=self.accent_purple,
            border_color=self.accent_purple_dim, hover_bg=self.button_act_hover,
            indicator_color=self.accent_purple)
        self.btn_copy_pass.pack(side="left", padx=1)

        self.btn_copy_all = self._cyber_button(
            copy_group, "[»] ALL", self.copy_both,
            bg=self.button_act_bg, fg="#7acfb4",
            border_color="#2a6a4a", hover_bg=self.button_act_hover,
            indicator_color="#7acfb4")
        self.btn_copy_all.pack(side="left", padx=1)

        tk.Frame(inner_bar, bg=self.border_2, width=1).pack(
            side="left", fill="y", padx=8, pady=2)

        sys_group = tk.Frame(inner_bar, bg=self.panel_bg_2)
        sys_group.pack(side="left")

        tk.Label(sys_group, text="◈ SYS:", bg=self.panel_bg_2,
                 fg=self.text_dim,
                 font=(self.mono_font, 6, "bold")).pack(side="left", padx=(0, 4))

        self.btn_delete = self._cyber_button(
            sys_group, "[×] DELETE", self.delete_entry,
            bg=self.button_del_bg, fg=self.accent_danger_bright,
            border_color=self.accent_danger, hover_bg=self.button_del_hover,
            indicator_color=self.accent_danger_bright)
        self.btn_delete.pack(side="left", padx=1)

    def _cyber_button(self, parent, text, command, bg, fg,
                      border_color, hover_bg=None, indicator_color=None):
        if hover_bg is None:
            hover_bg = self.card_bg_hover

        outer = tk.Frame(parent, bg=border_color, padx=1, pady=1)
        btn_frame = tk.Frame(outer, bg=bg)
        btn_frame.pack(fill="x")

        if indicator_color:
            indicator = tk.Frame(btn_frame, bg=indicator_color, width=2)
            indicator.pack(side="left", fill="y")
        else:
            indicator = None

        btn = tk.Button(
            btn_frame, text=text, command=command,
            bg=bg, fg=fg,
            activebackground=hover_bg,
            activeforeground=self.text_bright,
            relief="flat", bd=0, highlightthickness=0,
            font=(self.mono_font, 7, "bold"),
            padx=8, pady=4,
            cursor="hand2"
        )
        btn.pack(fill="x", side="left", expand=True)

        def on_enter(e):
            btn.config(bg=hover_bg, fg=self.text_bright)
            btn_frame.config(bg=hover_bg)
            if indicator:
                indicator.config(bg=self.accent_bright)

        def on_leave(e):
            btn.config(bg=bg, fg=fg)
            btn_frame.config(bg=bg)
            if indicator:
                indicator.config(bg=indicator_color)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        outer.btn = btn
        return outer

    def build_footer_progress(self):
        self.footer_progress = CyberProgressBar(
            self.content, bg=self.app_bg,
            bar_color=self.border_2, glow_color=self.accent_3, height=2)
        self.footer_progress.grid(row=6, column=0, sticky="ew", padx=4)
        self._progress_bars.append(self.footer_progress)

    def build_footer(self):
        self.footer_outer = tk.Frame(self.content, bg=self.border_dim, height=16)
        self.footer_outer.grid(row=7, column=0, sticky="ew", padx=4, pady=(0, 2))
        self.footer_outer.grid_propagate(False)

        self.footer = tk.Frame(self.footer_outer, bg=self.sidebar_bg)
        self.footer.pack(fill="both", expand=True, padx=1, pady=1)

        tk.Label(self.footer, text=" v3.0 ░ SECURE ░ AES-256-GCM",
                 bg=self.sidebar_bg, fg=self.text_dim,
                 font=(self.mono_font, 6, "bold")).pack(side="left", padx=4)

        self.footer_right = tk.Label(
            self.footer, text="",
            bg=self.sidebar_bg, fg=self.text_dim, font=(self.mono_font, 6))
        self.footer_right.pack(side="right", padx=4)

    def redraw_shell(self):
        c = self.shell_canvas
        c.delete("shell")
        w = max(400, c.winfo_width() or 1000)
        h = max(300, c.winfo_height() or 380)

        c.create_rectangle(0, 0, w, h, fill=self.app_bg, outline="", tags="shell")

        pad = 2
        corner = 10

        c.create_line(pad + corner, pad, w - pad - corner, pad,
                      fill=self.border_bright, width=1, tags="shell")
        c.create_line(w - pad, pad + corner, w - pad, h - pad - corner,
                      fill=self.border_bright, width=1, tags="shell")
        c.create_line(w - pad - corner, h - pad, pad + corner, h - pad,
                      fill=self.border_bright, width=1, tags="shell")
        c.create_line(pad, h - pad - corner, pad, pad + corner,
                      fill=self.border_bright, width=1, tags="shell")

        gc = self.accent_3
        c.create_line(pad, pad + corner, pad + corner, pad,
                      fill=gc, width=2, tags="shell")
        c.create_line(w - pad - corner, pad, w - pad, pad + corner,
                      fill=gc, width=2, tags="shell")
        c.create_line(w - pad, h - pad - corner, w - pad - corner, h - pad,
                      fill=gc, width=2, tags="shell")
        c.create_line(pad + corner, h - pad, pad, h - pad - corner,
                      fill=gc, width=2, tags="shell")

        dot_r = 2
        for (cx, cy) in [
            (pad + corner, pad), (w - pad - corner, pad),
            (w - pad, pad + corner), (w - pad, h - pad - corner),
            (w - pad - corner, h - pad), (pad + corner, h - pad),
            (pad, h - pad - corner), (pad, pad + corner)
        ]:
            c.create_oval(cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r,
                          fill=self.accent_1, outline=gc, width=1, tags="shell")

        c.itemconfigure(self.content_window, width=w - 4, height=h - 4)
        c.coords(self.content_window, 2, 2)

    def on_resize(self, event=None):
        self.redraw_shell()

    def position_side_right(self, width, height):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(sw - width - 20, 0)
        y = max((sh - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def bind_mouse_wheel(self):
        self.root.bind_all("<MouseWheel>", self.on_mouse_wheel)
        self.root.bind_all("<Button-4>", self.on_mouse_wheel)
        self.root.bind_all("<Button-5>", self.on_mouse_wheel)

    def on_mouse_wheel(self, event):
        if hasattr(event, "num"):
            if event.num == 4:
                self.prev_entry()
            elif event.num == 5:
                self.next_entry()
            return
        if event.delta > 0:
            self.prev_entry()
        else:
            self.next_entry()

    def show_current(self):
        total = len(self.entries)
        self.count_label.config(text=f"{str(total).zfill(3)}")
        self.current_lookup_id += 1
        self.current_lookup_entry = None

        if not self.entries:
            self.entry_big.config(text="[0000/0000]")
            self.email_card.value_label.config(
                text="NO_DATA_FOUND", fg=self.text_dim)
            self.pass_card.value_label.config(
                text="NO_DATA_FOUND", fg=self.text_dim)
            self.set_code_display(None)
            self.set_buttons_state("disabled")
            self.update_signal_dots(0)
            return

        em, pwd = self.entries[self.index]
        idx_str = str(self.index + 1).zfill(4)
        tot_str = str(total).zfill(4)
        self.entry_big.config(text=f"[{idx_str}/{tot_str}]")

        self.email_card.value_label.config(text=em, fg=self.text)
        self.pass_card.value_label.config(
            text=pwd if pwd else "[ EMPTY ]",
            fg=self.text if pwd else self.text_dim
        )

        try:
            domain_part = em.split("@")[1].upper() if "@" in em else "N/A"
            self.footer_right.config(text=f"{domain_part}")
        except Exception:
            pass

        self.set_buttons_state("normal")
        self.set_code_display({
            "status": "loading",
            "code": None,
            "sent_text": "SCANNING...",
            "message": "Waiting for signal..."
        })
        self.update_signal_dots(2)
        self.schedule_code_poll(immediate=True)

    def set_buttons_state(self, state):
        for b in [
            self.btn_prev.btn, self.btn_next.btn,
            self.btn_copy_email.btn, self.btn_copy_pass.btn,
            self.btn_copy_all.btn, self.btn_delete.btn
        ]:
            b.config(state=state)

    def set_code_display(self, result):
        self.maybe_show_code_notification(result)
        self.latest_code_result = result

        if not result:
            self.code_value_lbl.config(
                text="- - - - - -", fg=self.accent_dim_code, cursor="arrow")
            self.code_hint_lbl.config(
                text="[ AWAITING_SIGNAL ]", fg=self.text_dim)
            self.code_time_lbl.config(text="[NO_MSG]", fg=self.text_dim)
            self.update_signal_dots(0)
            return

        status = result.get("status")
        code = result.get("code")
        sent_text = result.get("sent_text", "NO_MSG")
        message = result.get("message", "")

        if status == "ok" and code:
            spaced = "  ".join(list(str(code)))
            self.code_value_lbl.config(
                text=spaced, fg=self.accent_code, cursor="hand2")
            self.code_hint_lbl.config(
                text="[ CLICK_TO_COPY ]", fg=self.accent_2)
            self.net_dot.config(fg=self.accent_glow)
            self.update_signal_dots(8)

        elif status == "loading":
            self.code_value_lbl.config(
                text=". . . . . .", fg=self.text_dim, cursor="arrow")
            self.code_hint_lbl.config(
                text=f"[ {(message.upper())[:28]} ]", fg=self.text_dim)
            self.update_signal_dots(3)

        elif status == "error":
            self.code_value_lbl.config(
                text="ERR: XX", fg=self.accent_danger_bright, cursor="arrow")
            self.code_hint_lbl.config(
                text=f"[ {(message.upper())[:28]} ]",
                fg=self.accent_danger_bright)
            self.net_dot.config(fg=self.accent_danger_bright)
            self.update_signal_dots(1)

        else:
            self.code_value_lbl.config(
                text="- - - - - -", fg=self.accent_dim_code, cursor="arrow")
            self.code_hint_lbl.config(
                text="[ NO_SIGNAL_FOUND ]", fg=self.text_dim)
            self.update_signal_dots(0)

        self.code_time_lbl.config(
            text=f"[{sent_text.upper()}]", fg=self.text_soft)

     # ═══════════════════════════════════════════════
    #  NEW INBOX SYSTEM (async + draggable + instant)
    # ═══════════════════════════════════════════════
    def open_inbox(self):
        if not self.entries:
            return
        em, pwd = self.entries[self.index]

        # Create themed Toplevel window
        win = tk.Toplevel(self.root)
        win.title("INBOX")
        win.configure(bg="#030803")
        win.overrideredirect(True)
        win.attributes("-topmost", True)

        win_w, win_h = 950, 560
        # Position near the main window
        try:
            base_x = self.root.winfo_rootx() - win_w - 20
            base_y = self.root.winfo_rooty()
            if base_x < 20:
                base_x = 40
        except Exception:
            base_x, base_y = 120, 60
        win.geometry(f"{win_w}x{win_h}+{base_x}+{base_y}")

        # Root canvas for border
        win_canvas = CyberCanvas(win, bg="#030803")
        win_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # Draw border
        def _draw_win_border():
            c = win_canvas
            c.delete("border")
            w = win.winfo_width()
            h = win.winfo_height()
            if w < 20 or h < 20:
                return
            pad = 2
            corner = 12
            c.create_line(pad + corner, pad, w - pad - corner, pad,
                          fill=self.border_bright, width=1, tags="border")
            c.create_line(w - pad, pad + corner, w - pad, h - pad - corner,
                          fill=self.border_bright, width=1, tags="border")
            c.create_line(w - pad - corner, h - pad, pad + corner, h - pad,
                          fill=self.border_bright, width=1, tags="border")
            c.create_line(pad, h - pad - corner, pad, pad + corner,
                          fill=self.border_bright, width=1, tags="border")
            c.create_line(pad, pad + corner, pad + corner, pad,
                          fill=self.accent_3, width=2, tags="border")
            c.create_line(w - pad - corner, pad, w - pad, pad + corner,
                          fill=self.accent_3, width=2, tags="border")
            c.create_line(w - pad, h - pad - corner, w - pad - corner, h - pad,
                          fill=self.accent_3, width=2, tags="border")
            c.create_line(pad + corner, h - pad, pad, h - pad - corner,
                          fill=self.accent_3, width=2, tags="border")
        win.bind("<Configure>", lambda e: _draw_win_border())
        win.after(50, _draw_win_border)

        # Main container inside border
        container = tk.Frame(win_canvas, bg=self.app_bg)
        container.place(x=4, y=4, width=win_w - 8, height=win_h - 8)

        # ── DRAGGABLE TITLEBAR ──
        titlebar = tk.Frame(container, bg=self.panel_bg, height=30)
        titlebar.pack(fill="x")
        titlebar.pack_propagate(False)

        tk.Frame(titlebar, bg=self.border_bright, height=1).pack(
            side="bottom", fill="x")

        left_tb = tk.Frame(titlebar, bg=self.panel_bg)
        left_tb.pack(side="left", padx=(10, 0))

        tk.Label(left_tb, text="◈", bg=self.panel_bg, fg=self.accent_glow,
                 font=(self.mono_font, 10, "bold")).pack(side="left")
        tk.Label(left_tb, text=" INBOX", bg=self.panel_bg,
                 fg=self.accent_glow,
                 font=(self.title_font, 9, "bold")).pack(side="left")
        tk.Label(left_tb, text=f"  ░  {em}",
                 bg=self.panel_bg, fg=self.text_dim,
                 font=(self.mono_font, 7, "bold")).pack(side="left")

        right_tb = tk.Frame(titlebar, bg=self.panel_bg)
        right_tb.pack(side="right", padx=(0, 4))

        # Refresh button
        refresh_btn = tk.Label(
            right_tb, text="  ↻  ",
            bg="#0a1520", fg=self.accent_cyan,
            font=(self.mono_font, 10, "bold"),
            padx=8, pady=2, cursor="hand2"
        )
        refresh_btn.pack(side="left", padx=(0, 2))
        refresh_btn.bind("<Enter>",
            lambda e: refresh_btn.config(bg="#1a3040", fg="#bfefff"))
        refresh_btn.bind("<Leave>",
            lambda e: refresh_btn.config(bg="#0a1520", fg=self.accent_cyan))

        # Close button
        close_btn = tk.Label(
            right_tb, text="  ×  ",
            bg="#200a0a", fg=self.accent_danger_bright,
            font=(self.mono_font, 10, "bold"),
            padx=8, pady=2, cursor="hand2"
        )
        close_btn.pack(side="left")
        close_btn.bind("<Enter>",
            lambda e: close_btn.config(bg="#8a2020", fg="#ffffff"))
        close_btn.bind("<Leave>",
            lambda e: close_btn.config(bg="#200a0a",
                                       fg=self.accent_danger_bright))
        close_btn.bind("<Button-1>", lambda e: win.destroy())

        # Drag logic
        drag_data = {"x": 0, "y": 0}
        def start_drag(event):
            drag_data["x"] = event.x_root - win.winfo_x()
            drag_data["y"] = event.y_root - win.winfo_y()
        def on_drag(event):
            x = event.x_root - drag_data["x"]
            y = event.y_root - drag_data["y"]
            win.geometry(f"+{x}+{y}")
        for w in [titlebar, left_tb] + list(left_tb.winfo_children()):
            w.bind("<Button-1>", start_drag)
            w.bind("<B1-Motion>", on_drag)

        # Status bar under titlebar
        status_bar = tk.Frame(container, bg=self.sidebar_bg, height=18)
        status_bar.pack(fill="x")
        status_bar.pack_propagate(False)

        status_lbl = tk.Label(
            status_bar, text=" ◈ CONNECTING TO IMAP...",
            bg=self.sidebar_bg, fg=self.accent_warn,
            font=(self.mono_font, 7, "bold"))
        status_lbl.pack(side="left", padx=6)

        count_lbl = tk.Label(
            status_bar, text="[0 MSGS]",
            bg=self.sidebar_bg, fg=self.text_dim,
            font=(self.mono_font, 7, "bold"))
        count_lbl.pack(side="right", padx=6)

        # Split: left list / right detail
        split = tk.Frame(container, bg=self.app_bg)
        split.pack(fill="both", expand=True, padx=4, pady=4)
        split.columnconfigure(0, weight=3, uniform="col")
        split.columnconfigure(1, weight=5, uniform="col")
        split.rowconfigure(0, weight=1)

        # LEFT LIST panel
        list_border = tk.Frame(split, bg=self.border_bright, padx=1, pady=1)
        list_border.grid(row=0, column=0, sticky="nsew", padx=(0, 3))
        list_inner = tk.Frame(list_border, bg=self.sidebar_bg)
        list_inner.pack(fill="both", expand=True)

        list_head = tk.Frame(list_inner, bg=self.panel_bg_3, height=20)
        list_head.pack(fill="x")
        list_head.pack_propagate(False)
        tk.Label(list_head, text=" ◈ MAILS", bg=self.panel_bg_3,
                 fg=self.accent_glow,
                 font=(self.mono_font, 7, "bold")).pack(side="left", padx=6)

        tk.Frame(list_inner, bg=self.accent_3, height=1).pack(fill="x")

        # Scrollable list
        list_wrap = tk.Frame(list_inner, bg=self.sidebar_bg)
        list_wrap.pack(fill="both", expand=True)

        list_canvas = tk.Canvas(list_wrap, bg=self.sidebar_bg,
                                highlightthickness=0, bd=0)
        list_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_wrap, orient="vertical",
                                 command=list_canvas.yview,
                                 bg=self.panel_bg,
                                 troughcolor=self.sidebar_bg,
                                 width=10, highlightthickness=0,
                                 activebackground=self.accent_3)
        scrollbar.pack(side="right", fill="y")
        list_canvas.configure(yscrollcommand=scrollbar.set)

        list_frame = tk.Frame(list_canvas, bg=self.sidebar_bg)
        list_frame_window = list_canvas.create_window(
            (0, 0), window=list_frame, anchor="nw")

        def on_list_config(e):
            list_canvas.configure(scrollregion=list_canvas.bbox("all"))
        list_frame.bind("<Configure>", on_list_config)
        list_canvas.bind("<Configure>",
            lambda e: list_canvas.itemconfig(list_frame_window, width=e.width))

        # Local mouse wheel on the list
        def list_wheel(event):
            try:
                list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass
        list_canvas.bind("<Enter>",
            lambda e: list_canvas.bind_all("<MouseWheel>", list_wheel))
        list_canvas.bind("<Leave>",
            lambda e: list_canvas.unbind_all("<MouseWheel>"))
        win.bind("<Destroy>",
            lambda e: list_canvas.unbind_all("<MouseWheel>"), add="+")

        # RIGHT DETAIL panel
        detail_border = tk.Frame(split, bg=self.border_bright, padx=1, pady=1)
        detail_border.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
        detail_area = tk.Frame(detail_border, bg=self.app_bg)
        detail_area.pack(fill="both", expand=True)

        detail_head = tk.Frame(detail_area, bg=self.panel_bg_3, height=20)
        detail_head.pack(fill="x")
        detail_head.pack_propagate(False)
        tk.Label(detail_head, text=" ◈ MESSAGE", bg=self.panel_bg_3,
                 fg=self.accent_glow,
                 font=(self.mono_font, 7, "bold")).pack(side="left", padx=6)

        tk.Frame(detail_area, bg=self.accent_3, height=1).pack(fill="x")

        detail_body_holder = tk.Frame(detail_area, bg=self.app_bg)
        detail_body_holder.pack(fill="both", expand=True)

        # Empty state
        def show_empty_state():
            for w in detail_body_holder.winfo_children():
                w.destroy()
            empty = tk.Frame(detail_body_holder, bg=self.app_bg)
            empty.pack(fill="both", expand=True)
            tk.Label(empty, text="◈", bg=self.app_bg, fg=self.accent_3,
                     font=(self.mono_font, 40, "bold")).pack(pady=(80, 6))
            tk.Label(empty, text="SELECT A MESSAGE",
                     bg=self.app_bg, fg=self.accent_glow,
                     font=(self.mono_font, 11, "bold")).pack()
            tk.Label(empty, text="[ CLICK ANY ITEM FROM THE MAIL LIST ]",
                     bg=self.app_bg, fg=self.text_dim,
                     font=(self.mono_font, 7)).pack(pady=(4, 0))
        show_empty_state()

        # Loading state in list
        loading_frame = tk.Frame(list_frame, bg=self.sidebar_bg)
        loading_frame.pack(fill="x", pady=20)
        tk.Label(loading_frame, text="◈ ◈ ◈", bg=self.sidebar_bg,
                 fg=self.accent_warn,
                 font=(self.mono_font, 12, "bold")).pack(pady=4)
        tk.Label(loading_frame, text="FETCHING MAILS...",
                 bg=self.sidebar_bg, fg=self.accent_glow,
                 font=(self.mono_font, 8, "bold")).pack()
        tk.Label(loading_frame, text="[ IMAP TUNNEL OPEN ]",
                 bg=self.sidebar_bg, fg=self.text_dim,
                 font=(self.mono_font, 7)).pack(pady=(2, 0))

        # Progress bar during load
        inbox_progress = CyberProgressBar(
            loading_frame, bg=self.sidebar_bg,
            bar_color=self.accent_3, glow_color=self.accent_glow, height=4)
        inbox_progress.pack(fill="x", pady=(10, 0), padx=20)

        # Queue for thread → UI communication
        inbox_queue = queue.Queue()
        fetch_in_progress = False
        selected_message = None

        def select_message(msg_info):
            nonlocal selected_message
            selected_message = msg_info
            display_info = dict(msg_info)
            if not msg_info.get("body_loaded"):
                display_info["body"] = "[ LOADING MESSAGE BODY... ]"
                display_info["html"] = None
            self.show_inbox_detail(detail_body_holder, display_info)

            if msg_info.get("body_loaded") or msg_info.get("body_loading"):
                return
            uid = msg_info.get("uid")
            if not uid:
                msg_info["body"] = "[ MESSAGE ID UNAVAILABLE ]"
                msg_info["body_loaded"] = True
                self.show_inbox_detail(detail_body_holder, msg_info)
                return

            msg_info["body_loading"] = True
            body_queue = queue.Queue()

            def body_worker():
                body, html_body, error = self.fetch_inbox_message_body(
                    em, pwd, uid)
                body_queue.put((body, html_body, error))

            def poll_body():
                try:
                    if not win.winfo_exists():
                        return
                    body, html_body, error = body_queue.get_nowait()
                except queue.Empty:
                    win.after(100, poll_body)
                    return
                except Exception:
                    return

                msg_info["body_loading"] = False
                if error:
                    msg_info["body"] = f"[ MESSAGE LOAD FAILED: {error} ]"
                    msg_info["html"] = None
                else:
                    msg_info["body"] = body[:6000]
                    msg_info["html"] = html_body
                msg_info["body_loaded"] = True
                if selected_message is msg_info:
                    self.show_inbox_detail(detail_body_holder, msg_info)

            threading.Thread(target=body_worker, daemon=True).start()
            win.after(100, poll_body)

        # Thread worker
        def fetch_worker():
            messages, error_message = self.fetch_inbox_data(em, pwd)
            inbox_queue.put(("done", messages, error_message))

        # Populate list when data arrives
        def populate_list(messages, error_message=None):
            # Remove loading widgets
            try:
                inbox_progress.stop()
            except Exception:
                pass
            for child in list_frame.winfo_children():
                child.destroy()

            if error_message:
                status_lbl.config(text=f" ◈ {error_message}",
                                  fg=self.accent_danger_bright)
                count_lbl.config(text="[0 MSGS]", fg=self.text_dim)
                empty_row = tk.Frame(list_frame, bg=self.sidebar_bg)
                empty_row.pack(fill="x", pady=20)
                tk.Label(empty_row, text="[ CLICK ↻ TO RETRY ]",
                         bg=self.sidebar_bg, fg=self.text_dim,
                         font=(self.mono_font, 8, "bold")).pack()
                return

            if not messages:
                status_lbl.config(text=" ◈ IMAP OK  ░  EMPTY INBOX",
                                  fg=self.accent_warn)
                count_lbl.config(text="[0 MSGS]", fg=self.text_dim)
                empty_row = tk.Frame(list_frame, bg=self.sidebar_bg)
                empty_row.pack(fill="x", pady=20)
                tk.Label(empty_row, text="[ EMPTY ]",
                         bg=self.sidebar_bg, fg=self.text_dim,
                         font=(self.mono_font, 8, "bold")).pack()
                return

            status_lbl.config(text=" ◈ IMAP OK  ░  LIVE",
                              fg=self.accent_glow)
            count_lbl.config(text=f"[{len(messages)} MSGS]",
                             fg=self.accent_glow)

            for msg_info in messages:
                self._build_inbox_row(list_frame, msg_info,
                                      detail_body_holder, show_empty_state,
                                      select_message)

        # Poll the queue
        def poll_queue():
            nonlocal fetch_in_progress
            try:
                if not win.winfo_exists():
                    return
            except Exception:
                return
            try:
                tag, data, error_message = inbox_queue.get_nowait()
                if tag == "done":
                    fetch_in_progress = False
                    populate_list(data, error_message)
                    return
            except queue.Empty:
                pass
            win.after(100, poll_queue)

        # Refresh function
        def do_refresh():
            nonlocal fetch_in_progress
            if fetch_in_progress:
                return
            fetch_in_progress = True
            # Clear and reload
            for child in list_frame.winfo_children():
                child.destroy()
            reload_frame = tk.Frame(list_frame, bg=self.sidebar_bg)
            reload_frame.pack(fill="x", pady=20)
            tk.Label(reload_frame, text="◈ ◈ ◈", bg=self.sidebar_bg,
                     fg=self.accent_warn,
                     font=(self.mono_font, 12, "bold")).pack(pady=4)
            tk.Label(reload_frame, text="REFRESHING...",
                     bg=self.sidebar_bg, fg=self.accent_glow,
                     font=(self.mono_font, 8, "bold")).pack()
            status_lbl.config(text=" ◈ REFRESHING IMAP...",
                              fg=self.accent_warn)
            threading.Thread(target=fetch_worker, daemon=True).start()
            win.after(100, poll_queue)

        refresh_btn.bind("<Button-1>", lambda e: do_refresh())

        # Kick off fetch instantly
        fetch_in_progress = True
        threading.Thread(target=fetch_worker, daemon=True).start()
        win.after(100, poll_queue)

    def _build_inbox_row(self, parent, msg_info, detail_holder, empty_fn,
                         on_select=None):
        """Build a compact themed inbox list item."""
        row_outer = tk.Frame(parent, bg=self.border_1)
        row_outer.pack(fill="x", padx=2, pady=1)

        row = tk.Frame(row_outer, bg=self.card_bg, cursor="hand2")
        row.pack(fill="x", padx=1, pady=1)

        # Left color indicator
        indicator = tk.Frame(row, bg=self.accent_3, width=3)
        indicator.pack(side="left", fill="y")

        # Content area
        content = tk.Frame(row, bg=self.card_bg)
        content.pack(side="left", fill="both", expand=True, padx=6, pady=4)

        sender = msg_info["from"]
        subject = msg_info["subject"]
        date_str = msg_info["date"]

        # Truncate for display
        sender_disp = sender if len(sender) <= 32 else sender[:30] + ".."
        subject_disp = subject if len(subject) <= 44 else subject[:42] + ".."

        line1 = tk.Label(content, text=sender_disp,
                         bg=self.card_bg, fg=self.text_bright,
                         font=(self.mono_font, 8, "bold"),
                         anchor="w", justify="left")
        line1.pack(fill="x")

        line2 = tk.Label(content, text=subject_disp,
                         bg=self.card_bg, fg=self.accent_2,
                         font=(self.mono_font, 7),
                         anchor="w", justify="left")
        line2.pack(fill="x")

        line3 = tk.Label(content, text=date_str,
                         bg=self.card_bg, fg=self.text_dim,
                         font=(self.mono_font, 6),
                         anchor="w", justify="left")
        line3.pack(fill="x")

        # Hover + click
        def on_enter(_=None):
            row.config(bg=self.card_bg_hover)
            content.config(bg=self.card_bg_hover)
            line1.config(bg=self.card_bg_hover)
            line2.config(bg=self.card_bg_hover)
            line3.config(bg=self.card_bg_hover)
            indicator.config(bg=self.accent_glow)

        def on_leave(_=None):
            row.config(bg=self.card_bg)
            content.config(bg=self.card_bg)
            line1.config(bg=self.card_bg)
            line2.config(bg=self.card_bg)
            line3.config(bg=self.card_bg)
            indicator.config(bg=self.accent_3)

        def on_click(_=None):
            if on_select:
                on_select(msg_info)
            else:
                self.show_inbox_detail(detail_holder, msg_info)

        for w in [row, content, line1, line2, line3, indicator]:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

    def show_inbox_detail(self, parent_frame, msg_info):
        # Clear
        for w in parent_frame.winfo_children():
            w.destroy()

        # Header info
        head = tk.Frame(parent_frame, bg=self.app_bg)
        head.pack(fill="x", padx=10, pady=(8, 4))

        def field_row(parent, label, value, val_color):
            r = tk.Frame(parent, bg=self.app_bg)
            r.pack(fill="x", pady=1)
            tk.Label(r, text=label, bg=self.app_bg, fg=self.text_dim,
                     font=(self.mono_font, 7, "bold"),
                     width=10, anchor="w").pack(side="left")
            tk.Label(r, text=value, bg=self.app_bg, fg=val_color,
                     font=(self.mono_font, 8, "bold"),
                     anchor="w", justify="left",
                     wraplength=460).pack(side="left", fill="x", expand=True)

        field_row(head, "◈ FROM:", msg_info["from"], self.accent_glow)
        field_row(head, "◈ SUBJECT:", msg_info["subject"], self.accent_bright)
        field_row(head, "◈ DATE:", msg_info["date"], self.accent_2)

        # View mode toggle bar
        mode_bar = tk.Frame(parent_frame, bg=self.panel_bg_2)
        mode_bar.pack(fill="x", padx=8, pady=(6, 0))

        tk.Label(mode_bar, text=" ◈ VIEW:", bg=self.panel_bg_2,
                 fg=self.text_dim,
                 font=(self.mono_font, 7, "bold")).pack(side="left", padx=(4, 6), pady=3)

        has_html = bool(msg_info.get("html")) and HTML_RENDER_AVAILABLE

        # Container that holds either HTML or text view
        view_holder = tk.Frame(parent_frame, bg=self.input_bg)

        def render_html_view():
            for w in view_holder.winfo_children():
                w.destroy()
            html_border = tk.Frame(view_holder, bg=self.border_2, padx=1, pady=1)
            html_border.pack(fill="both", expand=True)

            try:
                html_frame = HtmlFrame(html_border, messages_enabled=False,
                                       vertical_scrollbar="auto")
                html_frame.pack(fill="both", expand=True)
                # Load raw HTML
                html_frame.load_html(msg_info["html"])

                # Hook link clicks → open in real browser
                def on_link_click(url):
                    try:
                        webbrowser.open(url)
                    except Exception:
                        pass
                try:
                    html_frame.on_link_click(on_link_click)
                except Exception:
                    # Older tkinterweb API
                    try:
                        html_frame.bind("<<LinkClicked>>",
                            lambda e: webbrowser.open(e.widget.link))
                    except Exception:
                        pass
            except Exception as e:
                # Fallback if HTML fails
                fallback = tk.Label(html_border,
                    text=f"[ HTML RENDER FAILED: {e} ]",
                    bg=self.input_bg, fg=self.accent_danger_bright,
                    font=(self.mono_font, 8))
                fallback.pack(fill="both", expand=True, padx=10, pady=10)

        def render_text_view():
            for w in view_holder.winfo_children():
                w.destroy()
            body_border = tk.Frame(view_holder, bg=self.border_2, padx=1, pady=1)
            body_border.pack(fill="both", expand=True)

            body_inner = tk.Frame(body_border, bg=self.input_bg)
            body_inner.pack(fill="both", expand=True)

            body_text = tk.Text(
                body_inner,
                bg=self.input_bg, fg=self.text,
                insertbackground=self.accent_glow,
                font=(self.mono_font, 9),
                relief="flat", bd=0, wrap="word",
                padx=8, pady=8,
                selectbackground=self.accent_3,
                selectforeground=self.text_bright
            )
            body_text.pack(side="left", fill="both", expand=True)

            body_scroll = tk.Scrollbar(
                body_inner, orient="vertical", command=body_text.yview,
                bg=self.panel_bg, troughcolor=self.input_bg, width=10,
                highlightthickness=0, activebackground=self.accent_3)
            body_scroll.pack(side="right", fill="y")
            body_text.config(yscrollcommand=body_scroll.set)

            # Tag setup for clickable links in text view
            body_text.tag_configure("link", foreground=self.accent_cyan,
                                    underline=True)
            body_text.tag_bind("link", "<Enter>",
                lambda e: body_text.config(cursor="hand2"))
            body_text.tag_bind("link", "<Leave>",
                lambda e: body_text.config(cursor=""))

            content = msg_info["body"] if msg_info["body"] else "[ NO BODY CONTENT ]"

            # Find and tag URLs
            url_pattern = re.compile(r'(https?://[^\s\]\)]+)')
            body_text.config(state="normal")
            pos = 0
            for match in url_pattern.finditer(content):
                start, end = match.span()
                # Insert plain part
                if start > pos:
                    body_text.insert("end", content[pos:start])
                # Insert URL with tag
                url = match.group(1)
                tag_name = f"link_{start}"
                body_text.insert("end", url, ("link", tag_name))
                body_text.tag_bind(tag_name, "<Button-1>",
                    lambda e, u=url: webbrowser.open(u))
                pos = end
            if pos < len(content):
                body_text.insert("end", content[pos:])
            body_text.config(state="disabled")

        # Button builder for view toggle
        def make_view_btn(label, cmd, active=False):
            b_bg = self.accent_3 if active else self.button_nav_bg
            b_fg = self.text_bright if active else self.accent_glow
            border_col = self.accent_glow if active else self.border_2

            outer = tk.Frame(mode_bar, bg=border_col, padx=1, pady=1)
            outer.pack(side="left", padx=2, pady=3)
            btn = tk.Button(outer, text=label, command=cmd,
                bg=b_bg, fg=b_fg,
                activebackground=self.accent_3,
                activeforeground=self.text_bright,
                relief="flat", bd=0, highlightthickness=0,
                font=(self.mono_font, 7, "bold"),
                padx=8, pady=2, cursor="hand2")
            btn.pack()
            return btn, outer

        # Rebuild the view mode buttons with state
        def rebuild_buttons(active_mode):
            for w in mode_bar.winfo_children()[1:]:  # skip the VIEW: label
                w.destroy()

            if has_html:
                make_view_btn("◈ RENDERED",
                    lambda: (rebuild_buttons("html"), render_html_view()),
                    active=(active_mode == "html"))
            make_view_btn("◈ RAW TEXT",
                lambda: (rebuild_buttons("text"), render_text_view()),
                active=(active_mode == "text"))

            if not HTML_RENDER_AVAILABLE:
                tk.Label(mode_bar,
                    text="  [ install tkinterweb for HTML view ]",
                    bg=self.panel_bg_2, fg=self.accent_warn,
                    font=(self.mono_font, 6, "italic")).pack(
                    side="left", padx=6)

        # Pack view holder
        view_holder.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        # Default view: HTML if available, else text
        if has_html:
            rebuild_buttons("html")
            render_html_view()
        else:
            rebuild_buttons("text")
            render_text_view()

        def field_row(parent, label, value, val_color):
            r = tk.Frame(parent, bg=self.app_bg)
            r.pack(fill="x", pady=1)
            tk.Label(r, text=label, bg=self.app_bg, fg=self.text_dim,
                     font=(self.mono_font, 7, "bold"),
                     width=10, anchor="w").pack(side="left")
            tk.Label(r, text=value, bg=self.app_bg, fg=val_color,
                     font=(self.mono_font, 8, "bold"),
                     anchor="w", justify="left",
                     wraplength=460).pack(side="left", fill="x", expand=True)

        field_row(head, "◈ FROM:", msg_info["from"], self.accent_glow)
        field_row(head, "◈ SUBJECT:", msg_info["subject"], self.accent_bright)
        field_row(head, "◈ DATE:", msg_info["date"], self.accent_2)

        tk.Frame(parent_frame, bg=self.accent_3, height=1).pack(
            fill="x", padx=8, pady=(6, 0))

        # Body area
        body_wrap = tk.Frame(parent_frame, bg=self.input_bg)
        body_wrap.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        body_border = tk.Frame(body_wrap, bg=self.border_2, padx=1, pady=1)
        body_border.pack(fill="both", expand=True)

        body_inner = tk.Frame(body_border, bg=self.input_bg)
        body_inner.pack(fill="both", expand=True)

        body_text = tk.Text(
            body_inner,
            bg=self.input_bg, fg=self.text,
            insertbackground=self.accent_glow,
            font=(self.mono_font, 9),
            relief="flat", bd=0, wrap="word",
            padx=8, pady=8,
            selectbackground=self.accent_3,
            selectforeground=self.text_bright
        )
        body_text.pack(side="left", fill="both", expand=True)

        body_scroll = tk.Scrollbar(
            body_inner, orient="vertical", command=body_text.yview,
            bg=self.panel_bg, troughcolor=self.input_bg, width=10,
            highlightthickness=0, activebackground=self.accent_3)
        body_scroll.pack(side="right", fill="y")
        body_text.config(yscrollcommand=body_scroll.set)

        body_text.insert("1.0",
            msg_info["body"] if msg_info["body"] else "[ NO BODY CONTENT ]")
        body_text.config(state="disabled")

    def fetch_inbox_data(self, email_address, password):
        results = []
        client = None
        try:
            client = self.connect_imap()
            client.login(email_address, password)
            status, _ = client.select("INBOX", readonly=True)
            if status != "OK":
                return [], "INBOX OPEN FAILED"

            typ, data = client.uid("SEARCH", None, "ALL")
            if typ == "OK" and data and data[0]:
                uids = [uid.decode() if isinstance(uid, bytes) else str(uid)
                        for uid in reversed(data[0].split())]
                uids = uids[:INBOX_MESSAGE_LIMIT]
                typ, msg_data = client.uid(
                    "FETCH", ",".join(uids),
                    "(UID BODY.PEEK[HEADER])")
                if typ == "OK" and msg_data:
                    for item in reversed(msg_data):
                        if not isinstance(item, tuple) or len(item) < 2:
                            continue
                        raw = item[1]
                        if not isinstance(raw, bytes):
                            continue

                        msg = email.message_from_bytes(raw)
                        uid_match = re.search(rb"\bUID (\d+)\b", item[0])
                        from_hdr = msg.get("From", "")
                        subj_hdr = msg.get("Subject", "")
                        date_hdr = msg.get("Date", "")
                        from_decoded = self.decode_hdr(from_hdr)
                        subj_decoded = self.decode_hdr(subj_hdr)

                        parsed_dt = self.parse_message_datetime(date_hdr)
                        if parsed_dt:
                            try:
                                date_str = parsed_dt.astimezone().strftime(
                                    "%d.%m.%Y %H:%M")
                            except Exception:
                                date_str = date_hdr[:20]
                        else:
                            date_str = date_hdr[:20]

                        addr = email.utils.parseaddr(from_decoded)[1]
                        sender_display = addr if addr else from_decoded

                        results.append({
                            "from": sender_display,
                            "subject": subj_decoded or "(No Subject)",
                            "date": date_str,
                            "uid": uid_match.group(1).decode()
                            if uid_match else None,
                            "body": "",
                            "html": None
                        })
        except imaplib.IMAP4.error as exc:
            return [], f"AUTH/IMAP FAILED: {self.clean_error_message(exc)[:80]}"
        except (TimeoutError, OSError) as exc:
            return [], f"CONNECTION FAILED: {self.clean_error_message(exc)[:80]}"
        except Exception as exc:
            return [], f"INBOX FAILED: {self.clean_error_message(exc)[:80]}"
        finally:
            if client is not None:
                try:
                    client.logout()
                except Exception:
                    pass
        return results, None

    def fetch_inbox_message_body(self, email_address, password, uid):
        client = None
        try:
            client = self.connect_imap()
            client.login(email_address, password)
            status, _ = client.select("INBOX", readonly=True)
            if status != "OK":
                return "", None, "INBOX OPEN FAILED"

            status, data = client.uid("FETCH", uid, "(RFC822)")
            if status != "OK" or not data:
                return "", None, "MESSAGE FETCH FAILED"
            for item in data:
                if isinstance(item, tuple) and len(item) > 1:
                    raw = item[1]
                    if isinstance(raw, bytes):
                        message = email.message_from_bytes(raw)
                        return (self.extract_text(message),
                                self.extract_html(message), None)
            return "", None, "MESSAGE CONTENT UNAVAILABLE"
        except imaplib.IMAP4.error as exc:
            return "", None, self.clean_error_message(exc)[:80]
        except (TimeoutError, OSError) as exc:
            return "", None, self.clean_error_message(exc)[:80]
        except Exception as exc:
            return "", None, self.clean_error_message(exc)[:80]
        finally:
            if client is not None:
                try:
                    client.logout()
                except Exception:
                    pass

    def copy_mail(self, _event=None):
        if not self.entries:
            return
        em = self.entries[self.index][0]
        self.root.clipboard_clear()
        self.root.clipboard_append(em)
        self.flash_status("EMAIL >> CLIP")

    def copy_pass(self, _event=None):
        if not self.entries:
            return
        pwd = self.entries[self.index][1]
        self.root.clipboard_clear()
        self.root.clipboard_append(pwd)
        self.flash_status("PASS >> CLIP")

    def copy_both(self):
        if not self.entries:
            return
        em, pwd = self.entries[self.index]
        self.root.clipboard_clear()
        self.root.clipboard_append(f"{em}:{pwd}")
        self.flash_status("FULL >> CLIP")

    def copy_code(self, _event=None):
        if not self.latest_code_result or not self.latest_code_result.get("code"):
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.latest_code_result["code"])
        self.flash_status("CODE >> CLIP")

    def flash_status(self, text):
        self.entry_sub.config(text=text, fg=self.accent_glow)
        self.root.after(1500, lambda: self.entry_sub.config(
            text="ACTIVE ", fg=self.text_dim))

    def next_entry(self):
        if not self.entries:
            return
        self.index = (self.index + 1) % len(self.entries)
        self.show_current()

    def prev_entry(self):
        if not self.entries:
            return
        self.index = (self.index - 1) % len(self.entries)
        self.show_current()

    def delete_entry(self):
        if not self.entries:
            return
        em, pwd = self.entries[self.index]
        confirm = messagebox.askyesno(
            "CONFIRM DELETE",
            f"PURGE THIS RECORD?\n\n{em}"
        )
        if not confirm:
            return
        del self.entries[self.index]
        if self.index >= len(self.entries) and self.index > 0:
            self.index -= 1
        self.save_entries()
        self.show_current()
        self.flash_status("PURGED >> OK")

    def _search_focus_in(self, event=None):
        self._search_has_focus = True
        current = self.search_entry.get()
        if current == self._search_placeholder:
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(fg=self.text)

    def _search_focus_out(self, event=None):
        self._search_has_focus = False
        current = self.search_entry.get().strip()
        if not current:
            self.search_entry.insert(0, self._search_placeholder)
            self.search_entry.config(fg=self.text_dim)
        self._close_search_dropdown()

    def _on_search_typing(self, *args):
        if not self._search_has_focus:
            return
        query = self.search_var.get().strip().lower()
        if not query or query == self._search_placeholder.lower():
            self._close_search_dropdown()
            self.search_result_lbl.config(text="")
            return
        self._update_search_dropdown(query)

    def _update_search_dropdown(self, query):
        matches = []
        for idx, (em, pwd) in enumerate(self.entries):
            if query in em.lower():
                matches.append((idx, em))

        self._search_results = matches
        match_count = len(matches)

        if match_count == 0:
            self.search_result_lbl.config(
                text="[0]", fg=self.accent_danger_bright)
        elif match_count == 1:
            self.search_result_lbl.config(
                text="[1]", fg=self.accent_glow)
        else:
            self.search_result_lbl.config(
                text=f"[{match_count}]", fg=self.accent_2)

        self._close_search_dropdown()

        if not matches:
            return

        dd = tk.Toplevel(self.root)
        dd.overrideredirect(True)
        dd.attributes("-topmost", True)
        dd.configure(bg=self.accent_3)
        self._search_dropdown = dd

        self.root.update_idletasks()
        x = self.search_frame.winfo_rootx()
        y = self.search_frame.winfo_rooty() + self.search_frame.winfo_height() + 2
        dd_width = max(self.search_frame.winfo_width(), 300)

        outer_dd = tk.Frame(dd, bg=self.accent_3, padx=1, pady=1)
        outer_dd.pack(fill="both", expand=True)

        inner_dd = tk.Frame(outer_dd, bg=self.input_bg)
        inner_dd.pack(fill="both", expand=True)

        header_row = tk.Frame(inner_dd, bg=self.panel_bg_3)
        header_row.pack(fill="x")
        tk.Label(header_row, text=f" ◈ RESULTS [{match_count}]",
                 bg=self.panel_bg_3, fg=self.accent_dim_code,
                 font=(self.mono_font, 6, "bold")).pack(
            side="left", padx=4, pady=2)
        tk.Frame(inner_dd, bg=self.accent_3, height=1).pack(fill="x")

        max_visible = min(8, match_count)
        item_height = 24

        if match_count > max_visible:
            canvas_frame = tk.Frame(inner_dd, bg=self.input_bg)
            canvas_frame.pack(fill="both", expand=True)

            dd_canvas = tk.Canvas(canvas_frame, bg=self.input_bg,
                                  highlightthickness=0, bd=0)
            dd_scrollbar = tk.Scrollbar(
                canvas_frame, orient="vertical", command=dd_canvas.yview,
                bg=self.panel_bg, troughcolor=self.input_bg, width=8)
            scroll_frame = tk.Frame(dd_canvas, bg=self.input_bg)

            scroll_frame.bind("<Configure>",
                              lambda e: dd_canvas.configure(
                                  scrollregion=dd_canvas.bbox("all")))
            dd_canvas.create_window((0, 0), window=scroll_frame, anchor="nw",
                                    width=dd_width - 14)
            dd_canvas.configure(yscrollcommand=dd_scrollbar.set)
            dd_canvas.pack(side="left", fill="both", expand=True)
            dd_scrollbar.pack(side="right", fill="y")

            results_parent = scroll_frame
            canvas_height = max_visible * item_height
            dd_canvas.config(height=canvas_height)

            def dd_mousewheel(event):
                dd_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

            dd_canvas.bind_all("<MouseWheel>", dd_mousewheel)
            dd.bind("<Destroy>",
                    lambda e: dd_canvas.unbind_all("<MouseWheel>"))
            total_h = canvas_height + 30
        else:
            results_parent = inner_dd
            total_h = match_count * item_height + 30

        for rank, (entry_idx, entry_email) in enumerate(matches):
            self._build_search_result_item(
                results_parent, rank, entry_idx, entry_email, query, dd)

        dd.geometry(f"{dd_width}x{total_h}+{x}+{y}")

        def close_on_click(event):
            try:
                if dd.winfo_exists():
                    if not str(event.widget).startswith(str(dd)):
                        self._close_search_dropdown()
            except Exception:
                pass

        self.root.bind("<Button-1>", close_on_click, add="+")

    def _build_search_result_item(self, parent, rank, entry_idx,
                                   entry_email, query, dropdown):
        item = tk.Frame(parent, bg=self.input_bg, cursor="hand2")
        item.pack(fill="x", padx=2, pady=1)

        inner_item = tk.Frame(item, bg=self.card_bg)
        inner_item.pack(fill="x", padx=1, pady=1)

        indicator = tk.Frame(inner_item, bg=self.accent_3, width=2)
        indicator.pack(side="left", fill="y")

        idx_str = str(entry_idx + 1).zfill(4)
        tk.Label(inner_item, text=f"[{idx_str}]", bg=self.card_bg,
                 fg=self.text_dim,
                 font=(self.mono_font, 6, "bold")).pack(
            side="left", padx=(4, 3), pady=3)

        email_frame = tk.Frame(inner_item, bg=self.card_bg)
        email_frame.pack(side="left", fill="x", expand=True, padx=2, pady=3)

        low_email = entry_email.lower()
        q_start = low_email.find(query)
        if q_start >= 0:
            before = entry_email[:q_start]
            match_text = entry_email[q_start:q_start + len(query)]
            after = entry_email[q_start + len(query):]
            if before:
                tk.Label(email_frame, text=before, bg=self.card_bg,
                         fg=self.text_soft,
                         font=(self.mono_font, 7)).pack(side="left")
            tk.Label(email_frame, text=match_text, bg=self.card_bg,
                     fg=self.accent_code,
                     font=(self.mono_font, 7, "bold")).pack(side="left")
            if after:
                tk.Label(email_frame, text=after, bg=self.card_bg,
                         fg=self.text_soft,
                         font=(self.mono_font, 7)).pack(side="left")
        else:
            tk.Label(email_frame, text=entry_email, bg=self.card_bg,
                     fg=self.text_soft,
                     font=(self.mono_font, 7)).pack(side="left")

        tk.Label(inner_item, text="►", bg=self.card_bg, fg=self.text_muted,
                 font=(self.mono_font, 7)).pack(side="right", padx=(2, 6), pady=3)

        def go_to_entry(e=None, idx=entry_idx):
            self.index = idx
            self._close_search_dropdown()
            self.clear_search()
            self.show_current()
            self.flash_status(f"GO >> [{str(idx + 1).zfill(4)}]")

        def on_enter(e=None):
            inner_item.config(bg=self.card_bg_hover)
            indicator.config(bg=self.accent_glow)
            for child in email_frame.winfo_children():
                child.config(bg=self.card_bg_hover)
            for child in inner_item.winfo_children():
                try:
                    if child not in (indicator, email_frame):
                        child.config(bg=self.card_bg_hover)
                except Exception:
                    pass

        def on_leave(e=None):
            inner_item.config(bg=self.card_bg)
            indicator.config(bg=self.accent_3)
            for child in email_frame.winfo_children():
                child.config(bg=self.card_bg)
            for child in inner_item.winfo_children():
                try:
                    if child not in (indicator, email_frame):
                        child.config(bg=self.card_bg)
                except Exception:
                    pass

        for widget in [item, inner_item, indicator, email_frame]:
            widget.bind("<Button-1>", go_to_entry)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        for child in inner_item.winfo_children():
            child.bind("<Button-1>", go_to_entry)
        for child in email_frame.winfo_children():
            child.bind("<Button-1>", go_to_entry)

    def _close_search_dropdown(self):
        if self._search_dropdown:
            try:
                if self._search_dropdown.winfo_exists():
                    self._search_dropdown.destroy()
            except Exception:
                pass
        self._search_dropdown = None

    def perform_search(self, event=None):
        query = self.search_var.get().strip().lower()
        if not query or query == self._search_placeholder.lower():
            return

        exact_idx = None
        partial_idx = None
        for idx, (em, pwd) in enumerate(self.entries):
            em_low = em.lower()
            if em_low == query:
                exact_idx = idx
                break
            if partial_idx is None and query in em_low:
                partial_idx = idx

        target = exact_idx if exact_idx is not None else partial_idx

        if target is not None:
            self.index = target
            self._close_search_dropdown()
            self.clear_search()
            self.show_current()
            self.flash_status(f"HIT >> [{str(target + 1).zfill(4)}]")
        else:
            self.flash_status("NO MATCH")
            self.search_result_lbl.config(
                text="[N/A]", fg=self.accent_danger_bright)

    def clear_search(self, event=None):
        self._close_search_dropdown()
        self.search_entry.delete(0, tk.END)
        if not self._search_has_focus:
            self.search_entry.insert(0, self._search_placeholder)
            self.search_entry.config(fg=self.text_dim)
        self.search_result_lbl.config(text="")
        self._search_results = []

    def maybe_show_code_notification(self, result):
        if not result or result.get("status") != "ok" or not result.get("code"):
            return
        message_key = result.get("message_key")
        if not message_key or message_key == self.last_notified_message_key:
            return
        sent_dt = result.get("sent_dt")
        if not sent_dt:
            self.last_notified_message_key = message_key
            return
        age_seconds = abs(
            (datetime.now(sent_dt.tzinfo) - sent_dt).total_seconds())
        if age_seconds > self.code_notification_recent_seconds:
            self.last_notified_message_key = message_key
            return
        self.last_notified_message_key = message_key
        self.show_toast_notification(
            "TOKEN INTERCEPTED", f"CODE: {result['code']}")

    def show_toast_notification(self, title, text):
        if self.app_closing:
            return
        if self.toast_window and self.toast_window.winfo_exists():
            self.toast_window.destroy()
            self.toast_window = None

        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=self.accent_3)

        outer = tk.Frame(toast, bg=self.accent_3, padx=2, pady=2)
        outer.pack(fill="both", expand=True)
        inner_t = tk.Frame(outer, bg=self.panel_bg_3)
        inner_t.pack(fill="both", expand=True)

        tk.Frame(inner_t, bg=self.accent_glow, height=2).pack(fill="x", side="top")
        tk.Label(inner_t, text=f"  ◈ {title}  ",
                 bg=self.panel_bg_3, fg=self.accent_glow,
                 font=(self.mono_font, 8, "bold")).pack(
            fill="x", pady=(6, 2), padx=10)
        tk.Label(inner_t, text=text,
                 bg=self.panel_bg_3, fg=self.accent_code,
                 font=(self.mono_font, 11, "bold")).pack(
            fill="x", pady=(0, 6), padx=10)
        tk.Frame(inner_t, bg=self.accent_3, height=1).pack(fill="x", side="bottom")

        self.root.update_idletasks()
        x = self.root.winfo_rootx() + self.root.winfo_width() - 240
        y = self.root.winfo_rooty() + 60
        toast.geometry(f"220x64+{x}+{y}")
        self.toast_window = toast

        if self.toast_hide_job:
            self.root.after_cancel(self.toast_hide_job)
        self.toast_hide_job = self.root.after(3000, self.hide_toast_notification)

    def hide_toast_notification(self):
        self.toast_hide_job = None
        if self.toast_window and self.toast_window.winfo_exists():
            self.toast_window.destroy()
        self.toast_window = None

    def schedule_code_poll(self, immediate=False):
        if self.app_closing:
            return
        if self.code_poll_job:
            self.root.after_cancel(self.code_poll_job)
            self.code_poll_job = None
        delay = 150 if immediate else self.code_poll_interval_ms
        self.code_poll_job = self.root.after(delay, self.start_code_lookup)

    def start_code_lookup(self):
        self.code_poll_job = None
        if self.app_closing or self.lookup_in_flight or not self.entries:
            if not self.app_closing:
                self.schedule_code_poll(immediate=False)
            return
        em_address, password = self.entries[self.index]
        self.current_lookup_id += 1
        lookup_id = self.current_lookup_id
        lookup_entry = (em_address, password)
        self.current_lookup_entry = lookup_entry
        self.lookup_in_flight = True
        threading.Thread(
            target=self.lookup_code_worker,
            args=(lookup_id, lookup_entry),
            daemon=True,
        ).start()
        self.root.after(200, self.process_code_queue)

    def process_code_queue(self):
        if self.app_closing:
            return
        processed = False
        while True:
            try:
                lookup_id, result = self.code_queue.get_nowait()
            except queue.Empty:
                break
            processed = True
            self.lookup_in_flight = False
            current_entry = self.entries[self.index] if self.entries else None
            if (lookup_id == self.current_lookup_id
                    and result.get("entry_key") == current_entry):
                self.set_code_display(result)

        if self.lookup_in_flight and not processed:
            self.root.after(200, self.process_code_queue)
        else:
            self.schedule_code_poll(immediate=False)

    def lookup_code_worker(self, lookup_id, entry_key):
        em_address, password = entry_key
        result = self.fetch_latest_code(em_address, password)
        result["entry_key"] = entry_key
        self.code_queue.put((lookup_id, result))

    def fetch_latest_code(self, email_address, password):
        try:
            client = self.connect_imap()
        except Exception as exc:
            return {
                "status": "error", "code": None,
                "sent_text": "CONN_ERR",
                "message": self.clean_error_message(exc)
            }
        try:
            client.login(email_address, password)
            client.select("INBOX", readonly=True)
            match = self.find_latest_matching_code(client)
            if match:
                return {
                    "status": "ok",
                    "code": match["code"],
                    "sent_text": match["sent_text"],
                    "sent_dt": match["sent_dt"],
                    "message_key": match["message_key"],
                    "message": "Signal acquired",
                }
            return {
                "status": "empty", "code": None,
                "sent_text": "NO_SIG",
                "message": "No matching code found",
            }
        except imaplib.IMAP4.error as exc:
            return {
                "status": "error", "code": None,
                "sent_text": "AUTH_FAIL",
                "message": self.clean_error_message(exc)
            }
        except Exception as exc:
            return {
                "status": "error", "code": None,
                "sent_text": "READ_FAIL",
                "message": self.clean_error_message(exc)
            }
        finally:
            try:
                client.logout()
            except Exception:
                pass

    def connect_imap(self):
        ctx = ssl.create_default_context()
        try:
            return imaplib.IMAP4_SSL(
                IMAP_SERVER, IMAP_PORT, ssl_context=ctx,
                timeout=IMAP_TIMEOUT_SECONDS)
        except ssl.SSLCertVerificationError:
            fallback_ctx = ssl._create_unverified_context()
            return imaplib.IMAP4_SSL(
                IMAP_SERVER, IMAP_PORT, ssl_context=fallback_ctx,
                timeout=IMAP_TIMEOUT_SECONDS)

    def find_latest_matching_code(self, client):
        typ, data = client.uid("SEARCH", None, "ALL")
        if typ != "OK" or not data or not data[0]:
            return None

        recent_uids = list(reversed(data[0].split()))[:RECENT_MESSAGE_SCAN_LIMIT]

        for uid_bytes in recent_uids:
            uid = (uid_bytes.decode()
                   if isinstance(uid_bytes, bytes) else str(uid_bytes))
            typ, full_data = client.uid("FETCH", uid, "(RFC822)")
            if typ != "OK" or not full_data or not full_data[0]:
                continue

            raw_message = full_data[0][1]
            msg = email.message_from_bytes(raw_message)
            from_header = self.decode_hdr(msg.get("From", ""))
            sender = email.utils.parseaddr(from_header)[1].lower()
            subject = self.decode_hdr(msg.get("Subject", ""))
            combined = f"{subject}\n{self.extract_text(msg)}"
            subject_low = subject.lower()
            code = None

            if sender == MICROSOFT_SEARCH_SENDER.lower():
                code = self.find_code_in_text(combined, MICROSOFT_CODE_PATTERNS)
            elif (
                "chatgpt" in subject_low
                or "temporary" in subject_low
                or "verification" in subject_low
                or "login code" in subject_low
                or "openai" in sender
            ):
                code = self.find_code_in_text(combined, CHATGPT_CODE_PATTERNS)
            else:
                code = self.find_code_in_text(combined, CHATGPT_CODE_PATTERNS)

            if code:
                sent_dt = self.parse_message_datetime(msg.get("Date", ""))
                return {
                    "code": code,
                    "sent_text": self.format_message_time(msg.get("Date", "")),
                    "sent_dt": sent_dt,
                    "message_key": f"{uid}:{code}:{msg.get('Date', '')}",
                }
        return None

    def decode_hdr(self, header_value):
        if not header_value:
            return ""
        parts = decode_header(header_value)
        out = []
        for item, enc in parts:
            if isinstance(item, bytes):
                out.append(item.decode(enc or "utf-8", errors="replace"))
            else:
                out.append(item)
        return "".join(out)

    def extract_text(self, msg):
        def strip_html(html_text):
            text = re.sub(r"<script.*?>.*?</script>", "", html_text,
                          flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<style.*?>.*?</style>", "", text,
                          flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text)
            return text.strip()

        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = part.get("Content-Disposition", "")
                if ctype == "text/plain" and "attachment" not in (disp or ""):
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace")
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        return strip_html(
                            payload.decode(charset, errors="replace"))
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                text = payload.decode(charset, errors="replace")
                if msg.get_content_type() == "text/html":
                    return strip_html(text)
                return text
        return ""


    def extract_html(self, msg):
        """Extract raw HTML from message if available."""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    disp = part.get("Content-Disposition", "")
                    if "attachment" in (disp or ""):
                        continue
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        return payload.decode(charset, errors="replace")
        else:
            if msg.get_content_type() == "text/html":
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        return None

    def find_code_in_text(self, text, patterns):
        if not text:
            return None
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return match.group(1)
        return None

    def format_message_time(self, date_header):
        dt = self.parse_message_datetime(date_header)
        if not dt:
            return "UNKNOWN"
        return dt.astimezone().strftime("%b%d::%H:%M")

    def parse_message_datetime(self, date_header):
        if not date_header:
            return None
        try:
            return email.utils.parsedate_to_datetime(date_header)
        except Exception:
            return None

    def clean_error_message(self, exc):
        if not exc:
            return "UNKNOWN_ERROR"
        if getattr(exc, "args", None):
            first = exc.args[0]
            if isinstance(first, bytes):
                return first.decode("utf-8", errors="replace")
        text = str(exc)
        if text.startswith("b'") and text.endswith("'"):
            return text[2:-1]
        return text

    def on_close(self):
        self.app_closing = True
        if self.code_poll_job:
            self.root.after_cancel(self.code_poll_job)
        if self.toast_hide_job:
            self.root.after_cancel(self.toast_hide_job)
        for bar in self._progress_bars:
            bar.stop()
        self._close_search_dropdown()
        self.hide_toast_notification()
        self.root.destroy()


def main():
    root = tk.Tk()

    def launch_main_app():
        EPViewer(root)

    LoadingSplash(root, on_complete=launch_main_app)

    root.mainloop()


if __name__ == "__main__":
    main()