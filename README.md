# OmniBank Assistant 🏦💬

OmniBank Assistant is an AI-first conversational banking assistant that supports both text and raw audio (PCM) inputs. The system is designed to handle low-latency voice interactions by directly forwarding raw audio to an audio-capable model (e.g., Google ADK / Gemini Live).

## Key technical highlights:

No local speech-to-text (STT): Unlike traditional pipelines, the assistant does not convert audio to text locally. Instead, raw PCM audio is streamed directly to the model, which performs audio understanding natively.
Bidirectional streaming: The backend uses Google ADK's Runner with StreamingMode.BIDI to enable real-time communication between the client and the model.
Model capabilities:
Understands raw audio inputs (ASR and intent recognition in one step).
Returns structured JSON responses (e.g., intents, entities, tool calls).
Optionally synthesizes audio responses (base64 PCM) for playback.
Frontend integration: The browser captures audio using the Web Audio API and streams it to the backend via WebSocket. The backend relays the audio to the model and returns responses to the client.

---
## Layman-Friendly Explanation
OmniBank Assistant is like having a personal banker you can talk to or chat with online. Here’s how it works:

Talk or type: You can either type your questions (e.g., "What’s my balance?") or speak naturally into your microphone (e.g., "Can you transfer $200 to my savings?").
Smart listening: The assistant listens to your voice and sends it directly to a powerful AI model that understands what you’re saying — no need to convert your voice into text first.
Quick responses: The AI figures out what you want, like checking your balance or making a transfer, and sends back a response. It can even talk back to you with a voice reply!
Safe and secure: Your voice and data are sent securely, and the assistant doesn’t store your audio locally.
This makes the assistant fast, easy to use, and perfect for managing your banking needs on the go.

## Project structure

OmniBank_Assistant-main/
│
├── main.py # FastAPI entry point for API routes and routing logic
├── requirements.txt # Python dependencies for the project
├── Dockerfile # Instructions for containerizing the application
├── deploy.sh # A helper script to build and deploy the application to Cloud Run
├── .env # Environment variables, including API keys and project IDs (gitignored)
│
├── banking_agent/ # Core logic for the AI assistant
│ ├── agent.py # Orchestrates model calls and high-level AI logic
│ ├── context.py # Manages conversation context and state
│ └── tools.py # Defines banking-specific helper tools (e.g., for balance, transactions)
│
├── frontend/ # Frontend UI files
│ └── static/
│ ├── index.html # Main frontend page with the chat and voice interface
│ ├── js/
│ │ ├── app.js # Main chat UI and fetch logic
│ │ ├── audio-recorder-.js # Audio recorder for capturing user input
│ │ └── pcm-player-.js # PCM audio playback for the assistant's responses
│ └── styles/
│ └── style.css # Styles for the frontend UI
│
├── README.md # This file
└── LICENSE # The project license
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

## User journey — how OmniBank Assistant works (use-case view)

1. User arrives at the UI
   - Opens the web app (GET / serves frontend/static/index.html).
   - Sees a chat UI with text input and a microphone button for voice.

2. User starts a conversation
   - Text path: user types "What's my checking balance?" and presses send.
   - Voice path: user taps the mic, speaks naturally — e.g., "Hey, what is my balance and any recent large transactions?"

3. Browser captures audio
   - The frontend captures raw PCM via getUserMedia + AudioWorklet (pcm-recorder-processor).
   - PCM frames are packaged and base64-encoded into JSON frames.

4. Client streams to backend
   - The browser opens a WebSocket to /ws/{session_id}?lang=en-US&is_audio=true.
   - Audio frames (and text frames) are sent as JSON messages:
     { "mime_type": "audio/pcm", "data": "<base64-pcm>" } or { "mime_type":"text/plain", "data":"..." }.

5. Backend forwards audio unchanged to the model
   - main.py decodes base64 and uses google.adk LiveRequestQueue.send_realtime(Blob(...)) to forward binary to the Runner.
   - No local speech-to-text conversion occurs — the model receives raw audio and performs audio understanding natively.

6. Model analyzes audio and returns structured output
   - The model may return:
     - Structured JSON (intent, entities, tool_call requests)
     - Text transcripts or partial transcriptions
     - Synthesized audio (base64 PCM) for spoken replies
   - The backend relays these model events back to the client over the WebSocket.

7. Frontend presents results and acts on tool results
   - UI displays assistant text and partials in the chat.
   - If synthesized audio is provided, the PCM player decodes the returned base64 PCM and plays it immediately.
   - If the model requested a tool call (e.g., "check_balance"), the backend invokes banking_agent.tools, returns result events, and the assistant responds with formatted result: "Your checking balance is $X".

8. Multi-turn flow & confirmations
   - The system tracks conversation state in InMemorySessionService + banking_agent/context.py.
   - Example: Assistant asks "Transfer $500 to savings — confirm?" User replies (voice/text); the same streaming flow handles the confirmation and completes the transaction via tools.

Example quick scenario (voice):
- User: speaks "Transfer two hundred to my savings."
- Model: returns tool_call { name: "initiate_transfer", args: { amount: 200, to_account: "savings" } }
- Backend: banking_agent.tools executes transfer (or simulates), returns tool_result.
- Model: returns "Done — $200 moved to savings." and optional audio response.
- Frontend: shows text and plays audio.

Why no local STT?
- Simpler pipeline: raw audio is sent to a single audio-capable model that does both ASR/understanding and synthesis.
- Lower latency in bidirectional streaming (RunConfig.streaming_mode = BIDI).
- Relies on the chosen model (Gemini Live / ADK Runner) for robust audio understanding and transcription.

Implications / requirements
- Audio format consistency matters: recommended 16-bit PCM, mono, 16k–48kHz.
- Secure transport required: use WSS/TLS in production.
- Model must support audio modalities & streaming (configured via google.adk RunConfig: response_modalities=["AUDIO"]).
- Add authentication, RBAC, and audit before connecting to real banking backends.

Actors & responsibilities
- End user: interacts by speaking or typing; receives text and audio replies.
- Frontend dev: ensure recorder/player processors produce the required PCM and chunk sizes; encode to base64; manage WS lifecycle.
- Backend dev / integrator: ensure env vars (GOOGLE_API_KEY, PROJECT_ID, LOCATION, etc.), Runner/LiveRequestQueue usage, tool integrations, and secure deployment.

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

