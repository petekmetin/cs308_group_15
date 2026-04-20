import { useEffect, useState } from "react";

function ShoeSlider({ sneakers, title = "Featured Shoes" }) {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (!sneakers.length) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      setActiveIndex((current) => (current + 1) % sneakers.length);
    }, 4000);

    return () => window.clearInterval(intervalId);
  }, [sneakers]);

  if (!sneakers.length) {
    return null;
  }

  const activeShoe = sneakers[activeIndex];

  const goToPrevious = () => {
    setActiveIndex((current) => (current - 1 + sneakers.length) % sneakers.length);
  };

  const goToNext = () => {
    setActiveIndex((current) => (current + 1) % sneakers.length);
  };

  return (
    <section className="shoe-slider" aria-label={title}>
      <div className="shoe-slider-top">
        <div>
          <p className="shoe-slider-kicker">{title}</p>
          <h2 className="shoe-slider-title">{activeShoe.name}</h2>
        </div>

        <div className="shoe-slider-controls">
          <button
            type="button"
            className="shoe-slider-arrow"
            onClick={goToPrevious}
            aria-label="Show previous shoe"
          >
            ←
          </button>
          <button
            type="button"
            className="shoe-slider-arrow"
            onClick={goToNext}
            aria-label="Show next shoe"
          >
            →
          </button>
        </div>
      </div>

      <div className="shoe-slider-stage">
        {activeShoe.image ? (
          <img
            className="shoe-slider-image"
            src={activeShoe.image}
            alt={`${activeShoe.brand} ${activeShoe.name}`}
          />
        ) : (
          <div className="shoe-slider-fallback" aria-hidden="true">
            <span>{activeShoe.brand.slice(0, 2).toUpperCase()}</span>
          </div>
        )}

        {activeShoe.accent ? (
          <span className="shoe-slider-badge">{activeShoe.accent}</span>
        ) : null}
      </div>

      <div className="shoe-slider-meta">
        <div>
          <p className="shoe-slider-brand">{activeShoe.brand}</p>
          <p className="shoe-slider-description">{activeShoe.description}</p>
        </div>
        <p className="shoe-slider-price">
          {new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
            maximumFractionDigits: 0,
          }).format(activeShoe.price)}
        </p>
      </div>

      <div className="shoe-slider-dots" role="tablist" aria-label="Choose a featured shoe">
        {sneakers.map((sneaker, index) => (
          <button
            key={sneaker.id}
            type="button"
            className={`shoe-slider-dot${index === activeIndex ? " is-active" : ""}`}
            onClick={() => setActiveIndex(index)}
            aria-label={`Show ${sneaker.name}`}
            aria-pressed={index === activeIndex}
          />
        ))}
      </div>
    </section>
  );
}

export default ShoeSlider;
