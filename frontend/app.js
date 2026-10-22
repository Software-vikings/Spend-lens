(() => {
"use strict";
const $ = id => document.getElementById(id);
const state = {file:null,result:null,page:0,filter:"all",search:""};
const pageSize=50,maxBytes=10*1024*1024;
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const num=v=>new Intl.NumberFormat().format(Number(v||0));
const amount=(v,c)=>{
  try { if(c&&c!=="UNKNOWN") return new Intl.NumberFormat(undefined,{style:"currency",currency:c,maximumFractionDigits:2}).format(Number(v||0)); } catch(e) {}
  return esc(c||"")+" "+Number(v||0).toFixed(2);
};
const message=(v,kind="")=>{$("upload-message").textContent=v;$("upload-message").className="upload-message "+kind;};
const bytes=v=>v<1048576?(v/1024).toFixed(1)+" KB":(v/1048576).toFixed(2)+" MB";
const choose=()=> $("file-input").click();
function setFile(file){
 if(!file)return;
 const ext=file.name.split(".").pop().toLowerCase();
 if(!["csv","xlsx"].includes(ext)){clearFile();message("Choose a CSV or XLSX file.","error");return;}
 if(file.size>maxBytes){clearFile();message("The file is larger than 10 MB. Split it into smaller files.","error");return;}
 if(!file.size){clearFile();message("The selected file is empty.","error");return;}
 state.file=file;$("file-name").textContent=file.name;$("file-size").textContent=bytes(file.size);
 $("selected-file").classList.remove("hidden");$("analyse-button").disabled=false;message("File ready for analysis.");
}
function clearFile(){state.file=null;$("file-input").value="";$("selected-file").classList.add("hidden");$("analyse-button").disabled=true;message("");}
$("browse-button").addEventListener("click",choose);
$("drop-zone").addEventListener("click",e=>{if(!e.target.closest("button"))choose();});
$("drop-zone").addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();choose();}});
$("file-input").addEventListener("change",e=>setFile(e.target.files?.[0]));
$("remove-file").addEventListener("click",clearFile);
["dragenter","dragover"].forEach(t=>$("drop-zone").addEventListener(t,e=>{e.preventDefault();$("drop-zone").classList.add("dragover");}));
["dragleave","drop"].forEach(t=>$("drop-zone").addEventListener(t,e=>{e.preventDefault();$("drop-zone").classList.remove("dragover");}));
$("drop-zone").addEventListener("drop",e=>setFile(e.dataTransfer?.files?.[0]));

async function analyse(){
 if(!state.file)return;
 const btn=$("analyse-button");btn.disabled=true;btn.textContent="Analysing file…";message("Checking your transaction data.");
 try{
  const form=new FormData();form.append("file",state.file,state.file.name);
  const res=await fetch("/v1/imports/analyze",{method:"POST",body:form});
  const data=await res.json().catch(()=>({}));
  if(!res.ok){
   const wait=Number(res.headers.get("Retry-After")||data.retry_after_seconds||60);
   throw new Error(res.status===429?"Upload limit reached. Try again in about "+wait+" seconds.":(data.detail||"Analysis failed ("+res.status+")."));
  }
  state.result=data;state.page=0;state.filter="all";state.search="";
  $("search-results").value="";$("filter-results").value="all";renderResults();
  $("results").classList.remove("hidden");$("results").scrollIntoView({behavior:"smooth",block:"start"});
  message("Analysis complete. The uploaded file was not saved to a workspace.","success");
 }catch(e){message(e.message||"Unable to analyse this file.","error");}
 finally{btn.disabled=!state.file;btn.innerHTML='Analyse transactions <span>→</span>';}
}
$("analyse-button").addEventListener("click",analyse);

