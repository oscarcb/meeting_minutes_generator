from .config import get_openai_client

class Transcriber:
    @staticmethod
    def transcribe_audio(audio_file_path):
        client = get_openai_client()
        # Implementation here