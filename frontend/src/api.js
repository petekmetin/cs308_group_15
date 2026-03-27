// ============================================================
// src/api.js — Axios HTTP Client Configuration
// ============================================================
// This file creates a pre-configured axios "instance" that all
// pages use to talk to our Django backend.
//
// Why a shared instance instead of plain fetch() or axios()?
//   1. We set baseURL once — no need to repeat http://localhost:8000
//      in every component.
//   2. We use an "interceptor" to automatically attach the JWT
//      access token to every request, so individual pages don't
//      have to remember to add the Authorization header.
//
// Data flow for an authenticated request:
//   Component calls api.get('/api/auth/me/')
//     → interceptor adds header: Authorization: Bearer <token>
//     → Django receives request, validates token, returns data
//     → Component receives response
// ============================================================

// axios is a popular HTTP library for making API requests.
// It is similar to the browser's built-in fetch(), but with a
// cleaner API and automatic JSON parsing.
import axios from "axios";

// ── Base URL ───────────────────────────────────────────────
// All requests will be prefixed with this URL.
// In development our Django backend runs on port 8000.
// Vite's import.meta.env reads variables from a .env file —
// if none is set we fall back to the local development server.
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// ── Create the axios instance ──────────────────────────────
// Think of this like creating a "configured HTTP client" object.
// Every call made through `api` will automatically use these settings.
const api = axios.create({
  baseURL: API_BASE_URL,

  // Tell Django we're sending/receiving JSON data
  headers: {
    "Content-Type": "application/json",
  },
});

// ── Request Interceptor ────────────────────────────────────
// An interceptor is a function that runs BEFORE every request is sent.
// Here we use it to attach the JWT token to the Authorization header.
//
// JWT (JSON Web Token) is a string that proves "this user is logged in."
// Django checks this header on every protected endpoint.
// The format Django expects is: "Bearer <the_token_string>"
api.interceptors.request.use((config) => {
  // Retrieve the token we saved to localStorage during login
  const token = localStorage.getItem("access_token");

  if (token) {
    // Attach the token as a Bearer token in the Authorization header.
    // Every request made through this api instance will include this header.
    config.headers.Authorization = `Bearer ${token}`;
  }

  // Always return the config object so axios can proceed with the request
  return config;
});

export default api;
