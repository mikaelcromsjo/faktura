from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker# Base class for models
from sqlalchemy import Column, Integer, DateTime, String, ForeignKey, JSON, Boolean
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import sqltypes as satypes
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from pydantic import BaseModel, field_validator

from core.database import Base

from core.models.models import BaseMixin, Update

from typing import List, Optional, Dict, Any

from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy import Date
from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, field_validator
from core.functions.helpers import formatPhoneNr

# -------------------------------------------------
# Companies Model (SQLAlchemy ORM)
# -------------------------------------------------
class Company(BaseMixin, Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    caller_id = Column(Integer, ForeignKey("callers.id"), nullable=True)
    caller = relationship("Caller")
    comment = Column(String, nullable=True)
    extra = Column(MutableDict.as_mutable(JSON), default=dict)


class CompanyUpdate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    comment: Optional[str] = None
    caller: Optional[int] = None                 # Dropdown → int
    extra: Optional[Dict[str, Any]] = None



# -----------------------------
# SQLAlchemy ORM Invoice model
# -----------------------------

class InvoiceNumber(BaseMixin, Base):
    __tablename__ = "invoice_numbers"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)

class Invoice(BaseMixin, Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    # Relationship to customer
    company = relationship("Company")
    caller_id = Column(Integer, ForeignKey("callers.id"), nullable=True)
    caller = relationship("Caller")

    date = Column(DateTime, nullable=True)
    extra = Column(MutableDict.as_mutable(JSON), default=dict)    

class InvoiceUpdate(BaseModel):
    number: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None
    company_id: Optional[int] = None
    date: Optional[datetime] = None

    class Config:
        from_attributes = True


class Caller(BaseMixin, Base):
    __tablename__ = "callers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    account = relationship("Account")
    extra = Column(MutableDict.as_mutable(JSON), default=dict)

class CallerUpdate(BaseModel):
    id: Optional[int] = Field(None, alias='id')
    name: str = Field(..., alias='name')
    extra: Optional[Dict[str, Any]] = Field(None, alias='extra')
    
    class Config:
        from_attributes = True  # v2 syntclassax: populate_object=True (v1)

class Account(BaseMixin, Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    extra = Column(MutableDict.as_mutable(JSON), default=dict)

class AccountUpdate(BaseModel):
    id: Optional[int] = Field(None, alias='id')
    name: str = Field(..., alias='name')
    extra: Optional[Dict[str, Any]] = Field(None, alias='extra')
    
    class Config:
        from_attributes = True  # v2 syntclassax: populate_object=True (v1)
