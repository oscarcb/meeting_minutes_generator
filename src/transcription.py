import logging

from .config import get_openai_client

class Transcriber:
    @staticmethod
    def transcribe_audio(audio_file_path):
        client = get_openai_client()
        logging.info("Transcribing audio...")
        try:
            with open(audio_file_path, 'rb') as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            logging.info("Transcription complete.")
            return transcription.text
        except Exception as e:
            logging.error(f"Error during transcription: {e}")
            return None

    @staticmethod
    def clean_transcript(transcript):
        return ' '.join(line.strip() for line in transcript.split('\n') if line.strip())