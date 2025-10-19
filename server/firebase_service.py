
import os
import firebase_admin
from firebase_admin import credentials, storage, firestore
from datetime import datetime
from typing import Dict

# ---- configure these ----
FIREBASE_SERVICE_JSON = os.environ.get("FIREBASE_SERVICE_JSON", "firebase-service-account.json")
FIREBASE_BUCKET = os.environ.get("FIREBASE_BUCKET", "auth-view-f0237.firebasestorage.app")


# -------------------------

_app = None
_db = None
_bucket = None

def init_firebase():
    global _app, _db, _bucket
    if _app:
        return
    cred = credentials.Certificate(FIREBASE_SERVICE_JSON)
    _app = firebase_admin.initialize_app(cred, {"storageBucket": FIREBASE_BUCKET})
    _db = firestore.client()
    _bucket = storage.bucket()

def get_db():
    init_firebase()
    return _db

def get_bucket():
    init_firebase()
    return _bucket

def upload_file(local_path: str, dest_path: str) -> str:
    """
    Uploads a file to Cloud Storage and returns a signed URL (long-lived).
    """
    bucket = get_bucket()
    blob = bucket.blob(dest_path)
    blob.upload_from_filename(local_path, content_type="video/mp4")
    # Make public or use signed URL—choose one:
    blob.make_public()
    return blob.public_url  # or blob.generate_signed_url(datetime.utcnow()+timedelta(days=7))

def save_record_metadata(data: Dict) -> str:
    """
    Writes a Firestore document under 'recordings'.
    """
    db = get_db()
    doc_ref = db.collection("recordings").add(data)[1]  # add returns (update, ref)
    return doc_ref.id
