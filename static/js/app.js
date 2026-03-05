// Japan Travel Assistant - Core JS

// Socket.IO connection
const socket = io({ transports: ['websocket', 'polling'] });

socket.on('connect', () => console.log('Connected to server'));
socket.on('disconnect', () => console.log('Disconnected'));

// More menu
function toggleMore(e) {
    e.preventDefault();
    document.getElementById('moreMenu').classList.toggle('open');
}

function closeMore() {
    document.getElementById('moreMenu').classList.remove('open');
}

// Dark mode
function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    closeMore();
}

// Restore theme on load
(function() {
    const saved = localStorage.getItem('theme');
    if (saved) {
        document.documentElement.setAttribute('data-theme', saved);
    }
})();

// Swipe navigation for day view
let touchStartX = 0;
let touchStartY = 0;

document.addEventListener('touchstart', function(e) {
    touchStartX = e.changedTouches[0].screenX;
    touchStartY = e.changedTouches[0].screenY;
}, { passive: true });

document.addEventListener('touchend', function(e) {
    const dx = e.changedTouches[0].screenX - touchStartX;
    const dy = e.changedTouches[0].screenY - touchStartY;

    // Only horizontal swipe, not vertical scroll
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        // Check if we're on a day page
        const prevBtn = document.querySelector('.day-nav-btn:first-child');
        const nextBtn = document.querySelector('.day-nav-btn:last-child');

        if (dx > 0 && prevBtn && !prevBtn.classList.contains('disabled')) {
            prevBtn.click();
        } else if (dx < 0 && nextBtn && !nextBtn.classList.contains('disabled')) {
            nextBtn.click();
        }
    }
}, { passive: true });

// Real-time sync handlers
socket.on('activity_toggled', function(data) {
    const card = document.querySelector(`[data-id="${data.id}"]`);
    if (card) {
        const checkbox = card.querySelector('input[type="checkbox"]');
        if (checkbox) checkbox.checked = data.is_completed;
        card.classList.toggle('completed', data.is_completed);
    }
});

socket.on('checklist_toggled', function(data) {
    const item = document.querySelector(`[data-id="${data.id}"]`);
    if (item) {
        const checkbox = item.querySelector('input[type="checkbox"]');
        if (checkbox) checkbox.checked = data.is_completed;
        item.classList.toggle('completed', data.is_completed);
    }
});

socket.on('accommodation_updated', function(data) {
    // Refresh the page to show updated state
    if (window.location.pathname === '/accommodations') {
        location.reload();
    }
});

socket.on('journal_updated', function(data) {
    if (window.location.pathname === '/journal') {
        location.reload();
    }
});
