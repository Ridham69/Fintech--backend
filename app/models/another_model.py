# app/models/another_model.py

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class AnotherModel(Base):
    __tablename__ = 'another_model'
    id = Column(Integer, primary_key=True)
    description = Column(String)
    meta_data = Column(String, name='metadata')  # Renamed attribute, DB column is still 'metadata'