function renderResults(){
 const d=state.result,s=d.summary||{},cov=d.data_coverage||{};
 $("results-subtitle").textContent=(d.filename||"Uploaded file")+" · "+num(s.rows_analysed)+" records analysed";
 $("metric-rows").textContent=num(s.rows_analysed);$("metric-review").textContent=num(s.rows_with_signals);
 $("metric-duplicates").textContent=num(s.possible_duplicate_groups);$("metric-invalid").textContent=num(s.invalid_rows);
 const totals=Object.entries(s.positive_expense_totals||{});
 $("currency-totals").innerHTML=totals.length?totals.map(([c,v])=>'<div class="currency-chip">'+amount(v,c)+'<small>'+esc(c)+' positive transaction total</small></div>').join(""):'<span class="empty-text">No positive totals available.</span>';
 const names={transaction_date:"Date",merchant_name:"Merchant / payee",amount:"Amount",currency:"Currency",transaction_id:"Transaction reference",employee_id:"Employee",department:"Department",category:"Category",payment_method:"Payment method",business_purpose:"Business purpose",receipt_reference:"Receipt / invoice reference"};
 const found=Object.entries(cov.columns_detected||{}).map(([k,v])=>'<span class="coverage-chip">'+esc(names[k]||k)+' · '+esc(v)+'</span>');
 const missing=(cov.optional_fields_not_supplied||[]).map(k=>'<span class="coverage-chip missing">Not supplied · '+esc(names[k]||k)+'</span>');
 $("coverage").innerHTML=found.concat(missing).join("")||'<span class="empty-text">No column mapping data.</span>';
 $("limitations-copy").textContent=(d.limitations||[]).join(" ");
 const errors=d.row_errors||[];
 $("row-errors").classList.toggle("hidden",!errors.length);
 $("error-list").innerHTML=errors.map(x=>'<li>Row '+esc(x.row)+': '+esc(x.reason)+'</li>').join("");
 renderRows();
}
function filtered(){
 const q=state.search.trim().toLowerCase();
 return (state.result?.items||[]).filter(r=>{
  const review=r.review_status==="REVIEW";
  if(state.filter==="review"&&!review)return false;
  if(state.filter==="clear"&&review)return false;
  return !q||[r.transaction_id,r.merchant_name,r.employee_id,r.department,r.category].some(v=>String(v||"").toLowerCase().includes(q));
 });
}
function renderRows(){
 const rows=filtered(),pages=Math.max(1,Math.ceil(rows.length/pageSize));
 state.page=Math.min(state.page,pages-1);
 const current=rows.slice(state.page*pageSize,(state.page+1)*pageSize);
 $("results-table").innerHTML=current.length?current.map(r=>{
  const signals=r.signals||[];
  const reason=signals.length?'<div class="reason-list">'+signals.map(s=>'<span><strong>'+esc(s.title)+':</strong> '+esc(s.explanation)+'</span>').join("")+'</div>':'<span class="muted-reason">No configured screening signal detected.</span>';
  const badge=r.review_status==="REVIEW"?'<span class="status-pill review">Needs review</span>':'<span class="status-pill clear">No signal detected</span>';
  return '<tr><td>'+esc(r.transaction_date)+'<div class="subcell">Row '+esc(r.source_row)+'</div></td><td><strong>'+esc(r.merchant_name)+'</strong><div class="subcell">'+esc(r.transaction_id)+'</div></td><td>'+esc(r.category)+'</td><td class="numeric"><strong>'+amount(r.amount,r.currency)+'</strong></td><td>'+badge+'</td><td>'+reason+'</td></tr>';
 }).join(""):'<tr><td colspan="6" class="table-empty">No transactions match this filter.</td></tr>';
 $("table-count").innerHTML='<span>Showing '+(rows.length?state.page*pageSize+1:0)+'–'+Math.min((state.page+1)*pageSize,rows.length)+' of '+num(rows.length)+' matching rows</span><div class="table-pagination"><button id="table-prev" class="secondary-button" '+(state.page===0?"disabled":"")+'>Previous</button><button id="table-next" class="secondary-button" '+(state.page>=pages-1?"disabled":"")+'>Next</button></div>';
 $("table-prev").onclick=()=>{state.page--;renderRows();};$("table-next").onclick=()=>{state.page++;renderRows();};
}
$("search-results").addEventListener("input",e=>{state.search=e.target.value;state.page=0;renderRows();});
$("filter-results").addEventListener("change",e=>{state.filter=e.target.value;state.page=0;renderRows();});
const csvCell=v=>{const t=String(v??"");return /[",\r\n]/.test(t)?'"'+t.replace(/"/g,'""')+'"':t;};
$("download-report").addEventListener("click",()=>{
 if(!state.result)return;
 const fields=["source_row","transaction_id","transaction_date","merchant_name","category","amount","currency","employee_id","department","review_status","screening_signals"];
 const lines=[fields.join(",")];
 (state.result.items||[]).forEach(r=>{const row={...r,screening_signals:(r.signals||[]).map(s=>s.title+": "+s.explanation).join(" | ")};lines.push(fields.map(k=>csvCell(row[k])).join(","));});
 const blob=new Blob(["\ufeff"+lines.join("\r\n")],{type:"text/csv;charset=utf-8"}),url=URL.createObjectURL(blob);
 const a=document.createElement("a");a.href=url;a.download="spendlens-review-"+new Date().toISOString().slice(0,10)+".csv";document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
});
$("new-analysis").addEventListener("click",()=>{state.result=null;state.page=0;$("results").classList.add("hidden");clearFile();window.scrollTo({top:0,behavior:"smooth"});});
})();