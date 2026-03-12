import os
import sys

# Add backend directory to sys.path so we can import models
sys.path.append("/home/joe/repos/kith_foundry_V8/backend")

from models import SessionLocal, DesignMockup

def main():
    db = SessionLocal()
    # Get the most recently updated mockup
    mockup = db.query(DesignMockup).order_by(DesignMockup.updated_at.desc()).first()
    if not mockup:
        print("No mockups found")
        return
    print(f"Mockup ID: {mockup.id}")
    print(f"Project ID: {mockup.project_id}")
    print(f"Screen: {mockup.screen_name}")
    print("="*40)
    print(mockup.prompt or "No prompt stored")

if __name__ == "__main__":
    main()
