# How to Run the Project

## Prerequisites
- Python 3 installed
- Node.js and npm installed

---

## Backend (Django)

Open a terminal and run:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py runserver
```

> **Note:** After the first time, you only need to run:
> ```bash
> source venv/bin/activate
> python manage.py runserver
> ```

Backend runs at: http://127.0.0.1:8000

---

## Frontend (React + Vite)

Open a **new terminal** and run:

```bash
cd frontend
npm install
npm run dev
```

> **Note:** After the first time, you only need to run:
> ```bash
> npm run dev
> ```

Frontend runs at: http://localhost:5173

---

## Test Accounts

| Role             | Email                  | Password     |
|------------------|------------------------|--------------|
| Customer         | customer@test.com      | TestPass123! |
| Sales Manager    | sales@test.com         | TestPass123! |
| Product Manager  | product@test.com       | TestPass123! |
