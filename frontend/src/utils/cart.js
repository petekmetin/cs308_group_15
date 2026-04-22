import api from "../api";

const PENDING_CART_KEY = "solevault_pending_cart";
const GUEST_CART_KEY   = "solevault_guest_cart";

// ── Payload shape shared by add-to-cart calls ─────────────────────────

export function toCartPayload(sneaker, sizeOption) {
  if (!sizeOption?.id) {
    throw new Error("size_id is required to add an item to cart.");
  }
  const productId   = sneaker.product_id ?? sneaker.id;
  const productSlug = sneaker.slug || (productId ? `sneaker-${productId}` : "");
  return {
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
  };
}

// ── Guest cart (localStorage, multi-item) ─────────────────────────────

export function getGuestCart() {
  try {
    const parsed = JSON.parse(localStorage.getItem(GUEST_CART_KEY) || "[]");
    if (!Array.isArray(parsed)) {
      return [];
    }

    // One-time cleanup for legacy entries created before size selection
    // became mandatory.
    const cleaned = parsed.filter((item) => Number(item.size_id) > 0);
    if (cleaned.length !== parsed.length) {
      localStorage.setItem(GUEST_CART_KEY, JSON.stringify(cleaned));
    }

    return cleaned;
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

function getGuestCartEntryKey(slug, sizeId) {
  return `${slug}:${sizeId}`;
}

export function addToGuestCart(sneaker, sizeOption) {
  if (!sizeOption?.id) {
    throw new Error("size_id is required to add an item to cart.");
  }

  const cart      = getGuestCart();
  const productId = sneaker.product_id ?? sneaker.id;
  const slug      = sneaker.slug || `sneaker-${productId}`;
  const entryKey  = getGuestCartEntryKey(slug, sizeOption.id);
  const existing  = cart.find((i) => getGuestCartEntryKey(i.slug, i.size_id) === entryKey);
  const sizeStock = Number(sizeOption.stock ?? 0);

  if (existing) {
    if (sizeStock > 0 && existing.quantity + 1 > sizeStock) {
      throw new Error(`Only ${sizeStock} left for size ${sizeOption.size_system} ${sizeOption.size}.`);
    }
    existing.quantity += 1;
  } else {
    cart.push({
      id:          `local-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      slug,
      product_id:  productId,
      size_id:     sizeOption.id,
      size:        sizeOption.size,
      size_system: sizeOption.size_system,
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
        size_id:      item.size_id,
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

export function savePendingCartItem(sneaker, sizeOption) {
  sessionStorage.setItem(PENDING_CART_KEY, JSON.stringify(toCartPayload(sneaker, sizeOption)));
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
  if (!pendingItem || !pendingItem.size_id) return false;
  await api.post("/api/cart/items/", pendingItem);
  return true;
}
