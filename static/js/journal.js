// Journal JS

async function quickUpload(files) {
    if (!files || files.length === 0) return;

    const dayId = document.getElementById('quickDaySelect').value;
    const form = new FormData();
    form.append('day_id', dayId);
    for (const f of files) {
        form.append('photos', f);
    }

    try {
        const resp = await fetch('/api/photos/upload', {
            method: 'POST',
            body: form
        });
        const data = await resp.json();
        if (data.length > 0) {
            location.reload();
        }
    } catch (err) {
        console.error('Upload failed:', err);
    }
}

function viewPhoto(id, filename) {
    const viewer = document.getElementById('photoViewer');
    const img = document.getElementById('photoViewerImg');
    img.src = '/photos/originals/' + filename;
    viewer.style.display = 'flex';
}

function closePhotoViewer() {
    document.getElementById('photoViewer').style.display = 'none';
}

// Close on escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closePhotoViewer();
});
