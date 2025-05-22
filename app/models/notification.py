from sqlalchemy import Column, Integer, String, JSON
from app.db.base_class import Base

class Notification(Base):
    __tablename__ = "notification"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(String)
    meta_info = Column(JSON, name="metadata")  # Renamed attribute, DB column is still 'metadata'
