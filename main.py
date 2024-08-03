import sys
import os
import hashlib
import re
import json
import subprocess
from datetime import datetime
from openai import OpenAI
from moviepy.editor import VideoFileClip
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Path for the log file
LOG_FILE = "processed_meetings.json"
RECORDINGS_FOLDER = "recordings"

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

def check_audio_file_presence(audio_file_path):
    return os.path.exists(audio_file_path)

def hash_audio_file(audio_file_path):
    hasher = hashlib.sha256()
    with open(audio_file_path, 'rb') as af:
        buf = af.read()
        hasher.update(buf)
    return hasher.hexdigest()

def extract_time_from_filename(filename):
    # Assuming the filename format is something like "YYYYMMDD_HHMMSS_..."
    match = re.search(r'(\d{8}_\d{6})', filename)
    if match:
        time_str = match.group(1)
        return datetime.strptime(time_str, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d_%H-%M-%S")
    return None

def extract_title_from_transcript(transcript, max_length=50):
    # Use OpenAI to generate a title from the transcript
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {'role': 'system', 'content': 'Extract a concise title from the following meeting transcript. The title should be no more than 50 characters long.'},
                {'role': 'user', 'content': transcript[:1000]}  # Use first 1000 characters for title extraction
            ],
            max_tokens=60,
            temperature=0.7
        )
        title = response.choices[0].message.content.strip()
        return title[:max_length].replace(" ", "_")
    except Exception as e:
        print(f"Error extracting title: {e}")
        return "Untitled_Meeting"

def generate_output_filename(input_file_path, transcript):
    base_name = os.path.basename(input_file_path)
    time_str = extract_time_from_filename(base_name) or "Unknown_Time"
    title = extract_title_from_transcript(transcript)
    return f"{time_str}_{title}.md"

def save_summary_to_markdown(summary, filename):
    os.makedirs("meetings", exist_ok=True)
    file_path = os.path.join("meetings", filename)
    print(f" 💾  Saving summary to Markdown file: {file_path}...")
    try:
        with open(file_path, 'w', encoding='utf-8') as md_file:
            md_file.write(summary)
        print(f"Markdown file saved as {file_path}.")
    except Exception as e:
        print(f"Error saving summary to Markdown file: {e}")

def transcribe_audio(audio_file_path):
    print(" 🎙️  Transcribing audio...")
    try:
        with open(audio_file_path, 'rb') as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        print("Transcription complete.")
        return transcription.text
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None

def clean_transcript(transcript):
    lines = transcript.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    return ' '.join(cleaned_lines)

def split_transcript(transcript, max_tokens=4036):
    words = transcript.split()
    chunks = []
    current_chunk = []

    for word in words:
        if len(current_chunk) + len(word) + 1 > max_tokens:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
        current_chunk.append(word)

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks

def generate_summary_with_openai(transcription_chunk):
    print(" 🤖  Generating summary using OpenAI...")
    try:
        with open('prompt.txt', 'r', encoding='utf-8') as file:
            custom_prompt = file.read()

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {'role': 'system', 'content': custom_prompt},
                {'role': 'user', 'content': transcription_chunk}
            ],
            max_tokens=4036,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error during summary generation with OpenAI: {e}")
        return "Summary generation failed."

def convert_mp4_to_mp3(mp4_file_path, mp3_file_path):
    try:
        video_clip = VideoFileClip(mp4_file_path)
        audio_clip = video_clip.audio
        audio_clip.write_audiofile(mp3_file_path)
        audio_clip.close()
        video_clip.close()
        print(f"Audio extracted and saved as {mp3_file_path}")
    except Exception as e:
        print(f"Error converting MP4 to MP3: {e}")


def check_audio_properties(audio_file_path):
    try:
        # Use ffprobe to get audio file information
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

        # Get bit rate and number of channels
        bit_rate = int(stream_info.get('bit_rate', '0'))
        channels = int(stream_info.get('channels', '0'))

        # Check if audio meets requirements (96 kbps and mono)
        return bit_rate == 48000 and channels == 1
    except Exception as e:
        print(f"Error checking audio properties: {e}")
        return False


