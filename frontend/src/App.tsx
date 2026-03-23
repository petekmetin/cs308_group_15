import axios from "axios";
import { useEffect, useMemo, useState, type FormEvent } from "react";

type Page = "home" | "shop" | "cart" | "login" | "register" | "profile";

type Product = {
  id: number;
  name: string;
  brand: string;
  category: string;
  price: number;
  rating: number;
  reviews: number;
  stock: number;
  description: string;
  popularity: number;
  emoji: string;
};

type CartItem = Product & {
  quantity: number;
};

type AuthUser = {
  id: number;
  firstName: string;
  lastName: string;
  username: string;
  email: string;
};

const BRANDS = ["Nike", "Adidas", "Jordan", "New Balance", "Puma", "Converse", "Reebok", "Vans"];
const CATEGORIES = ["Running", "Basketball", "Lifestyle", "Skateboarding", "Training", "Classics"];

const CATEGORY_ICONS: Record<string, string> = {
  Running: "🏃",
  Basketball: "🏀",
  Lifestyle: "✦",
  Skateboarding: "🛹",
  Training: "🔥",
  Classics: "✶",
};

const PRODUCTS: Product[] = [
  { id: 1, name: "Air Max 97", brand: "Nike", category: "Lifestyle", price: 175, rating: 4.7, reviews: 342, stock: 12, description: "Heritage running style.", popularity: 95, emoji: "👟" },
  { id: 2, name: "Ultraboost 23", brand: "Adidas", category: "Running", price: 190, rating: 4.8, reviews: 518, stock: 8, description: "Responsive Boost cushioning.", popularity: 92, emoji: "👟" },
  { id: 3, name: "Retro 4 'Bred'", brand: "Jordan", category: "Basketball", price: 210, rating: 4.9, reviews: 1204, stock: 3, description: "Iconic AJ4 in Bred colorway.", popularity: 99, emoji: "🏆" },
  { id: 4, name: "550 White Green", brand: "New Balance", category: "Lifestyle", price: 110, rating: 4.5, reviews: 876, stock: 22, description: "Heritage court comfort.", popularity: 88, emoji: "👟" },
  { id: 5, name: "Suede Classic", brand: "Puma", category: "Classics", price: 75, rating: 4.3, reviews: 203, stock: 30, description: "Timeless icon since 1968.", popularity: 78, emoji: "⚡" },
  { id: 6, name: "Chuck 70 Hi", brand: "Converse", category: "Lifestyle", price: 90, rating: 4.6, reviews: 654, stock: 18, description: "Premium canvas, vintage details.", popularity: 85, emoji: "👟" },
  { id: 7, name: "Club C 85", brand: "Reebok", category: "Classics", price: 80, rating: 4.4, reviews: 312, stock: 25, description: "Clean leather from '85.", popularity: 80, emoji: "✨" },
  { id: 8, name: "Old Skool", brand: "Vans", category: "Skateboarding", price: 70, rating: 4.5, reviews: 921, stock: 35, description: "The sidestripe original.", popularity: 90, emoji: "🛹" },
  { id: 9, name: "Dunk Low Panda", brand: "Nike", category: "Lifestyle", price: 115, rating: 4.7, reviews: 2103, stock: 0, description: "Black and white streetwear icon.", popularity: 98, emoji: "🐼" },
  { id: 10, name: "Forum Low", brand: "Adidas", category: "Basketball", price: 100, rating: 4.4, reviews: 445, stock: 14, description: "Retro basketball with ankle strap.", popularity: 82, emoji: "🏀" },
  { id: 11, name: "Gel-Kayano 14", brand: "Nike", category: "Running", price: 150, rating: 4.6, reviews: 278, stock: 9, description: "Y2K runner aesthetics.", popularity: 87, emoji: "🌪" },
  { id: 12, name: "RS-X Reinvention", brand: "Puma", category: "Training", price: 120, rating: 4.2, reviews: 167, stock: 20, description: "Bold chunky silhouette.", popularity: 74, emoji: "🔥" },
];

const loadJson = <T,>(key: string, fallback: T): T => {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
};

