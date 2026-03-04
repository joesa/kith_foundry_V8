"""Quick script to create all DB tables."""
from models import Base, engine
Base.metadata.create_all(bind=engine)
print("All tables created successfully")
