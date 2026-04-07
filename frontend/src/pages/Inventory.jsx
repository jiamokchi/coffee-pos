import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, parseApiError } from "../lib/api";
import { compressImage } from "../lib/utils";

export default function Inventory() {
  const qc = useQueryClient();
  const [tab, setTab] = useState("list");
  const [lowOnly, setLowOnly] = useState(false);
  const [toast, setToast] = useState(null);
  const [showInactive, setShowInactive] = useState(false);

  const { data: ingredients = [], isLoading } = useQuery({
    queryKey: ["ingredients", lowOnly, showInactive],
    queryFn: () => api.get("/ingredients", { params: { low_stock_only: lowOnly, active_only: !showInactive } }).then(r => r.data),
  });

  const showToast = (msg, type="ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 2500);
  };

  const totalValue = ingredients.reduce((s,i) => s+parseFloat(i.current_stock)*parseFloat(i.avg_unit_cost), 0);

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%", overflow:"hidden", background:"#f8f7f3" }}>
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"14px 24px", background:"#fff", borderBottom:"1px solid #e5e4dc" }}>
        <span style={{ fontWeight:500, fontSize:15 }}>庫存管理</span>
        <div style={{ display:"flex", gap:8 }}>
          {[["list","原料清單"],["stockin","進貨入庫"],["adjust","盤點調整"]].map(([id,label]) => (
            <button key={id} onClick={() => setTab(id)} style={{ padding:"6px 14px", borderRadius:6, border:"1px solid", borderColor:tab===id?"#1a1a18":"#e0ddd6", background:tab===id?"#1a1a18":"#fff", color:tab===id?"#fff":"#555", fontSize:13, cursor:"pointer" }}>{label}</button>
          ))}
        </div>
      </div>
      <div style={{ flex:1, overflow:"auto", padding:24 }}>
        {tab==="list"    && <IngredientList ingredients={ingredients} isLoading={isLoading} lowOnly={lowOnly} setLowOnly={setLowOnly} totalValue={totalValue} qc={qc} showToast={showToast} showInactive={showInactive} setShowInactive={setShowInactive} />}
        {tab==="stockin" && <StockInForm   ingredients={ingredients} qc={qc} showToast={showToast} />}
        {tab==="adjust"  && <AdjustForm    ingredients={ingredients} qc={qc} showToast={showToast} />}
      </div>
      {toast && <div style={{ position:"fixed", bottom:24, left:"50%", transform:"translateX(-50%)", background:toast.type==="err"?"#A32D2D":"#1a1a18", color:"#fff", padding:"9px 20px", borderRadius:20, fontSize:13, zIndex:999, whiteSpace:"nowrap" }}>{toast.msg}</div>}
    </div>
  );
}

