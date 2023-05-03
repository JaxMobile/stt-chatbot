import os
from chatbot.whisper.ctranslate.utils import (
    model_converter as faster_whisper_model_converter,
)

import logging
import torch
import whisper
from faster_whisper import WhisperModel
from threading import Lock
from typing import BinaryIO, Union, Optional
import ffmpeg
import numpy as np
import environ

logger = logging.getLogger(__name__)
logger.info("Starting loading model: ")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR,'env/.dev.env'))


whisper_model_name= env('MODEL_NAME')
model_base_dir = os.path.join("{}/models".format(BASE_DIR))
faster_whisper_model_path = os.path.join("{}/faster_whisper".format(model_base_dir), whisper_model_name)
whisper_model_path = os.path.join("{}/whisper".format(model_base_dir), whisper_model_name)
faster_whisper_model_converter(whisper_model_name, faster_whisper_model_path)


if torch.cuda.is_available():
    whisper_model = whisper.load_model(whisper_model_name, download_root=whisper_model_path).cuda()
    faster_whisper_model = WhisperModel(faster_whisper_model_path, device="cuda", compute_type="float16")
else:
    whisper_model = whisper.load_model(whisper_model_name, download_root=whisper_model_path)
    faster_whisper_model = WhisperModel(faster_whisper_model_path)
model_lock = Lock()

######## INIT ############
def get_model(method: str = "openai-whisper"):
  if method == "faster-whisper":
      return faster_whisper_model
  return whisper_model


"""
- task: enum("transcribe", "translate")
- language: Language code recorded in audio. See ISO 639-1 Code https://www.loc.gov/standards/iso639-2/php/code_list.php
- method: enum("openai-whisper", "faster-whisper")
- encode: Boolean. True if you want to convert binary to wav format first before perform inference
"""
def run_asr(
    file: BinaryIO, 
    task: Union[str, None], 
    language: Union[str, None],
    method: Optional[str] = None,
    encode=True
):
    audio = load_audio(file, encode)
    options_dict = {"task" : task}
    if language:
        options_dict["language"] = language    
    with model_lock:   
        model = get_model(method)
        if method == "faster-whisper":
            segments = []
            text = ""
            i = 0
            segment_generator, info = model.transcribe(audio, beam_size=5, **options_dict)
            for segment in segment_generator:
                segments.append(segment)
                text = text + segment.text
            result = {
                "language": options_dict.get("language", info.language),
                "segments": segments,
                "text": text,
            }
        else:
            result = model.transcribe(audio, **options_dict)

    return result


SAMPLE_RATE = 16000
def load_audio(file: BinaryIO, encode=True, sr: int = SAMPLE_RATE):
    """
    Open an audio file object and read as mono waveform, resampling as necessary.
    Modified from https://github.com/openai/whisper/blob/main/whisper/audio.py to accept a file object
    Parameters
    ----------
    file: BinaryIO
        The audio file like object
    encode: Boolean
        If true, encode audio stream to WAV before sending to whisper
    sr: int
        The sample rate to resample the audio if necessary
    Returns
    -------
    A NumPy array containing the audio waveform, in float32 dtype.
    """
    if encode:
        try:
            # This launches a subprocess to decode audio while down-mixing and resampling as necessary.
            # Requires the ffmpeg CLI and `ffmpeg-python` package to be installed.
            out, _ = (
                ffmpeg.input("pipe:", threads=0)
                .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=sr)
                .run(cmd="ffmpeg", capture_stdout=True, capture_stderr=True, input=file.read())
            )
        except ffmpeg.Error as e:
            raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e
    else:
        out = file.read()

    return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0

if __name__ == "__main__":
  with open('./models/1.wav', 'rb') as f:
    result = run_asr(f, "transcribe", "en", "openai-whisper", False)
    print(result)
