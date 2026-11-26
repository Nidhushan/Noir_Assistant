const chatForm = document.getElementById("chat-form");
const messageInput = document.getElementById("message-input");
const chatMessages = document.getElementById("chat-messages");
const sendButton = chatForm.querySelector("button");
let currentConversationId = localStorage.getItem("noir_conversation_id");
const newChatButton = document.getElementById("new-chat-button");
const conversationList = document.getElementById("conversation-list");

newChatButton.addEventListener("click", function() {
    currentConversationId = null;
    localStorage.removeItem("noir_conversation_id");
    chatMessages.innerHTML = "";
    loadConversations();
    focusMessageInput();
});


chatForm.addEventListener("submit", async function(event) {
    event.preventDefault();

    const message = messageInput.value;
    if (!message.trim()) return;

    const userMessageElement = displayMessage("user", message, "pending");
    messageInput.value = "";
    sendButton.disabled = true;

    let assistantMessageElement = null;

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                message: message,
                conversation_id: currentConversationId === null
                    ? null
                    : Number(currentConversationId)
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(
                errorData.detail || "Something went wrong. Please try again."
            );
        }

        if (!response.body) {
            throw new Error("Your browser does not support response streaming.");
        }

        // Create an empty assistant message for progressive output.
        assistantMessageElement = displayMessage("assistant", "");
        const assistantContentElement =
            assistantMessageElement.querySelector(".message-content");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        function handleEvent(eventBlock) {
            const lines = eventBlock.split(/\r?\n/);
            let eventType = "";
            let eventData = "";

            for (const line of lines) {
                if (line.startsWith("event: ")) {
                    eventType = line.slice(7);
                } else if (line.startsWith("data: ")) {
                    eventData += line.slice(6);
                }
            }

            if (!eventType || !eventData) return;

            const data = JSON.parse(eventData);

            if (eventType === "metadata") {
                currentConversationId = data.conversation_id;
                localStorage.setItem(
                    "noir_conversation_id",
                    currentConversationId
                );
            }

            else if (eventType === "token") {
                assistantContentElement.textContent += data.content;
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }

            else if (eventType === "error") {
                throw new Error(data.message);
            }
        }

        while (true) {
            const { value, done } = await reader.read();

            if (done) break;

            buffer += decoder.decode(value, {stream: true});

            const events = buffer.split(/\r?\n\r?\n/);
            buffer = events.pop();

            for (const eventBlock of events) {
                handleEvent(eventBlock);
            }
        }

        buffer += decoder.decode();

        if (buffer.trim()) {
            handleEvent(buffer);
        }

        loadConversations();
    }

    catch (error) {
        console.error("Error:", error.message);

        // Remove an incomplete assistant response if generation failed.
        if (assistantMessageElement) {
            assistantMessageElement.remove();
        }

        const errorIndicator = document.createElement("span");
        errorIndicator.classList.add("message-error-indicator");
        errorIndicator.textContent = "ⓘ";

        const tooltip = document.createElement("span");
        tooltip.classList.add("error-tooltip");
        tooltip.textContent = error.message;

        errorIndicator.appendChild(tooltip);
        userMessageElement.appendChild(errorIndicator);
    }

    finally {
        sendButton.disabled = false;
        focusMessageInput();
    }
});


document.addEventListener("DOMContentLoaded", function() {
    loadConversations();
    // Code here runs after the HTML has been loaded.
    if (currentConversationId !== null) {
        fetch(`/api/chat/${currentConversationId}/messages`)
        .then(response => response.json())
        .then(data => {
            data.messages.forEach(function(message) {
                displayMessage(
                    message.role,
                    message.content,
                    message.status,
                    message.error_code,
                    message.error_detail
                );
            });
        })
        .catch(error => {
            console.error("Failed to load conversation:", error);
        });
    }

    focusMessageInput();
});

async function loadConversations() {
    conversationList.innerHTML = "";

    const response = await fetch("/api/conversations");

    const data = await response.json();

    data.conversations.forEach(function(conversation) {
        const conversationElement = document.createElement("button");

        conversationElement.textContent = conversation.title;
        if (Number(currentConversationId) === conversation.id) {
            conversationElement.classList.add("active");
        }

        conversationElement.addEventListener("click", function() {
            currentConversationId = conversation.id;
            loadConversations();
            localStorage.setItem("noir_conversation_id", currentConversationId);
            fetch(`/api/chat/${currentConversationId}/messages`)
                .then(response => response.json())
                .then(data => {
                    chatMessages.innerHTML = "";
                    data.messages.forEach(function(message) {
                        displayMessage(
                            message.role,
                            message.content,
                            message.status,
                            message.error_code,
                            message.error_detail
                        );
                    });
                    focusMessageInput();
                });
        });

        conversationList.appendChild(conversationElement);
    });
}

