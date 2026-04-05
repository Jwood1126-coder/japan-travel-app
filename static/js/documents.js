// Search/filter documents
function filterDocs(query) {
    const q = query.toLowerCase().trim();
    const items = document.querySelectorAll('.searchable');
    const sections = document.querySelectorAll('.searchable-section');

    if (!q) {
        // Show everything
        items.forEach(el => el.style.display = '');
        sections.forEach(s => {
            s.style.display = '';
            // Restore original open state
            if (s.dataset.wasOpen !== undefined) {
                s.open = s.dataset.wasOpen === 'true';
                delete s.dataset.wasOpen;
            }
        });
        return;
    }

    items.forEach(el => {
        const searchText = el.getAttribute('data-search') || el.textContent.toLowerCase();
        el.style.display = searchText.includes(q) ? '' : 'none';
    });

    // Auto-open sections that have visible results, hide empty ones
    sections.forEach(s => {
        const visibleItems = s.querySelectorAll('.searchable:not([style*="display: none"])');
        if (visibleItems.length === 0) {
            s.style.display = 'none';
        } else {
            s.style.display = '';
            if (s.dataset.wasOpen === undefined) {
                s.dataset.wasOpen = s.open;
            }
            s.open = true;
        }
    });
}

function updateFlightConfirmation(flightId, value) {
    fetch(`/api/documents/flight/${flightId}/confirmation`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_number: value }),
    });
}

function updateFlightStatus(flightId, status) {
    fetch(`/api/documents/flight/${flightId}/confirmation`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ booking_status: status }),
    }).then(r => r.json()).then(() => {
        const card = document.querySelector(`[data-flight-id="${flightId}"]`);
        if (!card) return;
        let badge = card.querySelector('.booking-badge');
        if (status === 'not_booked') {
            if (badge) badge.remove();
        } else {
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'booking-badge';
                card.querySelector('.flight-card-header').appendChild(badge);
            }
            badge.className = `booking-badge ${status}`;
            badge.textContent = status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        }
    });
}

async function uploadDocument(input) {
    const file = input.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const resp = await fetch('/api/documents/upload', {
            method: 'POST',
            body: formData,
        });
        const data = await resp.json();
        if (data.ok) {
            showToast('Document uploaded');
            location.reload();
        } else {
            showToast(data.error || 'Upload failed', 'error');
        }
    } catch (err) {
        showToast('Upload failed', 'error');
    }
    input.value = '';
}

async function deleteDocument(filename) {
    if (!confirm('Delete this document?')) return;
    try {
        const resp = await fetch(`/api/documents/file/${filename}`, { method: 'DELETE' });
        const data = await resp.json();
        if (data.ok) {
            const row = document.querySelector(`[data-filename="${filename}"]`);
            if (row) row.remove();
            showToast('Document deleted');
        } else {
            showToast(data.error || 'Delete failed', 'error');
        }
    } catch (err) {
        showToast('Delete failed', 'error');
    }
}
