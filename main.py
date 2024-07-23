import sys
import os
import hashlib
from openai import OpenAI
from moviepy.editor import VideoFileClip
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def check_audio_file_presence(audio_file_path):
    return os.path.exists(audio_file_path)

def hash_audio_file(audio_file_path):
    hasher = hashlib.sha256()
    with open(audio_file_path, 'rb') as af:
        buf = af.read()
        hasher.update(buf)
    return hasher.hexdigest()

def generate_output_filename(input_file_path):
    base_name = os.path.basename(input_file_path)
    name_without_extension = os.path.splitext(base_name)[0]
    return f"{name_without_extension}_Meeting_Minutes.md"

def transcribe_audio(audio_file_path):
    print(" 🎙️  Transcribing audio...")
    try:
        with open(audio_file_path, 'rb') as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        print("Transcription complete.")
        return transcription.text  # The text is now a direct attribute
    except Exception as e:
        print(f"Error during transcription: {e}")
        return None

def save_summary_to_markdown(summary, filename="Meeting_Minutes.md"):
    print(" 💾  Saving summary to Markdown file...")
    try:
        with open(filename, 'w', encoding='utf-8') as md_file:
            md_file.write(summary)
        print(f"Markdown file saved as {filename}.")
    except Exception as e:
        print(f"Error saving summary to Markdown file: {e}")

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
            max_tokens=1024,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error during summary generation with OpenAI: {e}")
        return "Summary generation failed."

def clean_transcript(transcript):
    lines = transcript.split('\n')
    cleaned_lines = [line.strip() for line in lines if line.strip()]
    return ' '.join(cleaned_lines)

def split_transcript(transcript, max_tokens=2048):
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

def save_summary_to_markdown(summary, filename):
    print(f" 💾  Saving summary to Markdown file: {filename}...")
    try:
        with open(filename, 'w', encoding='utf-8') as md_file:
            md_file.write(summary)
        print(f"Markdown file saved as {filename}.")
    except Exception as e:
        print(f"Error saving summary to Markdown file: {e}")

def process_meeting_minutes(file_path):
    if file_path.lower().endswith('.mp4'):
        print("MP4 file detected. Extracting audio...")
        mp3_file_path = file_path.rsplit('.', 1)[0] + '.mp3'
        convert_mp4_to_mp3(file_path, mp3_file_path)
        file_path = mp3_file_path

    if not check_audio_file_presence(file_path):
        print("  ⚠️  Please save the audio file in the root folder before running.")
        return

    audio_hash = hash_audio_file(file_path)
    transcript_file = f"{audio_hash}_transcription.txt"

    if os.path.exists(transcript_file):
        print("Transcription already exists. Loading from file...")
        with open(transcript_file, 'r', encoding='utf-8') as file:
            transcription = file.read()
    else:
        transcription = transcribe_audio(file_path)
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
    output_filename = generate_output_filename(file_path)
    save_summary_to_markdown(final_summary, filename=output_filename)
    print(" 📋  Process completed. The meeting minutes have been saved in a Markdown file.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_audio_or_video_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    process_meeting_minutes(file_path)

if __name__ == "__main__":
    main()
