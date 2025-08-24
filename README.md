# OmniBank Assistant 🏦💬

OmniBank Assistant is a cloud-native, agent-driven conversational banking solution that harnesses the multimodal capabilities of Google’s Gemini Live (or other ADK-compatible live models) for real-time financial interactions. Unlike traditional systems, it streams both text and raw audio (PCM) inputs from users directly to an advanced AI agent running in the cloud. The Gemini Live model natively processes multimodal inputs—understanding and transcribing speech, extracting banking intents, and executing tool calls in a single, end-to-end step.

This architecture enables:
- **Multimodal understanding:** The agent and Gemini Live process spoken language, typed queries, and even images (if enabled), returning structured JSON (intents, entities, tool calls) and optionally responding with synthesized speech.
- **Agent orchestration:** The backend agent coordinates the conversation, manages state, and dynamically invokes banking tools or APIs as requested by the model, ensuring domain-specific logic and secure, context-aware interactions.
- **Live, low-latency streaming:** Using FastAPI and WebSockets, the system provides bidirectional, real-time streaming between browser and model, supporting natural, interactive banking conversations.
- **Cloud-scale intelligence:** All AI understanding, transcription, and business logic happen in the cloud for maximum security, scalability, and flexibility—empowering instant banking operations through natural language and voice.

With OmniBank Assistant, users enjoy seamless, agent-powered banking via voice or text, powered by the latest in multimodal AI.

---

