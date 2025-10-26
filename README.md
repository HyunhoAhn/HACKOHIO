# 🦅 Hawk - AI-Powered English Learning Platform

**HACKOHIO Team #16 - Hawk**

Hawk is an AI-powered English conversation practice application that provides real-time pronunciation feedback and interactive conversation sessions. The system leverages OpenAI Whisper for speech-to-text, Azure Cognitive Services for pronunciation assessment, and Google Gemini for generating intelligent feedback and responses.

## Architecture

### Tech Stack
- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL
- **AI Services**:
  - OpenAI Whisper (Speech-to-Text)
  - Azure Cognitive Services (Pronunciation Assessment & Text-to-Speech)
  - Google Gemini (Feedback Generation & Conversation)
- **Frontend**: HTML/JavaScript (Static)

### Key Features
- 🎤 Real-time speech-to-text transcription using Whisper
- 📊 Detailed pronunciation assessment (accuracy, fluency, completeness, prosody)
- 🤖 AI-generated feedback on pronunciation, vocabulary, and grammar
- 🗣️ Interactive conversation sessions with AI responses
- 🔊 Natural text-to-speech using Azure Speech Services
- � Turn-by-turn conversation tracking and session summaries

## 📋 Prerequisites

- Python 3.11 or higher
- PostgreSQL 12+ 
- Conda (recommended) or virtualenv
- API Keys:
  - Azure Cognitive Services (Speech)
  - Google Gemini API

## � Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd HACKOHIO
```

### 2. Environment Setup (Conda Recommended)

#### Option A: Using Conda (Recommended)

```bash
# Create conda environment
conda create -n hawk python=3.11 -y

# Activate environment
conda activate hawk

# Install dependencies
pip install -r requirements.txt
```

#### Option B: Using venv

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate environment
source venv/bin/activate  # On macOS/Linux
# or
.\venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Database Setup

#### Create PostgreSQL Database

```bash
# Connect to PostgreSQL
psql postgres

# Create database
CREATE DATABASE hawk;

# Exit psql
\q
```

#### Initialize Schema

```bash
# Run schema file
psql -U <your_username> -d hawk -f TEMP/hawk_schema.sql

# Verify tables were created
psql -U <your_username> -d hawk -c "\dt"
```

The schema includes the following tables:
- `users` - User accounts
- `conversations` - Conversation sessions
- `turns` - Individual conversation turns
- `sentences` - Sentence-level data
- `sentence_scores` - Pronunciation scores per sentence
- `word_errors` - Detailed pronunciation errors
- `turn_feedbacks` - AI-generated feedback per turn
- `vocabulary_errors` - Vocabulary suggestions
- `grammar_errors` - Grammar corrections
- `conversation_summaries` - End-of-session summaries

### 4. Environment Variables

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database
DATABASE_URL=postgresql://<username>@localhost/hawk

# Azure Speech Services
AZURE_SPEECH_KEY=your_azure_speech_key_here
AZURE_REGION=koreacentral

# Google Gemini
GEMINI_API_KEY=your_gemini_api_key_here

# Whisper Configuration
WHISPER_MODEL_SIZE=large-v3

# Audio Settings
SAMPLE_RATE=16000
AUDIO_STORAGE_PATH=./audio_files
```

### 5. Verify Installation

```bash
# Test imports
python -c "import fastapi, whisper, azure.cognitiveservices.speech, google.genai; print('✅ All dependencies installed successfully!')"
```

## 🎮 Running the Application

### Start the Backend Server

```bash
# Make sure you're in the project root and environment is activated
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: `http://localhost:8000`
- **Interactive API Docs**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

### Access the Frontend

Open `frontend/index.html` in your browser or serve it using:

```bash
# Simple HTTP server
python -m http.server 8080 --directory frontend
```

Then navigate to `http://localhost:8080`

## 📡 API Endpoints

### Health Check
```
GET /health
GET /
```

### Conversation Flow

#### 1. Start Conversation
```bash
curl -X POST http://localhost:8000/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "00000000-0000-0000-0000-000000000001",
    "topic": "travel"
  }'
```

