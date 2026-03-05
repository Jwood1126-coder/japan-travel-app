// Chat JS

const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addBubble(role, text) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;
    const content = document.createElement('div');
    content.className = 'bubble-content';
    content.textContent = text;
    bubble.appendChild(content);
    chatMessages.appendChild(bubble);
    scrollToBottom();
    return content;
}

function sendQuickPrompt(btn) {
    chatInput.value = btn.textContent;
    sendMessage();
}

async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    chatInput.value = '';
    chatInput.disabled = true;

    // Remove welcome if present
    const welcome = document.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    // Add user bubble
    addBubble('user', text);

    // Add assistant bubble (empty, will stream into it)
    const assistantContent = addBubble('assistant', '');

    try {
        const response = await fetch('/api/chat/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.text) {
                            assistantContent.textContent += data.text;
                            scrollToBottom();
                        }
                        if (data.error) {
                            assistantContent.textContent = 'Error: ' + data.error;
                        }
                    } catch (e) {
                        // Ignore parse errors on partial chunks
                    }
                }
            }
        }
    } catch (err) {
        assistantContent.textContent = 'Connection error. Please try again.';
    }

    chatInput.disabled = false;
    chatInput.focus();
}

// Scroll to bottom on load
scrollToBottom();
