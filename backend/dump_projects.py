import os
import sys

# Add backend directory to sys.path so we can import models
sys.path.append("/home/joe/repos/kith_foundry_V8/backend")

from models import SessionLocal, Project

def main():
    db = SessionLocal()
    projects = db.query(Project).all()
    if not projects:
        print("No projects found")
        return
    for p in projects:
        print(f"Project ID: {p.id}")
        print(f"Name: {p.name}")
        print(f"Desc: {p.description}")
        print("="*40)

if __name__ == "__main__":
    main()
