from flask import Blueprint, render_template, jsonify
from models import db, ChecklistItem
from datetime import datetime

checklists_bp = Blueprint('checklists', __name__)


@checklists_bp.route('/checklists')
def checklists_view():
    items = ChecklistItem.query.order_by(ChecklistItem.sort_order).all()
    # Group by category
    categories = {}
    for item in items:
        categories.setdefault(item.category, []).append(item)
    return render_template('checklists.html', categories=categories)


@checklists_bp.route('/api/checklists/<int:item_id>/toggle', methods=['POST'])
def toggle_checklist(item_id):
    item = ChecklistItem.query.get_or_404(item_id)
    item.is_completed = not item.is_completed
    item.completed_at = datetime.utcnow() if item.is_completed else None
    db.session.commit()

    from app import socketio
    socketio.emit('checklist_toggled', {
        'id': item.id,
        'is_completed': item.is_completed,
    })

    return jsonify({'ok': True, 'is_completed': item.is_completed})
