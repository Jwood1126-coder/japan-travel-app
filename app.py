import os
from flask import Flask, redirect, url_for, session, request, render_template
from flask_socketio import SocketIO
from config import Config
from models import db

socketio = SocketIO()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    allowed = os.environ.get('CORS_ORIGINS', '*')
    socketio.init_app(app, cors_allowed_origins=allowed, async_mode='eventlet')

    # Register blueprints
    from blueprints.itinerary import itinerary_bp
    from blueprints.accommodations import accommodations_bp
    from blueprints.checklists import checklists_bp
    from blueprints.journal import journal_bp
    from blueprints.chat import chat_bp
    from blueprints.reference import reference_bp

    app.register_blueprint(itinerary_bp)
    app.register_blueprint(accommodations_bp)
    app.register_blueprint(checklists_bp)
    app.register_blueprint(journal_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(reference_bp)

    # Auth routes
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        error = None
        if request.method == 'POST':
            if request.form.get('password') == app.config['TRIP_PASSWORD']:
                session['authenticated'] = True
                return redirect(url_for('itinerary.index'))
            error = 'Wrong password'
        return render_template('login.html', error=error)

    @app.route('/logout')
    def logout():
        session.pop('authenticated', None)
        return redirect(url_for('login'))

    @app.before_request
    def check_auth():
        allowed = ['login', 'static']
        if request.endpoint and any(request.endpoint.startswith(a) for a in allowed):
            return
        if not session.get('authenticated'):
            return redirect(url_for('login'))

    # Ensure upload directories exist
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'originals'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails'), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)

    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
