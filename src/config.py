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
MAX_TOKENS = 100000
AUDIO_BITRATE = 48000
AUDIO_CHANNELS = 1
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

@lru_cache(maxsize=1)
def get_openai_client():
    # Implementation here

@lru_cache(maxsize=1)
def get_anthropic_client():
    # Implementation here