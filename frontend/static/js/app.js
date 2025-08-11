/**
* app.js: Frontend logic for the Omnibank Banking Assistant.
* FINAL WORKING VERSION with screen sharing and corrected function scope.
*/
import { startAudioPlayerWorklet } from "./audio-player.js";
import { startAudioRecorderWorklet, stopMicrophone } from "./audio-recorder.js";

class MediaHandler {
constructor() {
  this.videoElement = null;
  this.currentStream = null;
  this.frameCaptureInterval = null;
}
initialize(videoElement) { this.videoElement = videoElement; }
 async startWebcam() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 }, audio: false });
    this.handleNewStream(stream);
    return true;
  } catch (error) {
    console.error('Error accessing webcam:', error);
    return false;
  }
}

async startScreenShare(onStopCallback) {
  try {
    const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
    stream.getVideoTracks()[0].addEventListener('ended', onStopCallback);
    this.handleNewStream(stream);
    return true;
  } catch (error) {
    console.error('Error starting screen share:', error);
    return false;
  }
}

handleNewStream(stream) {
  if (this.currentStream) { this.stopAll(); }
  this.currentStream = stream;
  if (this.videoElement) {
    this.videoElement.srcObject = stream;
    this.videoElement.classList.remove('hidden');
  }
}

stopAll() {
  this.stopFrameCapture();
  if (this.currentStream) {
    this.currentStream.getTracks().forEach(track => track.stop());
    this.currentStream = null;
  }
  if (this.videoElement) {
    this.videoElement.srcObject = null;
    this.videoElement.classList.add('hidden');
  }
}
  startFrameCapture(onFrame) {
  if (this.frameCaptureInterval) { this.stopFrameCapture(); }
  this.frameCaptureInterval = setInterval(() => {
    if (!this.currentStream || !this.videoElement || this.videoElement.paused) return;
    const canvas = document.createElement('canvas');
    canvas.width = this.videoElement.videoWidth;
    canvas.height = this.videoElement.videoHeight;
    const context = canvas.getContext('2d');
    context.drawImage(this.videoElement, 0, 0, canvas.width, canvas.height);
    const base64Image = canvas.toDataURL('image/jpeg', 0.8).split(',')[1];
    onFrame(base64Image);
  }, 1000);
}

stopFrameCapture() {
  clearInterval(this.frameCaptureInterval);
  this.frameCaptureInterval = null;
}
}

const state = {
sessionId: Math.random().toString(36).substring(2),
websocket: null,
isAudioMode: false,
isVideoMode: false, // Represents either camera or screen share is active
activeMediaType: null, // Can be 'video' or 'screen'
userTranscriptionBuffer: "",
agentTranscriptionBuffer: "",
mediaHandler: new MediaHandler(),
audio: { playerNode: null, playerContext: null, recorderNode: null, recorderContext: null, micStream: null, }
};

const DOMElements = {
chatAppContainer: document.getElementById("chatAppContainer"),
messageForm: document.getElementById("messageForm"),
messageInput: document.getElementById("message"),
messagesDiv: document.getElementById("messages"),
connectionStatusDiv: document.getElementById("connectionStatus"),
languageSelector: document.getElementById("languageSelector"),
devModeToggle: document.getElementById("devModeToggle"),
startAudioButton: document.getElementById("startAudioButton"),
stopAudioButton: document.getElementById("stopAudioButton"),
sendButton: document.getElementById("sendButton"),
videoFeed: document.getElementById("videoFeed"),
startVideoButton: document.getElementById("startVideoButton"),
stopVideoButton: document.getElementById("stopVideoButton"),
startScreenButton: document.getElementById("startScreenButton"),
stopScreenButton: document.getElementById("stopScreenButton"),
imageUploadButton: document.getElementById("imageUploadButton"),
imageUploadInput: document.getElementById("imageUploadInput")
};