function displayMessage(role, content, status = "completed", errorCode = null, errorDetail = null) {
    const messageElement = document.createElement("div");
    messageElement.classList.add("message");

    const speakerElement = document.createElement("span");
    speakerElement.classList.add("message-speaker");

    const contentElement = document.createElement("span");
    contentElement.classList.add("message-content");

    if (role === "assistant") {
        messageElement.classList.add("assistant-message");
        speakerElement.textContent = "noir:";
    } else {
        messageElement.classList.add("user-message");
        speakerElement.textContent = "nate:";
    }

    contentElement.textContent = content;

    messageElement.appendChild(speakerElement);
    messageElement.appendChild(contentElement);

    if (role === "user" && status === "failed") {
        const errorIndicator = document.createElement("span");
        errorIndicator.classList.add("message-error-indicator");
        errorIndicator.textContent = "ⓘ";
        const tooltip = document.createElement("span");
        tooltip.classList.add("error-tooltip");
        tooltip.textContent = `${errorCode}: ${errorDetail}`;

        errorIndicator.appendChild(tooltip);

        messageElement.appendChild(errorIndicator);
    }

    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageElement;
}

function focusMessageInput() {
    if (window.matchMedia("(pointer: fine)").matches) {
        messageInput.focus();
    }
}

const voiceButton = document.getElementById("voice-button");
const voiceInterface = document.getElementById("voice-interface");
const voiceClose = document.getElementById("voice-close");
const voiceStatus = document.getElementById("voice-status");

const voiceRecordButton = document.getElementById("voice-record");
const voicePreview = document.getElementById("voice-preview");

let mediaRecorder = null;
let audioStream = null;
let audioChunks = [];
let audioUrl = null;


async function transcribeAndSend(audioBlob) {
    voiceStatus.textContent = "Transcribing...";
    voiceRecordButton.disabled = true;

    try {
        const formData = new FormData();

        formData.append("audio", audioBlob, "recording.webm");

        const response = await fetch("/api/voice/transcribe", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(
                errorData.detail || "Transcription failed."
            );
        }

        const data = await response.json();

        if (!data.text || !data.text.trim()) {
            throw new Error("No speech detected.");
        }

        console.log("Transcription:", data);

        // Put the transcript into the existing chat input.
        messageInput.value = data.text;

        // Trigger the existing chat submission workflow.
        chatForm.requestSubmit();

        voiceStatus.textContent = "Message sent";

    } catch (error) {
        console.error("Voice processing error:", error);

        voiceStatus.textContent = error.message;

    } finally {
        voiceRecordButton.disabled = false;
    }
}


voiceRecordButton.addEventListener("click", async function() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
        return;
    }

    try {
        voiceStatus.textContent = "Requesting microphone...";

        audioStream = await navigator.mediaDevices.getUserMedia({
            audio: true
        });

        audioChunks = [];

        const options = {};
        if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
            options.mimeType = "audio/webm;codecs=opus";
        }

        mediaRecorder = new MediaRecorder(audioStream, options);

        mediaRecorder.addEventListener("dataavailable", function(event) {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        });

        mediaRecorder.addEventListener("stop", function() {
            const audioBlob = new Blob(audioChunks, {
                type: mediaRecorder.mimeType
            });

            if (audioUrl) {
                URL.revokeObjectURL(audioUrl);
            }

            audioUrl = URL.createObjectURL(audioBlob);
            voicePreview.src = audioUrl;
            voicePreview.hidden = false;

            voiceStatus.textContent = "Recording ready";
            voiceRecordButton.textContent = "Record again";
            transcribeAndSend(audioBlob);

            console.log("Recording captured:", {
                type: audioBlob.type,
                size: audioBlob.size,
                sizeKB: (audioBlob.size / 1024).toFixed(2)
            });

            audioStream.getTracks().forEach(track => track.stop());
            audioStream = null;
        });

        mediaRecorder.start();

        voiceStatus.textContent = "Listening...";
        voiceRecordButton.textContent = "Stop recording";

    } catch (error) {
        console.error("Microphone error:", error);

        voiceStatus.textContent = "Microphone unavailable";
        voiceRecordButton.textContent = "Try again";

        if (audioStream) {
            audioStream.getTracks().forEach(track => track.stop());
            audioStream = null;
        }
    }
});

function openVoiceInterface() {
    voiceInterface.classList.add("active");
    voiceStatus.textContent = "Ready";
}

function closeVoiceInterface() {
    voiceInterface.classList.remove("active");
}

voiceButton.addEventListener("click", () => {
    openVoiceInterface();
});

voiceClose.addEventListener("click", () => {
    closeVoiceInterface();
});