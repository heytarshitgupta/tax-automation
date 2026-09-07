"""
scheduler.py
Background job engine (APScheduler) that runs daily at 09:00 to:
  1. Find compliance_dates that fall 7, 3, or 1 day(s) from today.
  2. Match them to active clients in the same category.
  3. Trigger a WhatsApp reminder for each matching client.
  4. Log every attempt into message_history.
"""
import logging
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from database import SessionLocal
from models import Client, Category, ComplianceDate, MessageHistory, MessageStatus
from whatsapp_service import send_gst_reminder

logger = logging.getLogger("scheduler")
logging.basicConfig(level=logging.INFO)

# Reminder windows required by the spec
REMINDER_WINDOWS_DAYS = [7, 3, 1]


def run_compliance_reminder_job():
    """
    Core automation job. Queries the DB for upcoming compliance dates in the
    reminder windows, and fires a WhatsApp template message to every active
    client in the matching category.
    """
    db = SessionLocal()
    logger.info("Running daily compliance reminder job...")
    try:
        today = date.today()
        total_sent, total_failed = 0, 0

        for days_ahead in REMINDER_WINDOWS_DAYS:
            target_date = today + timedelta(days=days_ahead)

            # Find compliance dates due exactly `days_ahead` days from now
            due_items = (
                db.query(ComplianceDate)
                .filter(ComplianceDate.due_date == target_date)
                .all()
            )

            for compliance in due_items:
                # Match active clients belonging to this compliance's category (many-to-many or legacy single)
                matching_clients = (
                    db.query(Client)
                    .filter(
                        (Client.categories.any(Category.id == compliance.category_id))
                        | (Client.category_id == compliance.category_id),
                        Client.is_active == True,  # noqa: E712
                    )
                    .all()
                )

                for client in matching_clients:
                    result = send_gst_reminder(
                        to_number=client.mobile_number,
                        business_name=client.business_name,
                        days_left=days_ahead,
                        due_date=compliance.due_date.strftime("%d-%b-%Y"),
                    )

                    status = MessageStatus.SENT if result["success"] else MessageStatus.FAILED
                    if result["success"]:
                        total_sent += 1
                    else:
                        total_failed += 1

                    history_entry = MessageHistory(
                        client_id=client.id,
                        message_type="GST_REMINDER",
                        message_content=(
                            f"{compliance.description} due on "
                            f"{compliance.due_date.strftime('%d-%b-%Y')} "
                            f"({days_ahead} day(s) remaining)."
                        ),
                        status=status,
                    )
                    db.add(history_entry)

        db.commit()
        logger.info(
            "Compliance reminder job finished. Sent=%s Failed=%s", total_sent, total_failed
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("Compliance reminder job failed: %s", exc)
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    """
    Initializes and starts the APScheduler instance.
    Runs `run_compliance_reminder_job` every day at 09:00 server time.
    """
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(
        run_compliance_reminder_job,
        trigger=CronTrigger(hour=9, minute=0),
        id="daily_compliance_reminder",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info("APScheduler started. Daily reminder job scheduled for 09:00 (Asia/Kolkata).")
    return scheduler
