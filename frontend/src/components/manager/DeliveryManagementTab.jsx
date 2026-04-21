import { useEffect, useState } from "react";

import { fetchJson } from "../../utils/http";

function normalizeList(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  return payload?.results ?? [];
}

function DeliveryManagementTab({ accessToken }) {
  const [deliveries, setDeliveries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updatingId, setUpdatingId] = useState(null);

  useEffect(() => {
    let mounted = true;

    const loadDeliveries = async () => {
      setLoading(true);
      setError("");
      try {
        const payload = await fetchJson("/api/orders/deliveries/", { token: accessToken });
        if (mounted) {
          setDeliveries(normalizeList(payload));
        }
      } catch (err) {
        if (mounted) {
          setError(err.message || "Could not load deliveries.");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    loadDeliveries();
    return () => {
      mounted = false;
    };
  }, [accessToken]);

  const handleStatusChange = async (deliveryId, newStatus) => {
    setUpdatingId(deliveryId);
    setError("");
    try {
      const payload = await fetchJson(`/api/orders/deliveries/${deliveryId}/`, {
        method: "PATCH",
        token: accessToken,
        body: { status: newStatus },
      });

      setDeliveries((prev) => {
        if (newStatus === "delivered" || payload?.is_completed) {
          return prev.filter((delivery) => delivery.id !== deliveryId);
        }
        return prev.map((delivery) => (delivery.id === deliveryId ? payload : delivery));
      });
    } catch (err) {
      setError(err.message || "Could not update delivery status.");
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <section className="manager-tab-panel">
      <h2>Delivery Management</h2>
      {error ? <p className="manager-error">{error}</p> : null}
      {loading ? (
        <p className="manager-status">Loading deliveries...</p>
      ) : deliveries.length === 0 ? (
        <p className="manager-empty">No incomplete deliveries right now.</p>
      ) : (
        <div className="manager-table-wrap">
          <table className="manager-table">
            <thead>
              <tr>
                <th>Delivery ID</th>
                <th>Customer ID</th>
                <th>Products</th>
                <th>Total Price</th>
                <th>Address</th>
                <th>Status</th>
                <th>Completed</th>
              </tr>
            </thead>
            <tbody>
              {deliveries.map((delivery) => (
                <tr key={delivery.id}>
                  <td>{delivery.id}</td>
                  <td>{delivery.order?.customer}</td>
                  <td>
                    {(delivery.order?.items || []).map((item) => (
                      <p key={item.id}>
                        {item.sneaker_name || `#${item.sneaker}`} x {item.quantity}
                      </p>
                    ))}
                  </td>
                  <td>{delivery.order?.total_price}</td>
                  <td>{delivery.delivery_address}</td>
                  <td>
                    <select
                      value={delivery.status}
                      disabled={updatingId === delivery.id}
                      onChange={(event) => handleStatusChange(delivery.id, event.target.value)}
                    >
                      <option value="pending">pending</option>
                      <option value="in_transit">in_transit</option>
                      <option value="delivered">delivered</option>
                    </select>
                  </td>
                  <td>{delivery.is_completed ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default DeliveryManagementTab;
