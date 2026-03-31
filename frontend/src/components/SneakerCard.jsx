// ============================================================
// src/components/SneakerCard.jsx — Single Sneaker Card
// ============================================================
// Props from the API (SneakerListSerializer):
//   id, name, colorway, brand_name, category_name, sku,
//   price, discounted_price, discount_percentage,
//   is_in_stock, total_stock, is_featured, primary_image,
//   popularity_score, created_at
// ============================================================

function SneakerCard({ sneaker }) {
  const {
    name,
    brand_name,
    price,
    discounted_price,
    discount_percentage,
    primary_image,
    is_in_stock,
    colorway,
  } = sneaker;

  const hasDiscount = discount_percentage > 0;

  return (
    <div className="sneaker-card">

      {/* Product image */}
      <div className="sneaker-image-wrap">
        {primary_image ? (
          <img
            src={primary_image}
            alt={`${brand_name} ${name}`}
            className="sneaker-image"
            onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }}
          />
        ) : null}
        <div className="sneaker-emoji" style={{ display: primary_image ? 'none' : 'flex' }}>👟</div>
      </div>

      {/* Sneaker details */}
      <div className="sneaker-info">
        <span className="sneaker-brand">{brand_name}</span>
        <h3 className="sneaker-name">{name}</h3>
        {colorway && <p className="sneaker-colorway">{colorway}</p>}

        <div className="sneaker-footer">
          <div className="sneaker-price-wrap">
            {hasDiscount ? (
              <>
                <span className="sneaker-price">${discounted_price}</span>
                <span className="sneaker-original-price">${price}</span>
                <span className="sneaker-discount">-{discount_percentage}%</span>
              </>
            ) : (
              <span className="sneaker-price">${price}</span>
            )}
          </div>
          {!is_in_stock && <span className="sneaker-out-of-stock">Out of stock</span>}
          <button className="sneaker-btn" disabled={!is_in_stock}>
            Add to Cart
          </button>
        </div>
      </div>
    </div>
  );
}

export default SneakerCard;
