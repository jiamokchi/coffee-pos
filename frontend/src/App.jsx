import { useState } from "react";
import Cashier      from "./pages/Cashier";
import Inventory    from "./pages/Inventory";
import Products     from "./pages/Products";
import Reports      from "./pages/Reports";
import { NavIcon }  from "./components/NavIcon";

const PAGES = [
  { id: "cashier",   label: "收銀",   icon: "cashier"   },
  { id: "products",  label: "商品",   icon: "products"  },
  { id: "inventory", label: "庫存",   icon: "inventory" },
  { id: "reports",   label: "報表",   icon: "reports"   },
];

export default function App() {
  const [page, setPage] = useState("cashier");

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", background: "var(--surface)" }}>
      {/* ── 左側導覽列 ── */}
      <nav style={{
        width: 64, display: "flex", flexDirection: "column", alignItems: "center",
        paddingTop: 16, paddingBottom: 16, gap: 4,
        background: "#1a1a18", borderRight: "1px solid #2a2a26",
      }}>
        {/* Logo */}
        <div style={{
          width: 36, height: 36, borderRadius: 8, background: "#3B6D11",
          display: "flex", alignItems: "center", justifyContent: "center",
          marginBottom: 16, fontSize: 18,
        }}>☕</div>

        {PAGES.map(p => (
          <button
            key={p.id}
            onClick={() => setPage(p.id)}
            title={p.label}
            style={{
              width: 44, height: 44, borderRadius: 8, border: "none", cursor: "pointer",
              display: "flex", flexDirection: "column", alignItems: "center",
              justifyContent: "center", gap: 2,
              background: page === p.id ? "#2d2d2a" : "transparent",
              color: page === p.id ? "#fff" : "#888",
              transition: "all 0.15s",
            }}
          >
            <NavIcon name={p.icon} active={page === p.id} />
            <span style={{ fontSize: 9, letterSpacing: "0.02em" }}>{p.label}</span>
          </button>
        ))}
      </nav>

      {/* ── 主內容區 ── */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {page === "cashier"   && <Cashier />}
        {page === "products"  && <Products />}
        {page === "inventory" && <Inventory />}
        {page === "reports"   && <Reports />}
      </div>
    </div>
  );
}