function updateButtonStates() {
  const audioOnlyMode = state.isAudioMode && !state.isVideoMode;
  const videoMode = state.isVideoMode && state.activeMediaType === 'video';
  const screenMode = state.isVideoMode && state.activeMediaType === 'screen';

  // Text Input is always enabled. Send button is handled by connection status.
  DOMElements.messageInput.disabled = false;

  // Audio Buttons (Microphone for dedicated audio call)
  DOMElements.startAudioButton.disabled = state.isVideoMode; // Disable if video/screen is active
  DOMElements.stopAudioButton.disabled = !audioOnlyMode;

  if (audioOnlyMode) {
      DOMElements.startAudioButton.classList.add('hidden');
      DOMElements.stopAudioButton.classList.remove('hidden');
  } else {
      DOMElements.startAudioButton.classList.remove('hidden');
      DOMElements.stopAudioButton.classList.add('hidden');
  }

  // Video Button (Webcam)
  DOMElements.startVideoButton.disabled = screenMode;
  DOMElements.stopVideoButton.disabled = !videoMode;
  if (videoMode) {
      DOMElements.startVideoButton.classList.add('hidden');
      DOMElements.stopVideoButton.classList.remove('hidden');
  } else {
      DOMElements.startVideoButton.classList.remove('hidden');
      DOMElements.stopVideoButton.classList.add('hidden');
  }

  // Screen Share Button
  DOMElements.startScreenButton.disabled = videoMode;
  DOMElements.stopScreenButton.disabled = !screenMode;
  if (screenMode) {
      DOMElements.startScreenButton.classList.add('hidden');
      DOMElements.stopScreenButton.classList.remove('hidden');
  } else {
      DOMElements.startScreenButton.classList.remove('hidden');
      DOMElements.stopScreenButton.classList.add('hidden');
  }
}

function connectWebsocket() {
updateConnectionStatus("Connecting...", "connecting");
const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
const wsUrl = `${wsProtocol}${window.location.host}/ws/${state.sessionId}`;
const selectedLang = DOMElements.languageSelector.value;
const isDevMode = DOMElements.devModeToggle.checked;
// The `is_audio` param is now fixed to what was set on the initial page load.
// The websocket connection will not be reset during the session.
const isAudioActive = state.isAudioMode || state.isVideoMode;
let fullWsUrl = `${wsUrl}?is_audio=${isAudioActive}&lang=${selectedLang}`;
if (isDevMode) { fullWsUrl += `&dev_mode=true`; }
console.log("Connecting to:", fullWsUrl);
state.websocket = new WebSocket(fullWsUrl);
state.websocket.onopen = onWsOpen;
state.websocket.onmessage = onWsMessage;
state.websocket.onclose = onWsClose;
state.websocket.onerror = onWsError;
}

function onWsOpen() {
console.log("WebSocket connection opened.");
updateConnectionStatus("Connected", "connected");
updateButtonStates();
DOMElements.sendButton.disabled = false;
}

function onWsClose(event) {
console.log("WebSocket connection closed.", event);
const status = event.code !== 1000 && event.code !== 1005 ? "error" : "disconnected";
updateConnectionStatus("Disconnected", status);
DOMElements.sendButton.disabled = true;
DOMElements.startAudioButton.disabled = true;
DOMElements.stopAudioButton.disabled = true;
DOMElements.startVideoButton.disabled = true;
DOMElements.stopVideoButton.disabled = true;
DOMElements.startScreenButton.disabled = true;
DOMElements.stopScreenButton.disabled = true;
state.userTranscriptionBuffer = "";
state.agentTranscriptionBuffer = "";
setTimeout(connectWebsocket, 1500);
}

function onWsError(error) { console.error("WebSocket error: ", error); updateConnectionStatus("Error", "error"); }

function onWsMessage(event) {
  try {
      const message = JSON.parse(event.data);
      if (message.turn_complete) { finalizeAndDisplayMessages(); return; }
      const isAgentMessage = ["tool_call", "tool_result", "audio/pcm", "text/transcription", "text/plain"].includes(message.mime_type);
      if (isAgentMessage && state.userTranscriptionBuffer) { displayFinalUserMessage(); }
      const messageHandlers = {
          "tool_call": displayDevMessage, "tool_result": displayDevMessage,
          "text/input_transcription": (msg) => { state.userTranscriptionBuffer = msg.data; },
          "audio/pcm": playAudioChunk,
          "text/transcription": (msg) => { state.agentTranscriptionBuffer = msg.data; },
          "text/plain": displayFinalAgentMessage,
      };
      const handler = messageHandlers[message.mime_type];
      if (handler) { handler(message); }
  } catch (error) { console.error("Error processing incoming message:", error); }
}

function createMessageWrapper(type, pElement) { const wrapper = document.createElement('div'); wrapper.className = `message-wrapper ${type}-wrapper`; wrapper.appendChild(pElement); DOMElements.messagesDiv.appendChild(wrapper); return wrapper; }
function finalizeAndDisplayMessages() { displayFinalUserMessage(); if (state.agentTranscriptionBuffer) { displayFinalAgentMessage({ data: state.agentTranscriptionBuffer }); } }
function displayFinalAgentMessage(message) { const text = message.data; if (!text) return; const pElement = document.createElement("p"); pElement.classList.add("agent-message"); pElement.textContent = text; createMessageWrapper('agent', pElement); scrollToBottom(DOMElements.messagesDiv); state.agentTranscriptionBuffer = ""; }
function displayFinalUserMessage() {
   // Per request, do not display the user's transcribed audio.
   // Simply clear the buffer. Typed text messages are handled separately.
   state.userTranscriptionBuffer = "";
}

