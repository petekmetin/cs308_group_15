import { Link, useNavigate } from "react-router-dom";

import SneakerCard from "../components/SneakerCard";
import ShoeSlider from "../components/ShoeSlider";
import { FEATURED_SNEAKERS } from "../data/sneakers";
import { savePendingCartItem } from "../utils/cart";

function LandingPage({ onAddToCart }) {
  const navigate = useNavigate();

  const handleAddToCart = async (sneaker) => {
    const token = localStorage.getItem("access_token");

    if (!token) {
      savePendingCartItem(sneaker);
      navigate("/login", {
        state: {
          redirectTo: "/cart",
          message: "Log in or sign up to add sneakers to your cart.",
        },
      });
      return;
    }

    await onAddToCart?.(sneaker);
    navigate("/cart");
  };

  return (
    <div className="landing-page">
      <header className="landing-nav">
        <Link to="/" className="landing-brand">
          SOLE<span>VAULT</span>
        </Link>

        <div className="landing-nav-actions">
          <Link to="/login" className="landing-link">
            Log In
          </Link>
          <Link to="/signup" className="landing-cta">
            Create Account
          </Link>
        </div>
      </header>

      <main className="landing-main">
        <section className="landing-hero">
          <div className="landing-copy">
            <h1 className="landing-title">Welcome to SoleVault</h1>

            <div className="landing-actions">
              <Link to="/signup" className="landing-primary-btn">
                Start Exploring
              </Link>
              <Link to="/login" className="landing-secondary-btn">
                I Already Have an Account
              </Link>
            </div>
          </div>

          <ShoeSlider sneakers={FEATURED_SNEAKERS} title="Public Showcase" />
        </section>

        <section className="landing-showcase">
          <div className="section-heading">
            <div>
              <p className="section-kicker">Featured Preview</p>
              <h2 className="section-title">Latest SoleVault Picks</h2>
            </div>
            <p className="section-note">
              This page is public. The authenticated shopping experience now lives at
              <code> /home</code>.
            </p>
          </div>

          <div className="sneaker-grid">
            {FEATURED_SNEAKERS.map((sneaker) => (
              <SneakerCard
                key={sneaker.id}
                sneaker={sneaker}
                onAddToCart={handleAddToCart}
              />
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

export default LandingPage;
