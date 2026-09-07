"""
main.py
Gateway Solutions | WhatsApp Tax Office Automation System
FastAPI backend entrypoint.

Run with:  uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
import logging
from datetime import date, datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
import schemas
from database import engine, get_db
from scheduler import start_scheduler, run_compliance_reminder_job
from whatsapp_service import (
    send_gst_reminder,
    send_document_request,
    send_billing_notification,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Auto-create tables if they don't already exist (schema.sql remains the
# source of truth for a fresh DB setup / dummy data).
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Gateway Solutions - WhatsApp Tax Automation API",
    description="Automates GST reminders, document requests & billing notifications via WhatsApp.",
    version="1.0.0",
)

# ---------------------------------------------------------------
# CORS - allow the Vue dev server (and production frontend) to call this API
# ---------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],  # dev ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_scheduler = None


@app.on_event("startup")
def on_startup():
    global _scheduler
    _scheduler = start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    if _scheduler:
        _scheduler.shutdown(wait=False)


# =================================================================
# HEALTH CHECK
# =================================================================
@app.get("/api/health", tags=["System"])
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# =================================================================
# CATEGORY CRUD
# =================================================================
@app.post("/api/categories", response_model=schemas.CategoryOut, status_code=201, tags=["Categories"])
def create_category(payload: schemas.CategoryCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Category).filter(models.Category.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category name already exists.")
    category = models.Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@app.get("/api/categories", response_model=list[schemas.CategoryOut], tags=["Categories"])
def list_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).order_by(models.Category.name).all()


@app.get("/api/categories/{category_id}", response_model=schemas.CategoryOut, tags=["Categories"])
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")
    return category


@app.put("/api/categories/{category_id}", response_model=schemas.CategoryOut, tags=["Categories"])
def update_category(category_id: int, payload: schemas.CategoryUpdate, db: Session = Depends(get_db)):
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


@app.delete("/api/categories/{category_id}", status_code=204, tags=["Categories"])
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")
    db.delete(category)
    db.commit()
    return None


# =================================================================
# CLIENT CRUD
# =================================================================
@app.post("/api/clients", response_model=schemas.ClientOut, status_code=201, tags=["Clients"])
def create_client(payload: schemas.ClientCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Client).filter(models.Client.mobile_number == payload.mobile_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="A client with this mobile number already exists.")

    # Validate and fetch categories if provided
    categories = []
    if payload.category_ids:
        unique_cat_ids = list(dict.fromkeys(payload.category_ids))
        found_categories = db.query(models.Category).filter(models.Category.id.in_(unique_cat_ids)).all()
        found_ids = {c.id for c in found_categories}
        missing_ids = [cid for cid in unique_cat_ids if cid not in found_ids]
        if missing_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Category ID(s) {missing_ids} do not exist.",
            )
        categories = found_categories
    elif payload.category_id:
        single_cat = db.query(models.Category).filter(models.Category.id == payload.category_id).first()
        if not single_cat:
            raise HTTPException(
                status_code=400,
                detail=f"Category ID {payload.category_id} does not exist.",
            )
        categories = [single_cat]

    client_data = payload.model_dump(exclude={"category_ids"})
    # Normalize tax identifiers: trim and uppercase if provided
    for key in ("gst_details", "pan_details", "tan_details"):
        if client_data.get(key):
            client_data[key] = client_data[key].strip().upper()
        else:
            client_data[key] = None

    if categories:
        client_data["category_id"] = categories[0].id

    client = models.Client(**client_data)
    if categories:
        client.categories = categories

    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@app.get("/api/clients", response_model=list[schemas.ClientOut], tags=["Clients"])
def list_clients(
    db: Session = Depends(get_db),
    category_id: int | None = None,
    category_ids: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
):
    query = db.query(models.Client)

    # Multi-category filter support (e.g. ?category_ids=1,3)
    parsed_category_ids = []
    if category_ids:
        try:
            parsed_category_ids = [int(cid.strip()) for cid in category_ids.split(",") if cid.strip().isdigit()]
        except Exception:
            parsed_category_ids = []

    if parsed_category_ids:
        query = query.filter(
            (models.Client.categories.any(models.Category.id.in_(parsed_category_ids)))
            | (models.Client.category_id.in_(parsed_category_ids))
        )
    elif category_id is not None:
        query = query.filter(
            (models.Client.categories.any(models.Category.id == category_id))
            | (models.Client.category_id == category_id)
        )

    if is_active is not None:
        query = query.filter(models.Client.is_active == is_active)

    if search:
        like = f"%{search}%"
        query = query.filter(
            (models.Client.business_name.like(like))
            | (models.Client.contact_name.like(like))
            | (models.Client.mobile_number.like(like))
        )
    return query.order_by(models.Client.business_name).all()



@app.get("/api/clients/{client_id}", response_model=schemas.ClientOut, tags=["Clients"])
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")
    return client


@app.put("/api/clients/{client_id}", response_model=schemas.ClientOut, tags=["Clients"])
def update_client(client_id: int, payload: schemas.ClientUpdate, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")

    dump = payload.model_dump(exclude_unset=True)

    if "mobile_number" in dump and dump["mobile_number"] and dump["mobile_number"] != client.mobile_number:
        existing = db.query(models.Client).filter(
            models.Client.mobile_number == dump["mobile_number"],
            models.Client.id != client_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="A client with this mobile number already exists.")

    if "category_ids" in dump:
        cat_ids = dump.pop("category_ids")
        if cat_ids is not None:
            unique_cat_ids = list(dict.fromkeys(cat_ids))
            found_categories = db.query(models.Category).filter(models.Category.id.in_(unique_cat_ids)).all() if unique_cat_ids else []
            found_ids = {c.id for c in found_categories}
            missing_ids = [cid for cid in unique_cat_ids if cid not in found_ids]
            if missing_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Category ID(s) {missing_ids} do not exist.",
                )
            client.categories = found_categories
            client.category_id = found_categories[0].id if found_categories else None

    for field, value in dump.items():
        if field in ("gst_details", "pan_details", "tan_details"):
            if isinstance(value, str) and value.strip():
                value = value.strip().upper()
            else:
                value = None
        setattr(client, field, value)
    db.commit()
    db.refresh(client)
    return client




@app.delete("/api/clients/{client_id}", status_code=204, tags=["Clients"])
def delete_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")
    db.delete(client)
    db.commit()
    return None


# =================================================================
# COMPLIANCE DATES CRUD (lightweight - create/list/delete)
# =================================================================
@app.post("/api/compliance-dates", response_model=schemas.ComplianceDateOut, status_code=201, tags=["Compliance Dates"])
def create_compliance_date(payload: schemas.ComplianceDateCreate, db: Session = Depends(get_db)):
    category = db.query(models.Category).filter(models.Category.id == payload.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")
    item = models.ComplianceDate(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/api/compliance-dates", response_model=list[schemas.ComplianceDateOut], tags=["Compliance Dates"])
def list_compliance_dates(db: Session = Depends(get_db)):
    return db.query(models.ComplianceDate).order_by(models.ComplianceDate.due_date).all()


@app.delete("/api/compliance-dates/{item_id}", status_code=204, tags=["Compliance Dates"])
def delete_compliance_date(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.ComplianceDate).filter(models.ComplianceDate.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Compliance date not found.")
    db.delete(item)
    db.commit()
    return None


# =================================================================
# INVOICES (create/list + trigger billing notification)
# =================================================================
@app.post("/api/invoices", response_model=schemas.InvoiceOut, status_code=201, tags=["Invoices"])
def create_invoice(payload: schemas.InvoiceCreate, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.id == payload.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")
    invoice = models.Invoice(**payload.model_dump())
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@app.get("/api/invoices", response_model=list[schemas.InvoiceOut], tags=["Invoices"])
def list_invoices(db: Session = Depends(get_db)):
    return db.query(models.Invoice).order_by(models.Invoice.created_at.desc()).all()


@app.post("/api/invoices/{invoice_id}/send", tags=["Invoices"])
def send_invoice_notification(invoice_id: int, db: Session = Depends(get_db)):
    """Manually trigger a WhatsApp billing notification for a given invoice."""
    invoice = db.query(models.Invoice).filter(models.Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    client = db.query(models.Client).filter(models.Client.id == invoice.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Associated client not found.")

    result = send_billing_notification(
        to_number=client.mobile_number,
        business_name=client.business_name,
        invoice_number=invoice.invoice_number,
        amount=str(invoice.amount),
    )
    status_enum = models.MessageStatus.SENT if result["success"] else models.MessageStatus.FAILED

    history = models.MessageHistory(
        client_id=client.id,
        message_type="BILLING_NOTIFICATION",
        message_content=f"Invoice {invoice.invoice_number} for Rs. {invoice.amount} sent.",
        status=status_enum,
    )
    db.add(history)
    if result["success"]:
        invoice.is_sent = True
    db.commit()
    return {"success": result["success"], "detail": result["response"]}


# =================================================================
# MESSAGE HISTORY (communication log)
# =================================================================
@app.get("/api/message-history", response_model=list[schemas.MessageHistoryOut], tags=["Message History"])
def list_message_history(
    db: Session = Depends(get_db),
    client_id: int | None = None,
    status_filter: models.MessageStatus | None = None,
    limit: int = 200,
):
    query = db.query(models.MessageHistory)
    if client_id is not None:
        query = query.filter(models.MessageHistory.client_id == client_id)
    if status_filter is not None:
        query = query.filter(models.MessageHistory.status == status_filter)
    return (
        query.order_by(models.MessageHistory.sent_timestamp.desc())
        .limit(limit)
        .all()
    )


@app.post("/api/message-history", response_model=schemas.MessageHistoryOut, status_code=201, tags=["Message History"])
def create_message_history_entry(payload: schemas.MessageHistoryCreate, db: Session = Depends(get_db)):
    entry = models.MessageHistory(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# =================================================================
# MANUAL TRIGGERS (send document request / run scheduler job now)
# =================================================================
@app.post("/api/clients/{client_id}/send-document-request", tags=["Manual Actions"])
def trigger_document_request(client_id: int, doc_description: str, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found.")

    result = send_document_request(client.mobile_number, client.business_name, doc_description)
    status_enum = models.MessageStatus.SENT if result["success"] else models.MessageStatus.FAILED

    history = models.MessageHistory(
        client_id=client.id,
        message_type="DOCUMENT_REQUEST",
        message_content=f"Requested: {doc_description}",
        status=status_enum,
    )
    db.add(history)
    db.commit()
    return {"success": result["success"], "detail": result["response"]}


@app.post("/api/scheduler/run-now", tags=["Manual Actions"])
def trigger_scheduler_manually():
    """Manually fire the daily compliance reminder job (useful for demos/testing)."""
    run_compliance_reminder_job()
    return {"detail": "Compliance reminder job executed."}


# =================================================================
# DASHBOARD METRICS
# =================================================================
@app.get("/api/dashboard", response_model=schemas.DashboardMetrics, tags=["Dashboard"])
def get_dashboard_metrics(db: Session = Depends(get_db)):
    total_clients = db.query(func.count(models.Client.id)).scalar() or 0
    active_clients = (
        db.query(func.count(models.Client.id)).filter(models.Client.is_active == True).scalar()  # noqa: E712
        or 0
    )
    inactive_clients = total_clients - active_clients

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = today_start + timedelta(days=1)

    messages_sent_today = (
        db.query(func.count(models.MessageHistory.id))
        .filter(
            models.MessageHistory.sent_timestamp >= today_start,
            models.MessageHistory.sent_timestamp < today_end,
            models.MessageHistory.status.in_(
                [models.MessageStatus.SENT, models.MessageStatus.DELIVERED, models.MessageStatus.READ]
            ),
        )
        .scalar()
        or 0
    )

    messages_failed_today = (
        db.query(func.count(models.MessageHistory.id))
        .filter(
            models.MessageHistory.sent_timestamp >= today_start,
            models.MessageHistory.sent_timestamp < today_end,
            models.MessageHistory.status == models.MessageStatus.FAILED,
        )
        .scalar()
        or 0
    )

    total_categories = db.query(func.count(models.Category.id)).scalar() or 0

    upcoming_window_end = date.today() + timedelta(days=7)
    upcoming_compliance_7_days = (
        db.query(func.count(models.ComplianceDate.id))
        .filter(
            models.ComplianceDate.due_date >= date.today(),
            models.ComplianceDate.due_date <= upcoming_window_end,
        )
        .scalar()
        or 0
    )

    return schemas.DashboardMetrics(
        total_clients=total_clients,
        active_clients=active_clients,
        inactive_clients=inactive_clients,
        messages_sent_today=messages_sent_today,
        messages_failed_today=messages_failed_today,
        total_categories=total_categories,
        upcoming_compliance_7_days=upcoming_compliance_7_days,
    )
