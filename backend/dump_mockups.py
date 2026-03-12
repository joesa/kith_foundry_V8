import os
import sys

# Add backend directory to sys.path so we can import models
sys.path.append("/home/joe/repos/kith_foundry_V8/backend")

from models import SessionLocal, DesignMockup

def main():
    db = SessionLocal()
    project_id = "ade41a8a-2e00-4750-8d4f-e42f617d4255"
    mockups = db.query(DesignMockup).filter(DesignMockup.project_id == project_id).all()
    for m in mockups:
        print(f"Mockup: {m.screen_name}, Status: {m.status}, Code Preview: {(m.component_code or '')[:100]}")

if __name__ == "__main__":
    main()
