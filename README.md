# OmniBank Assistant 🏦💬

OmniBank Assistant is an AI-first conversational banking assistant that accepts both text and raw audio (PCM) input. The repo forwards raw PCM audio through the stack to an audio-capable model (via Google ADK / Gemini Live) — there is no local speech-to-text step. The model performs audio understanding and (optionally) returns synthesized audio plus structured JSON.

---

## Quick summary

- No local STT: frontend streams raw PCM (base64 in JSON frames) to the backend WebSocket; backend sends binary to the ADK/GenAI runner unchanged.
- Low-latency voice interactions via bidirectional streaming (RunConfig.streaming_mode = BIDI).
- Uses Google ADK Runner + LiveRequestQueue to forward text/audio to the model.
- Backend: FastAPI + Uvicorn. Frontend: Vanilla JS + Web Audio API + AudioWorklet processors.

---

## Project structure

OmniBank_Assistant-main/
│── main.py                  # FastAPI entry point (API routes / routing logic)                                                                                                                                     
│── requirements.txt         # Python dependencies
│── Dockerfile               # Containerization instructions
│── deploy.sh                # Deployment helper script
│── .env                     # Environment variables (gitignored)
│── banking_agent/           # Core assistant logic
│   ├── agent.py             # Orchestrates model calls and high-level AI logic
│   ├── context.py           # Conversation context / state management
│   └── tools.py             # Banking helper tools (balance, transactions, etc.)
│── frontend/
│   └── static/
│       ├── index.html       # Frontend UI (chat + voice)
│       ├── js/
│       │   ├── app.js                   # Main chat UI & fetch logic
│       │   ├── audio-recorder-*.js      # Recorder / AudioWorklet for capture
│       │   └── pcm-player-*.js          # PCM playback
│       └── styles/
│           └── style.css
│── README.md
│── LICENSE

---

## Tech stack

Backend
- Python 3.9+
- FastAPI, WebSockets
- google.adk (Runner, LiveRequestQueue), google.genai types used in run config
- Uvicorn recommended for development
- InMemorySessionService for session lifecycle (see [main.py](main.py))

Frontend
- HTML5/CSS3, Vanilla JS (ES6+)
- Web Audio API + AudioWorklet (record/play processors in frontend/static/js)
- Client encodes PCM to base64 and sends JSON frames over WebSocket

DevOps
- Dockerfile + deploy.sh
- .env for secrets (do NOT commit)
- TLS recommended for production

---

## Environment variables (exact — taken from repository .env)
The repo's .env contains these keys. Create your own local `.env` with real values.

```text
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_PROJECT_ID=your-gcp-project
LOCATION=us-central1
STAGING_BUCKET=gs://your-staging-bucket
GCP_BUCKET_NAME=your-gcp-bucket
```

main.py uses load_dotenv(); search for os.getenv or dotenv usage if you add new keys.

---

## Run (windows)

1. Create & activate venv:
   - python -m venv venv
   - venv\Scripts\activate

2. Install:
   - pip install -r requirements.txt

3. Populate `.env` with your Google credentials.

4. Start server:
   - uvicorn main:app --host 0.0.0.0 --port 8000 --reload

5. Open UI:
   - http://localhost:8000/ (served by GET / which returns frontend/static/index.html)

Docker:
- Build: docker build -t omnibank-assistant .
- Run: docker run -p 8000:8000 --env-file .env omnibank-assistant

---

## Typical endpoints (exact / implemented in main.py)

