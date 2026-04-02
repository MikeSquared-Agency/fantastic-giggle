import sys
from pathlib import Path
_DEPS = Path(__file__).parent.parent / "deps"
if _DEPS.exists() and str(_DEPS) not in sys.path:
    sys.path.insert(0, str(_DEPS))

import threading
import numpy as np
import sounddevice as sd
import webrtcvad
from faster_whisper import WhisperModel
from config import WHISPER_DIR, SAMPLE_RATE, SILENCE_FRAMES, VAD_AGGRESSIVENESS, FRAME_MS

FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)

_model    = None
_vad      = None
_callback = None
_running  = False
_stream   = None

_speech_frames = []
_silence_count = 0
_in_speech     = False


def has_input_device() -> bool:
    try:
        devices = sd.query_devices()
    except Exception:
        return False

    return any(device.get("max_input_channels", 0) > 0 for device in devices)


def _load():
    global _model, _vad
    _model = WhisperModel(
        WHISPER_DIR,
        device="cpu",
        compute_type="int8",
        local_files_only=True
    )
    _vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)


def start(on_utterance_fn):
    global _callback, _running, _stream, _speech_frames, _silence_count, _in_speech
    if not has_input_device():
        raise RuntimeError("No audio input device was found.")

    if _model is None:
        _load()

    _callback = on_utterance_fn
    _running  = True
    _speech_frames = []
    _silence_count = 0
    _in_speech = False

    try:
        _stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=FRAME_SAMPLES,
            callback=_audio_callback
        )
        _stream.start()
    except Exception:
        _running = False
        if _stream:
            _stream.close()
            _stream = None
        raise


def stop():
    global _running, _stream, _speech_frames, _silence_count, _in_speech
    _running = False
    if _stream:
        _stream.stop()
        _stream.close()
        _stream = None
    _speech_frames = []
    _silence_count = 0
    _in_speech = False


def _audio_callback(indata, frames, time, status):
    global _speech_frames, _silence_count, _in_speech
    if not _running:
        return

    frame = (indata[:, 0] * 32768).astype(np.int16).tobytes()
    try:
        is_speech = _vad.is_speech(frame, SAMPLE_RATE)
    except Exception:
        return

    if is_speech:
        if not _in_speech:
            _in_speech = True
            _speech_frames.clear()
        _speech_frames.append(frame)
        _silence_count = 0
    elif _in_speech:
        _speech_frames.append(frame)
        _silence_count += 1
        if _silence_count >= SILENCE_FRAMES:
            _in_speech     = False
            _silence_count = 0
            frames_copy    = list(_speech_frames)
            _speech_frames.clear()
            threading.Thread(target=_transcribe, args=(frames_copy,), daemon=True).start()


def _transcribe(frames: list[bytes]):
    audio = np.frombuffer(b"".join(frames), dtype=np.int16).astype(np.float32) / 32768.0
    segments, _ = _model.transcribe(
        audio,
        language="en",
        initial_prompt="save close open copy paste undo redo find switch tab",
        vad_filter=True,
        beam_size=1
    )
    text = " ".join(s.text.strip() for s in segments).strip()
    print(f"[stt] transcribed: {text!r}")
    if text and _callback:
        _callback(text)
