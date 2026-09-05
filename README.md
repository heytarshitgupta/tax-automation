# Gateway Solutions — WhatsApp Tax Office Automation System (MVP)

Automates GST reminders, document requests, and billing notifications to tax clients
via the **Meta WhatsApp Cloud API**.

**Stack:** Vue 3 (Composition API) · FastAPI (Python) · MySQL · APScheduler

---

## 1. Project Structure

```
gateway-whatsapp-tax/
├── backend/
│   ├── schema.sql            # MySQL schema + dummy data
│   ├── main.py                # FastAPI app, all REST endpoints
│   ├── database.py            # SQLAlchemy engine/session
│   ├── models.py              # ORM models
│   ├── schemas.py             # Pydantic request/response models
│   ├── whatsapp_service.py    # Meta WhatsApp Cloud API integration
│   ├── scheduler.py           # APScheduler daily 09:00 automation job
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.vue                    # Sidebar layout shell
    │   ├── main.js
    │   ├── router/index.js
    │   ├── services/api.js            # Axios client + error handling
    │   ├── views/DashboardView.vue
    │   ├── views/ClientManager.vue
    │   ├── views/CommunicationLog.vue
    │   └── assets/main.css
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── .env.example
```

---

## 2. Database Setup (MySQL)

1. Make sure MySQL 8+ is running locally.
2. Load the schema and dummy data:

```bash
mysql -u root -p < backend/schema.sql
```

This creates the `gateway_tax_automation` database with `clients`, `categories`,
`compliance_dates`, `invoices`, and `message_history` tables, plus sample rows for
immediate testing.

---

## 3. Backend Setup (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your real MySQL credentials and Meta WhatsApp credentials
```

### Where to insert Meta developer credentials

Open `backend/.env` and set:

```
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_permanent_access_token
```

Get these from **https://developers.facebook.com/apps** → your app → **WhatsApp → API Setup**.
You'll also need to create and get approval for message templates named
`gst_reminder`, `document_request`, and `billing_notification` in Meta Business Manager
(see `whatsapp_service.py` for the exact parameter order each template expects).

### Run the API

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- Interactive API docs: http://localhost:8000/docs
- The APScheduler background job starts automatically with the app and fires daily at **09:00 (Asia/Kolkata)**.
- To test the automation without waiting, call `POST /api/scheduler/run-now` (also available as a button on the Dashboard).

---

## 4. Frontend Setup (Vue 3)

```bash
cd frontend
npm install
cp .env.example .env   # only needed if backend isn't on localhost:8000
npm run dev
```

Visit **http://localhost:5173**.

---

## 5. Core Features Implemented

| Feature | Location |
|---|---|
| Client / Category CRUD | `backend/main.py`, `frontend/src/views/ClientManager.vue` |
| Dashboard metrics (total/active clients, messages sent today) | `GET /api/dashboard`, `DashboardView.vue` |
| WhatsApp template message sender | `whatsapp_service.py` |
| Daily 09:00 compliance reminder automation (7/3/1-day windows) | `scheduler.py` |
| Communication / message history log | `GET /api/message-history`, `CommunicationLog.vue` |
| Manual invoice billing notification trigger | `POST /api/invoices/{id}/send` |
| Manual document request trigger | `POST /api/clients/{id}/send-document-request` |

## 6. Notes for Production Hardening (post-MVP)

- Add authentication (e.g. JWT) to protect all `/api` routes.
- Move WhatsApp template names/params into a DB-managed template table.
- Add a webhook receiver endpoint for Meta delivery/read receipts to update `message_history.status` automatically.
- Add pagination to `/api/clients` and `/api/message-history` for large datasets.
- Use Alembic for schema migrations instead of `Base.metadata.create_all`.
