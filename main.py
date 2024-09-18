import sys
import logging
import os
from datetime import datetime
from src.audio_processor import AudioProcessor
from src.transcription import Transcriber
from src.summarization import Summarizer
from src.file_utils import FileUtils
from src.config import RECORDINGS_FOLDER, LOG_FILE, OPENAI_API_KEY, ANTHROPIC_API_KEY

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_meeting_minutes(file_path):
    processed_file = AudioProcessor.process_audio_file(file_path)
    if not processed_file:
        return

    audio_hash = FileUtils.hash_audio_file(processed_file)
    processed_meetings = FileUtils.load_processed_meetings(LOG_FILE)

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
        transcription = Transcriber.transcribe_audio(processed_file)
        if transcription:
            logging.info("Transcription complete.")
            with open(transcript_file, 'w', encoding='utf-8') as file:
                file.write(transcription)
        else:
            logging.error("Transcription failed, no text to process.")
            return

    cleaned_transcription = Transcriber.clean_transcript(transcription)

    # Generate summary for the entire transcript
    final_summary = Summarizer.generate_summary(cleaned_transcription, custom_prompt="")

    output_filename = FileUtils.generate_output_filename(processed_file, cleaned_transcription)
    FileUtils.save_summary_to_markdown(final_summary, filename=output_filename)

    FileUtils.save_processed_meeting(LOG_FILE, audio_hash, {
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
    processed_meetings = FileUtils.load_processed_meetings(LOG_FILE)
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
    if not OPENAI_API_KEY or not ANTHROPIC_API_KEY:
        logging.error("API keys are not set in the environment variables")
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
