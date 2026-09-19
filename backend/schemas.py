"""
schemas.py
Pydantic models used for request validation and response serialization.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from models import MessageStatus, TaskStatus


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


# ---------------------- Staff ----------------------
class StaffBase(BaseModel):
    name: str
    email: Optional[str] = None
    mobile_number: Optional[str] = None
    role: str = "Staff"
    is_active: bool = True


class StaffCreate(StaffBase):
    pass


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    mobile_number: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class StaffOut(StaffBase):
    id: int
    created_at: Optional[datetime] = None
    task_count: Optional[int] = 0
    active_task_count: Optional[int] = 0

    class Config:
        from_attributes = True


class StaffMetrics(BaseModel):
    total_staff: int
    active_staff: int
    inactive_staff: int
    total_assigned_tasks: int


# ---------------------- Client ----------------------
class ClientBase(BaseModel):
    business_name: str
    contact_name: str
    mobile_number: str = Field(..., description="E.164 without '+' e.g. 91XXXXXXXXXX")
    gst_details: Optional[str] = None
    pan_details: Optional[str] = None
    tan_details: Optional[str] = None
    assigned_staff_id: Optional[int] = None
    is_active: bool = True


class ClientCreate(ClientBase):
    category_ids: Optional[List[int]] = None
    category_id: Optional[int] = None


class ClientUpdate(BaseModel):
    business_name: Optional[str] = None
    contact_name: Optional[str] = None
    mobile_number: Optional[str] = None
    gst_details: Optional[str] = None
    pan_details: Optional[str] = None
    tan_details: Optional[str] = None
    category_ids: Optional[List[int]] = None
    category_id: Optional[int] = None
    assigned_staff_id: Optional[int] = None
    is_active: Optional[bool] = None


class ClientOut(ClientBase):
    id: int
    category_id: Optional[int] = None
    category: Optional[CategoryOut] = None
    categories: List[CategoryOut] = []
    assigned_staff: Optional[StaffOut] = None

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


# ---------------------- Notifications ----------------------
class NotificationSendRequest(BaseModel):
    client_ids: Optional[List[int]] = None
    category_ids: Optional[List[int]] = None
    category_id: Optional[int] = None
    message_type: str = Field(default="CUSTOM_MESSAGE", description="CUSTOM_MESSAGE, GST_REMINDER, DOCUMENT_REQUEST, BILLING_NOTIFICATION, etc.")
    custom_message: Optional[str] = None
    template_params: Optional[dict] = None


class NotificationClientResult(BaseModel):
    client_id: int
    business_name: str
    contact_name: str
    mobile_number: str
    status: MessageStatus
    detail: Optional[str] = None
    simulated: bool = False


class NotificationSendResponse(BaseModel):
    total_targeted: int
    sent_count: int
    failed_count: int
    results: List[NotificationClientResult]


# ---------------------- Client Task ----------------------
class ClientTaskBase(BaseModel):
    matter: str = Field(..., description="Matter or work description e.g. GST Return Q2, ITR Filing")
    staff_id: Optional[int] = None
    assigned_staff: Optional[str] = None
    date_assigned: Optional[date] = None
    due_date: Optional[date] = None
    next_followup_date: Optional[date] = None
    status: TaskStatus = TaskStatus.PENDING
    remarks: Optional[str] = None
    documents: Optional[str] = None


class ClientTaskCreate(ClientTaskBase):
    client_id: Optional[int] = None
    new_client: Optional[ClientCreate] = None


class ClientTaskUpdate(BaseModel):
    client_id: Optional[int] = None
    staff_id: Optional[int] = None
    matter: Optional[str] = None
    assigned_staff: Optional[str] = None
    date_assigned: Optional[date] = None
    due_date: Optional[date] = None
    next_followup_date: Optional[date] = None
    status: Optional[TaskStatus] = None
    remarks: Optional[str] = None
    documents: Optional[str] = None


class ClientTaskStatusUpdate(BaseModel):
    status: TaskStatus


class ClientTaskOut(ClientTaskBase):
    id: int
    client_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    client: Optional[ClientOut] = None
    staff_member: Optional[StaffOut] = None
    staff: Optional[StaffOut] = None

    class Config:
        from_attributes = True


class TaskMetricsOut(BaseModel):
    total_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    waiting_documents_tasks: int
    under_review_tasks: int
    completed_tasks: int
    overdue_tasks: int
    due_today_tasks: int


class TaskReminderRequest(BaseModel):
    custom_message: Optional[str] = None

