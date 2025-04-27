# VoiceAI: Conversational Voice Assistant

This repository contains a full-stack voice assistant application that supports voice and text interactions, powered by AI for natural language processing, speech-to-text, text-to-speech, and image generation. The backend is built with Python and Flask, while the frontend is developed using React and TypeScript.

## Project Overview

VoiceAI is designed to:
- **Process Voice Input**: Record audio, transcribe it to text using Whisper, and generate AI responses.
- **Handle Text Input**: Accept text input for conversation with the AI.
- **Generate Speech**: Convert AI responses to speech using ElevenLabs TTS.
- **Create Images**: Generate context-aware images based on conversation using HuggingFace's image generation model.
- **Store Conversations**: Save conversation history in a MySQL database, including text and audio files.
- **Provide a Web Interface**: Offer a user-friendly UI for interacting with the assistant, displaying conversation history, and playing audio.

## Repository Structure

- **Backend (`voiceAI.py`)**: Flask API handling audio/text processing, LLM queries, TTS, image generation, and database operations.
- **Frontend (`App.tsx`, `App.css`)**: React/TypeScript application with a responsive UI for voice/text input and conversation display.
- **Data Storage**:
  - `userVoice/`: Stores user audio files.
  - `aiVoice/`: Stores AI-generated audio files.
  - MySQL database (`testing`): Stores conversation metadata.
- **Dependencies**:
  - Python: Whisper, Flask, MySQL Connector, ElevenLabs, HuggingFace Hub, Mem0, AutoGen.
  - JavaScript: React, TypeScript, UUID, React Icons.

## Prerequisites

### Backend
- Python 3.8+
- MySQL server running locally with a database named `testing`
- API keys for:
  - ElevenLabs (`ELEVENLABS_API_KEY`)
  - DeepSeek (`DEEPSEEK_API_KEY`)
  - HuggingFace (`huggingface_api_key`)
- Install Python dependencies:
  ```bash
  pip install whisper pyaudio flask flask-cors mysql-connector-python openai elevenlabs mem0 huggingface_hub pillow autogen python-dotenv
  ```

### Frontend
- Node.js 16+
- Install dependencies:
  ```bash
  npm install
  ```

### Database
Create a MySQL database named `testing` and a table for conversations:
```sql
CREATE TABLE conversations (
    id INT PRIMARY KEY,
    user TEXT,
    ai TEXT,
    user_audio_filename VARCHAR(255),
    ai_audio_filename VARCHAR(255),
    timestamp DATETIME
);
```

## Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/voiceAI.git
   cd voiceAI
   ```

2. **Configure Environment**:
   Create a `.env` file in the root directory with the following:
   ```
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   DEEPSEEK_API_KEY=your_deepseek_api_key
   HUGGINGFACE_API_KEY=your_huggingface_api_key
   ```

3. **Start the Backend**:
   ```bash
   python voiceAI.py
   ```
   The Flask server will run on `http://localhost:5000`.

4. **Start the Frontend**:
   ```bash
   npm start
   ```
   The React app will run on `http://localhost:3000`.

5. **Interact with the Assistant**:
   - Open the web interface in a browser.
   - Use the microphone button to record voice input or type in the text box.
   - View conversation history, play audio responses, and see generated images.

## Usage

### Features
- **Voice Interaction**: Click the microphone button to record audio, which is transcribed and processed by the AI.
- **Text Interaction**: Type a message and click "Send" to get an AI response.
- **Audio Playback**: Play user and AI audio directly in the UI.
- **Image Generation**: Automatically generates images based on the latest AI response.
- **Clear Conversations**: Delete all conversation data and reset the UI with the "Clear" button.
- **Conversation History**: View past interactions, including text and audio, fetched on page load.

### API Endpoints
- `POST /process-input`: Process voice or text input and return AI response with audio.
- `GET /get-user-audio/<filename>`: Retrieve user audio file.
- `GET /get-ai-audio/<filename>`: Retrieve AI audio file.
- `GET /generate-image`: Generate an image based on the latest conversation.
- `DELETE /delete-all-conversations`: Clear all conversation data.
- `GET /get-history`: Fetch conversation history.

### Example
To send a text message:
```bash
curl -X POST http://localhost:5000/process-input -H "Content-Type: application/json" -d '{"text": "Hello, how are you?"}'
```

To record audio, use the microphone button in the UI, which sends the audio to `/process-input`.

## Notes
- The backend uses a lightweight Whisper model (`tiny`) for faster transcription.
- Audio files are stored in `userVoice/` and `aiVoice/` directories; ensure write permissions.
- The frontend assumes the backend is running on `http://localhost:5000`.
- Image generation uses HuggingFace's FLUX.1-dev model via fal-ai provider.
- The AI assistant is configured with a persona ("May, Tom's girlfriend") using Mem0 for memory and AutoGen for conversation management.

## Contributing
Contributions are welcome! To contribute:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

## Acknowledgments
- Built with [Flask](https://flask.palletsprojects.com/), [React](https://reactjs.org/), and [TypeScript](https://www.typescriptlang.org/).
- Powered by [Whisper](https://github.com/openai/whisper), [ElevenLabs](https://elevenlabs.io/), [DeepSeek](https://www.deepseek.com/), and [HuggingFace](https://huggingface.co/).
- Memory management with [Mem0](https://github.com/mem0ai/mem0).
- Conversational AI with [AutoGen](https://github.com/microsoft/autogen).