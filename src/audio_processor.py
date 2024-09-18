import subprocess
import os
import json
import logging
from moviepy.editor import VideoFileClip
from .config import AUDIO_BITRATE, AUDIO_CHANNELS

class AudioProcessor:

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def reencode_audio(input_file, output_file):
        try:
            subprocess.run([
                'ffmpeg',
                '-i', input_file,
                '-ac', str(AUDIO_CHANNELS),
                '-b:a', f'{AUDIO_BITRATE // 1000}k',
                '-y',
                output_file
            ], check=True)
            logging.info(f"Audio re-encoded successfully: {output_file}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Error re-encoding audio: {e}")
            return False

    @staticmethod
    def process_audio_file(file_path):
        if file_path.lower().endswith('.mp4'):
            logging.info(f"Processing MP4 file: {file_path}")
            mp3_file_path = file_path.rsplit('.', 1)[0] + '.mp3'

            if os.path.exists(mp3_file_path):
                logging.info(f"Corresponding MP3 file already exists: {mp3_file_path}")
            else:
                logging.info(f"Converting MP4 to MP3: {file_path}")
                AudioProcessor.convert_mp4_to_mp3(file_path, mp3_file_path)

            file_path = mp3_file_path
        elif file_path.lower().endswith('.mp3'):
            logging.info(f"Processing MP3 file: {file_path}")
        else:
            logging.warning(f"Unsupported file type: {file_path}")
            return None

        if not os.path.exists(file_path):
            logging.warning(f"Audio file not found: {file_path}")
            return None

        if not AudioProcessor.check_audio_properties(file_path):
            logging.info("Audio does not meet requirements. Re-encoding...")
            reencoded_file = file_path.rsplit('.', 1)[0] + '_reencoded.mp3'
            if AudioProcessor.reencode_audio(file_path, reencoded_file):
                return reencoded_file
            else:
                logging.warning("Re-encoding failed. Proceeding with original file.")

        return file_path