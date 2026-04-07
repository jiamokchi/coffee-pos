/**
 * src/pages/Cashier.jsx  ── 收銀介面（大圖卡片 POS 風格）
 */
import { useState, useCallback, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

const TAX_RATE = 0.05;
const PAY_METHODS = [
  { id: "CASH",    label: "現金" },
  { id: "CARD",    label: "刷卡" },
  { id: "LINEPAY", label: "LINE Pay" },
  { id: "JKOPAY",  label: "街口" },
];
const CARRIER_OPTIONS = [
  { value: "",       label: "雲端發票" },
  { value: "3J0002", label: "手機條碼" },
  { value: "CQ0001", label: "自然人憑證" },
  { value: "UBN",    label: "公司抬頭" },
];

function getCategoryEmoji(cat) {
  const map = { "咖啡":"☕","茶飲":"🍵","飲品":"🥤","餐點":"🥐","熟豆":"📦","甜點":"🍰" };
  return map[cat] || "🛒";
}

const qtyBtnStyle = {
  width:26,height:26,borderRadius:6,border:"1px solid #ddd",
  background:"#f5f3ef",cursor:"pointer",fontSize:15,
  display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0,
};

export default function Cashier() {
  const [cart, setCart]               = useState([]);
  const [category, setCategory]       = useState("全部");
  const [search, setSearch]           = useState("");
  const [payMethod, setPayMethod]     = useState("CASH");
  const [carrierType, setCarrierType] = useState("");
  const [carrierId, setCarrierId]     = useState("");
  const [successData, setSuccessData] = useState(null);
  const [orderSeq, setOrderSeq]       = useState(() => Math.floor(Math.random()*900)+100);
  const [toast, setToast]             = useState(null);
  const [cashReceived, setCashReceived] = useState("");
  const toastTimer = useRef(null);
  const qc = useQueryClient();

  const { data: products = [] } = useQuery({
    queryKey: ["products"],
    queryFn: () => api.get("/products").then(r => r.data),
  });

  const categories = ["全部", ...new Set(products.map(p => p.category).filter(Boolean))];
  const visible = products.filter(p => {
    const catOk = category === "全部" || p.category === category;
    const qOk   = !search || p.name.toLowerCase().includes(search.toLowerCase());
    return catOk && qOk && p.is_active;
  });

  const addToCart = useCallback((product) => {
    setCart(prev => {
      const idx = prev.findIndex(i => i.product.id === product.id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = { ...next[idx], qty: next[idx].qty + 1 };
        return next;
      }
      return [...prev, { product, qty: 1 }];
    });
    showToast(`已加入 ${product.name}`);
  }, []);

  const changeQty = useCallback((id, delta) => {
    setCart(prev =>
      prev.map(i => i.product.id === id ? { ...i, qty: i.qty + delta } : i)
          .filter(i => i.qty > 0)
    );
  }, []);

  const total   = cart.reduce((s, i) => s + i.product.price * i.qty, 0);
  const untaxed = Math.round(total / (1 + TAX_RATE));
  const taxAmt  = total - untaxed;
  const orderNo = `#${String(orderSeq).padStart(4,"0")}`;

  const checkoutMut = useMutation({
    mutationFn: async () => {
      const order = await api.post("/orders", {
        items: cart.map(i => ({
          product_id: i.product.id, quantity: i.qty,
          unit_price: i.product.price, subtotal: i.product.price * i.qty,
        })),
        total_amount: total, tax_amount: taxAmt, payment_method: payMethod,
      }).then(r => r.data);

      // 必須先將訂單設為完成，才能開立發票
      await api.post(`/orders/${order.id}/complete`);

      await api.post("/invoices", {
        order_id: order.id,
        carrier_type: carrierType || null,
        carrier_id: carrierId || null
      });
      return order;
    },
    onSuccess: (order) => {
      setSuccessData({
        orderNo,
        total,
        payMethod,
        change: payMethod === "CASH" ? (parseFloat(cashReceived) - total || 0) : 0
      });
      qc.invalidateQueries({ queryKey: ["products"] });
    },
    onError: e => {
      const d = e.response?.data?.detail;
      showToast(typeof d==="object" ? `庫存不足：${d.ingredient}` : d || "結帳失敗");
    },
  });

  const nextOrder = () => {
    setCart([]); setCarrierType(""); setCarrierId(""); setCashReceived("");
    setSuccessData(null); setOrderSeq(s => s+1);
  };

  const showToast = (msg) => {
    clearTimeout(toastTimer.current);
    setToast(msg);
    toastTimer.current = setTimeout(() => setToast(null), 2000);
  };

  return (
    <div style={{ display:"flex", height:"100%", overflow:"hidden", background:"#f0ede8" }}>

      {/* ══ 左側：商品區 ══ */}
      <div style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" }}>
        <div style={{ background:"#fff", borderBottom:"1px solid #e0ddd6", padding:"10px 16px" }}>
          <input
            style={{ width:"100%", padding:"9px 14px", borderRadius:8, border:"1px solid #ddd", fontSize:14, marginBottom:8, background:"#f8f7f3", outline:"none", boxSizing:"border-box" }}
            placeholder="搜尋商品..."
            value={search} onChange={e => setSearch(e.target.value)}
          />
          <div style={{ display:"flex", gap:6, overflowX:"auto", paddingBottom:2 }}>
            {categories.map(cat => (
              <button key={cat} onClick={() => setCategory(cat)} style={{
                padding:"5px 14px", borderRadius:20, border:"none", cursor:"pointer",
                fontSize:12, fontWeight:500, whiteSpace:"nowrap",
                background: cat===category ? "#1a1a18" : "#ebe9e2",
                color:       cat===category ? "#fff" : "#555",
              }}>{cat}</button>
            ))}
          </div>
        </div>

        <div style={{
          flex:1, overflow:"auto", padding:12,
          display:"grid",
          gridTemplateColumns:"repeat(auto-fill, minmax(130px, 1fr))",
          gap:10, alignContent:"start",
        }}>
          {visible.map(p => (
            <ProductCard key={p.id} product={p} onClick={() => addToCart(p)} />
          ))}
          {visible.length === 0 && (
            <p style={{ color:"#aaa", fontSize:13, gridColumn:"1/-1", textAlign:"center", marginTop:40 }}>查無商品</p>
          )}
        </div>
      </div>

      {/* ══ 右側：購物車 ══ */}
      <div style={{ width:300, display:"flex", flexDirection:"column", background:"#fff", borderLeft:"1px solid #e0ddd6", flexShrink:0 }}>
        <div style={{ padding:"12px 16px", borderBottom:"1px solid #ede9e0", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
          <span style={{ fontWeight:500, fontSize:14 }}>訂單明細</span>
          <span style={{ fontFamily:"monospace", fontSize:11, color:"#999" }}>{orderNo}</span>
        </div>

        <div style={{ flex:1, overflowY:"auto" }}>
          {cart.length === 0 ? (
            <div style={{ textAlign:"center", color:"#bbb", fontSize:13, marginTop:48, lineHeight:1.8 }}>點選左側商品<br/>加入訂單</div>
          ) : cart.map(({ product, qty }) => (
            <div key={product.id} style={{ display:"flex", alignItems:"center", gap:8, padding:"9px 14px", borderBottom:"1px solid #f0ece5" }}>
              <div style={{ width:36, height:36, borderRadius:6, overflow:"hidden", flexShrink:0, background:"#f0ede8", display:"flex", alignItems:"center", justifyContent:"center", fontSize:20 }}>
                {product.image_url
                  ? <img src={product.image_url} style={{ width:"100%", height:"100%", objectFit:"cover" }} alt="" />
                  : getCategoryEmoji(product.category)}
              </div>
              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ fontSize:13, fontWeight:500, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{product.name}</div>
                <div style={{ fontSize:11, color:"#999", fontFamily:"monospace" }}>${product.price}</div>
              </div>
              <div style={{ display:"flex", alignItems:"center", gap:4, flexShrink:0 }}>
                <button onClick={() => changeQty(product.id,-1)} style={qtyBtnStyle}>−</button>
                <span style={{ fontSize:13, fontFamily:"monospace", minWidth:20, textAlign:"center" }}>{qty}</span>
                <button onClick={() => changeQty(product.id,+1)} style={qtyBtnStyle}>+</button>
              </div>
              <div style={{ fontFamily:"monospace", fontSize:12, minWidth:44, textAlign:"right", flexShrink:0 }}>${product.price*qty}</div>
            </div>
          ))}
        </div>

        {/* 載具 */}
        <div style={{ padding:"10px 14px", borderTop:"1px solid #ede9e0", borderBottom:"1px solid #ede9e0" }}>
          <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom: carrierType ? 6 : 0 }}>
            <span style={{ fontSize:11, color:"#999", width:40, flexShrink:0 }}>載具</span>
            <select value={carrierType} onChange={e => { setCarrierType(e.target.value); setCarrierId(""); }}
              style={{ flex:1, padding:"5px 8px", border:"1px solid #ddd", borderRadius:5, fontSize:12, background:"#f8f7f3" }}>
              {CARRIER_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          {carrierType && (
            <div style={{ display:"flex", alignItems:"center", gap:8 }}>
              <span style={{ fontSize:11, color:"#999", width:40, flexShrink:0 }}>
                {carrierType==="3J0002"?"條碼":carrierType==="CQ0001"?"憑證號":"統編"}
              </span>
              <input value={carrierId} onChange={e=>setCarrierId(e.target.value)}
                style={{ flex:1, padding:"5px 8px", border:"1px solid #ddd", borderRadius:5, fontSize:12, fontFamily:"monospace", background:"#f8f7f3", outline:"none" }} />
            </div>
          )}
        </div>

        {/* 金額 */}
        <div style={{ padding:"10px 14px" }}>
          <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, color:"#999", marginBottom:3 }}>
            <span>未稅</span><span style={{ fontFamily:"monospace" }}>${untaxed}</span>
          </div>
          <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, color:"#999", marginBottom:6 }}>
            <span>稅額 5%</span><span style={{ fontFamily:"monospace" }}>${taxAmt}</span>
          </div>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"baseline", borderTop:"1px solid #ede9e0", paddingTop:8 }}>
            <span style={{ fontSize:14, fontWeight:500 }}>總計</span>
            <span style={{ fontSize:26, fontWeight:700, fontFamily:"monospace" }}>${total}</span>
          </div>
        </div>

        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:6, padding:"0 14px 10px" }}>
          {PAY_METHODS.map(m => (
            <button key={m.id} onClick={() => setPayMethod(m.id)} style={{
              padding:"9px 4px", borderRadius:7,
              border: m.id===payMethod ? "2px solid #1a1a18" : "1px solid #e0ddd6",
              background: m.id===payMethod ? "#1a1a18" : "#f8f7f3",
              color:       m.id===payMethod ? "#fff" : "#555",
              fontSize:12, fontWeight:500, cursor:"pointer",
            }}>{m.label}</button>
          ))}
        </div>

        {/* 現金找零計算 */}
        {payMethod === "CASH" && (
          <div style={{ padding:"10px 14px", borderTop:"1px solid #ede9e0", background:"#fcfbf9" }}>
            <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8 }}>
              <span style={{ fontSize:11, color:"#999", width:40, flexShrink:0 }}>實收</span>
              <input
                type="number"
                value={cashReceived}
                onChange={e => setCashReceived(e.target.value)}
                placeholder="輸入金額..."
                style={{ flex:1, padding:"6px 10px", border:"1px solid #ddd", borderRadius:6, fontSize:14, fontFamily:"monospace", outline:"none" }}
              />
            </div>
            <div style={{ display:"flex", gap:4, marginBottom:8, overflowX:"auto" }}>
              {[1000, 500, 100, 50].map(v => (
                <button
                  key={v}
                  onClick={() => setCashReceived(prev => String((parseFloat(prev) || 0) + v))}
                  style={{ flex:1, padding:"4px 0", borderRadius:5, border:"1px solid #ddd", background:"#fff", fontSize:11, cursor:"pointer" }}
                >
                  +{v}
                </button>
              ))}
              <button onClick={() => setCashReceived("")} style={{ flex:1, padding:"4px 0", borderRadius:5, border:"1px solid #ddd", background:"#fff", fontSize:11, cursor:"pointer", color:"#999" }}>重設</button>
            </div>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
              <span style={{ fontSize:12, fontWeight:500, color:"#888" }}>應找零</span>
              <span style={{ fontSize:18, fontWeight:700, fontFamily:"monospace", color: (parseFloat(cashReceived) - total) >= 0 ? "#27500A" : "#A32D2D" }}>
                ${Math.max(0, (parseFloat(cashReceived) - total) || 0)}
              </span>
            </div>
          </div>
        )}

        {/* 結帳 */}
        <div style={{ padding:"0 14px 16px" }}>
          <button onClick={() => checkoutMut.mutate()}
            disabled={cart.length===0 || checkoutMut.isPending}
            style={{
              width:"100%", padding:"16px 0", borderRadius:10, border:"none",
              fontSize:16, fontWeight:700, letterSpacing:"0.02em",
              cursor: cart.length===0 ? "not-allowed" : "pointer",
              background: cart.length===0 ? "#ccc" : "#1a1a18",
              color: cart.length===0 ? "#999" : "#fff",
            }}>
            {checkoutMut.isPending ? "處理中..." : cart.length===0 ? "請選擇商品" : `結帳  $${total}`}
          </button>
        </div>
      </div>

      {toast && (
        <div style={{ position:"fixed", bottom:24, left:"50%", transform:"translateX(-50%)", background:"#1a1a18", color:"#fff", padding:"9px 20px", borderRadius:20, fontSize:13, zIndex:999, whiteSpace:"nowrap", pointerEvents:"none" }}>
          {toast}
        </div>
      )}

      {successData && (
        <div style={{ position:"fixed", inset:0, background:"rgba(248,247,243,0.97)", display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", zIndex:100 }}>
          <div style={{ fontSize:64, marginBottom:16 }}>✓</div>
          <div style={{ fontSize:12, color:"#999", fontFamily:"monospace", marginBottom:4 }}>{successData.orderNo} · {successData.payMethod}</div>
          <div style={{ fontSize:42, fontWeight:700, fontFamily:"monospace", marginBottom:8 }}>${successData.total}</div>
          <div style={{ fontSize:14, color:"#666", marginBottom:28 }}>
            {successData.payMethod==="CASH" && successData.change > 0 ? `找零 $${successData.change}` : "無需找零"}
          </div>
          <button onClick={nextOrder} style={{ padding:"12px 40px", borderRadius:10, background:"#1a1a18", color:"#fff", fontSize:15, fontWeight:600, border:"none", cursor:"pointer" }}>
            開始下一筆
          </button>
        </div>
      )}
    </div>
  );
}

