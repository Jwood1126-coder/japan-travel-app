from flask import Blueprint, render_template, jsonify, request, Response, \
    current_app
from models import db, ChatMessage, Day, Activity, AccommodationOption
from datetime import date, datetime
import json

chat_bp = Blueprint('chat', __name__)

SYSTEM_PROMPT = """You are a Japan travel assistant for Jake and his wife \
(both 33, from Cleveland, OH) on a 15-day cherry blossom trip, April 4-18, \
2026. You have deep knowledge of Japan: restaurants, etiquette, transit, \
language, hidden gems. Be concise — they're reading this on a phone. \
Give specific, actionable answers. When suggesting schedule changes, \
explain clearly what to add, remove, or move."""


@chat_bp.route('/chat')
def chat_view():
    messages = ChatMessage.query.order_by(ChatMessage.created_at).all()
    return render_template('chat.html', messages=messages)


@chat_bp.route('/api/chat/send', methods=['POST'])
def send_message():
    api_key = current_app.config.get('ANTHROPIC_API_KEY', '')
    if not api_key or api_key == 'sk-ant-your-key-here':
        return jsonify({'error': 'API key not configured. '
                        'Set ANTHROPIC_API_KEY in .env'}), 400

    data = request.get_json()
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    # Save user message
    user_msg = ChatMessage(role='user', content=user_message)
    db.session.add(user_msg)
    db.session.commit()

    # Build context
    context = _build_context()

    # Get recent chat history
    history = ChatMessage.query.order_by(
        ChatMessage.created_at.desc()).limit(20).all()
    history.reverse()
    messages = [{'role': m.role, 'content': m.content} for m in history]

    def generate():
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            full_response = ''
            with client.messages.stream(
                model='claude-sonnet-4-5-20250929',
                max_tokens=1024,
                system=SYSTEM_PROMPT + '\n\n' + context,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    yield f"data: {json.dumps({'text': text})}\n\n"

            # Save assistant response
            assistant_msg = ChatMessage(role='assistant', content=full_response)
            db.session.add(assistant_msg)
            db.session.commit()

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


@chat_bp.route('/api/chat/history')
def chat_history():
    messages = ChatMessage.query.order_by(
        ChatMessage.created_at.desc()).limit(50).all()
    messages.reverse()
    return jsonify([{
        'role': m.role,
        'content': m.content,
        'created_at': m.created_at.isoformat() if m.created_at else None,
    } for m in messages])


def _build_context():
    """Build dynamic context about the current trip state."""
    parts = []
    today = date.today()

    # Current day info
    current_day = Day.query.filter(Day.date == today).first()
    if current_day:
        parts.append(f"TODAY is Day {current_day.day_number} "
                     f"({current_day.date.strftime('%B %d')}): "
                     f"{current_day.title}")
        activities = Activity.query.filter_by(day_id=current_day.id).order_by(
            Activity.sort_order).all()
        if activities:
            parts.append("Today's activities:")
            for a in activities:
                status = '[DONE]' if a.is_completed else '[ ]'
                parts.append(f"  {status} {a.title} ({a.time_slot or ''})")

    # Tomorrow
    from datetime import timedelta
    tomorrow = today + timedelta(days=1)
    next_day = Day.query.filter(Day.date == tomorrow).first()
    if next_day:
        parts.append(f"\nTOMORROW is Day {next_day.day_number}: "
                     f"{next_day.title}")

    # Current accommodation
    from models import AccommodationLocation
    accom = AccommodationOption.query.filter_by(is_selected=True).all()
    if accom:
        parts.append("\nBooked accommodations:")
        for a in accom:
            loc = AccommodationLocation.query.get(a.location_id)
            parts.append(f"  {loc.location_name}: {a.name} "
                         f"({a.booking_status})")

    return '\n'.join(parts) if parts else 'Trip has not started yet.'
