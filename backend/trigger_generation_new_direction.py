import asyncio
import sys

# Add backend directory to sys.path so we can import models and API
sys.path.append("/home/joe/repos/kith_foundry_V8/backend")

from models import SessionLocal, Project
from design_api import _generate_all_mockups_ai_free

# AirScribe Project ID
PROJECT_ID = "ade41a8a-2e00-4750-8d4f-e42f617d4255"

async def test_generation():
    db = SessionLocal()
    
    # ensure project exists
    project = db.query(Project).filter(Project.id == PROJECT_ID).first()
    if not project:
        print("Project not found.")
        return

    # Call AI free generation with NEW DIRECTION
    print("Triggering generation...")
    await _generate_all_mockups_ai_free(
        project_id=PROJECT_ID,
        direction="Sleek and Modern Corporate",
        reference_images=None
    )
    print("Generation complete!")

if __name__ == "__main__":
    asyncio.run(test_generation())
