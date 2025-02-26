from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData

# Create base class for declarative models
Base = declarative_base()

# Initialize metadata
metadata = MetaData()
