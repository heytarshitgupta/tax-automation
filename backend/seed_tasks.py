"""
seed_tasks.py
Populate initial realistic sample compliance tasks for tax automation clients.
"""
from datetime import date, timedelta
import database
import models

def seed():
    db = database.SessionLocal()
    try:
        count = db.query(models.ClientTask).count()
        if count > 0:
            print(f"client_tasks already has {count} tasks. Skipping seed.")
            return

        clients = db.query(models.Client).all()
        if not clients:
            print("No clients found to associate tasks with.")
            return

        client_map = {c.business_name: c.id for c in clients}
        today = date.today()

        sample_tasks = [
            {
                "client_id": client_map.get("Sharma Traders", clients[0].id),
                "matter": "GSTR-3B Filing (August)",
                "assigned_staff": "Rahul Sharma",
                "date_assigned": today - timedelta(days=5),
                "due_date": today + timedelta(days=3),
                "next_followup_date": today + timedelta(days=1),
                "status": models.TaskStatus.IN_PROGRESS,
                "remarks": "Sales register verified. Awaiting final ITC match report from GST portal.",
                "documents": "Sales bills, Purchase 2B statement, ITC ledger summary",
            },
            {
                "client_id": client_map.get("Verma Textiles", clients[1].id if len(clients) > 1 else clients[0].id),
                "matter": "Monthly Bookkeeping & Sales Reconciliation",
                "assigned_staff": "Pooja Verma",
                "date_assigned": today - timedelta(days=7),
                "due_date": today - timedelta(days=1),  # Overdue!
                "next_followup_date": today,
                "status": models.TaskStatus.WAITING_DOCUMENTS,
                "remarks": "Bank statements for August still missing. Followed up twice on phone.",
                "documents": "HDFC current account statement (Aug), Vendor debit notes",
            },
            {
                "client_id": client_map.get("Patiala Auto Parts", clients[2].id if len(clients) > 2 else clients[0].id),
                "matter": "TDS 26Q Quarterly Return Filing",
                "assigned_staff": "Ankit Gupta",
                "date_assigned": today - timedelta(days=10),
                "due_date": today,  # Due today!
                "next_followup_date": today,
                "status": models.TaskStatus.UNDER_REVIEW,
                "remarks": "Challans reconciled with OLTAS. Return file generated via Conso file.",
                "documents": "TDS payment challans, Salary sheet, Contractor 194C invoices",
            },
            {
                "client_id": client_map.get("Kapoor & Associates", clients[3].id if len(clients) > 3 else clients[0].id),
                "matter": "Income Tax Audit Form 3CA/3CD",
                "assigned_staff": "CA Tarun Mehta",
                "date_assigned": today - timedelta(days=14),
                "due_date": today + timedelta(days=12),
                "next_followup_date": today + timedelta(days=3),
                "status": models.TaskStatus.IN_PROGRESS,
                "remarks": "Depreciation schedule pending verification. Section 43B disallowances noted.",
                "documents": "Audited Balance Sheet, Trial Balance, Form 26AS, Tax Audit annexures",
            },
            {
                "client_id": client_map.get("Singh Electronics", clients[4].id if len(clients) > 4 else clients[0].id),
                "matter": "GST Registration Amendment (Additional Place of Business)",
                "assigned_staff": "Pooja Verma",
                "date_assigned": today - timedelta(days=2),
                "due_date": today + timedelta(days=6),
                "next_followup_date": today + timedelta(days=2),
                "status": models.TaskStatus.PENDING,
                "remarks": "Client requested addition of new warehouse in Ludhiana on GST portal.",
                "documents": "Electricity bill of warehouse, Rent agreement, NOC from owner",
            },
            {
                "client_id": client_map.get("Bansal Consultancy", clients[5].id if len(clients) > 5 else clients[0].id),
                "matter": "Advance Tax Computation Q2 (15% Installment)",
                "assigned_staff": "Ankit Gupta",
                "date_assigned": today - timedelta(days=8),
                "due_date": today - timedelta(days=2),
                "next_followup_date": None,
                "status": models.TaskStatus.COMPLETED,
                "remarks": "Estimated taxable income calculated. Challan ITNS 280 paid & receipt shared.",
                "documents": "Profit & Loss estimate, Bank interest cert, Advance tax challan",
            },
        ]

        for item in sample_tasks:
            task = models.ClientTask(**item)
            db.add(task)

        db.commit()
        print(f"Successfully seeded {len(sample_tasks)} client tasks!")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
