import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))

# Railway volume mount (persistent storage across deploys)
# Falls back to local directories for development
volume = os.environ.get('RAILWAY_VOLUME_MOUNT_PATH', basedir)


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(volume, 'data', 'japan_trip.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(volume, 'uploads')
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20MB max upload
    THUMBNAIL_SIZE = (400, 400)
    TRIP_PASSWORD = os.environ.get('TRIP_PASSWORD', 'changeme')

    @classmethod
    def validate_production(cls):
        """Abort startup if insecure defaults are used in a Railway deployment."""
        import sys
        if os.environ.get('RAILWAY_ENVIRONMENT'):
            errors = []
            if cls.SECRET_KEY == 'dev-secret-change-me':
                errors.append('SECRET_KEY is not set')
            # TRIP_PASSWORD check disabled — auth turned off for sharing pre-trip
            # if cls.TRIP_PASSWORD == 'changeme':
            #     errors.append('TRIP_PASSWORD is not set')
            if errors:
                for e in errors:
                    print(f'FATAL: {e} — refusing to start in production with insecure default.', file=sys.stderr)
                sys.exit(1)
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('RAILWAY_ENVIRONMENT') is not None
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours
