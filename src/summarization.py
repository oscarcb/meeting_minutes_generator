import logging
from pip._vendor.rich.prompt import Confirm, Prompt

from .config import get_anthropic_client, MAX_TOKENS, MAX_TITLE_LENGTH


class Summarizer:
    @staticmethod
    def generate_summary(transcription, custom_prompt):
        client = get_anthropic_client()
        logging.info("Generating summary using Anthropic...")
        try:
            with open('prompt.txt', 'r', encoding='utf-8') as file:
                custom_prompt = file.read().strip()

            if not custom_prompt:
                use_custom_prompt = Confirm.ask("The prompt file is empty. Would you like to provide a custom prompt?")
                if use_custom_prompt:
                    custom_prompt = Prompt.ask("Please enter your custom prompt")
                else:
                    custom_prompt = "Summarize the following meeting transcript:"

            message = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=MAX_TOKENS,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": f"{custom_prompt}\n\nTranscript: {transcription}"}
                ]
            )
            return message.content[0].text.strip()
        except Exception as e:
            logging.error(f"Error during summary generation with Anthropic: {e}")
            return f"Summary generation failed. {e}"

    @staticmethod
    def extract_title(transcript):
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