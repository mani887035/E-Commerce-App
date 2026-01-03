/**
 * ShopSmart - Main JavaScript
 * Handles chatbot, favorites, and global functionality
 */

// ==========================================
// CHATBOT FUNCTIONALITY
// ==========================================

const chatWidget = document.getElementById('chatWidget');
const chatToggle = document.getElementById('chatToggle');
const chatWindow = document.getElementById('chatWindow');
const chatClose = document.getElementById('chatClose');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const chatSend = document.getElementById('chatSend');

let pendingOrder = null;

// Toggle chat window
if (chatToggle) {
    chatToggle.addEventListener('click', () => {
        chatWindow.classList.toggle('open');
        if (chatWindow.classList.contains('open')) {
            chatInput.focus();
        }
    });
}

if (chatClose) {
    chatClose.addEventListener('click', () => {
        chatWindow.classList.remove('open');
    });
}

// Send message
async function sendMessage(message) {
    if (!message.trim()) return;

    // Add user message to chat
    addMessage(message, 'user');
    chatInput.value = '';

    // Show typing indicator
    const typingId = showTyping();

    try {
        // Check if this is a confirmation for pending order
        if (pendingOrder && isConfirmation(message)) {
            await confirmPendingOrder();
        } else if (pendingOrder && isRejection(message)) {
            removeTyping(typingId);
            addMessage("No problem! Let me know if you'd like to order something else.", 'bot');
            pendingOrder = null;
        } else {
            // Send to chatbot API
            const response = await fetch('/chat/message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            removeTyping(typingId);

            if (data.success) {
                addMessage(data.response, 'bot');

                // Check if there are product suggestions for ordering
                if (data.action === 'order_intent' && data.sources && data.sources.length > 0) {
                    showOrderSuggestions(data.sources);
                }
            } else {
                addMessage("I'm sorry, I couldn't process your message. Please try again.", 'bot');
            }
        }
    } catch (error) {
        removeTyping(typingId);
        addMessage("I'm having trouble connecting. Please try again later.", 'bot');
        console.error('Chat error:', error);
    }
}

function addMessage(text, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;
    messageDiv.textContent = text;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTyping() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'chat-message bot typing';
    typingDiv.id = 'typing-' + Date.now();
    typingDiv.innerHTML = `
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
    `;
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return typingDiv.id;
}

function removeTyping(id) {
    const typingDiv = document.getElementById(id);
    if (typingDiv) typingDiv.remove();
}

function showOrderSuggestions(products) {
    const uniqueProducts = products.filter((p, i, arr) =>
        arr.findIndex(x => x.product_id === p.product_id) === i
    ).slice(0, 3);

    if (uniqueProducts.length === 0) return;

    const suggestionsDiv = document.createElement('div');
    suggestionsDiv.className = 'chat-message bot';
    suggestionsDiv.innerHTML = `
        <p style="margin-bottom: 8px;">Would you like to order any of these?</p>
        <div style="display: flex; flex-direction: column; gap: 8px;">
            ${uniqueProducts.map(p => `
                <button class="btn btn-secondary btn-sm order-product-btn" 
                        data-id="${p.product_id}" data-name="${p.name}" data-price="${p.price}"
                        style="text-align: left; justify-content: space-between;">
                    <span>${p.name}</span>
                    <span>₹${Math.round(p.price)}</span>
                </button>
            `).join('')}
        </div>
    `;
    chatMessages.appendChild(suggestionsDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Add click handlers
    suggestionsDiv.querySelectorAll('.order-product-btn').forEach(btn => {
        btn.addEventListener('click', () => initiateOrder(btn.dataset));
    });
}

async function initiateOrder(productData) {
    const typingId = showTyping();

    try {
        const response = await fetch('/chat/order-verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_ids: [parseInt(productData.id)],
                quantities: [1],
                confirm: false
            })
        });

        const data = await response.json();
        removeTyping(typingId);

        if (data.success) {
            addMessage(data.message, 'bot');

            if (data.action === 'pending_confirmation') {
                pendingOrder = {
                    product_ids: data.product_ids,
                    quantities: data.quantities
                };

                // Add confirmation buttons
                const confirmDiv = document.createElement('div');
                confirmDiv.className = 'chat-message bot';
                confirmDiv.innerHTML = `
                    <div style="display: flex; gap: 8px; margin-top: 8px;">
                        <button class="btn btn-success btn-sm" id="confirmOrderBtn">Yes, confirm</button>
                        <button class="btn btn-secondary btn-sm" id="cancelOrderBtn">No, cancel</button>
                    </div>
                `;
                chatMessages.appendChild(confirmDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;

                document.getElementById('confirmOrderBtn').addEventListener('click', confirmPendingOrder);
                document.getElementById('cancelOrderBtn').addEventListener('click', () => {
                    addMessage("Order cancelled. Let me know if you need anything else!", 'bot');
                    pendingOrder = null;
                });
            }
        }
    } catch (error) {
        removeTyping(typingId);
        addMessage("Sorry, I couldn't process that order. Please try again.", 'bot');
    }
}

async function confirmPendingOrder() {
    if (!pendingOrder) return;

    const typingId = showTyping();

    try {
        const response = await fetch('/chat/order-verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                product_ids: pendingOrder.product_ids,
                quantities: pendingOrder.quantities,
                confirm: true
            })
        });

        const data = await response.json();
        removeTyping(typingId);

        if (data.success) {
            addMessage(data.message, 'bot');
            pendingOrder = null;
        } else {
            addMessage(data.message || "Sorry, there was an issue with your order.", 'bot');
        }
    } catch (error) {
        removeTyping(typingId);
        addMessage("Sorry, I couldn't complete your order. Please try again.", 'bot');
    }
}

function isConfirmation(message) {
    const confirmWords = ['yes', 'confirm', 'ok', 'okay', 'sure', 'proceed', 'do it', 'place order', 'yep', 'yeah'];
    return confirmWords.some(word => message.toLowerCase().includes(word));
}

function isRejection(message) {
    const rejectWords = ['no', 'cancel', 'stop', 'nevermind', 'never mind', 'nope', 'nah', "don't"];
    return rejectWords.some(word => message.toLowerCase().includes(word));
}

// Event listeners
if (chatSend) {
    chatSend.addEventListener('click', () => sendMessage(chatInput.value));
}

if (chatInput) {
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage(chatInput.value);
    });
}

// Global function to open chat with a message
window.openChatWithMessage = function (message) {
    if (chatWindow) {
        chatWindow.classList.add('open');
        setTimeout(() => {
            sendMessage(message);
        }, 300);
    }
};

// ==========================================
// FAVORITES FUNCTIONALITY
// ==========================================

document.querySelectorAll('.product-favorite').forEach(btn => {
    btn.addEventListener('click', async function (e) {
        e.preventDefault();
        e.stopPropagation();

        const productId = this.dataset.productId;

        try {
            const response = await fetch(`/products/${productId}/favorite`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const data = await response.json();

            if (data.success) {
                if (data.action === 'added') {
                    this.classList.add('active');
                    this.innerHTML = '❤️';
                } else {
                    this.classList.remove('active');
                    this.innerHTML = '🤍';
                }
            }
        } catch (error) {
            console.error('Error toggling favorite:', error);
        }
    });
});

// ==========================================
// INITIALIZATION
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialize RAG service in background
    fetch('/chat/init', { method: 'POST' })
        .then(res => res.json())
        .then(data => console.log('RAG service:', data.message))
        .catch(err => console.log('RAG init skipped'));
});
