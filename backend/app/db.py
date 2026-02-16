from sqlmodel import SQLModel, Session, create_engine
from .settings import settings


def get_engine():
    connect_args = {"check_same_thread": False}
    return create_engine(f"sqlite:///{settings.DATABASE_PATH}", connect_args=connect_args)


engine = get_engine()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