function IngredientList({ ingredients, isLoading, lowOnly, setLowOnly, totalValue, qc, showToast, showInactive, setShowInactive }) {
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name:"", unit:"ml", min_stock_level:"" });

  const createMut = useMutation({
    mutationFn: d => api.post("/ingredients", { name:d.name, unit:d.unit, min_stock_level:parseFloat(d.min_stock_level)||0 }).then(r=>r.data),
    onSuccess: () => { qc.invalidateQueries({queryKey:["ingredients"]}); setAdding(false); setForm({name:"",unit:"ml",min_stock_level:""}); showToast("原料已新增"); },
    onError: e => showToast(parseApiError(e),"err"),
  });

  const updateMut = useMutation({
    mutationFn: ({id,data}) => api.patch(`/ingredients/${id}`,data).then(r=>r.data),
    onSuccess: () => { qc.invalidateQueries({queryKey:["ingredients"]}); setEditing(null); showToast("原料已更新"); },
    onError: e => showToast(parseApiError(e),"err"),
  });

  const deleteMut = useMutation({
    mutationFn: id => api.delete(`/ingredients/${id}`),
    onSuccess: () => { qc.invalidateQueries({queryKey:["ingredients"]}); showToast("原料已刪除"); },
    onError: e => showToast(parseApiError(e),"err"),
  });


  return (
    <div>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:12, marginBottom:20 }}>
        {[{label:"原料種類",value:`${ingredients.length} 種`},{label:"低庫存警報",value:`${ingredients.filter(i=>i.is_low_stock).length} 項`,warn:ingredients.filter(i=>i.is_low_stock).length>0},{label:"庫存總估值",value:`NT$ ${Math.round(totalValue).toLocaleString()}`}].map(c=>(
          <div key={c.label} style={{ background:"#fff", border:"1px solid #e5e4dc", borderRadius:8, padding:"16px 20px", textAlign:"center" }}>
            <div style={{ fontSize:11, color:c.warn?"#A32D2D":"#888", marginBottom:6 }}>{c.label}</div>
            <div style={{ fontSize:22, fontWeight:500, color:c.warn?"#A32D2D":"#1a1a18" }}>{c.value}</div>
          </div>
        ))}
      </div>
      <div style={{ display:"flex", gap:12, marginBottom:14, alignItems:"center" }}>
        <label style={{ display:"flex", alignItems:"center", gap:6, fontSize:12, color:"#666", cursor:"pointer" }}>
          <input type="checkbox" checked={showInactive} onChange={e=>setLowOnly(false)||setShowInactive(e.target.checked)} />顯示下架原料
        </label>
        <div style={{ flex:1 }} />
        <button onClick={()=>setAdding(true)} style={{ padding:"7px 16px", borderRadius:6, background:"#1a1a18", color:"#fff", border:"none", fontSize:13, cursor:"pointer" }}>+ 新增原料</button>
      </div>

      {adding && (
        <div style={{ background:"#fff", border:"1px solid #e5e4dc", borderRadius:8, padding:"16px 20px", marginBottom:16 }}>
          <div style={{ display:"flex", gap:10, alignItems:"flex-end", flexWrap:"wrap" }}>
            {[{label:"原料名稱",key:"name",type:"text",ph:"全脂牛奶"},{label:"單位",key:"unit",type:"text",ph:"ml / g / 個"},{label:"安全庫存",key:"min_stock_level",type:"number",ph:"500"}].map(f=>(
              <div key={f.key} style={{ display:"flex", flexDirection:"column", gap:4, flex:1, minWidth:120 }}>
                <label style={{ fontSize:11, color:"#888" }}>{f.label}</label>
                <input type={f.type} placeholder={f.ph} value={form[f.key]} onChange={e=>setForm(p=>({...p,[f.key]:e.target.value}))} style={{ padding:"7px 10px", border:"1px solid #ddd", borderRadius:6, fontSize:13, outline:"none" }} />
              </div>
            ))}
            <button onClick={()=>createMut.mutate(form)} disabled={!form.name||!form.unit||createMut.isPending} style={{ padding:"7px 16px", borderRadius:6, background:!form.name||!form.unit?"#ccc":"#1a1a18", color:"#fff", border:"none", fontSize:13, cursor:"pointer" }}>
              {createMut.isPending?"新增中...":"確認"}
            </button>
            <button onClick={()=>setAdding(false)} style={{ padding:"7px 14px", borderRadius:6, background:"#f0ede8", color:"#555", border:"1px solid #ddd", fontSize:13, cursor:"pointer" }}>取消</button>
          </div>
        </div>
      )}

      {editing && <EditIngredientForm ingredient={editing} onSave={(id,data)=>updateMut.mutate({id,data})} onClose={()=>setEditing(null)} qc={qc} showToast={showToast} />}

      <div style={{ background:"#fff", border:"1px solid #e5e4dc", borderRadius:8, overflow:"hidden" }}>
        {isLoading ? <p style={{ padding:20, color:"#aaa", fontSize:13 }}>載入中…</p> : (
          <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
            <thead><tr>{["","原料名稱","現有庫存","安全庫存","WAC","估值","狀態","操作"].map(h=><th key={h} style={{ textAlign:"left", padding:"8px 12px", fontSize:11, color:"#888", borderBottom:"1px solid #e5e4dc", fontWeight:500 }}>{h}</th>)}</tr></thead>
            <tbody>
              {ingredients.map(i=>(
                <tr key={i.id} style={{ borderBottom:"1px solid #f0ece5" }}>
                  <td style={{ padding:"10px 12px", width:44 }}>
                    <div style={{ width:36, height:36, borderRadius:6, overflow:"hidden", background:"#f0ede8", display:"flex", alignItems:"center", justifyContent:"center", fontSize:20 }}>
                      {i.image_url?<img src={i.image_url} style={{ width:"100%", height:"100%", objectFit:"cover" }} alt=""/>:"🧴"}
                    </div>
                  </td>
                  <td style={{ padding:"10px 12px", fontWeight:500 }}>{i.name}</td>
                  <td style={{ padding:"10px 12px", fontFamily:"monospace" }}>{parseFloat(i.current_stock).toFixed(1)} {i.unit}</td>
                  <td style={{ padding:"10px 12px", fontFamily:"monospace", color:"#888" }}>{parseFloat(i.min_stock_level).toFixed(0)} {i.unit}</td>
                  <td style={{ padding:"10px 12px", fontFamily:"monospace" }}>${parseFloat(i.avg_unit_cost).toFixed(2)}/{i.unit}</td>
                  <td style={{ padding:"10px 12px", fontFamily:"monospace" }}>NT$ {Math.round(parseFloat(i.current_stock)*parseFloat(i.avg_unit_cost)).toLocaleString()}</td>
                  <td style={{ padding:"10px 12px" }}>
                    <span style={{ display:"inline-flex", alignItems:"center", padding:"2px 10px", borderRadius:20, fontSize:11, fontWeight:500, background: !i.is_active ? "#f8f7f3" : (i.is_low_stock?"#FCEBEB":"#EAF3DE"), color: !i.is_active ? "#999" : (i.is_low_stock?"#A32D2D":"#27500A") }}>
                      {!i.is_active ? "已下架" : (i.is_low_stock?"庫存不足":"正常")}
                    </span>
                  </td>
                  <td style={{ padding:"10px 12px" }}>
                    <div style={{ display:"flex", gap:6 }}>
                      <button onClick={()=>setEditing(i)} style={{ padding:"4px 10px", borderRadius:5, border:"1px solid #ddd", background:"#f8f7f3", fontSize:11, cursor:"pointer" }}>編輯</button>
                      {i.is_active ? (
                        <button onClick={()=>updateMut.mutate({id:i.id, data:{is_active:false}})} style={{ padding:"4px 10px", borderRadius:5, border:"1px solid #f7c1c1", background:"#FCEBEB", color:"#A32D2D", fontSize:11, cursor:"pointer" }}>下架</button>
                      ) : (
                        <button onClick={()=>updateMut.mutate({id:i.id, data:{is_active:true}})} style={{ padding:"4px 10px", borderRadius:5, border:"1px solid #d1e7dd", background:"#eaf3de", color:"#27500A", fontSize:11, cursor:"pointer" }}>上架</button>
                      )}
                      <button onClick={()=>{ if(window.confirm(`確認刪除原料「${i.name}」？`)) deleteMut.mutate(i.id); }} style={{ padding:"4px 10px", borderRadius:5, border:"1px solid #ddd", background:"#fff", fontSize:11, cursor:"pointer" }}>刪除</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function EditIngredientForm({ ingredient, onSave, onClose, qc, showToast }) {
  const [form, setForm] = useState({ name:ingredient.name, unit:ingredient.unit, min_stock_level:ingredient.min_stock_level });
  const fileRef = useRef();

  const imgMut = useMutation({
    mutationFn: async (file) => {
      const compressed = await compressImage(file);
      const fd = new FormData();
      fd.append("file", compressed);
      return api.post(`/images/ingredient/${ingredient.id}`, fd, { headers: { "Content-Type": "multipart/form-data" } }).then(r => r.data);
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["ingredients"] }); showToast("圖片已更新"); },
    onError: e => showToast(parseApiError(e), "err"),
  });

  const handlePaste = async (e) => {
    const item = e.clipboardData.items[0];
    if (item?.type?.startsWith("image/")) {
      const file = item.getAsFile();
      imgMut.mutate(file);
    }
  };

  const delImgMut = useMutation({
    mutationFn: () => api.delete(`/images/ingredient/${ingredient.id}`),
    onSuccess: () => { qc.invalidateQueries({queryKey:["ingredients"]}); showToast("圖片已移除"); },
  });

  return (
    <div onPaste={handlePaste} style={{ background:"#fff", border:"2px solid #1a1a18", borderRadius:8, padding:"16px 20px", marginBottom:16 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:14 }}>
        <span style={{ fontWeight:500, fontSize:14 }}>編輯：{ingredient.name}</span>
        <button onClick={onClose} style={{ border:"none", background:"none", cursor:"pointer", color:"#888", fontSize:16 }}>✕</button>
      </div>
      <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:14, padding:"12px", background:"#f8f7f3", borderRadius:8 }}>
        <div style={{ width:64, height:64, borderRadius:8, overflow:"hidden", background:"#e0ddd6", display:"flex", alignItems:"center", justifyContent:"center", fontSize:32, flexShrink:0 }}>
          {ingredient.image_url?<img src={ingredient.image_url} style={{ width:"100%", height:"100%", objectFit:"cover" }} alt=""/>:"🧴"}
        </div>
        <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
          <input type="file" ref={fileRef} accept="image/*" style={{ display:"none" }} onChange={e=>e.target.files[0]&&imgMut.mutate(e.target.files[0])} />
          <button onClick={()=>fileRef.current.click()} style={{ padding:"6px 14px", borderRadius:5, border:"1px solid #ddd", background:"#fff", fontSize:12, cursor:"pointer" }}>{imgMut.isPending?"上傳中...":"上傳圖片"}</button>
          {ingredient.image_url&&<button onClick={()=>delImgMut.mutate()} style={{ padding:"6px 14px", borderRadius:5, border:"1px solid #f7c1c1", background:"#FCEBEB", color:"#A32D2D", fontSize:12, cursor:"pointer" }}>移除圖片</button>}
          <span style={{ fontSize:11, color:"#aaa" }}>支援 JPG / PNG / WebP，上限 2MB</span>
        </div>
      </div>
      <div style={{ display:"flex", gap:10, flexWrap:"wrap", marginBottom:12 }}>
        {[{label:"原料名稱",key:"name",type:"text"},{label:"單位",key:"unit",type:"text"},{label:"安全庫存",key:"min_stock_level",type:"number"}].map(f=>(
          <div key={f.key} style={{ display:"flex", flexDirection:"column", gap:4, flex:1, minWidth:120 }}>
            <label style={{ fontSize:11, color:"#888" }}>{f.label}</label>
            <input type={f.type} value={form[f.key]} onChange={e=>setForm(p=>({...p,[f.key]:e.target.value}))} style={{ padding:"7px 10px", border:"1px solid #ddd", borderRadius:6, fontSize:13, outline:"none" }} />
          </div>
        ))}
      </div>
      <div style={{ display:"flex", gap:8 }}>
        <button onClick={()=>onSave(ingredient.id,{...form,min_stock_level:parseFloat(form.min_stock_level)||0})} style={{ padding:"7px 20px", borderRadius:6, background:"#1a1a18", color:"#fff", border:"none", fontSize:13, cursor:"pointer" }}>儲存變更</button>
        <button onClick={onClose} style={{ padding:"7px 14px", borderRadius:6, background:"#f0ede8", color:"#555", border:"1px solid #ddd", fontSize:13, cursor:"pointer" }}>取消</button>
      </div>
    </div>
  );
}

function StockInForm({ ingredients, qc, showToast }) {
  const [form, setForm] = useState({ ingredient_id:"", qty:"", unit_cost:"", note:"" });
  const mut = useMutation({
    mutationFn: d => api.post("/inventory/stock-in",{ingredient_id:parseInt(d.ingredient_id),qty:parseFloat(d.qty),unit_cost:parseFloat(d.unit_cost),note:d.note}).then(r=>r.data),
    onSuccess: d => { qc.invalidateQueries({queryKey:["ingredients"]}); setForm({ingredient_id:"",qty:"",unit_cost:"",note:""}); showToast(`進貨完成，新 WAC: $${parseFloat(d.new_avg_cost).toFixed(2)}`); },
    onError: e => showToast(parseApiError(e),"err"),
  });
  const selected = ingredients.find(i=>i.id===parseInt(form.ingredient_id));
  const previewWAC = selected&&form.qty&&form.unit_cost ? (selected.current_stock<=0?parseFloat(form.unit_cost):(parseFloat(selected.current_stock)*parseFloat(selected.avg_unit_cost)+parseFloat(form.qty)*parseFloat(form.unit_cost))/(parseFloat(selected.current_stock)+parseFloat(form.qty))) : null;
  return (
    <div style={{ maxWidth:520 }}>
      <div style={{ background:"#fff", border:"1px solid #e5e4dc", borderRadius:8, padding:"20px" }}>
        <h3 style={{ fontSize:14, fontWeight:500, marginBottom:16 }}>新增進貨記錄</h3>
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
            <label style={{ fontSize:11, color:"#888" }}>選擇原料</label>
            <select value={form.ingredient_id} onChange={e=>setForm(p=>({...p,ingredient_id:e.target.value}))} style={{ padding:"7px 10px", border:"1px solid #ddd", borderRadius:6, fontSize:13, background:"#f8f7f3" }}>
              <option value="">-- 請選擇 --</option>
              {ingredients.map(i=><option key={i.id} value={i.id}>{i.name}（現有 {parseFloat(i.current_stock).toFixed(1)} {i.unit}）</option>)}
            </select>
          </div>
          {selected&&<div style={{ background:"#f8f7f3", borderRadius:6, padding:"8px 12px", fontSize:12, color:"#666" }}>現有庫存 <strong style={{ fontFamily:"monospace" }}>{parseFloat(selected.current_stock).toFixed(1)} {selected.unit}</strong>｜WAC <strong style={{ fontFamily:"monospace" }}>${parseFloat(selected.avg_unit_cost).toFixed(2)}</strong></div>}
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:12 }}>
            <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
              <label style={{ fontSize:11, color:"#888" }}>進貨數量 {selected?`(${selected.unit})`:""}</label>
              <input type="number" min="0" step="0.001" value={form.qty} onChange={e=>setForm(p=>({...p,qty:e.target.value}))} style={{ padding:"7px 10px", border:"1px solid #ddd", borderRadius:6, fontSize:13, outline:"none" }} />
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
              <label style={{ fontSize:11, color:"#888" }}>進貨單價（元/{selected?.unit||""}）</label>
              <input type="number" min="0" step="0.01" value={form.unit_cost} onChange={e=>setForm(p=>({...p,unit_cost:e.target.value}))} style={{ padding:"7px 10px", border:"1px solid #ddd", borderRadius:6, fontSize:13, outline:"none" }} />
            </div>
          </div>
          {previewWAC!==null&&<div style={{ background:"#EAF3DE", borderRadius:6, padding:"8px 12px", fontSize:12 }}>入庫後預估 WAC：<strong style={{ fontFamily:"monospace", color:"#27500A" }}>${previewWAC.toFixed(2)}</strong> / {selected.unit}</div>}
          <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
            <label style={{ fontSize:11, color:"#888" }}>備註（選填）</label>
            <input type="text" placeholder="供應商、發票號碼…" value={form.note} onChange={e=>setForm(p=>({...p,note:e.target.value}))} style={{ padding:"7px 10px", border:"1px solid #ddd", borderRadius:6, fontSize:13, outline:"none" }} />
          </div>
          <button disabled={!form.ingredient_id||!form.qty||!form.unit_cost||mut.isPending} onClick={()=>mut.mutate(form)} style={{ padding:"10px 24px", borderRadius:6, background:!form.ingredient_id||!form.qty||!form.unit_cost?"#ccc":"#1a1a18", color:"#fff", border:"none", fontSize:13, cursor:"pointer", alignSelf:"flex-start" }}>
            {mut.isPending?"處理中...":"確認入庫"}
          </button>
        </div>
      </div>
    </div>
  );
}

