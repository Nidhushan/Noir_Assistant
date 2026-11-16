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
    if (!message.trim()) {
        return;
    }

    const userMessageElement = displayMessage("user", message, "pending");
    messageInput.value = "";
    sendButton.disabled = true;

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
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
        
        const data = await response.json();
        currentConversationId = data.conversation_id;
        localStorage.setItem("noir_conversation_id", currentConversationId);
        loadConversations();

        // const reply = data.received_message;
        // const assistantMessage = document.createElement("div");
        // assistantMessage.classList.add("message", "assistant-message");
        // assistantMessage.textContent = reply;
        // chatMessages.appendChild(assistantMessage);
        displayMessage("assistant", data.received_message);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    catch (error) {
        console.error("Error:", error.message);

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