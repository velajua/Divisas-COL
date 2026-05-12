from pathlib import Path
from pydub import AudioSegment


def merge_wavs(
    wav_files: list[str | Path],
    output_wav: str | Path,
    silence_ms: int = 450,
) -> None:
    if not wav_files:
        raise ValueError("No WAV files provided for merge.")

    silence = AudioSegment.silent(duration=silence_ms)
    combined = AudioSegment.empty()

    for wav_file in wav_files:
        combined += AudioSegment.from_wav(str(wav_file))
        combined += silence

    output_wav = Path(output_wav)
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    combined.export(str(output_wav), format="wav")


def export_mp3(
    input_wav: str | Path,
    output_mp3: str | Path,
    bitrate: str = "192k",
) -> None:
    audio = AudioSegment.from_wav(str(input_wav))
    output_mp3 = Path(output_mp3)
    output_mp3.parent.mkdir(parents=True, exist_ok=True)
    audio.export(str(output_mp3), format="mp3", bitrate=bitrate)
