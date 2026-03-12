import sys
sys.path.append("/home/joe/repos/kith_foundry_V8/backend")
from models import SessionLocal, Artifact

db = SessionLocal()
PROJECT_ID = "ade41a8a-2e00-4750-8d4f-e42f617d4255"

artifact = db.query(Artifact).filter(Artifact.project_id == PROJECT_ID, Artifact.artifact_type == "design_system").first()
if artifact:
    text = artifact.content.get("text", "")
    print("--- TEXT CONTENT ---")
    print(text[-1000:])
    print("--- END TEXT ---")
else:
    print("No artifact found.")