function displayUserTextMessage(text) {
   const pElement = document.createElement("p");
   pElement.textContent = text;
   pElement.classList.add("user-message");
   createMessageWrapper('user', pElement);
   scrollToBottom(DOMElements.messagesDiv);
}

function displayUserImageMessage(base64Image, mimeType) {
   const imgElement = document.createElement("img");
   imgElement.src = `data:${mimeType};base64,${base64Image}`;
   imgElement.classList.add("user-image");
   createMessageWrapper('user', imgElement);
   scrollToBottom(DOMElements.messagesDiv);
}

function displayDevMessage(message) { const pre = document.createElement("pre"); pre.className = "dev-log-entry"; const type = message.mime_type.toUpperCase().replace('_', ' '); const data = message.data || {}; const jsonData = data.args || data.response || {}; pre.textContent = `[${type}] | Name: ${data.name || 'N/A'}\n${JSON.stringify(jsonData, null, 2)}`; DOMElements.messagesDiv.appendChild(pre); scrollToBottom(DOMElements.messagesDiv); }
function updateConnectionStatus(statusText, statusClass) { DOMElements.connectionStatusDiv.textContent = statusText; DOMElements.connectionStatusDiv.className = ''; DOMElements.connectionStatusDiv.classList.add(statusClass); }
function handleTextMessageSubmit(e) { e.preventDefault(); const messageText = DOMElements.messageInput.value.trim(); if (!messageText) return; if (state.userTranscriptionBuffer) { state.userTranscriptionBuffer = ""; } displayUserTextMessage(messageText); sendMessage({ mime_type: "text/plain", data: messageText }); DOMElements.messageInput.value = ""; }
function scrollToBottom(element) { element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' }); }

async function setupAudio() {
  state.isAudioMode = true;
  updateButtonStates();
  try {
      if (!state.audio.playerNode) { [state.audio.playerNode, state.audio.playerContext] = await startAudioPlayerWorklet(); }
      if (!state.audio.recorderNode) { [state.audio.recorderNode, state.audio.recorderContext, state.audio.micStream] = await startAudioRecorderWorklet(audioRecorderHandler); }
     
      // Per request, do not disconnect the websocket.
      // The server will use the connection parameters from the initial connection.
      if (!state.websocket || state.websocket.readyState !== WebSocket.OPEN) {
          connectWebsocket();
      }
  } catch (error) { console.error("Audio setup failed:", error); handleStopAudio(); }
}

function handleStopAudio() {
  state.isAudioMode = false;
  if (state.audio.micStream) { stopMicrophone(state.audio.micStream); }
  state.audio.recorderNode?.disconnect();
  state.audio.micStream = null;
  state.audio.recorderNode = null;
  updateButtonStates();
  // Per request, do not disconnect the websocket.
}

async function startMedia(mediaType) {
   // If we are upgrading from a dedicated audio-call, cleanly switch state.
   if (state.isAudioMode) {
       state.isAudioMode = false;
   }


  state.isVideoMode = true;
  state.activeMediaType = mediaType;
 
  try {
      let success = false;
      if (mediaType === 'video') {
          success = await state.mediaHandler.startWebcam();
      } else if (mediaType === 'screen') {
          success = await state.mediaHandler.startScreenShare(stopMedia);
      }
      if (!success) { throw new Error(`Could not start ${mediaType}.`); }
      if (!state.audio.playerNode) { [state.audio.playerNode, state.audio.playerContext] = await startAudioPlayerWorklet(); }
      if (!state.audio.recorderNode) { [state.audio.recorderNode, state.audio.recorderContext, state.audio.micStream] = await startAudioRecorderWorklet(audioRecorderHandler); }
      state.mediaHandler.startFrameCapture(videoFrameHandler);

      DOMElements.chatAppContainer.classList.add('video-active');
      updateButtonStates();

      // Per request, do not disconnect the websocket.
      // The server will use the connection parameters from the initial connection.
      if (!state.websocket || state.websocket.readyState !== WebSocket.OPEN) {
          connectWebsocket();
      }
  } catch(error) {
      console.error(`${mediaType} setup failed:`, error);
      stopMedia();
  }
}

function stopMedia() {
  state.isVideoMode = false;
  state.activeMediaType = null;
  state.mediaHandler.stopAll();
  if (state.audio.micStream) { stopMicrophone(state.audio.micStream); }
  state.audio.recorderNode?.disconnect();
  state.audio.micStream = null;
  state.audio.recorderNode = null;

  DOMElements.chatAppContainer.classList.remove('video-active');
  updateButtonStates();
   // Per request, do not disconnect the websocket.
}

// New function to handle image uploads
function handleImageUpload(e) {
   const file = e.target.files[0];
   if (!file) return;


   // Validate that the file is an image
   if (!file.type.startsWith('image/')) {
     console.error('File is not an image:', file.type);
     alert('Please upload a valid image file (e.g., JPEG, PNG, GIF).');
     e.target.value = ''; // Reset the input
     return;
   }


   const reader = new FileReader();
   reader.onload = function(event) {
       const base64Image = event.target.result.split(',')[1];
       if (base64Image) {
           displayUserImageMessage(base64Image, file.type);
           // Send the base64 encoded image to the backend with the correct mime_type
           sendMessage({ mime_type: file.type, data: base64Image });
       }
   };
   reader.onerror = function(error) {
       console.error("Error reading file:", error);
   };
   reader.readAsDataURL(file);
   e.target.value = ''; // Clear the input so the same image can be re-uploaded
}

function videoFrameHandler(base64Image) { if (state.isVideoMode) { sendMessage({ mime_type: "image/jpeg", data: base64Image }); } }
function audioRecorderHandler(pcmData) { if (state.isAudioMode || state.isVideoMode) { sendMessage({ mime_type: "audio/pcm", data: arrayBufferToBase64(pcmData) }); } }
function playAudioChunk(message) { if (state.audio.playerNode) { if (state.audio.playerContext && state.audio.playerContext.state === 'suspended') { state.audio.playerContext.resume().catch(e => console.error("Failed to resume AudioContext:", e)); } state.audio.playerNode.port.postMessage(base64ToArray(message.data)); } }
function sendMessage(message) { if (state.websocket && state.websocket.readyState === WebSocket.OPEN) { state.websocket.send(JSON.stringify(message)); } }
function base64ToArray(base64) { try { if (typeof base64 !== 'string' || base64.length === 0) return new ArrayBuffer(0); const binaryString = window.atob(base64); const len = binaryString.length; const bytes = new Uint8Array(len); for (let i = 0; i < len; i++) { bytes[i] = binaryString.charCodeAt(i); } return bytes.buffer; } catch (e) { console.error("Error decoding base64:", e); return new ArrayBuffer(0); } }
function arrayBufferToBase64(buffer) { let binary = ""; const bytes = new Uint8Array(buffer); for (let i = 0; i < bytes.byteLength; i++) { binary += String.fromCharCode(bytes[i]); } return window.btoa(binary); }

function initialize() {
DOMElements.messageForm.addEventListener("submit", handleTextMessageSubmit);
DOMElements.startAudioButton.addEventListener("click", setupAudio);
DOMElements.stopAudioButton.addEventListener("click", handleStopAudio);
DOMElements.startVideoButton.addEventListener("click", () => startMedia('video'));
DOMElements.stopVideoButton.addEventListener("click", stopMedia);
DOMElements.startScreenButton.addEventListener("click", () => startMedia('screen'));
DOMElements.stopScreenButton.addEventListener("click", stopMedia);
DOMElements.imageUploadButton.addEventListener("click", () => DOMElements.imageUploadInput.click());
DOMElements.imageUploadInput.addEventListener("change", handleImageUpload);
 const forceReconnect = () => {
   // Per request, do not disconnect the websocket.
   // Settings changes will require a page refresh to take effect.
   console.warn("Settings changes (language, dev mode) require a page refresh to take effect.");
 };
 DOMElements.languageSelector.addEventListener("change", forceReconnect);
 DOMElements.devModeToggle.addEventListener("change", (e) => {
  DOMElements.chatAppContainer.classList.toggle('dev-mode-active', e.target.checked);
  forceReconnect();
 });
 state.mediaHandler.initialize(DOMElements.videoFeed);
 DOMElements.sendButton.disabled = true;
 DOMElements.startAudioButton.disabled = true;
 DOMElements.stopAudioButton.disabled = true;
 DOMElements.startVideoButton.disabled = true;
 DOMElements.stopVideoButton.disabled = true;
 DOMElements.startScreenButton.disabled = true;
 DOMElements.stopScreenButton.disabled = true;
 DOMElements.chatAppContainer.classList.toggle('dev-mode-active', DOMElements.devModeToggle.checked);
 connectWebsocket();
}

initialize();
