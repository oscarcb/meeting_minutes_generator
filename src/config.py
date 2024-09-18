import os
from functools import lru_cache
import openai
import anthropic
from dotenv import load_dotenv

load_dotenv()

# Constants
LOG_FILE = "processed_meetings.json"
RECORDINGS_FOLDER = "recordings"
MAX_TITLE_LENGTH = 50
MAX_TOKENS = 8192
AUDIO_BITRATE = 48000
AUDIO_CHANNELS = 1
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@lru_cache(maxsize=1)
def get_openai_client():
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in the environment variables")
    return openai.OpenAI(api_key=OPENAI_API_KEY)

@lru_cache(maxsize=1)
def get_anthropic_client():
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not set in the environment variables")
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)