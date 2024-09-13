# 🎙️ Meeting Minutes Generator

This Python application automates the process of generating meeting minutes from audio recordings. It uses OpenAI's Whisper for transcription and Anthropic's Claude for summarization, outputting the result as a Markdown file.

## 🌟 Key Features

- **Multi-format Support**: Processes both MP3 and MP4 files.
- **Audio Preprocessing**: Converts MP4 to MP3 and re-encodes audio if necessary.
- **Efficient Transcription**: Uses OpenAI's Whisper model for accurate audio transcription.
- **Intelligent Summarization**: Leverages Anthropic's Claude model for generating comprehensive summaries.
- **Customizable Prompts**: Allows users to customize the summarization prompt.
- **Markdown Output**: Saves summaries in easily readable Markdown format.
- **Processing Log**: Maintains a record of processed meetings to avoid duplication.

## 🛠️ Prerequisites

- Python 3.8 or higher
- FFmpeg (for audio processing)
- OpenAI API key
- Anthropic API key

## 🚀 Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/your-username/meeting-minutes-generator.git
   cd meeting-minutes-generator
   ```

2. **Set Up Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**
   Create a `.env` file in the project root and add your API keys:
   ```bash
   OPENAI_API_KEY=your_openai_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

## 📋 Usage

1. **Prepare Audio Files**
   Place your MP3 or MP4 files in the `recordings` folder.

2. **Run the Script**
   - To process all files in the `recordings` folder:
     ```bash
     python main.py
     ```
   - To process a specific file:
     ```bash
     python main.py path/to/your/audio_file.mp3
     ```
   - To list all processed meetings:
     ```bash
     python main.py --list
     ```

3. **Customize Summarization (Optional)**
   Edit the `prompt.txt` file to customize the summarization prompt. If empty, you'll be prompted to enter a custom prompt during runtime.

## 📁 Project Structure

- `main.py`: The main script that orchestrates the entire process.
- `recordings/`: Folder to place input audio files.
- `meetings/`: Output folder for generated Markdown summaries.
- `prompt.txt`: File for custom summarization prompts.
- `processed_meetings.json`: Log of processed meetings.

## 🔧 Customization

- Adjust `MAX_TOKENS`, `AUDIO_BITRATE`, and other constants in `main.py` as needed.
- Modify the summarization logic in `generate_summary_with_anthropic()` for different output styles.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
