import asyncio
import sys

sys.path.append("/home/joe/repos/kith_foundry_V8/backend")

from design_api import _generate_all_mockups_ai_free

async def main():
    project_id = "ade41a8a-2e00-4750-8d4f-e42f617d4255" # AirScribe
    await _generate_all_mockups_ai_free(project_id)
    print("Done generating mockups for AirScribe")

if __name__ == "__main__":
    asyncio.run(main())
