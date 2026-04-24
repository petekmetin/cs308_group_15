import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

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
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState("reviews");
  const [loadingAccess, setLoadingAccess] = useState(true);
  const [user, setUser] = useState(() => getStoredUser());
  const accessToken = localStorage.getItem("access_token") || "";
  const userRole = useMemo(() => getStoredRole(), [user]);

  useEffect(() => {
    const requestedTab = (searchParams.get("tab") || "").trim();
    const allowedTabs = new Set(DASHBOARD_TABS.map((tab) => tab.id));
    if (!requestedTab || !allowedTabs.has(requestedTab)) {
      return;
    }
    setActiveTab((prev) => (prev === requestedTab ? prev : requestedTab));
  }, [searchParams]);

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

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    const next = new URLSearchParams(searchParams);
    next.set("tab", tabId);
    setSearchParams(next, { replace: true });
  };

  return (
    <div className="page">
      <Navbar user={user} cartCount={cartCount} />
      <main className="manager-page">
        <header className="manager-header">
          <p className="section-kicker">Management</p>
          <h1 className="welcome-title">Product Manager Dashboard</h1>
          <p className="section-note">
            Moderate reviews, manage catalog inventory, and update delivery progress.
          </p>
        </header>

        <div className="manager-tablist" role="tablist" aria-label="Product manager sections">
          {DASHBOARD_TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.id}
              className={`manager-tab ${activeTab === tab.id ? "active" : ""}`}
              onClick={() => handleTabChange(tab.id)}
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