function AdjustForm({ ingredients, qc, showToast }) {
  const [form, setForm] = useState({ ingredient_id:"", actual_qty:"", note:"盤點調整" });
  const mut = useMutation({
    mutationFn: d => api.post("/inventory/adjust",{ingredient_id:parseInt(d.ingredient_id),actual_qty:parseFloat(d.actual_qty),note:d.note}).then(r=>r.data),
    onSuccess: d => { qc.invalidateQueries({queryKey:["ingredients"]}); setForm({ingredient_id:"",actual_qty:"",note:"盤點調整"}); const diff=d.difference>0?`+${d.difference.toFixed(1)}`:d.difference.toFixed(1); showToast(`盤點完成，差異 ${diff}`); },
    onError: e => showToast(parseApiError(e),"err"),
  });
  const selected = ingredients.find(i=>i.id===parseInt(form.ingredient_id));
  const diff = selected&&form.actual_qty!==""?parseFloat(form.actual_qty)-parseFloat(selected.current_stock):null;
  return (
    <div style={{ maxWidth:480 }}>
      <div style={{ background:"#fff", border:"1px solid #e5e4dc", borderRadius:8, padding:"20px" }}>
        <h3 style={{ fontSize:14, fontWeight:500, marginBottom:16 }}>盤點庫存調整</h3>
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
            <label style={{ fontSize:11, color:"#888" }}>選擇原料</label>
            <select value={form.ingredient_id} onChange={e=>setForm(p=>({...p,ingredient_id:e.target.value}))} style={{ padding:"7px 10px", border:"1px solid #ddd", borderRadius:6, fontSize:13, background:"#f8f7f3" }}>
              <option value="">-- 請選擇 --</option>
              {ingredients.map(i=><option key={i.id} value={i.id}>{i.name}（系統 {parseFloat(i.current_stock).toFixed(1)} {i.unit}）</option>)}
            </select>
          </div>
          <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
            <label style={{ fontSize:11, color:"#888" }}>實際盤點數量 {selected?`(${selected.unit})`:""}</label>
            <input type="number" min="0" step="0.001" value={form.actual_qty} onChange={e=>setForm(p=>({...p,actual_qty:e.target.value}))} style={{ padding:"7px 10px", border:"1px solid #ddd", borderRadius:6, fontSize:13, outline:"none" }} />
          </div>
          {diff!==null&&<div style={{ background:diff===0?"#EAF3DE":diff>0?"#FAEEDA":"#FCEBEB", borderRadius:6, padding:"8px 12px", fontSize:12 }}>差異：<strong style={{ fontFamily:"monospace", color:diff===0?"#27500A":diff>0?"#633806":"#A32D2D" }}>{diff>0?"+":""}{diff.toFixed(1)} {selected.unit}</strong>{diff>0?" （盤盈）":diff<0?" （盤損）":" （吻合）"}</div>}
          <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
            <label style={{ fontSize:11, color:"#888" }}>備註</label>
            <input type="text" value={form.note} onChange={e=>setForm(p=>({...p,note:e.target.value}))} style={{ padding:"7px 10px", border:"1px solid #ddd", borderRadius:6, fontSize:13, outline:"none" }} />
          </div>
          <button disabled={!form.ingredient_id||form.actual_qty===""||mut.isPending} onClick={()=>mut.mutate(form)} style={{ padding:"10px 24px", borderRadius:6, background:!form.ingredient_id||form.actual_qty===""?"#ccc":"#1a1a18", color:"#fff", border:"none", fontSize:13, cursor:"pointer", alignSelf:"flex-start" }}>
            {mut.isPending?"處理中...":"確認調整"}
          </button>
        </div>
      </div>
    </div>
  );
}