1. GET /
- Serves the static UI: returns frontend/static/index.html  
- Implementation: [main.py#root](main.py)

2. Static files
- Mounted at /static -> frontend/static/*

3. WebSocket (primary audio & text channel)
- Path: /ws/{session_id}  
- Query params recognized:
  - lang (string, default "en-US")
  - is_audio (bool, optional) — frontend hint
  - dev_mode (bool, optional) — when true the server forwards tool_call/tool_result events
- Example connect URL:
  - ws://localhost:8000/ws/session123?lang=en-US&is_audio=true&dev_mode=false

Behavior:
- On connect the server:
  - creates a session via InMemorySessionService
  - starts a Runner.run_live(...) with RunConfig (speech_config, response_modalities=["AUDIO"], streaming_mode=StreamingMode.BIDI, input/output transcription configs)
  - uses a LiveRequestQueue to forward incoming client frames to the live runner
  - concurrently forwards live runner events back to client

See implementation in [main.py](main.py).

---

## WebSocket message formats (exact)

Client -> Server (JSON text frames)
- Text message:
  { "mime_type": "text/plain", "data": "What's my balance?" }
- Audio chunk (PCM base64):
  { "mime_type": "audio/pcm", "data": "<base64-pcm-chunk>" }
- Image:
  { "mime_type": "image/jpeg", "data": "<base64-jpeg-bytes>" }

Server -> Client (JSON text frames)
- Assistant text / final:
  { "mime_type": "text/plain", "data": "Your balance is $1,234.56" }
- Partial / transcription:
  { "mime_type": "text/transcription", "data": "Your balance is ..." }
- User input transcription:
  { "mime_type": "text/input_transcription", "data": "What's my balance?" }
- Audio (base64 PCM returned by model):
  { "mime_type": "audio/pcm", "data": "<base64-pcm-bytes>" }
- Turn control:
  { "turn_complete": true, "interrupted": false }
- Dev-mode tool events (dev_mode=true):
  { "mime_type": "tool_call", "data": { "name": "...", "args": {...} } }
  { "mime_type": "tool_result", "data": { "name": "...", "response": {...} } }

Transport detail:
- Client encodes binary audio to base64 and sends in JSON text frames.  
- main.py decodes base64 and calls live_request_queue.send_realtime(Blob(...)) for binary frames and live_request_queue.send_content(...) for text parts. See the functions `client_to_agent_messaging` and `agent_to_client_messaging` in [main.py](main.py).

---

## Audio expectations / recommended settings

- Format: 16-bit PCM (raw), mono
- Sample rate: 16kHz–48kHz (keep frontend and ADK device consistent)
- Chunking: frontend sends small PCM chunks (see `frontend/static/js/pcm-recorder-processor.js`)
- Playback: returned audio is base64 PCM; frontend PCM player decodes and plays it (`pcm-player-processor.js`)

---

## Gemini Live & Google ADK notes

- The app uses Google ADK Runner and LiveRequestQueue to run a live agent session (see [main.py](main.py)). RunConfig sets StreamingMode.BIDI and response_modalities=["AUDIO"] so the model can receive streaming audio and return audio responses.
- Docs:
  - Gemini Live: https://ai.google.dev/gemini-api/docs/live
  - Google ADK: https://google.github.io/adk-docs/

Ensure your chosen model supports audio streaming/modalities used in RunConfig.

---

## Audio processing workflow (exact, no-STT)

1. Browser captures microphone audio via getUserMedia.
2. AudioWorklet / PCM recorder converts audio frames into PCM chunks (raw or WAV-wrapped).
3. The frontend sends audio chunks to the backend:
   - either as multipart/form-data with a full audio file, or
   - streamed in small binary chunks (WebSocket or repeated POSTs) — see frontend/static/js (app.js, pcm-recorder-processor.js).
4. Backend receives binary audio and forwards it to the configured AI model endpoint that accepts audio input natively (no internal STT conversion). main.py decodes base64 frames and uses LiveRequestQueue.send_realtime(Blob(...)) to forward audio to the Runner.
5. The model returns a response (structured JSON text, intents/entities, and possibly audio synthesis content). The backend relays the model response to the frontend over the WebSocket.
6. If synthesized audio is returned, the frontend PCM player decodes base64 PCM and plays it back via AudioWorklet.

Note: Inspect frontend/static/js/* for capture/encoding details (sample rate, chunk size) and main.py for how audio payloads are accepted and forwarded to the model.

---

## Security & privacy notes

- Do not commit `.env` or API keys to source control. Add `.env` to your global gitignore if necessary.
- Treat recorded audio and transcripts as sensitive personal data (PII). Use TLS (HTTPS / WSS) in production for all transport.
- Minimize logging of raw audio or identifiable user data; redact or rotate logs containing PII.
- Add authentication (OAuth/JWT) and RBAC before connecting to real banking systems or production services.
- Use secure storage for any persisted audio or session data (encrypted at rest).
- Limit model access via API key restrictions, VPC Service Controls, or IAM policies where supported.

---

## Contributing

- Fork the repo, create a feature branch, and open a Pull Request with tests and a clear description.
- Run linters and unit tests (if present) before submitting changes.
- Keep changes modular:
  - Add domain logic in banking_agent/tools.py
  - Keep audio/capture logic in frontend/static/js/
  - Update README and add `.env.example` for new env keys
- Open issues for new feature requests (multi-language, JWT auth, external bank connectors).
- For sensitive changes (auth, banking connectors), include an architecture/security review in the PR description.

---

## License

MIT — see LICENSE file.

