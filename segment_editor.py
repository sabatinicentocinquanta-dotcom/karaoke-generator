"""Segment editor — opens after Whisper transcription.

Each segment is shown as an editable text row with its timestamp.
On confirm, edited text is split into words and timestamps are redistributed:
  - same word count as original → 1:1 timestamp mapping
  - different word count        → even distribution across segment duration
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
import copy
from typing import Callable


# ── Word-timestamp remapping ──────────────────────────────────────────────────

def _remap_words(segment: dict, new_text: str) -> dict:
    """Return a new segment dict with updated words and redistributed timestamps."""
    new_seg = copy.deepcopy(segment)
    new_words_text = new_text.split()
    if not new_words_text:
        return new_seg

    old_words  = segment["words"]
    seg_start  = old_words[0]["start"]  if old_words else segment["start"]
    seg_end    = old_words[-1]["end"]   if old_words else segment["end"]
    total_dur  = max(seg_end - seg_start, 0.01)

    if len(new_words_text) == len(old_words):
        # 1-to-1 mapping: keep original timestamps, replace text only
        new_words = [
            {"word": nw, "start": ow["start"], "end": ow["end"]}
            for nw, ow in zip(new_words_text, old_words)
        ]
    else:
        # Different word count: distribute evenly
        dur_per = total_dur / len(new_words_text)
        new_words = [
            {
                "word":  word,
                "start": seg_start + i * dur_per,
                "end":   seg_start + (i + 1) * dur_per,
            }
            for i, word in enumerate(new_words_text)
        ]

    new_seg["text"]  = new_text.strip()
    new_seg["start"] = seg_start
    new_seg["end"]   = seg_end
    new_seg["words"] = new_words
    return new_seg


def _merge_segments(a: dict, b: dict) -> dict:
    merged_text  = (a["text"].rstrip() + " " + b["text"].lstrip()).strip()
    merged_words = a["words"] + b["words"]
    return {
        "text":  merged_text,
        "start": a["start"],
        "end":   b["end"],
        "words": merged_words,
    }


def _split_segment(segment: dict, cursor_char: int) -> tuple[dict, dict]:
    """Split a segment at the word boundary closest to cursor_char position.

    Returns two new segment dicts (first_half, second_half).
    """
    text = segment["text"]
    words = segment["words"]

    # Find which word index corresponds to the cursor position
    # Walk through words and accumulate character positions
    pos = 0
    split_word_idx = len(words) // 2  # fallback: split at midpoint
    for i, w in enumerate(words):
        word_end_pos = pos + len(w["word"])
        if word_end_pos >= cursor_char:
            # Split before this word if cursor is closer to its start, else after
            split_word_idx = i if cursor_char <= pos + len(w["word"]) // 2 else i + 1
            split_word_idx = max(1, min(split_word_idx, len(words) - 1))
            break
        pos = word_end_pos + 1  # +1 for space

    words_a = words[:split_word_idx]
    words_b = words[split_word_idx:]

    seg_a = {
        "text":  " ".join(w["word"] for w in words_a),
        "start": words_a[0]["start"],
        "end":   words_a[-1]["end"],
        "words": words_a,
    }
    seg_b = {
        "text":  " ".join(w["word"] for w in words_b),
        "start": words_b[0]["start"],
        "end":   words_b[-1]["end"],
        "words": words_b,
    }
    return seg_a, seg_b


# ── Segment Editor window ─────────────────────────────────────────────────────

class SegmentEditor(tk.Toplevel):
    """
    Modal window that lets the user review and edit transcribed segments.
    on_confirm(segments) is called when the user confirms the edits.
    """

    BG      = "#0f0f1e"
    ROW_BG  = "#161628"
    ROW_ALT = "#1a1a30"
    FG      = "#d4d4f0"
    TS_FG   = "#6882c8"
    BTN_BG  = "#2d2d50"
    ACT_BG  = "#533483"
    OK_BG   = "#1b4332"
    DEL_FG  = "#ff6b6b"

    def __init__(self, parent: tk.Widget, segments: list[dict],
                 on_confirm: Callable[[list[dict]], None]) -> None:
        super().__init__(parent)
        self.title("Editor segmenti — Karaoke Generator")
        self.geometry("920x620")
        self.minsize(700, 400)
        self.configure(bg=self.BG)
        self.grab_set()   # modal

        self._source_segments = copy.deepcopy(segments)
        self._on_confirm = on_confirm

        # Working list: [(segment_dict, tk.StringVar, tk.Entry), ...]
        self._rows: list[tuple[dict, tk.StringVar, tk.Entry]] = []

        self._build_ui()
        self._populate()

    # ── UI construction ───────────────────────────────────────────

    def _build_ui(self) -> None:
        # Header
        hdr = tk.Frame(self, bg="#16213e")
        hdr.pack(fill="x")
        tk.Label(hdr, text="Revisione trascrizione",
                 font=("Arial", 13, "bold"), bg="#16213e", fg="#c8d6ff",
                 pady=8).pack(side="left", padx=14)
        tk.Label(hdr,
                 text="Correggi il testo • Unisci/elimina righe • Conferma per generare il video",
                 font=("Arial", 9), bg="#16213e", fg="#8090b0").pack(side="left")

        # Legend
        legend = tk.Frame(self, bg=self.BG)
        legend.pack(fill="x", padx=12, pady=4)
        for txt, fg in [
            ("  [×] elimina riga", self.DEL_FG),
            ("  [↓] unisci con successiva", self.TS_FG),
            ("  [✂] dividi dove si trova il cursore", "#c8a0ff"),
            ("  Testo modificabile inline", self.FG),
        ]:
            tk.Label(legend, text=txt, bg=self.BG, fg=fg,
                     font=("Arial", 8)).pack(side="left")

        # Scrollable area
        container = tk.Frame(self, bg=self.BG)
        container.pack(fill="both", expand=True, padx=8, pady=4)

        self._canvas = tk.Canvas(container, bg=self.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical",
                                  command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(self._canvas, bg=self.BG)
        self._canvas_win = self._canvas.create_window(
            (0, 0), window=self._inner, anchor="nw")

        self._inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Footer buttons
        footer = tk.Frame(self, bg="#16213e")
        footer.pack(fill="x", side="bottom")

        self._count_label = tk.Label(footer, text="", bg="#16213e", fg=self.TS_FG,
                                     font=("Arial", 9))
        self._count_label.pack(side="left", padx=14, pady=8)

        tk.Button(footer, text="Annulla", command=self.destroy,
                  bg=self.BTN_BG, fg=self.FG, width=10).pack(side="right", padx=8, pady=8)
        tk.Button(footer, text="✓  Conferma", command=self._confirm,
                  bg=self.OK_BG, fg="white", font=("Arial", 10, "bold"),
                  width=14).pack(side="right", padx=4, pady=8)

    # ── Populate / rebuild rows ───────────────────────────────────

    def _populate(self) -> None:
        """(Re)build the row list from self._source_segments."""
        # Clear inner frame
        for child in self._inner.winfo_children():
            child.destroy()
        self._rows.clear()

        for idx, seg in enumerate(self._source_segments):
            self._add_row(idx, seg)

        self._update_count()

    def _add_row(self, idx: int, seg: dict) -> None:
        bg = self.ROW_BG if idx % 2 == 0 else self.ROW_ALT

        frame = tk.Frame(self._inner, bg=bg, pady=3)
        frame.pack(fill="x", padx=4, pady=1)

        # Timestamp
        ts = f"[{seg['start']:6.1f}s]"
        tk.Label(frame, text=ts, width=9, bg=bg, fg=self.TS_FG,
                 font=("Courier New", 9)).pack(side="left", padx=(6, 2))

        # Editable text
        var = tk.StringVar(value=seg["text"])
        entry = tk.Entry(frame, textvariable=var,
                         bg="#0d1117", fg=self.FG, insertbackground="white",
                         relief="flat", font=("Arial", 10),
                         highlightthickness=1, highlightbackground="#3a3a5c",
                         highlightcolor="#6862c8")
        entry.pack(side="left", fill="x", expand=True, padx=4)

        # Word count badge
        n_words = len(seg["words"])
        wc_lbl = tk.Label(frame, text=f"{n_words}w", width=4,
                          bg=bg, fg="#606080", font=("Arial", 8))
        wc_lbl.pack(side="left", padx=2)

        # Split button
        split_btn = tk.Button(
            frame, text="✂", width=2,
            bg=self.BTN_BG, fg="#c8a0ff", relief="flat",
            command=lambda i=idx, e=entry: self._split(i, e),
        )
        split_btn.pack(side="left", padx=1)

        # Merge-with-next button
        merge_btn = tk.Button(
            frame, text="↓", width=2,
            bg=self.BTN_BG, fg=self.TS_FG, relief="flat",
            command=lambda i=idx: self._merge(i),
        )
        merge_btn.pack(side="left", padx=1)

        # Delete button
        del_btn = tk.Button(
            frame, text="×", width=2,
            bg=self.BTN_BG, fg=self.DEL_FG, relief="flat",
            command=lambda i=idx: self._delete(i),
        )
        del_btn.pack(side="left", padx=(1, 4))

        self._rows.append((seg, var, entry))

    # ── Row actions ───────────────────────────────────────────────

    def _delete(self, idx: int) -> None:
        if len(self._source_segments) <= 1:
            messagebox.showwarning("Attenzione", "Deve restare almeno un segmento.")
            return
        self._flush_edits()
        del self._source_segments[idx]
        self._populate()

    def _split(self, idx: int, entry: tk.Entry) -> None:
        seg = self._source_segments[idx]
        if len(seg["words"]) < 2:
            messagebox.showinfo("Dividi", "La riga deve avere almeno 2 parole per essere divisa.")
            return
        self._flush_edits()
        cursor_char = entry.index(tk.INSERT)
        seg_a, seg_b = _split_segment(self._source_segments[idx], cursor_char)
        self._source_segments[idx:idx + 1] = [seg_a, seg_b]
        self._populate()

    def _merge(self, idx: int) -> None:
        if idx >= len(self._source_segments) - 1:
            messagebox.showinfo("Merge", "Non c'è un segmento successivo da unire.")
            return
        self._flush_edits()
        merged = _merge_segments(
            self._source_segments[idx],
            self._source_segments[idx + 1],
        )
        self._source_segments[idx] = merged
        del self._source_segments[idx + 1]
        self._populate()

    # ── Helpers ───────────────────────────────────────────────────

    def _flush_edits(self) -> None:
        """Apply current Entry values back to _source_segments before any structural change."""
        for i, (seg, var, _entry) in enumerate(self._rows):
            new_text = var.get().strip()
            if new_text != seg["text"]:
                self._source_segments[i] = _remap_words(seg, new_text)

    def _confirm(self) -> None:
        self._flush_edits()
        result = [s for s in self._source_segments if s.get("words")]
        if not result:
            messagebox.showerror("Errore", "Non ci sono segmenti validi.")
            return
        self._on_confirm(result)
        self.destroy()

    def _update_count(self) -> None:
        n_seg   = len(self._source_segments)
        n_words = sum(len(s["words"]) for s in self._source_segments)
        self._count_label.config(text=f"{n_seg} segmenti  •  {n_words} parole")

    # ── Canvas scrolling ──────────────────────────────────────────

    def _on_inner_configure(self, _event=None) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self._canvas.itemconfig(self._canvas_win, width=event.width)

    def _on_mousewheel(self, event) -> None:
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
