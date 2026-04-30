import { fetchJson } from "./http";

export async function fetchWishlistIds(token) {
  if (!token) return new Set();
  try {
    const payload = await fetchJson("/api/products/wishlist/", { token });
    const list = Array.isArray(payload) ? payload : payload?.results ?? [];
    return new Set(list.map((item) => item.sneaker.id));
  } catch {
    return new Set();
  }
}

export async function addToWishlist(sneakerId, token) {
  await fetchJson("/api/products/wishlist/", {
    method: "POST",
    token,
    body: { sneaker_id: sneakerId },
  });
}

export async function removeFromWishlist(sneakerId, token) {
  await fetchJson(`/api/products/wishlist/${sneakerId}/`, {
    method: "DELETE",
    token,
  });
}
