// ============================================================
// src/App.jsx — Main Application Component (Router)
// ============================================================
// This file is the "root" of our React component tree.
// Its job is to define which URL path shows which page.
//
// Architecture overview:
//   index.html  → loads main.jsx
//   main.jsx    → mounts <App />
//   App.jsx     → sets up routing (this file)
//   pages/      → individual page components
//   components/ → reusable UI pieces (Navbar, SneakerCard)
//
// Routing: We use react-router-dom v6 to map URL paths to pages.
//   /login   → LoginPage
//   /signup  → SignupPage
//   /        → HomePage (protected — must be logged in)
//
// Authentication: After a successful login, we store the user's
// JWT access token in localStorage. PrivateRoute checks for
// that token to decide whether to show the page or redirect to /login.
// ============================================================

import { useEffect, useState } from "react";
// BrowserRouter  — wraps the whole app so routing context is available everywhere
// Routes         — container that holds all Route definitions
// Route          — maps a URL path to a component
// Navigate       — programmatically redirects (like a redirect tag)
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";

import api from "./api";
import LandingPage from "./pages/LandingPage";
import LoginPage  from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import HomePage   from "./pages/HomePage";
import CartPage   from "./pages/CartPage";

// ============================================================
// PrivateRoute — A "guard" component that protects pages
// ============================================================
// In Software Engineering terms this is an access-control check.
// If the user has a stored token they are considered logged in,
// so we render whatever children were passed in (the real page).
// Otherwise we redirect them to /login.
//
// Usage: <PrivateRoute><HomePage /></PrivateRoute>
// ============================================================
function PrivateRoute({ children }) {
  const location = useLocation();
  // localStorage is a browser key-value store that persists across
  // page refreshes (unlike regular variables which reset on refresh).
  // We stored the JWT access token here after a successful login.
  const token = localStorage.getItem("access_token");

  // If there is no token, the user is not logged in.
  // <Navigate> is react-router's way of doing a redirect.
  // replace={true} means the /login URL replaces the current history
  // entry instead of pushing a new one (so the back button works cleanly).
  if (!token) {
    return <Navigate to="/login" replace state={{ redirectTo: location.pathname }} />;
  }

  // Token exists → user is authenticated → show the real page
  return children;
}

// ============================================================
// App — The root component
// ============================================================
// BrowserRouter provides the routing context to the whole tree.
// Routes contains all route definitions.
// Route maps each path to a page component.
// ============================================================
function App() {
  const [cartItems, setCartItems] = useState([]);
  // authToken must be React state — not a plain variable — so that the
  // cart-loading effect re-fires when a different user logs in or out.
  // App is the *parent* of BrowserRouter, so it does NOT re-render on
  // route changes; only state changes can trigger a re-render here.
  const [authToken, setAuthToken] = useState(() =>
    localStorage.getItem("access_token")
  );

  // Listen for the custom "auth-changed" event dispatched by login,
  // signup, and logout handlers whenever they update localStorage.
  useEffect(() => {
    const handleAuthChange = () => {
      setAuthToken(localStorage.getItem("access_token"));
    };
    window.addEventListener("auth-changed", handleAuthChange);
    return () => window.removeEventListener("auth-changed", handleAuthChange);
  }, []);

  const normalizeCart = (cart) =>
    (cart?.items ?? []).map((item) => ({
      id: item.id,
      slug: item.product_slug,
      name: item.product_name,
      brand: item.brand,
      description: item.description,
      accent: item.accent,
      image: item.image_url,
      price: Number(item.unit_price),
      quantity: item.quantity,
    }));

  useEffect(() => {
    if (!authToken) {
      setCartItems([]);
      return;
    }

    api
      .get("/api/cart/")
      .then((response) => {
        setCartItems(normalizeCart(response.data));
      })
      .catch(() => {
        setCartItems([]);
      });
  }, [authToken]);

  const addToCart = async (sneaker) => {
    const response = await api.post("/api/cart/items/", {
      product_slug: sneaker.slug,
      product_name: sneaker.name,
      brand: sneaker.brand,
      description: sneaker.description,
      accent: sneaker.accent ?? "",
      image_url: sneaker.image ?? "",
      unit_price: sneaker.price,
      quantity: 1,
    });

    setCartItems(normalizeCart(response.data));
  };

  const updateCartQuantity = async (id, quantity) => {
    const response = await api.patch(`/api/cart/items/${id}/`, { quantity });
    setCartItems(normalizeCart(response.data));
  };

  const removeFromCart = async (id) => {
    const response = await api.delete(`/api/cart/items/${id}/delete/`);
    setCartItems(normalizeCart(response.data));
  };

  const cartCount = cartItems.reduce((sum, item) => sum + item.quantity, 0);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes — anyone can visit these */}
        <Route
          path="/"
          element={<LandingPage onAddToCart={addToCart} />}
        />
        <Route path="/login"  element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        {/*
          Protected route — only logged-in users can visit /.
          We wrap HomePage inside PrivateRoute, which checks for
          a valid token before rendering the page.
        */}
        <Route
          path="/home"
          element={
            <PrivateRoute>
              <HomePage onAddToCart={addToCart} cartCount={cartCount} />
            </PrivateRoute>
          }
        />

        <Route
          path="/cart"
          element={
            <PrivateRoute>
              <CartPage
                cartItems={cartItems}
                onUpdateQuantity={updateCartQuantity}
                onRemoveFromCart={removeFromCart}
                cartCount={cartCount}
              />
            </PrivateRoute>
          }
        />

        {/*
          Catch-all: any URL that doesn't match above redirects to /.
          If the user is not logged in, PrivateRoute will then send
          them to /login.
        */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
