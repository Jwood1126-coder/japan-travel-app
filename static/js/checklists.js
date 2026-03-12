// Checklists JS

function scrollToCategory(e, id) {
    e.preventDefault();
    document.getElementById(id).scrollIntoView({ behavior: 'smooth' });
}

// Simple task toggle
async function toggleChecklist(itemId) {
    const item = document.querySelector(`[data-id="${itemId}"]`);
    try {
        const resp = await fetch(`/api/checklists/${itemId}/toggle`, { method: 'POST' });
        const data = await resp.json();
        if (data.ok) {
            item.classList.toggle('completed', data.is_completed);
            showToast(data.is_completed ? 'Done!' : 'Unmarked');
        }
    } catch (err) {
        console.error('Toggle failed:', err);
        showToast('Failed to update', 'error');
    }
}

// ---------- Delete checklist item ----------

async function deleteItem(itemId) {
    if (!confirm('Delete this item?')) return;
    try {
        const resp = await fetch(`/api/checklists/${itemId}`, { method: 'DELETE' });
        const data = await resp.json();
        if (data.ok) {
            const el = document.querySelector(`[data-id="${itemId}"]`);
            if (el) el.remove();
            showToast('Item deleted');
        } else {
            showToast(data.error || 'Cannot delete', 'error');
        }
    } catch (err) {
        console.error('Delete failed:', err);
        showToast('Failed to delete', 'error');
    }
}

// ---------- Add new checklist item ----------

function showAddItem(sectionKey) {
    const section = document.getElementById(`cat-${sectionKey}`);
    if (!section || section.querySelector('.add-item-form')) return;

    let categoryOptions = '';
    if (sectionKey === 'preparation') {
        categoryOptions = '<option value="preparation">Preparation</option>';
    } else if (sectionKey === 'packing') {
        categoryOptions = '<option value="packing_essential">Essential</option>' +
                          '<option value="packing_helpful">Helpful</option>';
    }

    const form = document.createElement('div');
    form.className = 'add-item-form';
    form.innerHTML = `
        <input type="text" placeholder="Item name" class="new-item-title"
               onkeydown="if(event.key==='Enter')submitNewItem('${sectionKey}',this)">
        <select class="new-item-category">${categoryOptions}</select>
        <div class="add-option-form-btns">
            <button onclick="submitNewItem('${sectionKey}', this)" class="select-btn-sm">Add</button>
            <button onclick="this.closest('.add-item-form').remove()" class="eliminate-btn">Cancel</button>
        </div>
    `;
    section.appendChild(form);
    form.querySelector('.new-item-title').focus();
}

async function submitNewItem(sectionKey, el) {
    const form = el.closest('.add-item-form');
    const title = form.querySelector('.new-item-title').value.trim();
    const category = form.querySelector('.new-item-category').value;
    if (!title) return;
    try {
        const resp = await fetch('/api/checklists', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, category })
        });
        if ((await resp.json()).ok) location.reload();
    } catch (err) {
        console.error('Add item failed:', err);
        showToast('Failed to add', 'error');
    }
}

// ---------- Touch gesture initialization ----------
document.addEventListener('DOMContentLoaded', function() {
    if (!window.TouchGestures) return;

    // Swipe-to-complete on task items, swipe-to-delete on deletable items
    document.querySelectorAll('.checklist-section').forEach(section => {
        const sectionKey = (section.id || '').replace('cat-', '');
        const isDeletable = ['preparation', 'packing'].includes(sectionKey);

        section.querySelectorAll('.checklist-item').forEach(item => {
            const isTask = !!item.querySelector('.check-label');
            if (!isTask && !isDeletable) return;

            // Wrap content for swipe
            if (!item.querySelector('.swipe-content')) {
                const content = document.createElement('div');
                content.className = 'swipe-content';
                while (item.firstChild) content.appendChild(item.firstChild);
                item.appendChild(content);
            }

            // Add swipe actions
            if (!item.querySelector('.swipe-actions')) {
                const actions = document.createElement('div');
                actions.className = 'swipe-actions';

                if (isTask) {
                    const btn = document.createElement('button');
                    btn.className = 'swipe-action-btn swipe-complete';
                    btn.innerHTML = '&#10003;';
                    btn.title = 'Toggle complete';
                    btn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        const id = item.dataset.id;
                        if (id) toggleChecklist(parseInt(id));
                        closeSwipeItem(item);
                    });
                    actions.appendChild(btn);
                }

                if (isDeletable) {
                    const delBtn = document.createElement('button');
                    delBtn.className = 'swipe-action-btn swipe-delete';
                    delBtn.innerHTML = '&#x2717;';
                    delBtn.title = 'Delete';
                    delBtn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        const id = item.dataset.id;
                        if (id) deleteItem(parseInt(id));
                        closeSwipeItem(item);
                    });
                    actions.appendChild(delBtn);
                }

                item.appendChild(actions);
                item.classList.add('swipe-enabled');
            }
        });

        // Init swipe on the section
        TouchGestures.initSwipeActions(section, {
            itemSelector: '.checklist-item.swipe-enabled',
            actions: [] // Already added manually
        });
    });

    function closeSwipeItem(item) {
        const content = item.querySelector('.swipe-content');
        if (content) {
            content.style.transition = 'transform 0.25s ease';
            content.style.transform = 'translateX(0)';
        }
        item.classList.remove('swipe-open');
    }
});
