import api from "../api";

const PENDING_CART_KEY = "solevault_pending_cart";

export function toCartPayload(sneaker) {
  const productId = sneaker.product_id ?? sneaker.id;
  const productSlug = sneaker.slug || (productId ? `sneaker-${productId}` : "");

  return {
    product_id: productId,
    product_slug: productSlug,
    product_name: sneaker.name,
    brand: sneaker.brand,
    description: sneaker.description,
    accent: sneaker.accent ?? "",
    image_url: sneaker.image ?? "",
    unit_price: sneaker.price,
    quantity: 1,
  };
}

export function savePendingCartItem(sneaker) {
  sessionStorage.setItem(PENDING_CART_KEY, JSON.stringify(toCartPayload(sneaker)));
}

export function consumePendingCartItem() {
  const raw = sessionStorage.getItem(PENDING_CART_KEY);
  if (!raw) {
    return null;
  }

  sessionStorage.removeItem(PENDING_CART_KEY);

  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export async function syncPendingCartItem() {
  const pendingItem = consumePendingCartItem();
  if (!pendingItem) {
    return false;
  }

  await api.post("/api/cart/items/", pendingItem);
  return true;
}
