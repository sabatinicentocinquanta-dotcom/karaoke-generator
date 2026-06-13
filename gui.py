"""Tkinter GUI for Karaoke Generator."""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import sys
import os
import re
from datetime import datetime

_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
_OUTPUT_DIR  = os.path.join(_PROJECT_DIR, "output")
os.makedirs(_OUTPUT_DIR, exist_ok=True)


def _parse_mp3(path: str) -> dict:
    """Parse 'Titolo - Artista_(Vocal).mp3' → {title, artist, kind}.
    kind is 'vocal', 'instrumental', or 'unknown'.
    """
    basename = os.path.splitext(os.path.basename(path))[0]
    kind = "unknown"
    for tag in ("_(Vocal)", "_(Instrumental)"):
        if tag in basename:
            kind = tag[2:-1].lower()   # 'vocal' or 'instrumental'
            basename = basename.replace(tag, "").strip()
            break
    parts = basename.split(" - ", 1)
    return {
        "title":  parts[0].strip() if parts else "",
        "artist": parts[1].strip() if len(parts) > 1 else "",
        "kind":   kind,
    }


def _sibling_path(vocal_path: str, tag_from: str, tag_to: str) -> str:
    """Return the instrumental path derived from the vocal path."""
    d   = os.path.dirname(vocal_path)
    b   = os.path.basename(vocal_path)
    new = b.replace(tag_from, tag_to)
    return os.path.join(d, new)


def _output_path(title: str, artist: str) -> str:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = re.sub(r'[\\/*?:"<>|]', "_", f"{title} - {artist}_{ts}.mp4")
    return os.path.join(_OUTPUT_DIR, name)


class KaraokeApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.vocal_path        = tk.StringVar()
        self.instrumental_path = tk.StringVar()
        self.output_path       = tk.StringVar()
        self.title_var         = tk.StringVar()
        self.artist_var        = tk.StringVar()
        self.language_var      = tk.StringVar(value="auto")
        self.segments: list[dict] | None = None
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────

    def _build_ui(self) -> None:
        self.root.configure(bg="#1a1a2e")
        pad = {"padx": 10, "pady": 6}

        # Header
        header = tk.Frame(self.root, bg="#16213e")
        header.pack(fill="x")
        tk.Label(
            header, text="🎤  Karaoke Generator",
            font=("Arial", 18, "bold"), bg="#16213e", fg="#e0d7ff",
        ).pack(side="left", padx=14, pady=12)

        gpu_text, gpu_color = self._detect_gpu()
        tk.Label(
            header, text=gpu_text,
            font=("Arial", 9), bg="#16213e", fg=gpu_color,
        ).pack(side="right", padx=14)

        # Form
        form = tk.LabelFrame(self.root, text=" Impostazioni ", bg="#1a1a2e",
                             fg="#8ab4f8", font=("Arial", 10))
        form.pack(fill="x", padx=16, pady=8)

        def row(label, var, r, pick_fn=None, choices=None) -> tk.Entry | None:
            tk.Label(form, text=label, bg="#1a1a2e", fg="white",
                     width=18, anchor="w").grid(row=r, column=0, **pad)
            widget = None
            if choices:
                om = ttk.Combobox(form, textvariable=var, values=choices, width=10, state="readonly")
                om.grid(row=r, column=1, sticky="w", **pad)
            else:
                widget = tk.Entry(form, textvariable=var, width=42,
                                  bg="#0f3460", fg="white", insertbackground="white")
                widget.grid(row=r, column=1, sticky="ew", **pad)
            if pick_fn:
                tk.Button(form, text="…", command=pick_fn, width=3,
                          bg="#533483", fg="white").grid(row=r, column=2, **pad)
            return widget

        row("Titolo brano:",   self.title_var,  0)
        row("Artista:",        self.artist_var, 1)
        entry_vocal = row("MP3 Vocale:",     self.vocal_path, 2,
                          pick_fn=lambda: self._pick_mp3(self.vocal_path))
        entry_inst  = row("MP3 Strumentale:", self.instrumental_path, 3,
                          pick_fn=lambda: self._pick_mp3(self.instrumental_path))
        row("Output MP4:",     self.output_path, 4, pick_fn=self._pick_output)
        row("Lingua (Whisper):", self.language_var, 5,
            choices=["auto", "it", "en", "es", "fr", "de", "pt"])

        form.columnconfigure(1, weight=1)

        # Drag & drop
        self._register_dnd(entry_vocal, kind_hint="vocal")
        self._register_dnd(entry_inst,  kind_hint="instrumental")

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(pady=8)

        self.btn_transcribe = tk.Button(
            btn_frame, text="1 ▶  Trascrivi con Whisper",
            command=self._transcribe, width=28,
            bg="#533483", fg="white", font=("Arial", 10, "bold"),
            activebackground="#7b52ab",
        )
        self.btn_transcribe.pack(side="left", padx=8)

        self.btn_edit = tk.Button(
            btn_frame, text="✎  Editor segmenti",
            command=self._reopen_editor, width=18, state="disabled",
            bg="#2c2c4a", fg="white", font=("Arial", 10),
            activebackground="#44446a",
        )
        self.btn_edit.pack(side="left", padx=8)

        self.btn_generate = tk.Button(
            btn_frame, text="2 ▶  Genera Video MP4",
            command=self._generate, width=24, state="disabled",
            bg="#1b4332", fg="white", font=("Arial", 10, "bold"),
            activebackground="#2d6a4f",
        )
        self.btn_generate.pack(side="left", padx=8)

        # Progress bar
        self.progress = ttk.Progressbar(self.root, mode="indeterminate", length=400)
        self.progress.pack(pady=4)

        # Status label
        self.status_var = tk.StringVar(value="In attesa…")
        tk.Label(self.root, textvariable=self.status_var,
                 bg="#1a1a2e", fg="#8ab4f8",
                 font=("Arial", 9)).pack()

        # Log
        tk.Label(self.root, text="Log:", bg="#1a1a2e", fg="#aaa",
                 anchor="w").pack(anchor="w", padx=16)
        self.log_box = scrolledtext.ScrolledText(
            self.root, height=10, state="disabled",
            bg="#0d0d1a", fg="#c8d6e5", font=("Courier New", 9),
            insertbackground="white",
        )
        self.log_box.pack(fill="both", expand=True, padx=16, pady=(2, 12))

    # ── Hardware detection ────────────────────────────────────────

    @staticmethod
    def _detect_gpu() -> tuple[str, str]:
        try:
            import torch
            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                return f"⚡ GPU: {name}", "#4cff91"
            else:
                return "CPU (nessuna GPU CUDA)", "#aaaaaa"
        except ImportError:
            return "CPU (torch non installato)", "#ff9944"

    # ── Drag & drop ───────────────────────────────────────────────

    def _register_dnd(self, entry: tk.Entry | None, kind_hint: str) -> None:
        if entry is None:
            return
        try:
            from tkinterdnd2 import DND_FILES
            entry.drop_target_register(DND_FILES)
            entry.dnd_bind("<<Drop>>", lambda e, k=kind_hint: self._on_drop(e, k))
        except Exception:
            pass  # tkinterdnd2 not available — drag & drop silently disabled

    def _on_drop(self, event, kind_hint: str) -> None:
        # tkinterdnd2 may wrap paths with spaces in curly braces
        raw = event.data.strip()
        paths = self.root.tk.splitlist(raw)
        if not paths:
            return
        path = paths[0].strip()

        if not path.lower().endswith((".mp3", ".wav", ".m4a", ".flac")):
            return

        info = _parse_mp3(path)
        kind = info["kind"] if info["kind"] != "unknown" else kind_hint

        if kind == "vocal":
            self.vocal_path.set(path)
            if info["title"]:
                self.title_var.set(info["title"])
            if info["artist"]:
                self.artist_var.set(info["artist"])
            # Derive instrumental path
            inst = _sibling_path(path, "_(Vocal)", "_(Instrumental)")
            if os.path.exists(inst):
                self.instrumental_path.set(inst)
            # Set output path
            if info["title"] and info["artist"]:
                self.output_path.set(_output_path(info["title"], info["artist"]))
            self._log(f"File vocale caricato: {os.path.basename(path)}")
            if os.path.exists(inst):
                self._log(f"Strumentale rilevato: {os.path.basename(inst)}")
            else:
                self._log("Strumentale non trovato automaticamente — selezionalo manualmente.")
        else:
            self.instrumental_path.set(path)
            self._log(f"File strumentale caricato: {os.path.basename(path)}")

    # ── File pickers ──────────────────────────────────────────────

    def _pick_mp3(self, var: tk.StringVar) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Audio", "*.mp3 *.wav *.m4a *.flac"), ("Tutti", "*.*")])
        if path:
            var.set(path)

    def _pick_output(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("Video MP4", "*.mp4")])
        if path:
            self.output_path.set(path)

    # ── Logging ───────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")
        self.status_var.set(msg[:80])
        self.root.update_idletasks()

    # ── Validation ────────────────────────────────────────────────

    def _validate(self, require_output: bool = False) -> bool:
        checks = [
            (self.title_var.get().strip(),          "Inserisci il titolo del brano"),
            (self.artist_var.get().strip(),          "Inserisci il nome dell'artista"),
            (self.vocal_path.get().strip(),          "Seleziona il file MP3 vocale"),
            (self.instrumental_path.get().strip(),   "Seleziona il file MP3 strumentale"),
        ]
        if require_output:
            checks.append((self.output_path.get().strip(), "Seleziona il file di output MP4"))
        for value, msg in checks:
            if not value:
                messagebox.showerror("Campo mancante", msg)
                return False
        return True

    # ── Transcription ─────────────────────────────────────────────

    def _transcribe(self) -> None:
        if not self._validate():
            return
        lang = self.language_var.get()
        language = None if lang == "auto" else lang

        self._set_busy(True)
        self._log(f"Avvio trascrizione — modello: Whisper medium, lingua: {lang}")

        def run() -> None:
            try:
                # Ensure the generator directory is on sys.path
                gen_dir = os.path.dirname(os.path.abspath(__file__))
                if gen_dir not in sys.path:
                    sys.path.insert(0, gen_dir)

                import transcriber
                raw_segments = transcriber.transcribe(
                    self.vocal_path.get(), log=self._log, language=language)
                n_words = sum(len(s["words"]) for s in raw_segments)
                self._log(f"Trascrizione OK — {len(raw_segments)} segmenti, {n_words} parole")
                self._log("Apertura editor segmenti…")
                self.root.after(0, lambda: self._open_editor(raw_segments))
            except Exception as exc:
                self._log(f"ERRORE trascrizione: {exc}")
                import traceback
                self._log(traceback.format_exc())
            finally:
                self.root.after(0, lambda: self._set_busy(False))

        threading.Thread(target=run, daemon=True).start()

    def _reopen_editor(self) -> None:
        if not self.segments:
            messagebox.showinfo("Nessuna trascrizione", "Esegui prima la trascrizione.")
            return
        self._open_editor(self.segments)

    def _open_editor(self, segments: list[dict]) -> None:
        """Open the segment editor; on confirm, store segments and unlock generation."""
        gen_dir = os.path.dirname(os.path.abspath(__file__))
        if gen_dir not in sys.path:
            sys.path.insert(0, gen_dir)
        from segment_editor import SegmentEditor

        def on_confirm(edited_segments: list[dict]) -> None:
            self.segments = edited_segments
            n = sum(len(s["words"]) for s in edited_segments)
            self._log(f"Segmenti confermati: {len(edited_segments)} righe, {n} parole")
            self._log("Pronto per generare il video.")
            self.btn_generate.config(state="normal")

        SegmentEditor(self.root, segments, on_confirm=on_confirm)

    # ── Video generation ──────────────────────────────────────────

    def _generate(self) -> None:
        if not self._validate(require_output=True):
            return
        if not self.segments:
            messagebox.showerror("Errore", "Esegui prima la trascrizione (passo 1).")
            return

        self._set_busy(True)
        self._log("Avvio generazione video — operazione lenta (diversi minuti)…")

        def run() -> None:
            try:
                gen_dir = os.path.dirname(os.path.abspath(__file__))
                if gen_dir not in sys.path:
                    sys.path.insert(0, gen_dir)

                import video_generator
                video_generator.generate_video(
                    segments=self.segments,
                    instrumental_path=self.instrumental_path.get(),
                    output_path=self.output_path.get(),
                    title=self.title_var.get().strip(),
                    artist=self.artist_var.get().strip(),
                    log=self._log,
                )
                out = self.output_path.get()
                self.root.after(0, lambda: messagebox.showinfo(
                    "Completato!", f"Video karaoke salvato:\n{out}"))
            except Exception as exc:
                self._log(f"ERRORE generazione: {exc}")
                import traceback
                self._log(traceback.format_exc())
            finally:
                self.root.after(0, lambda: self._set_busy(False))

        threading.Thread(target=run, daemon=True).start()

    # ── Helpers ───────────────────────────────────────────────────

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.btn_transcribe.config(state=state)
        has_segments = bool(self.segments)
        self.btn_generate.config(state="normal" if (not busy and has_segments) else "disabled")
        self.btn_edit.config(state="normal" if (not busy and has_segments) else "disabled")
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()
            self.status_var.set("Pronto.")
