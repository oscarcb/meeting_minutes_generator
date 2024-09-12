import sys
import os
import hashlib
import re
import json
import subprocess
import logging
from datetime import datetime
from functools import lru_cache
import anthropic
import openai
from moviepy.editor import VideoFileClip
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
LOG_FILE = "processed_meetings.json"
RECORDINGS_FOLDER = "recordings"
MAX_TITLE_LENGTH = 50
MAX_TOKENS = 100000  # Adjust as needed for Claude
AUDIO_BITRATE = 48000
AUDIO_CHANNELS = 1
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client (cached)
@lru_cache(maxsize=1)
def get_openai_client():
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set in the environment variables")
    return openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialize Anthropic client (cached)
@lru_cache(maxsize=1)
def get_anthropic_client():
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not set in the environment variables")
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def load_processed_meetings():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_processed_meeting(file_hash, metadata):
    processed_meetings = load_processed_meetings()
    processed_meetings[file_hash] = metadata
    with open(LOG_FILE, 'w') as f:
        json.dump(processed_meetings, f, indent=2)

def hash_audio_file(audio_file_path):
    hasher = hashlib.sha256()
    with open(audio_file_path, 'rb') as af:
        for chunk in iter(lambda: af.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def extract_time_from_filename(filename):
    match = re.search(r'(\d{8}_\d{6})', filename)
    if match:
        time_str = match.group(1)
        return datetime.strptime(time_str, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d_%H-%M-%S")
    return None

def extract_title_from_transcript(transcript):
    client = get_anthropic_client()
    try:
        response = client.completions.create(
            model="claude-2",
            prompt=f"Human: Extract a concise title from the following meeting transcript. The title should be no more than {MAX_TITLE_LENGTH} characters long.\n\nTranscript: {transcript[:1000]}\n\nAssistant: Here's a concise title for the meeting transcript:",
            max_tokens_to_sample=60,
            temperature=0.7
        )
        title = response.completion.strip()
        return title[:MAX_TITLE_LENGTH].replace(" ", "_")
    except Exception as e:
        logging.error(f"Error extracting title: {e}")
        return "Untitled_Meeting"

def generate_output_filename(input_file_path, transcript):
    base_name = os.path.basename(input_file_path)
    time_str = extract_time_from_filename(base_name) or "Unknown_Time"
    title = extract_title_from_transcript(transcript)
    return f"{time_str}_{title}.md"

def save_summary_to_markdown(summary, filename):
    os.makedirs("meetings", exist_ok=True)
    file_path = os.path.join("meetings", filename)
    logging.info(f"Saving summary to Markdown file: {file_path}")
    try:
        with open(file_path, 'w', encoding='utf-8') as md_file:
            md_file.write(summary)
        logging.info(f"Markdown file saved as {file_path}")
    except Exception as e:
        logging.error(f"Error saving summary to Markdown file: {e}")

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

def clean_transcript(transcript):
    return ' '.join(line.strip() for line in transcript.split('\n') if line.strip())

def generate_summary_with_anthropic(transcription):
    client = get_anthropic_client()
    logging.info("Generating summary using Anthropic...")
    try:
        with open('prompt.txt', 'r', encoding='utf-8') as file:
            custom_prompt = file.read()

        response = client.completions.create(
            model="claude-2",
            prompt=f"Human: {custom_prompt}\n\nTranscript: {transcription}\n\nAssistant: Here's a summary of the meeting:",
            max_tokens_to_sample=MAX_TOKENS,
            temperature=0.7
        )
        return response.completion.strip()
    except Exception as e:
        logging.error(f"Error during summary generation with Anthropic: {e}")
        return "Summary generation failed."

def convert_mp4_to_mp3(mp4_file_path, mp3_file_path):
    try:
        video_clip = VideoFileClip(mp4_file_path)
        audio_clip = video_clip.audio
        audio_clip.write_audiofile(mp3_file_path)
        audio_clip.close()
        video_clip.close()
        logging.info(f"Audio extracted and saved as {mp3_file_path}")
    except Exception as e:
        logging.error(f"Error converting MP4 to MP3: {e}")

def check_audio_properties(audio_file_path):
    try:
        result = subprocess.run([
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'a:0',
            '-show_entries', 'stream=bit_rate,channels',
            '-of', 'json',
            audio_file_path
        ], capture_output=True, text=True)

        audio_info = json.loads(result.stdout)
        stream_info = audio_info['streams'][0]

        bit_rate = int(stream_info.get('bit_rate', '0'))
        channels = int(stream_info.get('channels', '0'))

        return bit_rate == AUDIO_BITRATE and channels == AUDIO_CHANNELS
    except Exception as e:
        logging.error(f"Error checking audio properties: {e}")
        return False

def reencode_audio(input_file, output_file):
    try:
        subprocess.run([
            'ffmpeg',
            '-i', input_file,
            '-ac', str(AUDIO_CHANNELS),
            '-b:a', f'{AUDIO_BITRATE//1000}k',
            '-y',
            output_file
        ], check=True)
        logging.info(f"Audio re-encoded successfully: {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error re-encoding audio: {e}")
        return False

def process_audio_file(file_path):
    if file_path.lower().endswith('.mp4'):
        logging.info(f"Processing MP4 file: {file_path}")
        mp3_file_path = file_path.rsplit('.', 1)[0] + '.mp3'
        
        if os.path.exists(mp3_file_path):
            logging.info(f"Corresponding MP3 file already exists: {mp3_file_path}")
        else:
            logging.info(f"Converting MP4 to MP3: {file_path}")
            convert_mp4_to_mp3(file_path, mp3_file_path)
        
        file_path = mp3_file_path
    elif file_path.lower().endswith('.mp3'):
        logging.info(f"Processing MP3 file: {file_path}")
    else:
        logging.warning(f"Unsupported file type: {file_path}")
        return None

    if not os.path.exists(file_path):
        logging.warning(f"Audio file not found: {file_path}")
        return None

    if not check_audio_properties(file_path):
        logging.info("Audio does not meet requirements. Re-encoding...")
        reencoded_file = file_path.rsplit('.', 1)[0] + '_reencoded.mp3'
        if reencode_audio(file_path, reencoded_file):
            return reencoded_file
        else:
            logging.warning("Re-encoding failed. Proceeding with original file.")

    return file_path

def process_meeting_minutes(file_path):
    processed_file = process_audio_file(file_path)
    if not processed_file:
        return

    audio_hash = hash_audio_file(processed_file)
    processed_meetings = load_processed_meetings()

    if audio_hash in processed_meetings:
        logging.info(f"This meeting has already been processed on {processed_meetings[audio_hash]['process_date']}")
        logging.info(f"Output file: {processed_meetings[audio_hash]['output_file']}")
        return

    transcript_file = f"{audio_hash}_transcription.txt"

    if os.path.exists(transcript_file):
        logging.info("Transcription already exists. Loading from file...")
        with open(transcript_file, 'r', encoding='utf-8') as file:
            transcription = file.read()
    else:
        transcription = transcribe_audio(processed_file)
        if transcription:
            logging.info("Transcription complete.")
            with open(transcript_file, 'w', encoding='utf-8') as file:
                file.write(transcription)
        else:
            logging.error("Transcription failed, no text to process.")
            return

    cleaned_transcription = clean_transcript(transcription)
    
    # Generate summary for the entire transcript
    final_summary = generate_summary_with_anthropic(cleaned_transcription)
    
    output_filename = generate_output_filename(processed_file, cleaned_transcription)
    save_summary_to_markdown(final_summary, filename=output_filename)

    save_processed_meeting(audio_hash, {
        "process_date": datetime.now().isoformat(),
        "input_file": file_path,
        "processed_file": processed_file,
        "output_file": os.path.join("meetings", output_filename)
    })

    logging.info(f"Process completed for {file_path}. The meeting minutes have been saved in the meetings folder.")

def process_recordings_folder():
    if not os.path.exists(RECORDINGS_FOLDER):
        logging.error(f"The '{RECORDINGS_FOLDER}' folder does not exist. Please create it and add your recordings.")
        return

    audio_files = [f for f in os.listdir(RECORDINGS_FOLDER) if f.lower().endswith(('.mp3', '.mp4'))]

    if not audio_files:
        logging.warning(f"No MP3 or MP4 files found in the '{RECORDINGS_FOLDER}' folder.")
        return

    for file in audio_files:
        process_meeting_minutes(os.path.join(RECORDINGS_FOLDER, file))

def list_processed_meetings():
    processed_meetings = load_processed_meetings()
    if not processed_meetings:
        print("No meetings have been processed yet.")
    else:
        print("Processed Meetings:")
        for hash, metadata in processed_meetings.items():
            print(f"Hash: {hash}")
            print(f"  Processed on: {metadata['process_date']}")
            print(f"  Input file: {metadata['input_file']}")
            print(f"  Output file: {metadata['output_file']}")
            print()

def main():
    if not OPENAI_API_KEY:
        logging.error("OPENAI_API_KEY is not set in the environment variables")
        return
    if not ANTHROPIC_API_KEY:
        logging.error("ANTHROPIC_API_KEY is not set in the environment variables")
        return
    if len(sys.argv) == 1:
        logging.info(f"No file specified. Processing all files in the '{RECORDINGS_FOLDER}' folder.")
        process_recordings_folder()
    elif sys.argv[1] == '--list':
        list_processed_meetings()
    else:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            process_meeting_minutes(file_path)
        else:
            logging.error(f"File not found: {file_path}")

if __name__ == "__main__":
    main()
