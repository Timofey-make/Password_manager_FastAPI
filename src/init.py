from sqlalchemy import create_engine, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30))
    password: Mapped[str] = mapped_column(String(30))
    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.username!r}, password={self.password!r})"

class Password(Base):
    __tablename__ = "passwords"
    categories: Mapped[str]
    user_id: Mapped[str]
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    username: Mapped[str]
    password: Mapped[str]
    def __repr__(self) -> str:
        return f"Password(categories={self.categories!r}, user_id={self.user_id!r}, name={self.name!r}, username={self.username!r}, password={self.password!r})"

class Share(Base):
    __tablename__ = "share"
    ownername: Mapped[int]
    sendername: Mapped[str]
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    username: Mapped[str]
    password: Mapped[str]
    def __repr__(self) -> str:
        return f"Share(ownername={self.ownername!r}, sendername={self.sendername!r}, name={self.name!r}, username={self.username!r}, password={self.password!r})"


engine = create_engine("sqlite:///users.db", echo=False)