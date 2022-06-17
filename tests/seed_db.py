from curses import echo
from sqlalchemy import (create_engine, Column, String, Integer, engine)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "user"
    username = Column("username", String(20), primary_key=True)
    age = Column("age", Integer)


def create_table():
    e: engine.Engine = create_engine(
        "sqlite:///test.db", echo=True, future=True)
    with e.begin() as c:
        Base.metadata.create_all(bind=c)
    return e
