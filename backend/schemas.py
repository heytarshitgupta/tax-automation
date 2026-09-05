"""
schemas.py
Pydantic models used for request validation and response serialization.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from models import MessageStatus


# ---------------------- Category ----------------------
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class CategoryOut(CategoryBase):
    id: int

    class Config:
        from_attributes = True


# ---------------------- Client ----------------------
class ClientBase(BaseModel):
    business_name: str
    contact_name: str
    mobile_number: str = Field(..., description="E.164 without '+' e.g. 91XXXXXXXXXX")
    gst_details: Optional[str] = None
    pan_details: Optional[str] = None
    category_id: Optional[int] = None
    is_active: bool = True


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    business_name: Optional[str] = None
    contact_name: Optional[str] = None
    mobile_number: Optional[str] = None
    gst_details: Optional[str] = None
    pan_details: Optional[str] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None


class ClientOut(ClientBase):
    id: int
    category: Optional[CategoryOut] = None

    class Config:
        from_attributes = True


# ---------------------- Compliance Date ----------------------
class ComplianceDateBase(BaseModel):
    category_id: int
    description: str
    due_date: date


class ComplianceDateCreate(ComplianceDateBase):
    pass


class ComplianceDateOut(ComplianceDateBase):
    id: int

    class Config:
        from_attributes = True


# ---------------------- Invoice ----------------------
class InvoiceBase(BaseModel):
    client_id: int
    invoice_number: str
    amount: Decimal
    service_type: str
    is_sent: bool = False


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceOut(InvoiceBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------- Message History ----------------------
class MessageHistoryOut(BaseModel):
    id: int
    client_id: int
    message_type: str
    message_content: Optional[str] = None
    sent_timestamp: datetime
    status: MessageStatus
    client: Optional[ClientOut] = None

    class Config:
        from_attributes = True


class MessageHistoryCreate(BaseModel):
    client_id: int
    message_type: str
    message_content: Optional[str] = None
    status: MessageStatus = MessageStatus.PENDING


# ---------------------- Dashboard ----------------------
class DashboardMetrics(BaseModel):
    total_clients: int
    active_clients: int
    inactive_clients: int
    messages_sent_today: int
    messages_failed_today: int
    total_categories: int
    upcoming_compliance_7_days: int
