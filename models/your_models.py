from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ExampleModel(Base):
    __tablename__ = 'example_model'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    meta_data = Column(JSON, name='metadata')  # Renamed attribute, DB column is still 'metadata'

class AnotherModel(Base):
    __tablename__ = 'another_model'
    id = Column(Integer, primary_key=True)
    description = Column(String)
    meta_data = Column(String, name='metadata')  # Renamed attribute, DB column is still 'metadata'