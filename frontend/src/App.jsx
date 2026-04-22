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
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from "react-router-dom";

import api from "./api";
import {
  addToGuestCart,
  clearGuestCart,
  getGuestCart,
  mergeGuestCartToServer,
  removeGuestCartItem,
  updateGuestCartItem,
} from "./utils/cart";
import LandingPage from "./pages/LandingPage";
import LoginPage  from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import HomePage   from "./pages/HomePage";
import CartPage   from "./pages/CartPage";
import OrdersPage from "./pages/OrdersPage";
import ProductManagerDashboard from "./pages/ProductManagerDashboard";
import SneakerDetail from "./pages/SneakerDetail";

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
  const [authToken, setAuthToken] = useState(() =>
    localStorage.getItem("access_token")
  );
  const [addToast, setAddToast] = useState(null);

  // Initialise from guest cart when not logged in.
  const [cartItems, setCartItems] = useState(() =>
    localStorage.getItem("access_token") ? [] : getGuestCart()
  );

  useEffect(() => {
    const handleAuthChange = () => {
      setAuthToken(localStorage.getItem("access_token"));
    };
    window.addEventListener("auth-changed", handleAuthChange);
    return () => window.removeEventListener("auth-changed", handleAuthChange);
  }, []);

  const normalizeCart = (cart) =>
    [...(cart?.items ?? [])]
      .sort((a, b) => Number(a.id || 0) - Number(b.id || 0))
      .map((item) => ({
      id: item.id,
      slug: item.product_slug,
      name: item.product_name,
      brand: item.brand,
      description: item.description,
      accent: item.accent,
      image: item.image_url,
      size_id: item.size_id,
      size: item.size,
      size_system: item.size_system,
      product_id: Number(String(item.product_slug || "").replace("sneaker-", "")) || null,
      price: Number(item.unit_price),
      quantity: item.quantity,
      }));

  const clearStaleAuth = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    localStorage.removeItem("user_role");
    window.dispatchEvent(new Event("auth-changed"));
  };

  const showAddToast = (sneaker, sizeOption) => {
    const sizeLabel = `${sizeOption.size_system} ${sizeOption.size}`;
    setAddToast({
      key: Date.now(),
      message: `${sneaker.name} (${sizeLabel}) added to cart.`,
    });
  };

  useEffect(() => {
    if (!addToast) {
      return undefined;
    }
    const timer = setTimeout(() => setAddToast(null), 6000);
    return () => clearTimeout(timer);
  }, [addToast]);

  useEffect(() => {
    if (!authToken) {
      setCartItems(getGuestCart());
      return;
    }

    const load = async () => {
      await mergeGuestCartToServer();
      try {
        const response = await api.get("/api/cart/");
        setCartItems(normalizeCart(response.data));
      } catch {
        setCartItems([]);
      }
    };

    load();
  }, [authToken]);

  const addToCart = async (sneaker, sizeOption) => {
    if (!sizeOption?.id) {
      throw new Error("Please select a size before adding to cart.");
    }

    if (!authToken) {
      const nextCart = addToGuestCart(sneaker, sizeOption);
      setCartItems(nextCart);
      showAddToast(sneaker, sizeOption);
      return;
    }
    const productId   = sneaker.product_id ?? sneaker.id;
    const productSlug = sneaker.slug || (productId ? `sneaker-${productId}` : "");
    try {
      const response = await api.post("/api/cart/items/", {
        product_id:   productId,
        size_id:      sizeOption.id,
        product_slug: productSlug,
        product_name: sneaker.name,
        brand:        sneaker.brand,
        description:  sneaker.description,
        accent:       sneaker.accent ?? "",
        image_url:    sneaker.image  ?? "",
        unit_price:   sneaker.price,
        quantity:     1,
      });
      setCartItems(normalizeCart(response.data));
      showAddToast(sneaker, sizeOption);
    } catch (error) {
      if (error?.response?.status === 401) {
        clearStaleAuth();
        const nextCart = addToGuestCart(sneaker, sizeOption);
        setCartItems(nextCart);
        showAddToast(sneaker, sizeOption);
        return;
      }
      throw error;
    }
  };

  const updateCartQuantity = async (id, quantity) => {
    if (!authToken) {
      const currentItem = cartItems.find((item) => item.id === id);
      if (currentItem && quantity > currentItem.quantity) {
        const sneakerId =
          currentItem.product_id ??
          Number(String(currentItem.slug || "").replace("sneaker-", ""));
        const response = await api.get(`/api/products/sneakers/${sneakerId}/`);
        const selectedSize = (response.data?.sizes || []).find(
          (size) => size.id === currentItem.size_id
        );
        const stock = Number(selectedSize?.stock ?? 0);

        if (!selectedSize) {
          throw new Error("The selected size is no longer available.");
        }
        if (quantity > stock) {
          throw new Error(
            `Only ${stock} left for size ${selectedSize.size_system} ${selectedSize.size}.`
          );
        }
      }
      setCartItems(updateGuestCartItem(id, quantity));
      return;
    }
    const response = await api.patch(`/api/cart/items/${id}/`, { quantity });
    setCartItems(normalizeCart(response.data));
  };

  const removeFromCart = async (id) => {
    if (!authToken) {
      setCartItems(removeGuestCartItem(id));
      return;
    }
    const response = await api.delete(`/api/cart/items/${id}/delete/`);
    setCartItems(normalizeCart(response.data));
  };

  const clearCart = async () => {
    if (!authToken) {
      clearGuestCart();
      setCartItems([]);
      return;
    }
    await api.post("/api/cart/clear/");
    setCartItems([]);
  };

  const cartCount = cartItems.reduce((sum, item) => sum + item.quantity, 0);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes — anyone can visit these */}
        <Route
          path="/"
          element={<LandingPage onAddToCart={addToCart} cartCount={cartCount} />}
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
          path="/manager/dashboard"
          element={
            <PrivateRoute>
              <ProductManagerDashboard cartCount={cartCount} />
            </PrivateRoute>
          }
        />

        <Route
          path="/sneakers/:id"
          element={
            <PrivateRoute>
              <SneakerDetail cartCount={cartCount} />
            </PrivateRoute>
          }
        />

        <Route
          path="/cart"
          element={
            <CartPage
              cartItems={cartItems}
              onUpdateQuantity={updateCartQuantity}
              onRemoveFromCart={removeFromCart}
              onClearCart={clearCart}
              cartCount={cartCount}
            />
          }
        />

        <Route
          path="/orders"
          element={
            <PrivateRoute>
              <OrdersPage cartCount={cartCount} />
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

      {addToast ? (
        <div className="cart-action-toast" key={addToast.key}>
          <p>{addToast.message}</p>
          <div className="cart-action-toast-actions">
            <Link to="/cart" className="landing-primary-btn" onClick={() => setAddToast(null)}>
              Go to Cart
            </Link>
            <button
              type="button"
              className="landing-secondary-btn"
              onClick={() => setAddToast(null)}
            >
              Continue Shopping
            </button>
          </div>
        </div>
      ) : null}
    </BrowserRouter>
  );
}

export default App;
