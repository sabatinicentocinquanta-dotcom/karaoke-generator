"""Assembles the karaoke MP4 from segments + instrumental audio."""

from __future__ import annotations
from typing import Callable
import numpy as np

import renderer as R

INSTRUMENTAL_THRESHOLD = 15.0  # seconds of silence → "Strumentale" screen
INTRO_DURATION         = 4.0   # title/artist intro screen duration
ENDING_DURATION        = 3.5   # "Ending" screen
BY_FRANK_DURATION      = 3.5   # "by Frank" screen


def _clip(arr: np.ndarray, duration: float):
    from moviepy.editor import ImageClip
    return ImageClip(arr).set_duration(max(duration, 0.05))


def _flatten_words(segments: list[dict]) -> list[dict]:
    flat = []
    for si, seg in enumerate(segments):
        words = seg.get("words", [])
        if not words:
            continue
        for wi, w in enumerate(words):
            flat.append({
                "word":          w["word"],
                "start":         w["start"],
                "end":           w["end"],
                "seg_idx":       si,
                "w_idx":         wi,
                "seg_words":     words,
                "next_seg_text": segments[si + 1]["text"].strip() if si + 1 < len(segments) else None,
            })
    return flat


def generate_video(
    segments: list[dict],
    instrumental_path: str,
    output_path: str,
    title: str,
    artist: str,
    log: Callable[[str], None] = print,
) -> None:
    from moviepy.editor import AudioFileClip, concatenate_videoclips

    log("Caricamento audio strumentale...")
    audio = AudioFileClip(instrumental_path)
    audio_dur = audio.duration
    log(f"Durata audio: {audio_dur:.1f}s")

    all_words = _flatten_words(segments)
    if not all_words:
        raise ValueError("Nessuna parola trovata nella trascrizione.")

    log(f"Parole da animare: {len(all_words)}")
    clips = []

    first_start = all_words[0]["start"]
    last_end    = all_words[-1]["end"]

    # ── Intro screen ─────────────────────────────────────────────
    intro_screen_dur = min(first_start, INTRO_DURATION)
    if intro_screen_dur > 0:
        clips.append(_clip(R.render_intro(title, artist), intro_screen_dur))
        log(f"Intro: {intro_screen_dur:.1f}s")

    if first_start > intro_screen_dur + 0.1:
        pre_inst_dur = first_start - intro_screen_dur
        clips.append(_clip(R.render_instrumental(title, artist), pre_inst_dur))
        log(f"Strumentale iniziale: {pre_inst_dur:.1f}s")

    # ── Word-by-word karaoke ──────────────────────────────────────
    for i, wi in enumerate(all_words):
        si_idx   = wi["seg_idx"]
        w_idx    = wi["w_idx"]
        seg_words = wi["seg_words"]
        next_line = wi["next_seg_text"]

        # Build coloured words_state for this moment
        words_state = [
            (sw["word"], "sung" if j < w_idx else "current" if j == w_idx else "upcoming")
            for j, sw in enumerate(seg_words)
        ]

        if i + 1 < len(all_words):
            nw = all_words[i + 1]
            gap_after  = nw["start"] - wi["end"]
            clip_until = wi["end"] if gap_after >= INSTRUMENTAL_THRESHOLD else nw["start"]
            word_dur   = max(clip_until - wi["start"], 0.08)

            clips.append(_clip(R.render_karaoke(words_state, next_line, title, artist), word_dur))

            if gap_after >= INSTRUMENTAL_THRESHOLD:
                log(f"  Strumentale a t={wi['end']:.1f}s ({gap_after:.1f}s)")
                clips.append(_clip(R.render_instrumental(title, artist), gap_after))
        else:
            # Last word: keep highlighted until ending sequence
            ending_seq_start = max(last_end, audio_dur - ENDING_DURATION - BY_FRANK_DURATION)
            word_dur = max(ending_seq_start - wi["start"], 0.5)
            clips.append(_clip(R.render_karaoke(words_state, None, title, artist), word_dur))

    # ── Post-vocal instrumental (if any) ─────────────────────────
    ending_seq_start = max(last_end, audio_dur - ENDING_DURATION - BY_FRANK_DURATION)
    post_inst_dur = ending_seq_start - last_end
    if post_inst_dur > 0.5:
        log(f"Strumentale finale: {post_inst_dur:.1f}s")
        clips.append(_clip(R.render_instrumental(title, artist), post_inst_dur))

    # ── Ending + by Frank ─────────────────────────────────────────
    log("Aggiunta Ending e 'by Frank'...")
    clips.append(_clip(R.render_ending(title, artist), ENDING_DURATION))
    clips.append(_clip(R.render_by_frank(), BY_FRANK_DURATION))

    # ── Render ────────────────────────────────────────────────────
    log("Concatenazione clip...")
    video = concatenate_videoclips(clips, method="compose")

    # Align to audio (trim overshoot, keep if slightly short)
    if video.duration > audio_dur + 0.1:
        video = video.subclip(0, audio_dur)

    log("Aggiunta traccia audio strumentale...")
    video = video.set_audio(audio)

    log(f"Esportazione '{output_path}' ({video.duration:.1f}s) — operazione lenta, attendere...")
    video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp_karaoke_audio.m4a",
        remove_temp=True,
        verbose=False,
        logger=None,
        preset="medium",
    )
    log("Video completato!")