## Table of Contents
- [Key Technical Highlights](#key-technical-highlights)
- [Layman-Friendly Explanation](#layman-friendly-explanation)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Environment Variables](#environment-variables)
- [Running Locally](#running-locally)
- [Using Docker](#using-docker)
- [Endpoints](#endpoints)
- [User Journey](#user-journey)
- [WebSocket Message Formats](#websocket-message-formats)
- [Audio Recommendations](#audio-recommendations)
- [Gemini Live & Google ADK](#gemini-live--google-adk-notes)
- [Audio Processing Workflow](#audio-processing-workflow)
- [Security & Privacy](#security--privacy)
- [Contributing](#contributing)
- [License](#license)

---

## Key Technical Highlights

- **End-to-end audio understanding:** The assistant does not perform local speech-to-text (STT). Instead, raw PCM audio is streamed directly from the browser to the backend, which relays it to the AI model. The model natively processes the audio and handles both transcription and intent recognition in a single step.
- **Bidirectional streaming:** Utilizes Google ADK's Runner with `StreamingMode.BIDI`, enabling live, low-latency, two-way communication between client and model for both audio and text.
- **Rich model responses:**
  - Natively understands and processes raw audio inputs.
  - Produces structured JSON outputs containing intents, entities, tool calls, and more.
  - Can optionally synthesize audio (as base64-encoded PCM) for real-time voice responses.
- **Seamless frontend integration:** Audio is captured in the browser via the Web Audio API and streamed as PCM chunks over WebSocket to the backend. The backend orchestrates real-time communication with the model and streams structured responses (text and/or audio) back to the client for immediate playback and UI display.

---

## Layman-Friendly Explanation

OmniBank Assistant is like having a personal banker you can chat with or talk to. You can type or speak your requests, and the assistant listens, understands, and responds—sometimes even with a voice reply! It's fast, secure, and designed for easy banking on the go.

---

## Project Structure

```text
OmniBank_Assistant/
├── main.py                  # FastAPI entry point
├── requirements.txt         # Python dependencies
├── Dockerfile               # Containerization instructions
├── deploy.sh                # Deployment helper for Cloud Run
├── .env                     # Environment variables (not committed)
├── banking_agent/           # Core AI logic
│   ├── agent.py
│   ├── context.py
│   └── tools.py
├── frontend/
│   └── static/
│       ├── index.html
│       ├── js/
│       │   ├── app.js
│       │   ├── audio-recorder.js
│       │   └── pcm-player.js
│       └── styles/
│           └── style.css
├── README.md
└── LICENSE
```

---

## Tech Stack

**Backend**
- Python 3.9+
- FastAPI, WebSockets
- google.adk (Runner, LiveRequestQueue)
- Uvicorn (recommended for development)
- InMemorySessionService for session management

**Frontend**
- HTML5, CSS3, Vanilla JS (ES6+)
- Web Audio API + AudioWorklet
- Streams PCM as base64-encoded JSON over WebSocket

**DevOps**
- Docker & deploy.sh
- `.env` for secrets (not committed)
- TLS recommended for production

---

## Environment Variables

Create a `.env` file with the following keys:

```env
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_PROJECT_ID=your-gcp-project
LOCATION=us-central1
STAGING_BUCKET=gs://your-staging-bucket
GCP_BUCKET_NAME=your-gcp-bucket
```

> **Note:** Never commit `.env` or API keys to source control.

---

## Running Locally

**1. Create & activate virtual environment:**
```sh
python -m venv venv
venv\Scripts\activate  # On Windows
# Or on Unix/Mac: source venv/bin/activate
```

**2. Install dependencies:**
```sh
pip install -r requirements.txt
```

**3. Add your Google credentials to `.env`.**

**4. Start the server:**
```sh
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**5. Open the UI in your browser:**  
[http://localhost:8000/](http://localhost:8000/)

---

## Using Docker

**Build the image:**
```sh
docker build -t omnibank-assistant .
```

**Run the container:**
```sh
docker run -p 8000:8000 --env-file .env omnibank-assistant
```

---

## Endpoints

**1. `GET /`**  
Serves the static UI (`frontend/static/index.html`)

**2. Static files**  
Mounted at `/static` → `frontend/static/*`

**3. WebSocket (audio & text):**  
`/ws/{session_id}`  
Supports query params: `lang`, `is_audio`, `dev_mode`

Example:  
`ws://localhost:8000/ws/session123?lang=en-US&is_audio=true&dev_mode=false`

Backend manages session, streaming, and relays events between client and model.

---

## User Journey

1. **User opens UI:** Sees chat and mic button.
2. **User types or speaks:** Chat or voice input is captured.
3. **Browser captures audio:** AudioWorklet records raw PCM and encodes as base64.
4. **Client streams data:** Text/audio is sent over WebSocket as JSON.
5. **Backend relays audio to model:** No local STT; model understands audio directly.
6. **Model returns response:** Structured JSON and/or synthesized audio.
7. **Frontend displays results:** Shows text, plays audio, and handles tool results.
8. **Multi-turn:** Conversation state tracked for follow-ups, confirmations, etc.

---

## WebSocket Message Formats

**Client → Server:**
```json
{ "mime_type": "text/plain", "data": "What's my balance?" }
{ "mime_type": "audio/pcm", "data": "<base64-pcm-chunk>" }
{ "mime_type": "image/jpeg", "data": "<base64-jpeg-bytes>" }
```

**Server → Client:**
```json
{ "mime_type": "text/plain", "data": "Your balance is $1,234.56" }
{ "mime_type": "text/transcription", "data": "Your balance is ..." }
{ "mime_type": "audio/pcm", "data": "<base64-pcm-bytes>" }
{ "turn_complete": true, "interrupted": false }
{ "mime_type": "tool_call", "data": { "name": "...", "args": {...} } }
{ "mime_type": "tool_result", "data": { "name": "...", "response": {...} } }
```

---

## Audio Recommendations

- **Format:** 16-bit PCM (raw), mono
- **Sample rate:** 16kHz–48kHz (consistent across frontend/backend)
- **Chunking:** Frontend sends small PCM chunks
- **Playback:** Frontend decodes and plays base64 PCM

---

## Gemini Live & Google ADK Notes

- Uses Google ADK Runner and LiveRequestQueue for live sessions (see `main.py`)
- RunConfig: `StreamingMode.BIDI`, `response_modalities=["AUDIO"]`
- **References:**
  - [Gemini Live](https://ai.google.dev/gemini-api/docs/live)
  - [Google ADK](https://google.github.io/adk-docs/)

---

## Audio Processing Workflow

1. Browser captures audio via getUserMedia.
2. AudioWorklet/PCM recorder creates PCM chunks.
3. Frontend sends audio chunks to backend (WebSocket).
4. Backend decodes and forwards to AI model endpoint.
5. Model returns structured JSON and/or synthesized audio.
6. Frontend plays audio and displays results.

---

## Security & Privacy

- **Never commit `.env` or keys.**
- Treat audio and transcripts as sensitive; use TLS in production.
- Minimize logging of PII.
- Add authentication, RBAC, and secure storage before production use.
- Restrict model/API access via IAM or API key rules.

---

## Contributing

- Fork the repo, create a feature branch, and open a Pull Request.
- Run linters and tests before submitting.
- Keep changes modular:
  - Domain logic in `banking_agent/tools.py`
  - Audio/capture logic in `frontend/static/js/`
  - Update README and `.env.example` for new keys
- Open issues for feature requests or improvements.
- For sensitive areas (auth, banking connectors), include an architecture/security review.

---

## License

MIT — see [LICENSE](LICENSE).