def reencode_audio(input_file, output_file):
    try:
        # Use ffmpeg to re-encode audio to 96 kbps mono
        subprocess.run([
            'ffmpeg',
            '-i', input_file,
            '-ac', '1',  # Set to mono
            '-b:a', '48k',  # Set bitrate to 96 kbps
            '-y',  # Overwrite output file if it exists
            output_file
        ], check=True)
        print(f"Audio re-encoded successfully: {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error re-encoding audio: {e}")
        return False


def process_audio_file(file_path):
    if file_path.lower().endswith('.mp4'):
        print(f"Processing MP4 file: {file_path}")
        print("Extracting audio...")
        mp3_file_path = file_path.rsplit('.', 1)[0] + '.mp3'
        convert_mp4_to_mp3(file_path, mp3_file_path)
        file_path = mp3_file_path
    elif file_path.lower().endswith('.mp3'):
        print(f"Processing MP3 file: {file_path}")
    else:
        print(f"Unsupported file type: {file_path}")
        return None

    if not check_audio_file_presence(file_path):
        print(f"  ⚠️  Audio file not found: {file_path}")
        return None

    if not check_audio_properties(file_path):
        print("Audio does not meet requirements. Re-encoding...")
        reencoded_file = file_path.rsplit('.', 1)[0] + '_reencoded.mp3'
        if reencode_audio(file_path, reencoded_file):
            return reencoded_file
        else:
            print("Re-encoding failed. Proceeding with original file.")

    return file_path

def process_meeting_minutes(file_path):
    processed_file = process_audio_file(file_path)
    if not processed_file:
        return

    audio_hash = hash_audio_file(processed_file)
    processed_meetings = load_processed_meetings()

    if audio_hash in processed_meetings:
        print(f"This meeting has already been processed on {processed_meetings[audio_hash]['process_date']}")
        print(f"Output file: {processed_meetings[audio_hash]['output_file']}")
        return

    transcript_file = f"{audio_hash}_transcription.txt"

    if os.path.exists(transcript_file):
        print("Transcription already exists. Loading from file...")
        with open(transcript_file, 'r', encoding='utf-8') as file:
            transcription = file.read()
    else:
        transcription = transcribe_audio(processed_file)
        if transcription:
            print("Transcription complete.")
            with open(transcript_file, 'w', encoding='utf-8') as file:
                file.write(transcription)
        else:
            print(" ❌  Transcription failed, no text to process.")
            return

    cleaned_transcription = clean_transcript(transcription)
    transcript_chunks = split_transcript(cleaned_transcription)

    all_summaries = []
    for chunk in transcript_chunks:
        summary = generate_summary_with_openai(chunk)
        all_summaries.append(summary)

    final_summary = "\n\n".join(all_summaries)
    output_filename = generate_output_filename(processed_file, cleaned_transcription)
    save_summary_to_markdown(final_summary, filename=output_filename)

    # Log the processed meeting
    save_processed_meeting(audio_hash, {
        "process_date": datetime.now().isoformat(),
        "input_file": file_path,
        "processed_file": processed_file,
        "output_file": os.path.join("meetings", output_filename)
    })

    print(f" 📋  Process completed for {file_path}. The meeting minutes have been saved in the meetings folder.")

def process_recordings_folder():
    if not os.path.exists(RECORDINGS_FOLDER):
        print(f"The '{RECORDINGS_FOLDER}' folder does not exist. Please create it and add your recordings.")
        return

    files = os.listdir(RECORDINGS_FOLDER)
    audio_files = [f for f in files if f.lower().endswith(('.mp3', '.mp4'))]

    if not audio_files:
        print(f"No MP3 or MP4 files found in the '{RECORDINGS_FOLDER}' folder.")
        return

    for file in audio_files:
        file_path = os.path.join(RECORDINGS_FOLDER, file)
        process_meeting_minutes(file_path)

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
    if len(sys.argv) == 1:
        print(f"No file specified. Processing all files in the '{RECORDINGS_FOLDER}' folder.")
        process_recordings_folder()
    elif sys.argv[1] == '--list':
        list_processed_meetings()
    else:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            process_meeting_minutes(file_path)
        else:
            print(f"File not found: {file_path}")

if __name__ == "__main__":
    main()