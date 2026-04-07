/**
 * src/pages/Reports.jsx
 * 財務報表：毛利分析、庫存估值、401 申報匯出
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

const CURRENT_MONTH = new Date().getMonth() + 1;
const CURRENT_BIMONTH = Math.ceil(CURRENT_MONTH / 2);
const CURRENT_YEAR  = new Date().getFullYear();

export default function Reports() {
  const [tab, setTab] = useState("profit");

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <div className="page-header">
        <span className="page-title">財務報表</span>
        <div style={{ display: "flex", gap: 8 }}>
          {[
            { id: "profit",    label: "毛利分析" },
            { id: "inventory", label: "庫存估值" },
            { id: "tax401",    label: "401 報表" },
          ].map(t => (
            <button key={t.id} className={`btn ${tab === t.id ? "btn-primary" : ""}`}
              onClick={() => setTab(t.id)}>{t.label}</button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: 24 }}>
        {tab === "profit"    && <GrossProfitReport />}
        {tab === "inventory" && <InventoryValuation />}
        {tab === "tax401"    && <Tax401Report />}
      </div>
    </div>
  );
}

// ── 毛利分析 ──────────────────────────────────────────────────
function GrossProfitReport() {
  const { data = [], isLoading } = useQuery({
    queryKey: ["report-gross-profit"],
    queryFn: () => api.get("/reports/gross-profit").then(r => r.data),
  });

  if (isLoading) return <p style={{ color: "var(--ink3)", fontSize: 13 }}>計算中…</p>;

  const avg = data.length
    ? data.reduce((s, d) => s + parseFloat(d.gross_margin_pct), 0) / data.length
    : 0;

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12, marginBottom: 20 }}>
        {[
          { label: "商品數", value: data.length + " 項" },
          { label: "平均毛利率", value: avg.toFixed(1) + "%" },
          { label: "最高毛利", value: data[0]?.product_name || "—" },
        ].map(c => (
          <div key={c.label} className="card" style={{ textAlign: "center" }}>
            <div style={{ fontSize: 11, color: "var(--ink2)", marginBottom: 4 }}>{c.label}</div>
            <div style={{ fontSize: 20, fontWeight: 500 }}>{c.value}</div>
          </div>
        ))}
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table className="data-table">
          <thead>
            <tr>{["商品名稱", "售價", "BOM 成本", "毛利", "毛利率", "毛利視覺化"].map(h => <th key={h}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {data.map(d => {
              const pct = parseFloat(d.gross_margin_pct);
              const color = pct >= 60 ? "var(--accent)" : pct >= 40 ? "var(--amber)" : "var(--red)";
              return (
                <tr key={d.product_id}>
                  <td style={{ fontWeight: 500 }}>{d.product_name}</td>
                  <td className="mono">${d.selling_price}</td>
                  <td className="mono" style={{ color: "var(--ink2)" }}>${parseFloat(d.bom_cost).toFixed(1)}</td>
                  <td className="mono" style={{ color: parseFloat(d.gross_profit) >= 0 ? "var(--accent-tx)" : "var(--red)" }}>
                    ${parseFloat(d.gross_profit).toFixed(1)}
                  </td>
                  <td className="mono" style={{ color }}>{d.gross_margin_pct}</td>
                  <td style={{ width: 140 }}>
                    <div style={{ background: "var(--border)", borderRadius: 4, height: 8, overflow: "hidden" }}>
                      <div style={{
                        width: Math.min(100, Math.max(0, pct)) + "%",
                        height: "100%", background: color,
                        borderRadius: 4, transition: "width 0.3s",
                      }} />
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── 庫存估值 ──────────────────────────────────────────────────
function InventoryValuation() {
  const { data, isLoading } = useQuery({
    queryKey: ["report-inventory"],
    queryFn: () => api.get("/reports/inventory-valuation").then(r => r.data),
  });

  if (isLoading) return <p style={{ color: "var(--ink3)", fontSize: 13 }}>計算中…</p>;
  if (!data) return null;

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12, marginBottom: 20 }}>
        {[
          { label: "原料種類",   value: data.item_count + " 種" },
          { label: "低庫存項目", value: data.low_stock_count + " 項", warn: data.low_stock_count > 0 },
          { label: "庫存總估值", value: "NT$ " + parseInt(data.total_value).toLocaleString() },
        ].map(c => (
          <div key={c.label} className="card" style={{ textAlign: "center" }}>
            <div style={{ fontSize: 11, color: c.warn ? "var(--red)" : "var(--ink2)", marginBottom: 4 }}>{c.label}</div>
            <div style={{ fontSize: 20, fontWeight: 500, color: c.warn ? "var(--red)" : "var(--ink)" }}>{c.value}</div>
          </div>
        ))}
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <table className="data-table">
          <thead>
            <tr>{["原料名稱", "現有庫存", "平均成本", "帳面估值", "狀態"].map(h => <th key={h}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {(data.items || []).map(i => (
              <tr key={i.ingredient_id}>
                <td style={{ fontWeight: 500 }}>{i.name}</td>
                <td className="mono">{parseFloat(i.current_stock).toFixed(1)} {i.unit}</td>
                <td className="mono" style={{ color: "var(--ink2)" }}>${parseFloat(i.avg_unit_cost).toFixed(2)}/{i.unit}</td>
                <td className="mono">NT$ {parseInt(i.total_value).toLocaleString()}</td>
                <td>
                  <span className={`badge ${i.is_low_stock ? "badge-red" : "badge-green"}`}>
                    {i.is_low_stock ? "庫存不足" : "正常"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── 401 申報報表 ──────────────────────────────────────────────
function Tax401Report() {
  const [year, setYear]       = useState(CURRENT_YEAR);
  const [bimonth, setBimonth] = useState(CURRENT_BIMONTH);
  const [queried, setQueried] = useState(true);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["report-401", year, bimonth],
    queryFn: () => api.get("/reports/401", { params: { year, bimonth } }).then(r => r.data),
    enabled: queried,
  });

  const handleExport = () => {
    const url = `${import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1"}/reports/401/export-csv?year=${year}&bimonth=${bimonth}`;
    window.open(url, "_blank");
  };

  const BIMONTH_LABELS = [
    "1~2月", "3~4月", "5~6月", "7~8月", "9~10月", "11~12月",
  ];

  return (
    <div style={{ maxWidth: 600 }}>
      <div className="card" style={{ marginBottom: 20 }}>
        <h3 style={{ fontSize: 14, fontWeight: 500, marginBottom: 14 }}>選擇申報期間</h3>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
          <div className="field-group">
            <label className="field-label">年度</label>
            <select className="field-select" value={year} onChange={e => setYear(parseInt(e.target.value))}>
              {[CURRENT_YEAR, CURRENT_YEAR - 1, CURRENT_YEAR - 2].map(y =>
                <option key={y} value={y}>{y} 年</option>
              )}
            </select>
          </div>
          <div className="field-group">
            <label className="field-label">雙月期別</label>
            <select className="field-select" value={bimonth} onChange={e => setBimonth(parseInt(e.target.value))}>
              {BIMONTH_LABELS.map((l, i) =>
                <option key={i+1} value={i+1}>第 {i+1} 期（{l}）</option>
              )}
            </select>
          </div>
          <button className="btn btn-primary"
            onClick={() => { setQueried(true); refetch(); }}>
            查詢
          </button>
          {data && (
            <button className="btn" onClick={handleExport}>⬇ 匯出 CSV</button>
          )}
        </div>
      </div>

      {isLoading && <p style={{ color: "var(--ink3)", fontSize: 13 }}>查詢中…</p>}

      {data && (
        <div className="card">
          <div style={{ fontSize: 12, color: "var(--ink2)", marginBottom: 14 }}>
            申報期間：{data.period}
          </div>
          <table className="data-table">
            <tbody>
              {[
                { label: "應稅銷售額（未稅）", value: "NT$ " + parseInt(data.taxable_sales).toLocaleString(), bold: false },
                { label: "銷項稅額",            value: "NT$ " + parseInt(data.output_tax).toLocaleString(),   bold: false },
                { label: "零稅率銷售額",        value: "NT$ " + parseInt(data.zero_rate_sales).toLocaleString(), bold: false },
                { label: "免稅銷售額",          value: "NT$ " + parseInt(data.exempt_sales).toLocaleString(),    bold: false },
                { label: "發票開立張數",        value: data.invoice_count + " 張", bold: false },
                { label: "應繳稅額",
                  value: "NT$ " + (parseInt(data.output_tax)).toLocaleString(),
                  bold: true },
              ].map(r => (
                <tr key={r.label}>
                  <td style={{ color: "var(--ink2)", width: "55%" }}>{r.label}</td>
                  <td className="mono" style={{ fontWeight: r.bold ? 500 : 400, fontSize: r.bold ? 15 : 13 }}>
                    {r.value}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ fontSize: 11, color: "var(--ink3)", marginTop: 12, lineHeight: 1.6 }}>
            ※ 此報表僅供參考，實際申報請以財政部電子申報系統為準。
          </p>
        </div>
      )}
    </div>
  );
}
