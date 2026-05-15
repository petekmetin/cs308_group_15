import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import Navbar from "../components/Navbar";
import InvoiceManagementTab from "../components/sales/InvoiceManagementTab";
import PricingDiscountsTab from "../components/sales/PricingDiscountsTab";
import RevenueProfitTab from "../components/sales/RevenueProfitTab";
import ReturnRequestsTab from "../components/sales/ReturnRequestsTab";
import { fetchJson, getStoredRole, getStoredUser } from "../utils/http";

const DASHBOARD_TABS = [
  { id: "pricing", label: "Pricing & Discounts" },
  { id: "invoices", label: "Invoices" },
  { id: "returns", label: "Returns & Refunds" },
  { id: "reports", label: "Revenue & Profit" },
];

function SalesManagerDashboard({ cartCount = 0 }) {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState("pricing");
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

        if (profile.role !== "sales_manager") {
          navigate(profile.role === "product_manager" ? "/manager/dashboard" : "/home", {
            replace: true,
          });
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

  if (userRole !== "sales_manager") {
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
          <h1 className="welcome-title">Sales Manager Dashboard</h1>
          <p className="section-note">
            Manage pricing, apply discounts, review invoices, and track revenue performance.
          </p>
        </header>

        <div className="manager-tablist" role="tablist" aria-label="Sales manager sections">
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

        {activeTab === "pricing" ? <PricingDiscountsTab accessToken={accessToken} /> : null}
        {activeTab === "invoices" ? <InvoiceManagementTab accessToken={accessToken} /> : null}
        {activeTab === "returns" ? <ReturnRequestsTab accessToken={accessToken} /> : null}
        {activeTab === "reports" ? <RevenueProfitTab accessToken={accessToken} /> : null}
      </main>
    </div>
  );
}

export default SalesManagerDashboard;
