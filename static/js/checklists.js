// Checklists JS

function scrollToCategory(e, id) {
    e.preventDefault();
    document.getElementById(id).scrollIntoView({ behavior: 'smooth' });
}

async function toggleChecklist(itemId) {
    const item = document.querySelector(`[data-id="${itemId}"]`);
    try {
        const resp = await fetch(`/api/checklists/${itemId}/toggle`, {
            method: 'POST'
        });
        const data = await resp.json();
        if (data.ok) {
            item.classList.toggle('completed', data.is_completed);
        }
    } catch (err) {
        console.error('Toggle failed:', err);
    }
}
