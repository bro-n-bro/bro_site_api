import enum
from random import randrange

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Date, DateTime, func, Float, CheckConstraint, Enum, \
    BigInteger
from sqlalchemy.orm import relationship
import sqlalchemy_utils
from sqlalchemy_utils import ChoiceType
from .database import Base


class Network(Base):
    __tablename__ = "networks"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    apr = Column(Float(precision=2))
    delegators = Column(Integer)
    denom = Column(String)
    health = Column(Integer, default=lambda: randrange(21))
    network = Column(String)
    place = Column(Integer)
    price = Column(Float(precision=2))
    tokens = Column(BigInteger)
    __table_args__ = (
        CheckConstraint(delegators >= 0, name='check_delegators_positive'),
        CheckConstraint(place >= 1, name='check_place_positive'),
        {}
    )
