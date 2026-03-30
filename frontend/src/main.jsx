// ============================================================
// src/main.jsx — React Application Entry Point
// ============================================================
// This is the very first JavaScript file that runs in our app.
// Its only job is to find the <div id="root"> in index.html
// and tell React to take over rendering from that point on.
//
// After this file runs, React controls everything you see
// in the browser — no more plain HTML updates.
// ============================================================

// React 18+ uses createRoot instead of the older ReactDOM.render.
// StrictMode is a development helper that warns you about common mistakes.
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

// Import global CSS (dark theme, fonts, resets) defined in index.css
import "./index.css";

// Import our top-level App component — this is where routing lives
import App from "./App";

// Find the <div id="root"> in index.html, then mount our React tree into it.
// StrictMode wraps App to enable additional runtime warnings in development.
createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