function ProductCard({ product, onClick }) {
  const isOut = product.current_stock !== undefined && product.current_stock <= 0;
  return (
    <div onClick={isOut ? undefined : onClick}
      style={{
        background:"#fff", borderRadius:10, border:"1px solid #e8e5de",
        overflow:"hidden", cursor: isOut ? "not-allowed" : "pointer",
        opacity: isOut ? 0.5 : 1, userSelect:"none",
        transition:"transform 0.1s, box-shadow 0.1s",
      }}
      onMouseEnter={e => { if (!isOut) { e.currentTarget.style.transform="translateY(-2px)"; e.currentTarget.style.boxShadow="0 4px 12px rgba(0,0,0,0.1)"; }}}
      onMouseLeave={e => { e.currentTarget.style.transform=""; e.currentTarget.style.boxShadow=""; }}
      onMouseDown={e => { if (!isOut) e.currentTarget.style.transform="scale(0.97)"; }}
      onMouseUp={e => { e.currentTarget.style.transform=""; }}
    >
      <div style={{ width:"100%", aspectRatio:"1/1", overflow:"hidden", background:"#f0ede8", display:"flex", alignItems:"center", justifyContent:"center", fontSize:48 }}>
        {product.image_url
          ? <img src={product.image_url} style={{ width:"100%", height:"100%", objectFit:"cover" }} alt={product.name} />
          : getCategoryEmoji(product.category)}
      </div>
      <div style={{ padding:"8px 10px 10px" }}>
        <div style={{ fontSize:12, fontWeight:600, marginBottom:3, lineHeight:1.3, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{product.name}</div>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
          <span style={{ fontSize:14, fontWeight:700, fontFamily:"monospace", color:"#27500A" }}>${product.price}</span>
          {isOut && <span style={{ fontSize:10, color:"#A32D2D", background:"#FCEBEB", padding:"1px 6px", borderRadius:10 }}>售完</span>}
        </div>
      </div>
    </div>
  );
}
