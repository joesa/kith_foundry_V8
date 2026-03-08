"""
Verify AES-256-GCM encryption on all rows in the provider_keys table.

Usage:
    cd backend && venv/Scripts/python.exe check_encryption.py

Output:
    - Raw encrypted blob from the DB (should start with "gcm:")
    - Whether it decrypts successfully
    - First 8 chars of the plaintext key (so you can match it visually)
"""
import os, sys
from dotenv import load_dotenv
load_dotenv()

# Fix postgres:// scheme before importing models
db_url = os.environ.get("DATABASE_URL", "")
if db_url.startswith("postgres://"):
    os.environ["DATABASE_URL"] = db_url.replace("postgres://", "postgresql://", 1)

from sqlalchemy.orm import Session
from models import ProviderKey, engine
from provider_api import decrypt_key


with Session(engine) as db:
    rows = db.query(ProviderKey).all()

if not rows:
    print("No provider_keys rows in the database yet.")
    print("Add a key via the UI, then re-run this script.")
    sys.exit(0)

print(f"Found {len(rows)} provider key(s):\n")
all_ok = True
for row in rows:
    enc = row.api_key_encrypted or ""
    fmt = "gcm ✓" if enc.startswith("gcm:") else "UNKNOWN FORMAT ✗"
    try:
        plain = decrypt_key(enc)
        preview = plain[:4] + "..." + plain[-4:] if len(plain) >= 8 else plain
        status = f"Decrypts OK → {preview}"
    except Exception as e:
        status = f"DECRYPT FAILED: {e}"
        all_ok = False

    print(f"  user_id  : {row.user_id}")
    print(f"  provider : {row.provider}")
    print(f"  format   : {fmt}")
    print(f"  blob     : {enc[:40]}...")
    print(f"  result   : {status}")
    print()

if all_ok:
    print("✓ All keys encrypted with AES-256-GCM and decrypt correctly.")
else:
    print("✗ Some keys failed — check PROVIDER_ENCRYPTION_KEY in .env")
