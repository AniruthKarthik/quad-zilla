const chatMessages = document.getElementById("chatMessages");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const typingIndicator = document.getElementById("typingIndicator");

function addMessage(message, isUser = false) {
  const messageDiv = document.createElement("div");
  messageDiv.classList.add("message");
  messageDiv.classList.add(isUser ? "user-message" : "bot-message");
  messageDiv.textContent = message;

  chatMessages.appendChild(messageDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTypingIndicator() {
  typingIndicator.style.display = "block";
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
  typingIndicator.style.display = "none";
}

async function sendMessage() {
  const message = messageInput.value.trim();
  if (!message) return;

  addMessage(message, true);
  messageInput.value = "";
  sendButton.disabled = true;

  showTypingIndicator();

  try {
    const response = await fetch("http://127.0.0.1:8000/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text: message }),
    });

    if (!response.ok) {
      throw new Error("Network response was not ok");
    }

    const data = await response.json();

    hideTypingIndicator();

    if (data.agent_role === "Default chatbot") {
      addMessage(data.reply, false);
    } else {
      let page = "";
      if (data.agent_role === "Search") {
        page = "search.html";
      } else if (data.agent_role === "Practice Problem Generator") {
        page = "practice.html";
      } else if (data.agent_role === "Tutor") {
        page = "tutor.html";
      }

      if (page) {
        window.location.href = `${page}?q=${encodeURIComponent(data.task_description)}`;
      }
    }
  } catch (error) {
    hideTypingIndicator();
    addMessage(
      "Sorry, I'm having trouble processing your message. Please try again.",
      false,
    );
    console.error("Error:", error);
  }

  sendButton.disabled = false;
}

// Event listeners
sendButton.addEventListener("click", sendMessage);

messageInput.addEventListener("keypress", function (e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

messageInput.addEventListener("input", function () {
  sendButton.disabled = this.value.trim().length === 0;
});

// Initialize
sendButton.disabled = true;
