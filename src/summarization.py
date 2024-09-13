from .config import get_anthropic_client, MAX_TOKENS

class Summarizer:
    @staticmethod
    def generate_summary(transcription, custom_prompt):
        client = get_anthropic_client()
        # Implementation here

    @staticmethod
    def extract_title(transcript):
        # Implementation here