function App() {
  const [page, setPage] = useState<Page>("home");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("popularity");
  const [category, setCategory] = useState("All");
  const [cart, setCart] = useState<CartItem[]>(() => loadJson<CartItem[]>("sv_cart", []));
  const [user, setUser] = useState<AuthUser | null>(() => loadJson<AuthUser | null>("sv_user", null));
  const [token, setToken] = useState<string | null>(() => window.localStorage.getItem("sv_token"));
  const [toast, setToast] = useState<{ message: string; ok: boolean } | null>(null);
  const [loginError, setLoginError] = useState("");
  const [registerError, setRegisterError] = useState("");
  const [showBillingFields, setShowBillingFields] = useState(false);
  const [isAuthSubmitting, setIsAuthSubmitting] = useState(false);
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

  useEffect(() => {
    window.localStorage.setItem("sv_cart", JSON.stringify(cart));
  }, [cart]);

  useEffect(() => {
    if (user) {
      window.localStorage.setItem("sv_user", JSON.stringify(user));
    } else {
      window.localStorage.removeItem("sv_user");
    }
  }, [user]);

  useEffect(() => {
    if (token) {
      window.localStorage.setItem("sv_token", token);
    } else {
      window.localStorage.removeItem("sv_token");
    }
  }, [token]);

  useEffect(() => {
    if (!toast) {
      return;
    }

    const timeoutId = window.setTimeout(() => setToast(null), 3000);
    return () => window.clearTimeout(timeoutId);
  }, [toast]);

  const filteredProducts = useMemo(() => {
    const query = search.trim().toLowerCase();

    return PRODUCTS.filter((product) => {
      const matchesSearch =
        !query ||
        product.name.toLowerCase().includes(query) ||
        product.description.toLowerCase().includes(query) ||
        product.brand.toLowerCase().includes(query);
      const matchesCategory = category === "All" || product.category === category;

      return matchesSearch && matchesCategory;
    }).sort((left, right) => {
      if (sort === "price-asc") {
        return left.price - right.price;
      }

      if (sort === "price-desc") {
        return right.price - left.price;
      }

      if (sort === "rating") {
        return right.rating - left.rating;
      }

      return right.popularity - left.popularity;
    });
  }, [category, search, sort]);

  const cartCount = cart.reduce((total, item) => total + item.quantity, 0);
  const cartTotal = cart.reduce((total, item) => total + item.price * item.quantity, 0);

  const navigate = (nextPage: Page) => {
    setPage(nextPage);
    setMobileNavOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const showToast = (message: string, ok = true) => {
    setToast({ message, ok });
  };

  const addToCart = (productId: number) => {
    const product = PRODUCTS.find((entry) => entry.id === productId);
    if (!product || product.stock === 0) {
      return;
    }

    const existing = cart.find((entry) => entry.id === productId);
    if (existing && existing.quantity >= product.stock) {
      showToast("Max stock reached", false);
      return;
    }

    setCart((currentCart) => {
      const current = currentCart.find((entry) => entry.id === productId);
      if (!current) {
        return [...currentCart, { ...product, quantity: 1 }];
      }

      return currentCart.map((entry) =>
        entry.id === productId ? { ...entry, quantity: entry.quantity + 1 } : entry,
      );
    });

    showToast(`${product.name} added to cart`);
  };

  const updateQuantity = (productId: number, delta: number) => {
    const product = PRODUCTS.find((entry) => entry.id === productId);
    if (!product) {
      return;
    }

    const current = cart.find((entry) => entry.id === productId);
    if (!current) {
      return;
    }

    const nextQuantity = current.quantity + delta;
    if (nextQuantity > product.stock) {
      showToast("Max stock reached", false);
      return;
    }

    setCart((currentCart) =>
      currentCart
        .map((entry) => (entry.id === productId ? { ...entry, quantity: entry.quantity + delta } : entry))
        .filter((entry) => entry.quantity > 0),
    );
  };

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsAuthSubmitting(true);
    setLoginError("");
    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "").trim().toLowerCase();
    const password = String(formData.get("password") ?? "");

    try {
      const response = await axios.post(`${API_BASE_URL}/api/auth/login/`, { email, password });
      const { token: nextToken, user: nextUser } = response.data as { token: string; user: AuthUser };
      setToken(nextToken);
      setUser(nextUser);
      navigate("home");
      showToast("Signed in successfully");
    } catch (error) {
      const fallbackMessage = "Invalid email or password.";
      if (axios.isAxiosError(error)) {
        setLoginError((error.response?.data as { detail?: string } | undefined)?.detail ?? fallbackMessage);
      } else {
        setLoginError(fallbackMessage);
      }
    } finally {
      setIsAuthSubmitting(false);
    }
  };

  const handleRegister = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setRegisterError("");
    setIsAuthSubmitting(true);
    const formData = new FormData(event.currentTarget);

    const firstName = String(formData.get("firstName") ?? "").trim();
    const lastName = String(formData.get("lastName") ?? "").trim();
    const username = String(formData.get("username") ?? "").trim();
    const email = String(formData.get("email") ?? "").trim().toLowerCase();
    const password = String(formData.get("password") ?? "");
    const confirmPassword = String(formData.get("confirmPassword") ?? "");
    const taxId = String(formData.get("taxId") ?? "").trim();
    const homeAddress = String(formData.get("homeAddress") ?? "").trim();

    if (!firstName || !lastName || !username || !email || !password) {
      setRegisterError("Please fill in all required fields.");
      return;
    }

    if (password.length < 6) {
      setRegisterError("Password must be at least 6 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setRegisterError("Passwords do not match.");
      return;
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/api/auth/register/`, {
        first_name: firstName,
        last_name: lastName,
        username,
        email,
        password,
        tax_id: taxId,
        home_address: homeAddress,
      });
      const { token: nextToken, user: nextUser } = response.data as { token: string; user: AuthUser };
      setToken(nextToken);
      setUser(nextUser);
      navigate("home");
      showToast("Account created");
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.data) {
        const data = error.response.data as Record<string, string[] | string | undefined>;
        const firstError =
          Object.values(data).flatMap((entry) => (Array.isArray(entry) ? entry : entry ? [entry] : [])).at(0) ??
          "Registration failed.";
        setRegisterError(firstError);
      } else {
        setRegisterError("Registration failed.");
      }
    } finally {
      setIsAuthSubmitting(false);
    }
  };

  const handleLogout = async () => {
    if (token) {
      try {
        await axios.post(
          `${API_BASE_URL}/api/auth/logout/`,
          {},
          {
            headers: { Authorization: `Token ${token}` },
          },
        );
      } catch {
        // Ignore logout API failures and clear local session anyway.
      }
    }

    setToken(null);
    setUser(null);
    navigate("home");
    showToast("Signed out");
  };

  const jumpToSection = (sectionId: string) => {
    if (page !== "shop") {
      navigate("shop");
    }
    window.setTimeout(() => {
      document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 80);
  };

  return (
    <>
      {page !== "login" && page !== "register" ? (
        <nav className="navbar">
          <button className="nav-logo" onClick={() => navigate("home")} type="button">
            ✦ <span>SOLE</span>VAULT
          </button>

          <button className="mob-btn" onClick={() => setMobileNavOpen((current) => !current)} type="button">
            {mobileNavOpen ? "✕" : "☰"}
          </button>

          <div className={`nav-links ${mobileNavOpen ? "mob-open" : "desk"}`}>
            <button className={`nav-link ${page === "home" ? "active" : ""}`} onClick={() => navigate("home")} type="button">
              Home
            </button>
            <button className={`nav-link ${page === "shop" ? "active" : ""}`} onClick={() => navigate("shop")} type="button">
              Shop
            </button>
            <button className="nav-link nav-cart-link" onClick={() => navigate("cart")} type="button">
              🛒 Cart
              {cartCount > 0 ? <span className="badge">{cartCount}</span> : null}
            </button>
            {user ? (
              <>
                <button className={`nav-link ${page === "profile" ? "active" : ""}`} onClick={() => navigate("profile")} type="button">
                  👤 {user.firstName || user.username}
                </button>
                <button className="nav-btn nav-btn-ghost" onClick={handleLogout} type="button">
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <button className="nav-btn nav-btn-ghost" onClick={() => navigate("login")} type="button">
                  Sign In
                </button>
                <button className="nav-btn nav-btn-primary" onClick={() => navigate("register")} type="button">
                  Sign Up
                </button>
              </>
            )}
          </div>
        </nav>
      ) : null}

      {page === "login" ? (
        <section className="auth-page">
          <div className="auth-visual">
            <div className="auth-grid" />
            <div className="auth-glow" />
            <div className="auth-visual-inner">
              <h1>
                STEP
                <br />
                INTO
                <br />
                <span>STYLE</span>
              </h1>
              <p>Premium Sneakers • Since 2026</p>
            </div>
          </div>
          <div className="auth-form-side">
            <button className="back-home" onClick={() => navigate("home")} type="button">
              ← Back to home
            </button>
            <h2>Welcome back</h2>
            <p className="sub">Sign in to your SOLEVAULT account</p>
            {loginError ? <div className="auth-error">{loginError}</div> : null}
            <form className="auth-form" onSubmit={handleLogin}>
              <div className="fg">
                <label className="fl" htmlFor="login-email">
                  Email
                </label>
                <input className="fi" id="login-email" name="email" placeholder="you@example.com" required type="email" />
              </div>
              <div className="fg">
                <label className="fl" htmlFor="login-password">
                  Password
                </label>
                <input className="fi" id="login-password" name="password" placeholder="••••••••" required type="password" />
              </div>
              <button className="auth-submit" disabled={isAuthSubmitting} type="submit">
                {isAuthSubmitting ? "Signing In..." : "Sign In"}
              </button>
            </form>
            <p className="auth-switch">
              Don&apos;t have an account?
              <button onClick={() => navigate("register")} type="button">
                Create one
              </button>
            </p>
          </div>
        </section>
      ) : null}

      {page === "register" ? (
        <section className="auth-page">
          <div className="auth-visual">
            <div className="auth-grid" />
            <div className="auth-glow" />
            <div className="auth-visual-inner">
              <h1>
                JOIN
                <br />
                THE
                <br />
                <span>VAULT</span>
              </h1>
              <p>Your Sneaker Journey Starts Here</p>
            </div>
          </div>
          <div className="auth-form-side">
            <button className="back-home" onClick={() => navigate("home")} type="button">
              ← Back to home
            </button>
            <h2>Create account</h2>
            <p className="sub">Join SOLEVAULT and start shopping</p>
            {registerError ? <div className="auth-error">{registerError}</div> : null}
            <form className="auth-form" onSubmit={handleRegister}>
              <div className="form-row">
                <div className="fg">
                  <label className="fl" htmlFor="register-first-name">
                    First Name *
                  </label>
                  <input className="fi" id="register-first-name" name="firstName" placeholder="John" required />
                </div>
                <div className="fg">
                  <label className="fl" htmlFor="register-last-name">
                    Last Name *
                  </label>
                  <input className="fi" id="register-last-name" name="lastName" placeholder="Doe" required />
                </div>
              </div>

              <div className="fg">
                <label className="fl" htmlFor="register-username">
                  Username *
                </label>
                <input className="fi" id="register-username" name="username" placeholder="johndoe" required />
              </div>

              <div className="fg">
                <label className="fl" htmlFor="register-email">
                  Email *
                </label>
                <input className="fi" id="register-email" name="email" placeholder="you@example.com" required type="email" />
              </div>

              <div className="form-row">
                <div className="fg">
                  <label className="fl" htmlFor="register-password">
                    Password *
                  </label>
                  <input className="fi" id="register-password" name="password" placeholder="Min 6 characters" required type="password" />
                </div>
                <div className="fg">
                  <label className="fl" htmlFor="register-confirm-password">
                    Confirm *
                  </label>
                  <input className="fi" id="register-confirm-password" name="confirmPassword" placeholder="Re-enter" required type="password" />
                </div>
              </div>

              <button className="extra-toggle" onClick={() => setShowBillingFields((current) => !current)} type="button">
                {showBillingFields ? "Hide billing details" : "Add billing details (optional)"}
              </button>

              {showBillingFields ? (
                <div className="billing-fields">
                  <div className="fg">
                    <label className="fl" htmlFor="register-tax-id">
                      Tax ID
                    </label>
                    <input className="fi" id="register-tax-id" name="taxId" placeholder="Optional" />
                  </div>
                  <div className="fg">
                    <label className="fl" htmlFor="register-home-address">
                      Home Address
                    </label>
                    <input className="fi" id="register-home-address" name="homeAddress" placeholder="Optional" />
                  </div>
                </div>
              ) : null}

              <button className="auth-submit" disabled={isAuthSubmitting} type="submit">
                {isAuthSubmitting ? "Creating Account..." : "Create Account"}
              </button>
            </form>
            <p className="auth-switch">
              Already have an account?
              <button onClick={() => navigate("login")} type="button">
                Sign in
              </button>
            </p>
          </div>
        </section>
      ) : null}

      {page === "home" ? (
        <>
          <section className="hero">
            <div className="hero-grid" />
            <div className="hero-fade" />
            <div className="hero-content">
              <div className="hero-tag">
                <span className="hero-dot" />
                New Arrivals - Spring &apos;26
              </div>
              <h1>
                THE <span className="a">SOLE</span>
                <br />
                <span className="o">VAULT</span>
              </h1>
              <p className="hero-desc">
                Curated drops, timeless silhouettes, and next-gen heat. Your one-stop destination for premium sneakers.
              </p>
              <div className="hero-actions">
                <button className="btn-p" onClick={() => navigate("shop")} type="button">
                  Shop Now
                </button>
                <button className="btn-o" onClick={() => jumpToSection("cats")} type="button">
                  Browse Categories
                </button>
              </div>
            </div>
          </section>

          <div className="marquee-wrap" aria-hidden="true">
            <div className="marquee-track">
              {[...BRANDS, ...BRANDS].map((brand, index) => (
                <span className="marquee-item" key={`${brand}-${index}`}>
                  {brand.toUpperCase()} <span className="mdot" />
                </span>
              ))}
            </div>
          </div>

          <footer className="footer">
            <div className="footer-grid">
              <div className="footer-col">
                <h4>Shop</h4>
                <button className="footer-link-btn" onClick={() => jumpToSection("shop")} type="button">
                  New Arrivals
                </button>
                <button className="footer-link-btn" onClick={() => jumpToSection("shop")} type="button">
                  Best Sellers
                </button>
                <button className="footer-link-btn" onClick={() => jumpToSection("shop")} type="button">
                  Sale
                </button>
              </div>
              <div className="footer-col">
                <h4>Help</h4>
                <button className="footer-link-btn" onClick={() => jumpToSection("shop")} type="button">
                  FAQ
                </button>
                <button className="footer-link-btn" onClick={() => jumpToSection("shop")} type="button">
                  Shipping
                </button>
                <button className="footer-link-btn" onClick={() => jumpToSection("shop")} type="button">
                  Returns
                </button>
              </div>
              <div className="footer-col">
                <h4>Company</h4>
                <button className="footer-link-btn" onClick={() => navigate("home")} type="button">
                  About
                </button>
                <button className="footer-link-btn" onClick={() => navigate("home")} type="button">
                  Careers
                </button>
                <button className="footer-link-btn" onClick={() => navigate("home")} type="button">
                  Blog
                </button>
              </div>
              <div className="footer-col">
                <h4>Legal</h4>
                <button className="footer-link-btn" onClick={() => navigate("home")} type="button">
                  Privacy
                </button>
                <button className="footer-link-btn" onClick={() => navigate("home")} type="button">
                  Terms
                </button>
              </div>
            </div>
            <div className="footer-bottom">
              <p>© 2026 SOLEVAULT. All rights reserved.</p>
              <p className="footer-mark">✦ SOLEVAULT</p>
            </div>
          </footer>
        </>
      ) : null}

      {page === "shop" ? (
        <>
          <section className="sec sec-surface shop-page-top" id="cats">
            <div className="sec-head">
              <div>
                <h2>
                  Shop by <span>Category</span>
                </h2>
              </div>
            </div>
            <div className="cat-grid">
              {CATEGORIES.map((entry) => (
                <button
                  className="cat-card"
                  key={entry}
                  onClick={() => {
                    setCategory(entry);
                    jumpToSection("shop");
                  }}
                  type="button"
                >
                  <div className="cat-icon">{CATEGORY_ICONS[entry]}</div>
                  <div className="cat-name">{entry}</div>
                </button>
              ))}
            </div>
          </section>

          <section className="sec" id="shop">
            <div className="sec-head">
              <div>
                <h2>
                  All <span>Sneakers</span>
                </h2>
                <p>
                  {filteredProducts.length} product{filteredProducts.length === 1 ? "" : "s"}
                </p>
              </div>
            </div>

            <div className="filter-bar">
              <div className="search-wrap">
                <span className="ico">⌕</span>
                <input
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search by name, brand..."
                  type="search"
                  value={search}
                />
              </div>

              <select className="sel" onChange={(event) => setSort(event.target.value)} value={sort}>
                <option value="popularity">Popularity</option>
                <option value="price-asc">Price ↑</option>
                <option value="price-desc">Price ↓</option>
                <option value="rating">Rating</option>
              </select>
            </div>

            <div className="chip-row">
              <button className={`chip ${category === "All" ? "on" : ""}`} onClick={() => setCategory("All")} type="button">
                All
              </button>
              {CATEGORIES.map((entry) => (
                <button
                  className={`chip ${category === entry ? "on" : ""}`}
                  key={entry}
                  onClick={() => setCategory(entry)}
                  type="button"
                >
                  {entry}
                </button>
              ))}
            </div>

            {filteredProducts.length ? (
              <div className="pgrid">
                {filteredProducts.map((product, index) => {
                  const stockText =
                    product.stock === 0 ? "Sold Out" : product.stock <= 5 ? `Only ${product.stock} left` : "In Stock";
                  const stockClass = product.stock === 0 ? "s-out" : product.stock <= 5 ? "s-low" : "s-ok";

                  return (
                    <article className="pcard" key={product.id} style={{ animationDelay: `${index * 0.04}s` }}>
                      <div className="pcard-img">
                        <span className="shoe">{product.emoji}</span>
                        <span className={`stock-badge ${stockClass}`}>{stockText}</span>
                      </div>
                      <div className="pcard-body">
                        <div className="pcard-brand">{product.brand}</div>
                        <div className="pcard-name">{product.name}</div>
                        <p className="pcard-desc">{product.description}</p>
                        <div className="pcard-meta">
                          <span className="pcard-price">${product.price}</span>
                          <span className="pcard-rating">
                            <span className="star">★</span> {product.rating} <span className="pcard-reviews">({product.reviews})</span>
                          </span>
                        </div>
                        <button className="cart-btn" disabled={product.stock === 0} onClick={() => addToCart(product.id)} type="button">
                          {product.stock === 0 ? "Out of Stock" : "Add to Cart"}
                        </button>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : (
              <div className="empty">
                <div className="big">👟</div>
                <p className="t">No sneakers found</p>
                <p>Try adjusting your search or filters</p>
              </div>
            )}
          </section>
        </>
      ) : null}

      {page === "cart" ? (
        <section className="sec cart-page">
          <h2 className="page-title">Your Cart</h2>
          {cart.length ? (
            <div className="cart-layout">
              <div className="cart-list">
                {cart.map((item) => (
                  <article className="cart-item" key={item.id}>
                    <div className="cart-thumb">{item.emoji}</div>
                    <div className="cart-info">
                      <div className="cart-brand">{item.brand}</div>
                      <div className="cart-name">{item.name}</div>
                      <div className="cart-price">${item.price}</div>
                    </div>
                    <div className="cart-qty">
                      <button className="qty-btn" onClick={() => updateQuantity(item.id, -1)} type="button">
                        −
                      </button>
                      <span>{item.quantity}</span>
                      <button className="qty-btn" onClick={() => updateQuantity(item.id, 1)} type="button">
                        +
                      </button>
                    </div>
                    <div className="cart-line-total">${(item.price * item.quantity).toFixed(2)}</div>
                  </article>
                ))}
              </div>

              <aside className="summary-box">
                <h3>Order Summary</h3>
                <div className="summary-row">
                  <span>Subtotal ({cartCount} items)</span>
                  <span>${cartTotal.toFixed(2)}</span>
                </div>
                <div className="summary-row">
                  <span>Shipping</span>
                  <span>Free</span>
                </div>
                <div className="summary-total">
                  <span>Total</span>
                  <span>${cartTotal.toFixed(2)}</span>
                </div>
                <button
                  className="auth-submit checkout-btn"
                  onClick={() => {
                    if (user) {
                      showToast("Checkout coming soon!");
                    } else {
                      navigate("login");
                      showToast("Please sign in to checkout", false);
                    }
                  }}
                  type="button"
                >
                  {user ? "Proceed to Checkout" : "Sign In to Checkout"}
                </button>
              </aside>
            </div>
          ) : (
            <div className="empty">
              <div className="big">🛒</div>
              <p className="t">Your cart is empty</p>
              <button className="btn-p" onClick={() => navigate("home")} type="button">
                Start Shopping
              </button>
            </div>
          )}
        </section>
      ) : null}

      {page === "profile" ? (
        <section className="sec placeholder-page">
          <div className="placeholder-icon">👤</div>
          <h2 className="page-title">My Profile</h2>
          <p className="placeholder-text">Signed in as {user?.email}. Account dashboard is coming in the next sprint.</p>
          <button className="btn-o" onClick={() => navigate("home")} type="button">
            Back to Home
          </button>
        </section>
      ) : null}

      {toast ? (
        <div className={`toast ${toast.ok ? "ok" : "err"}`}>
          <span>{toast.ok ? "✓" : "✕"}</span>
          {toast.message}
        </div>
      ) : null}
    </>
  );
}

export default App;
