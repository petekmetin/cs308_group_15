# SOLEVAULT Frontend

This repository now contains the frontend-only version of the sneaker project.

## What is included

- `frontend/` Vite + React + TypeScript app
- SOLEVAULT landing page, category browsing, cart flow, and localStorage-based sign in/register demo

## What was removed

- Django backend
- backend seed/data files
- old multi-page dashboard/storefront modules
- generated local environment folders

## Run locally

```bash
cd frontend
npm install
npm run dev
```

## Build

```bash
cd frontend
npm run build
```

## Notes

- Authentication and cart state are stored in `localStorage` so the frontend works without an API.
- This workspace was cleaned for a frontend-only GitHub upload.
