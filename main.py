# main.py 

import os
import json
import asyncio
import base64
from pathlib import Path
from dotenv import load_dotenv

from google.genai.types import Part, Content, Blob
from google.genai import types as genai_types
from google.protobuf.struct_pb2 import Struct

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from banking_agent.agent import root_agent
from banking_agent.tools import session_context

from google.cloud import translate_v2 as translate

load_dotenv()

APP_NAME = "Santander Banking Assistant"
STATIC_DIR = Path("frontend/static")
session_service = InMemorySessionService()

try:
    translate_client = translate.Client()
    print("Google Translate client initialized successfully.")
except Exception as e:
    print(f"Error initializing Google Translate client: {e}")
    translate_client = None

def translate_text(text: str, target_language: str = "en") -> str:

    """Translates text using the Google Cloud Translation API."""
    if not translate_client:
        print("Translate client not available. Returning original text.")
        return text
    try:
        result = translate_client.translate(text, target_language=target_language)
        return result["translatedText"]
    except Exception as e:
        print(f"Error during translation: {e}")
        return text # Return original text on error

async def start_agent_session(session_id: str, language_code: str):
    """Starts a dedicated banking agent session."""
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=session_id,
        session_id=session_id,
        state={"language": language_code}
    )

    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        session_service=session_service,
    )

    run_config = RunConfig(
        speech_config=genai_types.SpeechConfig(
            language_code=language_code,
            voice_config=genai_types.VoiceConfig(
                prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name="Leda")
            ),
        ),
        response_modalities=["AUDIO"],
        streaming_mode=StreamingMode.BIDI,
        output_audio_transcription=genai_types.AudioTranscriptionConfig(),
        input_audio_transcription=genai_types.AudioTranscriptionConfig(),
    )

    live_request_queue = LiveRequestQueue()
    live_events = runner.run_live(
        session=session,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )
    return live_events, live_request_queue, session

async def agent_to_client_messaging(websocket: WebSocket, live_events, dev_mode: bool = False):
    async for event in live_events:
        if event.turn_complete or event.interrupted:
            await websocket.send_text(json.dumps({
                "turn_complete": event.turn_complete,
                "interrupted": event.interrupted
            }))
            continue

        if event.content and event.content.parts:
            author = event.content.role
            for part in event.content.parts:
               # If there's text, send it with the correct type based on the author
                if part.text:
                   # If the author is the USER, it's an input transcription
                    if author == 'user':
                       native_text = part.text
                       print(f"Input language code: {native_text}")
                       await websocket.send_text(json.dumps({
                           "mime_type": "text/input_transcription",
                           "data": native_text
                       }))
                       translated_list = []
                       translated_eng_text = translate_text(native_text)
                       translated_list.append(translated_eng_text)
                       all_translations_str = "".join(translated_list)
                       print(f"Complete Translated text: {all_translations_str}")
                       await websocket.send_text(json.dumps({
                           "mime_type": "text/input_translated",
                           "data": all_translations_str
                       }))
                    # If the author is the MODEL, it's the agent's speech
                    elif author == 'model':
                        # Use the event.partial flag to distinguish live transcript from final text
                        if event.partial:
                           await websocket.send_text(json.dumps({
                               "mime_type": "text/transcription",
                               "data": part.text
                           }))
                        else:
                           await websocket.send_text(json.dumps({
                               "mime_type": "text/plain",
                               "data": part.text
                           }))

                # Handle audio data from the agent (this remains the same)
                elif part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                   await websocket.send_text(json.dumps({
                       "mime_type": "audio/pcm",
                       "data": base64.b64encode(part.inline_data.data).decode("ascii")
                   }))

                if dev_mode:
                    if part.function_call:
                        args_dict = {key: value for key, value in part.function_call.args.items()}
                        await websocket.send_text(json.dumps({"mime_type": "tool_call", "data": {"name": part.function_call.name, "args": args_dict}}))
                    elif part.function_response:
                        response_dict = {key: value for key, value in part.function_response.response.items()} if part.function_response.response else {}
                        await websocket.send_text(json.dumps({"mime_type": "tool_result", "data": {"name": part.function_response.name, "response": response_dict}}))

async def client_to_agent_messaging(websocket: WebSocket, live_request_queue: LiveRequestQueue):
    while True:
        message_json = await websocket.receive_text()
        message = json.loads(message_json)
        mime_type = message.get("mime_type")
        data = message.get("data")
        if mime_type == "text/plain":
            live_request_queue.send_content(content=Content(role="user", parts=[Part.from_text(text=data)]))
        elif mime_type in ["audio/pcm", "image/jpeg"]:
            live_request_queue.send_realtime(Blob(data=base64.b64decode(data), mime_type=mime_type))

app = FastAPI()
# origins = ["https://mms-ui-socket-new.en.enterprise-europe.flutterflow.app", "http://localhost", "http://localhost:8080"]
origins = ["https://webviewsocket-da1tah.enterprise-europe.flutterflow.app", "http://localhost", "http://localhost:8080"]

app.add_middleware(CORSMiddleware, 
                    allow_origins=["*"], 
                    allow_credentials=True, 
                    allow_methods=["*"], 
                    allow_headers=["*"])

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, lang: str = "en-US", is_audio: bool = False, dev_mode: bool = False):
    await websocket.accept()
    print(f"Client #{session_id} connected. Audio: {is_audio}, Lang: {lang}, Dev Mode: {dev_mode}")
    async def run_tasks_with_context():
        live_events, live_request_queue, session_object = await start_agent_session(session_id, lang)
        session_context.set(session_object)
        tasks = [
            asyncio.create_task(agent_to_client_messaging(websocket, live_events, dev_mode)),
            asyncio.create_task(client_to_agent_messaging(websocket, live_request_queue)),
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending: task.cancel()
    try:
        await run_tasks_with_context()
    except WebSocketDisconnect:
        print(f"Client #{session_id} disconnected cleanly.")
    except Exception as e:
        print(f"An error occurred in the websocket endpoint for client #{session_id}: {e}")
    finally:
        print(f"Connection for client #{session_id} closed.")
