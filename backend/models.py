"""
models.py
SQLAlchemy ORM models mirroring schema.sql
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DECIMAL, Date, DateTime,
    ForeignKey, Enum, func, Table, Text
)
from sqlalchemy.orm import relationship
from database import Base
import enum


class MessageStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DELIVERED = "DELIVERED"
    READ = "READ"


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_DOCUMENTS = "WAITING_DOCUMENTS"
    ON_HOLD = "ON_HOLD"
    UNDER_REVIEW = "UNDER_REVIEW"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# Association table for Client <-> Category (Many-to-Many)
client_categories = Table(
    "client_categories",
    Base.metadata,
    Column("client_id", Integer, ForeignKey("clients.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    clients = relationship("Client", secondary=client_categories, back_populates="categories")
    compliance_dates = relationship(
        "ComplianceDate", back_populates="category", cascade="all, delete-orphan"
    )


class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    mobile_number = Column(String(20), nullable=True)
    role = Column(String(50), default="Staff", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    tasks = relationship("ClientTask", back_populates="staff_member")


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String(150), nullable=False)
    contact_name = Column(String(100), nullable=False)
    mobile_number = Column(String(20), unique=True, nullable=False)
    gst_details = Column(String(20), nullable=True)
    pan_details = Column(String(15), nullable=True)
    tan_details = Column(String(15), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    assigned_staff_id = Column(Integer, ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    categories = relationship("Category", secondary=client_categories, back_populates="clients")
    category = relationship("Category")
    assigned_staff = relationship("Staff")
    invoices = relationship("Invoice", back_populates="client", cascade="all, delete-orphan")
    messages = relationship("MessageHistory", back_populates="client", cascade="all, delete-orphan")
    tasks = relationship("ClientTask", back_populates="client", cascade="all, delete-orphan")


class ComplianceDate(Base):
    __tablename__ = "compliance_dates"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    description = Column(String(255), nullable=False)
    due_date = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    category = relationship("Category", back_populates="compliance_dates")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    invoice_number = Column(String(50), unique=True, nullable=False)
    amount = Column(DECIMAL(12, 2), nullable=False)
    service_type = Column(String(100), nullable=False)
    is_sent = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="invoices")


class MessageHistory(Base):
    __tablename__ = "message_history"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    message_type = Column(String(50), nullable=False)
    message_content = Column(String(500), nullable=True)
    sent_timestamp = Column(DateTime, server_default=func.now())
    status = Column(Enum(MessageStatus), default=MessageStatus.PENDING, nullable=False)

    client = relationship("Client", back_populates="messages")


class ClientTask(Base):
    __tablename__ = "client_tasks"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    staff_id = Column(Integer, ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    matter = Column(String(200), nullable=False)
    assigned_staff = Column(String(100), nullable=True)
    date_assigned = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    next_followup_date = Column(Date, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    remarks = Column(Text, nullable=True)
    documents = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", back_populates="tasks")
    staff_member = relationship("Staff", back_populates="tasks")

