import api from "../api";

const PENDING_CART_KEY = "solevault_pending_cart";
const GUEST_CART_KEY   = "solevault_guest_cart";

// ── Payload shape shared by add-to-cart calls ─────────────────────────

export function toCartPayload(sneaker) {
  const productId   = sneaker.product_id ?? sneaker.id;
  const productSlug = sneaker.slug || (productId ? `sneaker-${productId}` : "");
  return {
    product_id:   productId,
    product_slug: productSlug,
    product_name: sneaker.name,
    brand:        sneaker.brand,
    description:  sneaker.description,
    accent:       sneaker.accent ?? "",
    image_url:    sneaker.image  ?? "",
    unit_price:   sneaker.price,
    quantity:     1,
  };
}

// ── Guest cart (localStorage, multi-item) ─────────────────────────────

export function getGuestCart() {
  try {
    return JSON.parse(localStorage.getItem(GUEST_CART_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveGuestCart(items) {
  localStorage.setItem(GUEST_CART_KEY, JSON.stringify(items));
}

export function clearGuestCart() {
  localStorage.removeItem(GUEST_CART_KEY);
}

export function addToGuestCart(sneaker) {
  const cart      = getGuestCart();
  const productId = sneaker.product_id ?? sneaker.id;
  const slug      = sneaker.slug || `sneaker-${productId}`;
  const existing  = cart.find((i) => i.slug === slug);

  if (existing) {
    existing.quantity += 1;
  } else {
    cart.push({
      id:          `local-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      slug,
      name:        sneaker.name,
      brand:       sneaker.brand        ?? "",
      description: sneaker.description ?? "",
      accent:      sneaker.accent       ?? "",
      image:       sneaker.image        ?? "",
      price:       Number(sneaker.price),
      quantity:    1,
    });
  }

  saveGuestCart(cart);
  return [...cart];
}

export function updateGuestCartItem(id, quantity) {
  const cart = getGuestCart().map((i) => (i.id === id ? { ...i, quantity } : i));
  saveGuestCart(cart);
  return [...cart];
}

export function removeGuestCartItem(id) {
  const cart = getGuestCart().filter((i) => i.id !== id);
  saveGuestCart(cart);
  return [...cart];
}

// Merge all guest cart items to the server cart, then wipe localStorage.
export async function mergeGuestCartToServer() {
  const guestItems = getGuestCart();
  if (!guestItems.length) return;

  for (const item of guestItems) {
    try {
      const productId = Number(item.slug.replace("sneaker-", ""));
      await api.post("/api/cart/items/", {
        product_id:   productId,
        product_slug: item.slug,
        product_name: item.name,
        brand:        item.brand,
        description:  item.description,
        accent:       item.accent,
        image_url:    item.image,
        unit_price:   item.price,
        quantity:     item.quantity,
      });
    } catch {
      // Skip items the server rejects (e.g. out of stock).
    }
  }

  clearGuestCart();
}

// ── Pending item (single item saved before a login redirect) ──────────
// Kept for backwards compatibility with LoginPage / SignupPage.

export function savePendingCartItem(sneaker) {
  sessionStorage.setItem(PENDING_CART_KEY, JSON.stringify(toCartPayload(sneaker)));
}

export function consumePendingCartItem() {
  const raw = sessionStorage.getItem(PENDING_CART_KEY);
  if (!raw) return null;
  sessionStorage.removeItem(PENDING_CART_KEY);
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export async function syncPendingCartItem() {
  const pendingItem = consumePendingCartItem();
  if (!pendingItem) return false;
  await api.post("/api/cart/items/", pendingItem);
  return true;
}
