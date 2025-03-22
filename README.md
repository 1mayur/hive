# Order-Taking Chatbot with Pipecat

A voice-enabled order-taking chatbot that uses Pipecat-AI to process audio over WebSocket connections.

## Setup

```bash
# Create a virtual environment
python3 -m venv env
source env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from template
cp .env.example .env
# Edit the .env file and add your OpenAI API key
```

## Configuration

Configure your environment variables in the `.env` file:

```
OPENAI_API_KEY=your_openai_api_key_here
```

## Running the Bot

```bash
# Start the bot with default settings (0.0.0.0:8765)
python src/main.py

# Or specify custom host and port
python src/main.py --url localhost --port 9000
```

## Using the Example Client

An example client is provided to test the bot:

```bash
# Install PyAudio (if not already installed)
pip install pyaudio

# Record a test audio file (using any recording tool)
# Then run the example client:
python src/examples/example_client.py --audio-file path/to/your/audio.wav

# Optionally specify a different WebSocket URL:
python src/examples/example_client.py --url ws://localhost:9000 --audio-file path/to/your/audio.wav
```

The example client will:
1. Connect to the WebSocket server
2. Send the audio file
3. Receive the bot's response
4. Save the response to a file called `response.wav`
5. Play the response audio

## How it Works

The bot creates a WebSocket server that:

1. Accepts WebSocket connections from clients
2. Processes incoming audio data
3. Transcribes speech using OpenAI Whisper
4. Processes the text with GPT-4 to handle order-taking conversations
5. Converts responses to speech using OpenAI TTS
6. Sends the audio response back to the client

## WebSocket Client Implementation

To connect to this bot, clients need to:

1. Establish a WebSocket connection to the provided URL and port
2. Send audio data in the expected format (raw PCM audio)
3. Listen for audio responses from the bot

## Architecture

The bot uses a Pipecat pipeline with the following components:

- **Transport**: WebSocketServerTransport for audio I/O
- **STT**: OpenAISTTService for speech recognition
- **LLM**: OpenAILLMService for conversation handling
- **TTS**: OpenAITTSService for speech synthesis
- **Context**: ContextAggregator for maintaining conversation history
- **RTVI**: Real-Time Voice Interface components for managing transcriptions and speaking states

## Requirements

- Python 3.10+
- OpenAI API key

## Code Formatting and Linting

This project uses pre-commit hooks for automatic code formatting and linting. The configuration includes:

- **Ruff**: Fast Python linter and formatter
- **Black**: Code formatter
- Basic file checks (trailing whitespace, YAML validation, etc.)

### Setup Pre-commit Hooks

Run the setup script to install pre-commit hooks:

```bash
# Activate your virtual environment first
source env/bin/activate

# Run the setup script
python setup_precommit.py
```

### Format Existing Files

To format all existing files in the repository:

```bash
pre-commit run --all-files
```

The pre-commit hooks will also run automatically on every git commit.
