import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import Navbar from "../components/Navbar";
import CategoryManagementTab from "../components/manager/CategoryManagementTab";
import DeliveryManagementTab from "../components/manager/DeliveryManagementTab";
import ProductManagementTab from "../components/manager/ProductManagementTab";
import ReviewModerationTab from "../components/manager/ReviewModerationTab";
import { fetchJson, getStoredRole, getStoredUser } from "../utils/http";

const DASHBOARD_TABS = [
  { id: "reviews", label: "Review Moderation" },
  { id: "products", label: "Product Management" },
  { id: "deliveries", label: "Delivery Management" },
  { id: "categories", label: "Category Management" },
];

function ProductManagerDashboard({ cartCount = 0 }) {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("reviews");
  const [loadingAccess, setLoadingAccess] = useState(true);
  const [user, setUser] = useState(() => getStoredUser());
  const accessToken = localStorage.getItem("access_token") || "";
  const userRole = useMemo(() => getStoredRole(), [user]);

  useEffect(() => {
    let mounted = true;

    const verifyAccess = async () => {
      if (!accessToken) {
        navigate("/login", { replace: true });
        return;
      }

      try {
        const profile = await fetchJson("/api/auth/me/", { token: accessToken });
        if (!mounted) {
          return;
        }
        localStorage.setItem("user", JSON.stringify(profile));
        localStorage.setItem("user_role", profile?.role || "");
        setUser(profile);

        if (profile.role !== "product_manager") {
          navigate("/home", { replace: true });
          return;
        }
      } catch {
        if (!mounted) {
          return;
        }
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
        localStorage.removeItem("user_role");
        navigate("/login", { replace: true });
        return;
      } finally {
        if (mounted) {
          setLoadingAccess(false);
        }
      }
    };

    verifyAccess();
    return () => {
      mounted = false;
    };
  }, [accessToken, navigate]);

  if (loadingAccess) {
    return <p className="manager-status manager-access-status">Checking dashboard access...</p>;
  }

  if (userRole !== "product_manager") {
    return null;
  }

  return (
    <div className="page">
      <Navbar user={user} cartCount={cartCount} />
      <main className="manager-page">
        <header className="manager-header">
          <h1>Product Manager Dashboard</h1>
          <p>Moderate reviews, manage catalog inventory, and update delivery progress.</p>
        </header>

        <div className="manager-tablist" role="tablist" aria-label="Product manager sections">
          {DASHBOARD_TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              className={`manager-tab ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "reviews" ? <ReviewModerationTab accessToken={accessToken} /> : null}
        {activeTab === "products" ? <ProductManagementTab accessToken={accessToken} /> : null}
        {activeTab === "deliveries" ? <DeliveryManagementTab accessToken={accessToken} /> : null}
        {activeTab === "categories" ? <CategoryManagementTab accessToken={accessToken} /> : null}
      </main>
    </div>
  );
}

export default ProductManagerDashboard;
