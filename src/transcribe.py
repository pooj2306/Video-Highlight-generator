"""
Stage 1: audio extraction + transcription with segment AND word timestamps.

Backends: "groq" (Whisper large-v3-turbo via API, chunked) or "local" (faster-whisper).
Both return list[Segment]; each Segment carries its words so later stages can
snap clip boundaries to word edges.
"""

import json
import os
import subprocess
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Word:
    word: str
    start: float
    end: float


@dataclass
class Segment:
    id: int
    start: float
    end: float
    text: str
    avg_logprob: float = 0.0
    words: list[Word] = field(default_factory=list)

    @staticmethod
    def from_dict(d: dict) -> "Segment":
        d = dict(d)
        d["words"] = [Word(**w) for w in d.get("words", [])]
        return Segment(**d)


# ------------------------------------------------------------------ ffmpeg helpers
def has_audio_stream(media_path: str) -> bool:
    out = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
        "stream=codec_type", "-of", "csv=p=0", media_path
    ], capture_output=True, text=True).stdout.strip()
    return out == "audio"

def extract_audio(video_path: str, out_path: str) -> str:
    if not has_audio_stream(video_path):
        raise ValueError(
            f"The uploaded file '{os.path.basename(video_path)}' contains no audio track. "
            "Please upload a video with sound or re-download using 'yt-dlp -f bv*+ba/b --merge-output-format mp4'."
        )

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "flac",
        "-ac", "1",
        "-ar", "16000",
        out_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"\n[FFmpeg Error in extract_audio]:\n{e.stderr}")
        raise RuntimeError(f"FFmpeg failed to extract audio from '{video_path}'.") from e

    return out_path


def get_duration_seconds(media_path: str) -> float:
    out = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", media_path
    ], check=True, capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0



def has_video_stream(media_path: str) -> bool:
    out = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=codec_type", "-of", "csv=p=0", media_path
    ], capture_output=True, text=True).stdout.strip()
    return out == "video"


def split_audio(audio_path: str, chunk_seconds: int, work_dir: str) -> list[tuple[str, float]]:
    total = get_duration_seconds(audio_path)
    chunks, start, i = [], 0.0, 0
    while start < total:
        p = str(Path(work_dir) / f"chunk_{i:03d}.flac")
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-t", str(chunk_seconds),
            "-i", audio_path,
            "-c:a", "flac",  # Re-encode FLAC header cleanly rather than '-c copy'
            p
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"\n[FFmpeg Error in split_audio]:\n{e.stderr}")
            raise
        chunks.append((p, start))
        start += chunk_seconds
        i += 1
    return chunks


def _attach_words(segments: list[Segment], words: list[Word]) -> None:
    """Assign each word to the segment whose span contains its midpoint."""
    if not words:
        return
    j = 0
    for seg in segments:
        while j < len(words) and (words[j].start + words[j].end) / 2 < seg.start:
            j += 1
        while j < len(words) and (words[j].start + words[j].end) / 2 <= seg.end:
            seg.words.append(words[j])
            j += 1


# ------------------------------------------------------------------ backends

def _as_dict(obj):
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return dict(getattr(obj, "__dict__", {}))


def _transcribe_groq(audio_path, model, language, chunk_seconds, work_dir):
    from groq import Groq
    from src.config import get_api_key

    client = Groq(api_key=get_api_key())
    segments, words, sid = [], [], 0

    for chunk_path, offset in split_audio(audio_path, chunk_seconds, work_dir):
        kwargs = dict(model=model, response_format="verbose_json",
                      timestamp_granularities=["word", "segment"])
        if language:
            kwargs["language"] = language
        resp = None
        for attempt in range(5):
            try:
                with open(chunk_path, "rb") as f:
                    resp = client.audio.transcriptions.create(
                        file=(os.path.basename(chunk_path), f.read()), **kwargs)
                break
            except Exception as e:
                err_str = str(e).lower()
                if "invalid api key" in err_str or "invalid_api_key" in err_str or "401" in err_str:
                    raise RuntimeError(
                        "Groq API key is invalid. Please update GROQ_API_KEY in .env or switch to 'On this machine' transcription."
                    ) from e
                if attempt == 4:
                    if "connection error" in err_str or "10053" in err_str or "readerror" in err_str:
                        raise RuntimeError(
                            "Connection to Groq API failed. Please check your internet connection or switch to 'On this machine' for offline transcription."
                        ) from e
                    raise
                time.sleep(2 ** attempt)

        data = _as_dict(resp)
        for s in data.get("segments") or []:
            s = _as_dict(s)
            text = (s.get("text") or "").strip()
            if not text:
                continue
            segments.append(Segment(sid, float(s["start"]) + offset, float(s["end"]) + offset,
                                    text, float(s.get("avg_logprob", 0.0))))
            sid += 1
        for w in data.get("words") or []:
            w = _as_dict(w)
            words.append(Word(str(w.get("word", "")).strip(), float(w["start"]) + offset,
                              float(w["end"]) + offset))

    _attach_words(segments, words)
    return segments


def _transcribe_local(audio_path, model_size, language):
    import soundfile as sf
    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="auto", compute_type="int8")
    # Read audio with soundfile to avoid PyAV metadata_errors incompatibility on newer av versions
    audio_data, _ = sf.read(audio_path, dtype="float32")
    raw, _ = model.transcribe(audio_data, language=language, vad_filter=True, word_timestamps=True)
    segments = []
    for s in raw:
        text = s.text.strip()
        if not text:
            continue
        seg = Segment(len(segments), s.start, s.end, text, s.avg_logprob)
        seg.words = [Word(w.word.strip(), w.start, w.end) for w in (s.words or [])]
        segments.append(seg)
    return segments


# ------------------------------------------------------------------ public

def transcribe(video_path, backend="groq", groq_model="whisper-large-v3-turbo", local_model="small",
               language=None, chunk_seconds=600, cache_dir="data/transcripts") -> list[Segment]:
    from src.config import has_valid_api_key

    if backend == "groq" and not has_valid_api_key():
        # Fallback to local transcription if no valid Groq key is configured
        backend = "local"

    name = Path(video_path).stem
    cache = Path(cache_dir) / f"{name}.json"
    os.makedirs(cache_dir, exist_ok=True)
    if cache.exists():
        return [Segment.from_dict(s) for s in json.loads(cache.read_text(encoding="utf-8"))]

    work = Path(cache_dir) / f"_work_{name}"
    work.mkdir(exist_ok=True)
    audio = extract_audio(video_path, str(work / "audio.flac"))
    try:
        try:
            segs = (_transcribe_groq(audio, groq_model, language, chunk_seconds, str(work))
                    if backend == "groq" else _transcribe_local(audio, local_model, language))
        except Exception:
            if backend == "groq":
                # If Groq transcription fails (e.g. network/connection issue), fall back to local
                segs = _transcribe_local(audio, local_model, language)
            else:
                raise
    finally:
        for p in work.glob("*"):
            p.unlink(missing_ok=True)
        try:
            work.rmdir()
        except OSError:
            pass

    cache.write_text(json.dumps([asdict(s) for s in segs], indent=1, ensure_ascii=False), encoding="utf-8")
    return segs