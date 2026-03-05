// Chat JS

const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
let selectedImage = null;

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addBubble(role, text, imageUrl) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${role}`;

    if (imageUrl) {
        const img = document.createElement('img');
        img.src = imageUrl;
        img.className = 'chat-image';
        img.onclick = () => window.open(imageUrl.replace('/thumbnails/thumb_', '/originals/').replace('.jpg', ''));
        bubble.appendChild(img);
    }

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

function handleImageSelect(input) {
    if (input.files && input.files[0]) {
        selectedImage = input.files[0];
        const reader = new FileReader();
        reader.onload = (e) => {
            document.getElementById('previewImg').src = e.target.result;
            document.getElementById('imagePreview').style.display = 'flex';
        };
        reader.readAsDataURL(selectedImage);
    }
}

function clearImage() {
    selectedImage = null;
    document.getElementById('chatImageInput').value = '';
    document.getElementById('imagePreview').style.display = 'none';
    document.getElementById('previewImg').src = '';
}

async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text && !selectedImage) return;

    chatInput.value = '';
    chatInput.disabled = true;
    document.getElementById('sendBtn').disabled = true;

    // Remove welcome if present
    const welcome = document.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    // Add user bubble with optional image preview
    const imagePreviewUrl = selectedImage ? document.getElementById('previewImg').src : null;
    addBubble('user', text || 'Analyzing document...', imagePreviewUrl);

    // Hide image preview
    if (selectedImage) {
        document.getElementById('imagePreview').style.display = 'none';
    }

    // Add assistant bubble (empty, will stream into it)
    const assistantContent = addBubble('assistant', '');

    try {
        let response;

        if (selectedImage) {
            // Multipart form upload
            const formData = new FormData();
            formData.append('message', text);
            formData.append('image', selectedImage);
            selectedImage = null;
            document.getElementById('chatImageInput').value = '';

            response = await fetch('/api/chat/send', {
                method: 'POST',
                body: formData,
            });
        } else {
            response = await fetch('/api/chat/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text }),
            });
        }

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
                        if (data.processing) {
                            // Show processing status
                            const proc = document.createElement('div');
                            proc.className = 'processing-indicator';
                            proc.textContent = data.processing;
                            assistantContent.parentNode.insertBefore(proc, assistantContent);
                            scrollToBottom();
                        }
                        if (data.error) {
                            assistantContent.textContent = 'Error: ' + data.error;
                        }
                        if (data.done) {
                            // Remove processing indicators
                            document.querySelectorAll('.processing-indicator').forEach(el => el.remove());
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
    document.getElementById('sendBtn').disabled = false;
    chatInput.focus();
}

// Scroll to bottom on load
scrollToBottom();
