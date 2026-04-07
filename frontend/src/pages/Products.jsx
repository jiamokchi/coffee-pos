import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, parseApiError } from "../lib/api";
import { compressImage } from "../lib/utils";

export default function Products() {
  const qc = useQueryClient();
  const [editing, setEditing]   = useState(null);
  const [creating, setCreating] = useState(false);
  const [toast, setToast]       = useState(null);
  const [showInactive, setShowInactive] = useState(false);

  const showToast = (msg, type="ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 2500);
  };

  const { data: products = [], isLoading } = useQuery({
    queryKey: ["products", showInactive],
    queryFn: () => api.get("/products", { params: { active_only: !showInactive } }).then(r => r.data),
  });

  const { data: ingredients = [] } = useQuery({
    queryKey: ["ingredients"],
    queryFn: () => api.get("/ingredients").then(r => r.data),
  });

  const deactivateMut = useMutation({
    mutationFn: id => api.patch(`/products/${id}/deactivate`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["products"] }); showToast("商品已下架"); },
    onError: e => showToast(parseApiError(e), "err"),
  });

  const deleteMut = useMutation({
    mutationFn: id => api.delete(`/products/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["products"] }); showToast("商品已刪除"); },
    onError: e => showToast(parseApiError(e), "err"),
  });

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%", overflow:"hidden", background:"#f8f7f3" }}>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"14px 24px", background:"#fff", borderBottom:"1px solid #e5e4dc" }}>
        <span style={{ fontWeight:500, fontSize:15 }}>商品管理</span>
        <div style={{ display:"flex", gap:10, alignItems:"center" }}>
          <label style={{ fontSize:12, color:"#666", display:"flex", gap:5, cursor:"pointer" }}>
            <input type="checkbox" checked={showInactive} onChange={e => setShowInactive(e.target.checked)} />
            顯示下架商品
          </label>
          <button onClick={() => setCreating(true)} style={{ padding:"7px 16px", borderRadius:6, background:"#1a1a18", color:"#fff", border:"none", fontSize:13, cursor:"pointer" }}>
            + 新增商品
          </button>
        </div>
      </div>

      <div style={{ flex:1, overflow:"auto", padding:24 }}>
        {(creating || editing) && (
          <ProductForm
            product={editing}
            ingredients={ingredients}
            onClose={() => { setEditing(null); setCreating(false); }}
            onSaved={() => {
              qc.invalidateQueries({ queryKey: ["products"] });
              setEditing(null); setCreating(false);
              showToast(editing ? "商品已更新" : "商品已新增");
            }}
            qc={qc}
            showToast={showToast}
          />
        )}

        <div style={{ background:"#fff", border:"1px solid #e5e4dc", borderRadius:8, overflow:"hidden" }}>
          {isLoading ? (
            <p style={{ padding:20, color:"#aaa", fontSize:13 }}>載入中…</p>
          ) : (
            <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
              <thead>
                <tr>
                  {["","商品名稱","類別","售價","稅別","BOM","毛利","狀態","操作"].map(h => (
                    <th key={h} style={{ textAlign:"left", padding:"8px 12px", fontSize:11, color:"#888", borderBottom:"1px solid #e5e4dc", fontWeight:500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {products.map(p => {
                  const bomCost = p.bom_items.reduce((s, b) => {
                    const ing = ingredients.find(i => i.id === b.ingredient_id);
                    return s + (ing ? parseFloat(b.qty_required) * parseFloat(ing.avg_unit_cost) : 0);
                  }, 0);
                  const gp = parseFloat(p.price) - bomCost;
                  const margin = parseFloat(p.price) > 0 ? (gp/parseFloat(p.price)*100).toFixed(1) : "—";
                  return (
                    <tr key={p.id} style={{ borderBottom:"1px solid #f0ece5", opacity: p.is_active ? 1 : 0.5 }}>
                      <td style={{ padding:"10px 12px", width:44 }}>
                        <div style={{ width:36, height:36, borderRadius:6, overflow:"hidden", background:"#f0ede8", display:"flex", alignItems:"center", justifyContent:"center", fontSize:20 }}>
                          {p.image_url ? <img src={p.image_url} style={{ width:"100%", height:"100%", objectFit:"cover" }} alt="" /> : "☕"}
                        </div>
                      </td>
                      <td style={{ padding:"10px 12px", fontWeight:500 }}>{p.name}</td>
                      <td style={{ padding:"10px 12px" }}>
                        <span style={{ padding:"2px 10px", borderRadius:20, fontSize:11, background:"#EAF3DE", color:"#27500A" }}>{p.category||"—"}</span>
                      </td>
                      <td style={{ padding:"10px 12px", fontFamily:"monospace" }}>${parseFloat(p.price).toFixed(0)}</td>
                      <td style={{ padding:"10px 12px", fontSize:11, color:"#888" }}>{p.tax_type}</td>
                      <td style={{ padding:"10px 12px", color:"#888" }}>{p.bom_items.length} 項</td>
                      <td style={{ padding:"10px 12px", fontFamily:"monospace", color: gp>=0?"#27500A":"#A32D2D" }}>
                        ${gp.toFixed(0)} <span style={{ fontSize:11, color:"#aaa" }}>({margin}%)</span>
                      </td>
                      <td style={{ padding:"10px 12px" }}>
                        <span style={{ padding:"2px 10px", borderRadius:20, fontSize:11, fontWeight:500, background: p.is_active?"#EAF3DE":"#FAEEDA", color: p.is_active?"#27500A":"#633806" }}>
                          {p.is_active?"上架":"下架"}
                        </span>
                      </td>
                      <td style={{ padding:"10px 12px" }}>
                        <div style={{ display:"flex", gap:6 }}>
                          <button onClick={() => setEditing(p)} style={{ padding:"4px 10px", borderRadius:5, border:"1px solid #ddd", background:"#f8f7f3", fontSize:11, cursor:"pointer" }}>編輯</button>
                          {p.is_active ? (
                            <button onClick={() => { if(window.confirm(`確認下架「${p.name}」？`)) deactivateMut.mutate(p.id); }}
                              style={{ padding:"4px 10px", borderRadius:5, border:"1px solid #f7c1c1", background:"#FCEBEB", color:"#A32D2D", fontSize:11, cursor:"pointer" }}>下架</button>
                          ) : (
                            <button onClick={() => api.patch(`/products/${p.id}`, {is_active:true}).then(()=>qc.invalidateQueries({queryKey:["products"]}))}
                              style={{ padding:"4px 10px", borderRadius:5, border:"1px solid #d1e7dd", background:"#eaf3de", color:"#27500A", fontSize:11, cursor:"pointer" }}>上架</button>
                          )}
                          <button onClick={() => { if(window.confirm(`確認「實體刪除」商品「${p.name}」？此操作不可逆。`)) deleteMut.mutate(p.id); }}
                            style={{ padding:"4px 10px", borderRadius:5, border:"1px solid #ddd", background:"#fff", fontSize:11, cursor:"pointer" }}>刪除</button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {toast && (
        <div style={{ position:"fixed", bottom:24, left:"50%", transform:"translateX(-50%)", background: toast.type==="err"?"#A32D2D":"#1a1a18", color:"#fff", padding:"9px 20px", borderRadius:20, fontSize:13, zIndex:999, whiteSpace:"nowrap" }}>
          {toast.msg}
        </div>
      )}
    </div>
  );
}

function ProductForm({ product, ingredients, onClose, onSaved, qc, showToast }) {
  const isEdit = !!product;
  const fileRef = useRef();
  const [form, setForm] = useState({
    name:     product?.name     || "",
    category: product?.category || "",
    price:    product?.price    || "",
    barcode:  product?.barcode  || "",
    tax_type: product?.tax_type || "TAX",
  });
  const uniqueCategories = [...new Set(qc.getQueryData(["products"])?.map(p => p.category).filter(Boolean) || [])];
  const [bom, setBom] = useState(
    product?.bom_items.map(b => ({ ingredient_id: String(b.ingredient_id), qty_required: String(b.qty_required) })) || []
  );
  const [savedId, setSavedId] = useState(product?.id || null);
  const [previewImg, setPreviewImg] = useState(product?.image_url || null);

  const saveMut = useMutation({
    mutationFn: d => isEdit
      ? api.patch(`/products/${product.id}`, d).then(r => r.data)
      : api.post("/products", d).then(r => r.data),
    onSuccess: (data) => {
      setSavedId(data.id);
      onSaved();
    },
    onError: e => showToast(parseApiError(e), "err"),
  });

  const imgMut = useMutation({
    mutationFn: async ({ id, file }) => {
      const compressed = await compressImage(file);
      const fd = new FormData();
      fd.append("file", compressed);
      return api.post(`/images/product/${id}`, fd, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data);
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["products"] });
      setPreviewImg(URL.createObjectURL(vars.file));
      showToast("圖片已更新");
    },
    onError: e => showToast(e.response?.data?.detail || "圖片上傳失敗", "err"),
  });

  const handlePaste = async (e) => {
    if (!savedId) {
      showToast("請先建立商品，再貼上圖片", "err");
      return;
    }
    const item = e.clipboardData.items[0];
    if (item?.type?.startsWith("image/")) {
      const file = item.getAsFile();
      imgMut.mutate({ id: savedId, file });
    }
  };

  const addBOM = () => setBom(p => [...p, { ingredient_id:"", qty_required:"" }]);
  const removeBOM = idx => setBom(p => p.filter((_,i) => i!==idx));

  const bomCost = bom.reduce((s,b) => {
    const ing = ingredients.find(i => i.id===parseInt(b.ingredient_id));
    return s + (ing ? parseFloat(b.qty_required||0)*parseFloat(ing.avg_unit_cost) : 0);
  }, 0);

  const handleSave = () => saveMut.mutate({
    ...form,
    price: parseFloat(form.price),
    bom: bom.filter(b => b.ingredient_id && b.qty_required).map(b => ({
      ingredient_id: parseInt(b.ingredient_id),
      qty_required: parseFloat(b.qty_required),
    })),
  });

  return (
    <div onPaste={handlePaste} style={{ background:"#fff", border:"2px solid #1a1a18", borderRadius:8, padding:"20px", marginBottom:20 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:16 }}>
        <h3 style={{ fontSize:14, fontWeight:500 }}>{isEdit ? `編輯：${product.name}` : "新增商品"}</h3>
        <button onClick={onClose} style={{ border:"none", background:"none", cursor:"pointer", color:"#888", fontSize:16 }}>✕ 關閉</button>
      </div>

      {/* 圖片上傳 */}
      <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:16, padding:"12px", background:"#f8f7f3", borderRadius:8 }}>
        <div style={{ width:80, height:80, borderRadius:8, overflow:"hidden", background:"#e0ddd6", display:"flex", alignItems:"center", justifyContent:"center", fontSize:40, flexShrink:0 }}>
          {previewImg ? <img src={previewImg} style={{ width:"100%", height:"100%", objectFit:"cover" }} alt="" /> : "☕"}
        </div>
        <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
          <input type="file" ref={fileRef} accept="image/*" style={{ display:"none" }}
            onChange={e => {
              const f = e.target.files[0];
              if (!f) return;
              if (savedId) {
                imgMut.mutate({ id: savedId, file: f });
              } else {
                setPreviewImg(URL.createObjectURL(f));
                showToast("請先建立商品，再上傳圖片");
              }
            }} />
          <button onClick={() => fileRef.current.click()} style={{ padding:"6px 14px", borderRadius:5, border:"1px solid #ddd", background:"#fff", fontSize:12, cursor:"pointer" }}>
            {imgMut.isPending ? "上傳中..." : "上傳圖片"}
          </button>
          <span style={{ fontSize:11, color:"#aaa" }}>
            {savedId ? "支援 JPG / PNG / WebP，上限 2MB" : "請先建立商品後再上傳圖片"}
          </span>
        </div>
      </div>

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12, marginBottom:16 }}>
        {[
          { label:"商品名稱", key:"name", type:"text", ph:"拿鐵" },
          { label:"類別", key:"category", type:"text", ph:"咖啡" },
          { label:"售價（元）", key:"price", type:"number", ph:"120" },
          { label:"條碼", key:"barcode", type:"text", ph:"選填" },
        ].map(f => (
          <div key={f.key} style={{ display:"flex", flexDirection:"column", gap:4 }}>
            <label style={{ fontSize:11, color:"#888" }}>{f.label}</label>
            <input type={f.type} placeholder={f.ph} value={form[f.key]}
              list={f.key==="category" ? "categories-list" : undefined}
              onChange={e => setForm(p => ({...p,[f.key]:e.target.value}))}
              style={{ padding:"7px 10px", border:"1px solid #ddd", borderRadius:6, fontSize:13, outline:"none" }} />
            {f.key==="category" && (
              <datalist id="categories-list">
                {uniqueCategories.map(c => <option key={c} value={c} />)}
              </datalist>
            )}
          </div>
        ))}
        <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
          <label style={{ fontSize:11, color:"#888" }}>稅別</label>
          <select value={form.tax_type} onChange={e => setForm(p=>({...p,tax_type:e.target.value}))}
            style={{ padding:"7px 10px", border:"1px solid #ddd", borderRadius:6, fontSize:13, background:"#f8f7f3" }}>
            <option value="TAX">TAX（應稅 5%）</option>
            <option value="ZERO">ZERO（零稅率）</option>
            <option value="EXEMPT">EXEMPT（免稅）</option>
          </select>
        </div>
      </div>

      {/* BOM */}
      <div style={{ marginBottom:16 }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
          <span style={{ fontSize:12, fontWeight:500 }}>BOM 配方</span>
          <button onClick={addBOM} style={{ padding:"4px 10px", borderRadius:5, border:"1px solid #ddd", background:"#f8f7f3", fontSize:11, cursor:"pointer" }}>+ 加入原料</button>
        </div>
        {bom.map((b,idx) => {
          const ing = ingredients.find(i => i.id===parseInt(b.ingredient_id));
          return (
            <div key={idx} style={{ display:"flex", gap:8, alignItems:"center", marginBottom:6 }}>
              <select value={b.ingredient_id} onChange={e => setBom(p=>p.map((x,i)=>i===idx?{...x,ingredient_id:e.target.value}:x))}
                style={{ flex:2, padding:"6px 8px", border:"1px solid #ddd", borderRadius:5, fontSize:12, background:"#f8f7f3" }}>
                <option value="">-- 選擇原料 --</option>
                {ingredients.map(i => <option key={i.id} value={i.id}>{i.name}（{i.unit}）</option>)}
              </select>
              <input type="number" min="0" step="0.001" placeholder={`用量${ing?`(${ing.unit})`:""}`}
                value={b.qty_required}
                onChange={e => setBom(p=>p.map((x,i)=>i===idx?{...x,qty_required:e.target.value}:x))}
                style={{ flex:1, padding:"6px 8px", border:"1px solid #ddd", borderRadius:5, fontSize:12, maxWidth:100, outline:"none" }} />
              <button onClick={() => removeBOM(idx)} style={{ padding:"4px 8px", borderRadius:5, border:"1px solid #f7c1c1", background:"#FCEBEB", color:"#A32D2D", fontSize:12, cursor:"pointer" }}>✕</button>
            </div>
          );
        })}
        {bom.length > 0 && form.price && (
          <div style={{ fontSize:12, color:"#888", marginTop:8 }}>
            BOM 成本：<span style={{ fontFamily:"monospace" }}>${bomCost.toFixed(2)}</span>
            ｜毛利：<span style={{ fontFamily:"monospace", color: (parseFloat(form.price)-bomCost)>=0?"#27500A":"#A32D2D" }}>
              ${(parseFloat(form.price)-bomCost).toFixed(2)}
              （{parseFloat(form.price)>0?((parseFloat(form.price)-bomCost)/parseFloat(form.price)*100).toFixed(1):"—"}%）
            </span>
          </div>
        )}
      </div>

      <button disabled={!form.name||!form.price||saveMut.isPending} onClick={handleSave}
        style={{ padding:"9px 24px", borderRadius:6, background: !form.name||!form.price?"#ccc":"#1a1a18", color:"#fff", border:"none", fontSize:13, cursor:"pointer" }}>
        {saveMut.isPending ? "儲存中..." : isEdit ? "儲存變更" : "建立商品"}
      </button>
    </div>
  );
}
