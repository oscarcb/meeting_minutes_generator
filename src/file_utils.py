import os
import json
import hashlib
from datetime import datetime
import re
from src.config import get_anthropic_client, LOG_FILE, MAX_TITLE_LENGTH
import logging

class FileUtils:
    @staticmethod
    def load_processed_meetings(log_file):
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                return json.load(f)
        return {}

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

    @staticmethod
    def save_processed_meeting(log_file, file_hash, metadata):
        processed_meetings = FileUtils.load_processed_meetings(log_file)
        processed_meetings[file_hash] = metadata
        with open(log_file, 'w') as f:
            json.dump(processed_meetings, f, indent=2)

    @staticmethod
    def hash_audio_file(audio_file_path):
        hasher = hashlib.sha256()
        with open(audio_file_path, 'rb') as af:
            for chunk in iter(lambda: af.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def generate_output_filename(input_file_path, transcript):
        base_name = os.path.basename(input_file_path)
        time_str = FileUtils.extract_time_from_filename(base_name) or "Unknown_Time"
        title = FileUtils.extract_title_from_transcript(transcript)
        return f"{time_str}_{title}.md"
    @staticmethod
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