export function normalizePaginatedList(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  return payload?.results ?? [];
}

export function mapSneakerFromApi(item) {
  return {
    id: item.id,
    product_id: item.id,
    slug: `sneaker-${item.id}`,
    name: item.name,
    modelNumber: item.model_number || "",
    brand: item.brand_name || "Unknown",
    description: item.description || item.colorway || "No description available yet.",
    accent: item.category_name || "",
    category: item.category_name || "",
    image: item.primary_image || "",
    price: Number(item.discounted_price ?? item.price ?? 0),
    is_in_stock: item.is_in_stock,
    total_stock: item.total_stock,
    averageRating: item.average_rating,
    ratingCount: item.rating_count ?? item.review_count ?? 0,
    latestApprovedComment: item.latest_approved_comment || "",
  };
}
