from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, JSON

Base = declarative_base()

class MyModel(Base):
    __tablename__ = 'my_model'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    meta_info = Column(JSON, name='metadata')  # Renamed attribute, DB column still 'metadata'

# Example for another model
class AnotherModel(Base):
    __tablename__ = 'another_model'
    id = Column(Integer, primary_key=True)
    description = Column(String)
    meta_info = Column(String, name='metadata')  # Renamed attribute, DB column still 'metadata'