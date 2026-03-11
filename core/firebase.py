import firebase_admin
from django.conf import settings
from firebase_admin import credentials, db, firestore


def initialize_firebase():
    """Initialize Firebase app once and reuse in the process."""
    if firebase_admin._apps:
        return firebase_admin.get_app()

    options = {}
    if getattr(settings, 'FIREBASE_DATABASE_URL', ''):
        options['databaseURL'] = settings.FIREBASE_DATABASE_URL

    cred_path = getattr(settings, 'FIREBASE_CREDENTIALS_PATH', '')
    if not cred_path:
        raise RuntimeError('FIREBASE_CREDENTIALS_PATH is not configured')

    cred = credentials.Certificate(cred_path)
    return firebase_admin.initialize_app(cred, options)


def get_firestore_client():
    initialize_firebase()
    return firestore.client()


def get_realtime_db_ref(path='/'):
    initialize_firebase()
    return db.reference(path)
