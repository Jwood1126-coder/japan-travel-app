"""Budget mutation service — single canonical write path.

Every mutation follows: validate → normalize → write → cascade → emit.
Both UI routes and AI chat tools call these functions.
"""
from models import db, BudgetItem
from guardrails import validate_non_negative
from extensions import socketio


def _strip_or_none(value):
    """Strip whitespace from string, return None if empty."""
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip()
        return v if v else None
    return value


def _emit_budget_updated():
    """Emit Socket.IO event for any budget change."""
    socketio.emit('budget_updated', {})


def record_expense(budget_item_id, amount, notes=None):
    """Record an actual expense against a budget item.

    Adds the amount to the item's running actual_amount total.

    Args:
        budget_item_id: BudgetItem record ID
        amount: Non-negative expense amount to add
        notes: Optional note to append

    Returns:
        Updated BudgetItem object

    Raises:
        ValueError: if amount is negative
    """
    item = BudgetItem.query.get_or_404(budget_item_id)

    amount = validate_non_negative(amount, 'actual_amount')
    item.actual_amount = (item.actual_amount or 0) + amount

    note_text = _strip_or_none(notes)
    if note_text:
        existing = _strip_or_none(item.notes)
        item.notes = f"{existing}\n{note_text}" if existing else note_text

    db.session.commit()
    _emit_budget_updated()
    return item
