"""
main.py
Gateway Solutions | WhatsApp Tax Office Automation System
FastAPI backend entrypoint.

Run with:  uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
import os
import logging
from datetime import date, datetime, timedelta

from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_

import models
import schemas
from database import engine, get_db, SessionLocal
from scheduler import start_scheduler, run_compliance_reminder_job
from whatsapp_service import (
    send_gst_reminder,
    send_document_request,
    send_billing_notification,
    send_whatsapp_text_message,
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
default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
env_origins = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = list(dict.fromkeys(
    default_origins + [o.strip() for o in env_origins.split(",") if o.strip()]
))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_scheduler = None


def seed_initial_staff():
    db = SessionLocal()
    try:
        count = db.query(models.Staff).count()
        if count == 0:
            initial_staff = [
                models.Staff(
                    name="Rahul Sharma",
                    role="Tax Consultant",
                    email="rahul.sharma@gatewaytax.in",
                    mobile_number="919876540001",
                    is_active=True,
                ),
                models.Staff(
                    name="Pooja Verma",
                    role="Senior Accountant",
                    email="pooja.verma@gatewaytax.in",
                    mobile_number="919876540002",
                    is_active=True,
                ),
                models.Staff(
                    name="Ankit Gupta",
                    role="Audit Assistant",
                    email="ankit.gupta@gatewaytax.in",
                    mobile_number="919876540003",
                    is_active=True,
                ),
                models.Staff(
                    name="CA Tarun Mehta",
                    role="Partner / CA",
                    email="tarun.mehta@gatewaytax.in",
                    mobile_number="919876540004",
                    is_active=True,
                ),
            ]
            db.add_all(initial_staff)
            db.commit()

            # Link existing tasks with assigned_staff matching name
            for s in initial_staff:
                db.refresh(s)
                db.query(models.ClientTask).filter(
                    models.ClientTask.assigned_staff == s.name
                ).update({"staff_id": s.id}, synchronize_session=False)
            db.commit()
            logger.info("Seeded initial staff members and linked existing tasks.")
    except Exception as exc:
        logger.warning(f"Initial staff seeding skipped or error: {exc}")
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    global _scheduler
    _scheduler = start_scheduler()
    seed_initial_staff()


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
# NOTIFICATIONS (send custom or template WhatsApp messages to clients)
# =================================================================
@app.post(
    "/api/notifications/send",
    response_model=schemas.NotificationSendResponse,
    tags=["Notifications"],
)
def send_notifications_to_clients(
    payload: schemas.NotificationSendRequest,
    db: Session = Depends(get_db),
):
    """
    Sends WhatsApp messages (custom freeform text or pre-approved templates)
    to a selected list of clients.
    Supports variables {client_name}, {business_name}, {mobile_number} in custom messages.
    """
    target_client_ids = list(payload.client_ids) if payload.client_ids else []

    if not target_client_ids:
        # Check if category_ids or category_id is provided
        cat_ids = []
        if payload.category_ids:
            cat_ids = [int(cid) for cid in payload.category_ids if cid]
        elif payload.category_id:
            cat_ids = [int(payload.category_id)]

        if cat_ids:
            cat_clients = db.query(models.Client).filter(
                models.Client.is_active == True,
                (models.Client.categories.any(models.Category.id.in_(cat_ids)))
                | (models.Client.category_id.in_(cat_ids))
            ).all()
            target_client_ids = [c.id for c in cat_clients]

    if not target_client_ids:
        raise HTTPException(
            status_code=400,
            detail="No clients selected. Please provide client IDs or select a client type/category.",
        )

    clients = db.query(models.Client).filter(models.Client.id.in_(target_client_ids)).all()
    if not clients:
        raise HTTPException(status_code=404, detail="None of the specified clients were found.")

    client_map = {c.id: c for c in clients}
    results = []
    sent_count = 0
    failed_count = 0

    params = payload.template_params or {}
    msg_type = payload.message_type or "CUSTOM_MESSAGE"

    for cid in target_client_ids:
        client = client_map.get(cid)
        if not client:
            failed_count += 1
            results.append(
                schemas.NotificationClientResult(
                    client_id=cid,
                    business_name="Unknown",
                    contact_name="Unknown",
                    mobile_number="N/A",
                    status=models.MessageStatus.FAILED,
                    detail="Client not found in database.",
                    simulated=False,
                )
            )
            continue

        content_for_history = ""
        api_result = None

        if msg_type == "CUSTOM_MESSAGE":
            raw_text = payload.custom_message or f"Hello {client.contact_name}, notification from Gateway Solutions."
            personalized_text = (
                raw_text.replace("{client_name}", client.contact_name or "")
                .replace("{business_name}", client.business_name or "")
                .replace("{mobile_number}", client.mobile_number or "")
            )
            content_for_history = personalized_text[:500]
            api_result = send_whatsapp_text_message(
                to_number=client.mobile_number,
                message_text=personalized_text,
            )
        elif msg_type == "GST_REMINDER":
            days_left = int(params.get("days_left", 3))
            due_date = str(params.get("due_date", date.today().strftime("%d-%m-%Y")))
            content_for_history = f"GST reminder: {days_left} days left (due {due_date})"
            api_result = send_gst_reminder(
                to_number=client.mobile_number,
                business_name=client.business_name,
                days_left=days_left,
                due_date=due_date,
            )
        elif msg_type == "DOCUMENT_REQUEST":
            doc_desc = str(params.get("doc_description", "required compliance documents"))
            content_for_history = f"Requested: {doc_desc}"
            api_result = send_document_request(
                to_number=client.mobile_number,
                business_name=client.business_name,
                doc_description=doc_desc,
            )
        elif msg_type == "BILLING_NOTIFICATION":
            inv_no = str(params.get("invoice_number", "INV-NEW"))
            amt = str(params.get("amount", "0.00"))
            content_for_history = f"Invoice {inv_no} for Rs. {amt} sent."
            api_result = send_billing_notification(
                to_number=client.mobile_number,
                business_name=client.business_name,
                invoice_number=inv_no,
                amount=amt,
            )
        else:
            # Fallback / Quick Template treated as custom text
            raw_text = payload.custom_message or f"Notification for {client.business_name}"
            personalized_text = (
                raw_text.replace("{client_name}", client.contact_name or "")
                .replace("{business_name}", client.business_name or "")
                .replace("{mobile_number}", client.mobile_number or "")
            )
            content_for_history = personalized_text[:500]
            api_result = send_whatsapp_text_message(
                to_number=client.mobile_number,
                message_text=personalized_text,
            )

        is_success = bool(api_result and api_result.get("success"))
        is_simulated = bool(api_result and api_result.get("simulated", False))
        status_enum = models.MessageStatus.SENT if is_success else models.MessageStatus.FAILED

        if is_success:
            sent_count += 1
        else:
            failed_count += 1

        history_entry = models.MessageHistory(
            client_id=client.id,
            message_type=msg_type,
            message_content=content_for_history,
            status=status_enum,
        )
        db.add(history_entry)

        resp_detail = None
        if api_result:
            if isinstance(api_result.get("response"), dict):
                resp_detail = api_result["response"].get("note") or str(api_result["response"])
            else:
                resp_detail = str(api_result.get("response"))

        results.append(
            schemas.NotificationClientResult(
                client_id=client.id,
                business_name=client.business_name,
                contact_name=client.contact_name,
                mobile_number=client.mobile_number,
                status=status_enum,
                detail=resp_detail,
                simulated=is_simulated,
            )
        )

    db.commit()

    return schemas.NotificationSendResponse(
        total_targeted=len(target_client_ids),
        sent_count=sent_count,
        failed_count=failed_count,
        results=results,
    )


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


# =================================================================
# CLIENT TASKS
# =================================================================
@app.get("/api/tasks", response_model=List[schemas.ClientTaskOut], tags=["Client Tasks"])
def list_tasks(
    status: Optional[models.TaskStatus] = None,
    client_id: Optional[int] = None,
    assigned_staff: Optional[str] = None,
    overdue: Optional[bool] = None,
    search: Optional[str] = None,
    due_date_from: Optional[date] = None,
    due_date_to: Optional[date] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.ClientTask).options(joinedload(models.ClientTask.client))

    if status:
        query = query.filter(models.ClientTask.status == status)
    if client_id:
        query = query.filter(models.ClientTask.client_id == client_id)
    if assigned_staff:
        query = query.filter(models.ClientTask.assigned_staff.ilike(f"%{assigned_staff}%"))
    if overdue:
        today = date.today()
        query = query.filter(
            models.ClientTask.due_date < today,
            models.ClientTask.status.notin_([models.TaskStatus.COMPLETED, models.TaskStatus.CANCELLED]),
        )
    if due_date_from:
        query = query.filter(models.ClientTask.due_date >= due_date_from)
    if due_date_to:
        query = query.filter(models.ClientTask.due_date <= due_date_to)
    if search:
        search_term = f"%{search}%"
        query = query.join(models.Client, isouter=True).filter(
            or_(
                models.ClientTask.matter.ilike(search_term),
                models.ClientTask.assigned_staff.ilike(search_term),
                models.ClientTask.remarks.ilike(search_term),
                models.ClientTask.documents.ilike(search_term),
                models.Client.business_name.ilike(search_term),
                models.Client.contact_name.ilike(search_term),
            )
        )

    tasks = query.order_by(
        models.ClientTask.due_date.is_(None),
        models.ClientTask.due_date.asc(),
        models.ClientTask.id.desc(),
    ).all()
    return tasks


@app.get("/api/tasks/metrics", response_model=schemas.TaskMetricsOut, tags=["Client Tasks"])
def get_task_metrics(db: Session = Depends(get_db)):
    today = date.today()
    total = db.query(func.count(models.ClientTask.id)).scalar() or 0
    pending = (
        db.query(func.count(models.ClientTask.id))
        .filter(models.ClientTask.status == models.TaskStatus.PENDING)
        .scalar()
        or 0
    )
    in_progress = (
        db.query(func.count(models.ClientTask.id))
        .filter(models.ClientTask.status == models.TaskStatus.IN_PROGRESS)
        .scalar()
        or 0
    )
    waiting_docs = (
        db.query(func.count(models.ClientTask.id))
        .filter(models.ClientTask.status == models.TaskStatus.WAITING_DOCUMENTS)
        .scalar()
        or 0
    )
    under_review = (
        db.query(func.count(models.ClientTask.id))
        .filter(models.ClientTask.status == models.TaskStatus.UNDER_REVIEW)
        .scalar()
        or 0
    )
    completed = (
        db.query(func.count(models.ClientTask.id))
        .filter(models.ClientTask.status == models.TaskStatus.COMPLETED)
        .scalar()
        or 0
    )

    overdue = (
        db.query(func.count(models.ClientTask.id))
        .filter(
            models.ClientTask.due_date < today,
            models.ClientTask.status.notin_([models.TaskStatus.COMPLETED, models.TaskStatus.CANCELLED]),
        )
        .scalar()
        or 0
    )

    due_today = (
        db.query(func.count(models.ClientTask.id))
        .filter(
            models.ClientTask.due_date == today,
            models.ClientTask.status.notin_([models.TaskStatus.COMPLETED, models.TaskStatus.CANCELLED]),
        )
        .scalar()
        or 0
    )

    return schemas.TaskMetricsOut(
        total_tasks=total,
        pending_tasks=pending,
        in_progress_tasks=in_progress,
        waiting_documents_tasks=waiting_docs,
        under_review_tasks=under_review,
        completed_tasks=completed,
        overdue_tasks=overdue,
        due_today_tasks=due_today,
    )


@app.get("/api/tasks/{task_id}", response_model=schemas.ClientTaskOut, tags=["Client Tasks"])
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = (
        db.query(models.ClientTask)
        .options(joinedload(models.ClientTask.client))
        .filter(models.ClientTask.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post(
    "/api/tasks",
    response_model=schemas.ClientTaskOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Client Tasks"],
)
def create_task(task_in: schemas.ClientTaskCreate, db: Session = Depends(get_db)):
    client_id = task_in.client_id

    # Handle inline client creation if provided
    if not client_id and task_in.new_client:
        new_client_data = task_in.new_client.dict(exclude={"category_ids", "category_id"})
        client = models.Client(**new_client_data)
        if task_in.new_client.category_ids:
            cats = db.query(models.Category).filter(models.Category.id.in_(task_in.new_client.category_ids)).all()
            client.categories = cats
        db.add(client)
        db.commit()
        db.refresh(client)
        client_id = client.id

    if not client_id:
        raise HTTPException(status_code=400, detail="client_id or new_client details must be provided")

    client = db.query(models.Client).filter(models.Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Selected client does not exist")

    task = models.ClientTask(
        client_id=client_id,
        matter=task_in.matter,
        assigned_staff=task_in.assigned_staff,
        date_assigned=task_in.date_assigned or date.today(),
        due_date=task_in.due_date,
        next_followup_date=task_in.next_followup_date,
        status=task_in.status or models.TaskStatus.PENDING,
        remarks=task_in.remarks,
        documents=task_in.documents,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return (
        db.query(models.ClientTask)
        .options(joinedload(models.ClientTask.client))
        .filter(models.ClientTask.id == task.id)
        .first()
    )


@app.put("/api/tasks/{task_id}", response_model=schemas.ClientTaskOut, tags=["Client Tasks"])
def update_task(task_id: int, task_in: schemas.ClientTaskUpdate, db: Session = Depends(get_db)):
    task = db.query(models.ClientTask).filter(models.ClientTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_in.dict(exclude_unset=True)
    if "client_id" in update_data and update_data["client_id"]:
        client = db.query(models.Client).filter(models.Client.id == update_data["client_id"]).first()
        if not client:
            raise HTTPException(status_code=404, detail="Target client not found")

    for field, val in update_data.items():
        setattr(task, field, val)

    db.commit()
    db.refresh(task)
    return (
        db.query(models.ClientTask)
        .options(joinedload(models.ClientTask.client))
        .filter(models.ClientTask.id == task.id)
        .first()
    )


@app.patch("/api/tasks/{task_id}/status", response_model=schemas.ClientTaskOut, tags=["Client Tasks"])
def update_task_status(
    task_id: int, status_in: schemas.ClientTaskStatusUpdate, db: Session = Depends(get_db)
):
    task = db.query(models.ClientTask).filter(models.ClientTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = status_in.status
    db.commit()
    db.refresh(task)
    return (
        db.query(models.ClientTask)
        .options(joinedload(models.ClientTask.client))
        .filter(models.ClientTask.id == task.id)
        .first()
    )


@app.delete("/api/tasks/{task_id}", tags=["Client Tasks"])
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(models.ClientTask).filter(models.ClientTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"ok": True, "message": "Task deleted successfully"}


@app.post("/api/tasks/{task_id}/send-reminder", tags=["Client Tasks"])
def send_task_reminder(
    task_id: int, req: schemas.TaskReminderRequest = None, db: Session = Depends(get_db)
):
    task = (
        db.query(models.ClientTask)
        .options(joinedload(models.ClientTask.client))
        .filter(models.ClientTask.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.client:
        raise HTTPException(status_code=400, detail="Task does not have an associated client")
    if not task.client.mobile_number:
        raise HTTPException(status_code=400, detail="Client does not have a registered mobile number")

    client = task.client

    if req and req.custom_message and req.custom_message.strip():
        msg_text = req.custom_message.strip()
    else:
        due_str = task.due_date.strftime("%d-%b-%Y") if task.due_date else "soon"
        doc_part = f"\n*Pending Documents:* {task.documents}" if task.documents else ""
        remarks_part = f"\n*Notes:* {task.remarks}" if task.remarks else ""
        msg_text = (
            f"Hello *{client.contact_name or 'Client'}*,\n\n"
            f"This is Gateway Solutions regarding your compliance task: *{task.matter}* for *{client.business_name}*.\n"
            f"📅 *Due Date:* {due_str}\n"
            f"📌 *Status:* {task.status.value.replace('_', ' ').title()}"
            f"{doc_part}"
            f"{remarks_part}\n\n"
            f"Please share the pending details or documents at the earliest to ensure timely filing. Thank you!"
        )

    wa_result = send_whatsapp_text_message(client.mobile_number, msg_text)

    status_str = "SENT" if wa_result.get("success") else "FAILED"
    simulated = wa_result.get("simulated", False)

    history_entry = models.MessageHistory(
        client_id=client.id,
        message_type="DOCUMENT_REQUEST",
        message_content=msg_text,
        status=models.MessageStatus.SENT if wa_result.get("success") else models.MessageStatus.FAILED,
    )
    db.add(history_entry)
    db.commit()

    return {
        "success": wa_result.get("success", False),
        "status": status_str,
        "simulated": simulated,
        "sent_message": msg_text,
        "client_name": client.contact_name,
        "mobile_number": client.mobile_number,
    }


# =================================================================
# STAFF CRUD
# =================================================================
@app.get("/api/staff/metrics", response_model=schemas.StaffMetrics, tags=["Staff"])
def get_staff_metrics(db: Session = Depends(get_db)):
    total = db.query(models.Staff).count()
    active = db.query(models.Staff).filter(models.Staff.is_active == True).count()
    inactive = total - active
    total_assigned_tasks = db.query(models.ClientTask).filter(
        or_(models.ClientTask.staff_id != None, models.ClientTask.assigned_staff != None)
    ).count()
    return {
        "total_staff": total,
        "active_staff": active,
        "inactive_staff": inactive,
        "total_assigned_tasks": total_assigned_tasks,
    }


@app.get("/api/staff", response_model=list[schemas.StaffOut], tags=["Staff"])
def list_staff(
    db: Session = Depends(get_db),
    is_active: Optional[bool] = None,
    role: Optional[str] = None,
    search: Optional[str] = None,
):
    query = db.query(models.Staff)
    if is_active is not None:
        query = query.filter(models.Staff.is_active == is_active)
    if role and role.strip() and role != "ALL":
        query = query.filter(models.Staff.role == role.strip())
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                models.Staff.name.ilike(term),
                models.Staff.email.ilike(term),
                models.Staff.mobile_number.ilike(term),
                models.Staff.role.ilike(term),
            )
        )
    staff_list = query.order_by(models.Staff.name.asc()).all()

    result = []
    for s in staff_list:
        tasks_query = db.query(models.ClientTask).filter(
            or_(models.ClientTask.staff_id == s.id, models.ClientTask.assigned_staff == s.name)
        )
        task_count = tasks_query.count()
        active_task_count = tasks_query.filter(
            ~models.ClientTask.status.in_([models.TaskStatus.COMPLETED, models.TaskStatus.CANCELLED])
        ).count()
        out = schemas.StaffOut.model_validate(s)
        out.task_count = task_count
        out.active_task_count = active_task_count
        result.append(out)

    return result


@app.post("/api/staff", response_model=schemas.StaffOut, status_code=201, tags=["Staff"])
def create_staff(payload: schemas.StaffCreate, db: Session = Depends(get_db)):
    clean_name = payload.name.strip() if payload.name else ""
    if not clean_name:
        raise HTTPException(status_code=400, detail="Staff name is required.")

    if payload.email and payload.email.strip():
        clean_email = payload.email.strip().lower()
        existing_email = db.query(models.Staff).filter(models.Staff.email == clean_email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="A staff member with this email already exists.")

    staff_data = payload.model_dump()
    staff_data["name"] = clean_name
    if staff_data.get("email"):
        staff_data["email"] = staff_data["email"].strip().lower()
    if staff_data.get("mobile_number"):
        raw_m = "".join(c for c in str(staff_data["mobile_number"]) if c.isdigit())
        staff_data["mobile_number"] = raw_m or None

    new_staff = models.Staff(**staff_data)
    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)

    # Automatically link tasks where assigned_staff == clean_name
    db.query(models.ClientTask).filter(
        models.ClientTask.assigned_staff == clean_name,
        models.ClientTask.staff_id == None,
    ).update({"staff_id": new_staff.id}, synchronize_session=False)
    db.commit()

    out = schemas.StaffOut.model_validate(new_staff)
    out.task_count = 0
    out.active_task_count = 0
    return out


@app.get("/api/staff/{staff_id}", tags=["Staff"])
def get_staff_member(staff_id: int, db: Session = Depends(get_db)):
    staff = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found.")

    tasks = (
        db.query(models.ClientTask)
        .options(joinedload(models.ClientTask.client))
        .filter(or_(models.ClientTask.staff_id == staff.id, models.ClientTask.assigned_staff == staff.name))
        .order_by(models.ClientTask.due_date.asc())
        .all()
    )

    out = schemas.StaffOut.model_validate(staff)
    out.task_count = len(tasks)
    out.active_task_count = len([t for t in tasks if t.status not in (models.TaskStatus.COMPLETED, models.TaskStatus.CANCELLED)])

    task_list = []
    for t in tasks:
        task_list.append({
            "id": t.id,
            "matter": t.matter,
            "status": t.status.value if hasattr(t.status, "value") else str(t.status),
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "client_business_name": t.client.business_name if t.client else "—",
            "client_contact_name": t.client.contact_name if t.client else "—",
            "documents": t.documents,
            "remarks": t.remarks,
        })

    return {
        "staff": out,
        "tasks": task_list,
    }


@app.put("/api/staff/{staff_id}", response_model=schemas.StaffOut, tags=["Staff"])
def update_staff(staff_id: int, payload: schemas.StaffUpdate, db: Session = Depends(get_db)):
    staff = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found.")

    dump = payload.model_dump(exclude_unset=True)

    if "name" in dump:
        clean_name = dump["name"].strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Staff name cannot be empty.")
        old_name = staff.name
        staff.name = clean_name
        # Also update assigned_staff string on linked tasks
        db.query(models.ClientTask).filter(
            or_(models.ClientTask.staff_id == staff.id, models.ClientTask.assigned_staff == old_name)
        ).update({"assigned_staff": clean_name, "staff_id": staff.id}, synchronize_session=False)

    if "email" in dump:
        new_email = dump["email"].strip().lower() if dump["email"] else None
        if new_email and new_email != staff.email:
            existing_email = db.query(models.Staff).filter(
                models.Staff.email == new_email,
                models.Staff.id != staff_id,
            ).first()
            if existing_email:
                raise HTTPException(status_code=400, detail="A staff member with this email already exists.")
        staff.email = new_email

    if "mobile_number" in dump:
        raw_m = "".join(c for c in str(dump["mobile_number"]) if c.isdigit()) if dump["mobile_number"] else None
        staff.mobile_number = raw_m

    if "role" in dump and dump["role"]:
        staff.role = dump["role"].strip()

    if "is_active" in dump and dump["is_active"] is not None:
        staff.is_active = bool(dump["is_active"])

    db.commit()
    db.refresh(staff)

    tasks_query = db.query(models.ClientTask).filter(
        or_(models.ClientTask.staff_id == staff.id, models.ClientTask.assigned_staff == staff.name)
    )
    out = schemas.StaffOut.model_validate(staff)
    out.task_count = tasks_query.count()
    out.active_task_count = tasks_query.filter(
        ~models.ClientTask.status.in_([models.TaskStatus.COMPLETED, models.TaskStatus.CANCELLED])
    ).count()
    return out


@app.patch("/api/staff/{staff_id}/toggle-status", response_model=schemas.StaffOut, tags=["Staff"])
def toggle_staff_status(staff_id: int, db: Session = Depends(get_db)):
    staff = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found.")

    staff.is_active = not staff.is_active
    db.commit()
    db.refresh(staff)

    tasks_query = db.query(models.ClientTask).filter(
        or_(models.ClientTask.staff_id == staff.id, models.ClientTask.assigned_staff == staff.name)
    )
    out = schemas.StaffOut.model_validate(staff)
    out.task_count = tasks_query.count()
    out.active_task_count = tasks_query.filter(
        ~models.ClientTask.status.in_([models.TaskStatus.COMPLETED, models.TaskStatus.CANCELLED])
    ).count()
    return out


@app.delete("/api/staff/{staff_id}", tags=["Staff"])
def delete_staff(staff_id: int, db: Session = Depends(get_db)):
    staff = db.query(models.Staff).filter(models.Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found.")

    staff_name = staff.name
    # Unlink tasks before deletion so tasks are preserved
    db.query(models.ClientTask).filter(models.ClientTask.staff_id == staff.id).update(
        {"staff_id": None}, synchronize_session=False
    )
    db.query(models.Client).filter(models.Client.assigned_staff_id == staff.id).update(
        {"assigned_staff_id": None}, synchronize_session=False
    )

    db.delete(staff)
    db.commit()
    return {"ok": True, "message": f"Staff member '{staff_name}' deleted successfully."}


