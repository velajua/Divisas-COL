from pathlib import Path
from TTS.api import TTS


class XTTSVoiceover:
    def __init__(
        self,
        model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2",
        use_gpu: bool = False,
    ):
        self.tts = TTS(model_name, gpu=use_gpu)

    def synthesize_chunk(
        self,
        text: str,
        voice_wav: str | Path,
        output_wav: str | Path,
        language: str = "es",
    ) -> None:
        output_wav = Path(output_wav)
        output_wav.parent.mkdir(parents=True, exist_ok=True)

        self.tts.tts_to_file(
            text=text,
            speaker_wav=str(voice_wav),
            language=language,
            file_path=str(output_wav),
        )
