from sqlalchemy import Column, Integer, String, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ExampleModel(Base):
    __tablename__ = 'example_model'
    id = Column(Integer, primary_key=True)
    name = Column(String)  # From original file
    description = Column(String)  # From duplicate
    meta_data = Column(JSON, name='metadata')  # From duplicate