**Response:**
```json
{
  "conversation_id": "uuid",
  "welcome_message_text": "Hello! Let's practice English...",
  "welcome_message_audio_url": "/audio/...",
  "started_at": "2025-10-25T10:00:00"
}
```

#### 2. Process Turn (Submit audio and get feedback)
```bash
curl -X POST http://localhost:8000/api/v1/conversations/{conversation_id}/turns \
  -F "turn_number=1" \
  -F "audio_file=@samples/test_audio.wav"
```

**Response includes:**
- User's transcribed text
- Detailed pronunciation scores
- AI-generated feedback
- LLM response text and audio

#### 3. End Conversation
```bash
curl -X POST http://localhost:8000/api/v1/conversations/{conversation_id}/end
```

**Response:**
```json
{
  "conversation_id": "uuid",
  "total_turns": 5,
  "average_scores": {...},
  "total_errors": 10,
  "summary_text": "...",
  "ended_at": "2025-10-25T10:30:00"
}
```

## 🛠️ Development

### Project Structure

```
HACKOHIO/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py              # Configuration management
│   ├── database.py            # Database connection
│   ├── models.py              # Pydantic models
│   ├── controller/
│   │   └── conversation_controller.py  # API endpoints
│   └── service/
│       ├── whisper_service.py          # Speech-to-text
│       ├── azure_service.py            # Pronunciation assessment
│       ├── gemini_service.py           # AI feedback generation
│       ├── polly_service.py            # Text-to-speech
│       └── conversation_service.py     # Business logic
├── audio_files/               # Uploaded audio storage (auto-created)
├── frontend/                  # Static frontend files
│   └── index.html
├── samples/                   # Sample audio files
├── TEMP/
│   └── hawk_schema.sql       # Database schema
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
├── .gitignore              # Git ignore rules
└── README.md              # This file
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

## 🔧 Troubleshooting

### Whisper Model Loading Issues
If Whisper models fail to load:
```bash
# Clear cache
rm -rf ~/.cache/whisper/

# Download specific model manually
python -c "import whisper; whisper.load_model('large-v3')"
```

### Database Connection Issues
```bash
# Check PostgreSQL is running
pg_isready

# Check connection
psql -U <username> -d hawk -c "SELECT 1;"

# Check DATABASE_URL format
# Format: postgresql://username@host:port/database
# Example: postgresql://myuser@localhost:5432/hawk
```

### Audio File Issues
- Ensure audio files are in WAV format
- Sample rate should be 16000 Hz
- Use mono channel audio
- Check file permissions on `audio_files/` directory

### API Key Issues
- Verify all API keys in `.env` file
- **Azure Speech**: Visit Azure Portal → Speech Services → Keys and Endpoint
- **Gemini API**: Visit [Google AI Studio](https://ai.google.dev/)
- Ensure `.env` file is in the root directory

## 📝 Environment Variables Reference

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | - |
| `AZURE_SPEECH_KEY` | Yes | Azure Cognitive Services key | - |
| `AZURE_REGION` | Yes | Azure service region | `koreacentral` |
| `GEMINI_API_KEY` | Yes | Google Gemini API key | - |
| `WHISPER_MODEL_SIZE` | No | Whisper model size (`tiny`, `base`, `small`, `medium`, `large`, `large-v3`) | `large-v3` |
| `SAMPLE_RATE` | No | Audio sample rate (Hz) | `16000` |
| `AUDIO_STORAGE_PATH` | No | Audio file storage path | `./audio_files` |

## 🎯 Quick Start for Developers

```bash
# 1. Setup
conda create -n hawk python=3.11 -y
conda activate hawk
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your API keys

# 3. Database
psql postgres -c "CREATE DATABASE hawk;"
psql -U $USER -d hawk -f TEMP/hawk_schema.sql

# 4. Run
uvicorn app.main:app --reload

# 5. Test
curl http://localhost:8000/health
```

## 🤝 Contributing

1. Create a new branch for your feature
2. Make your changes
3. Test thoroughly
4. Submit a pull request

