(() => {
  const $ = id => document.getElementById(id);
  const state = {key:"", findings:[], transactions:[], page:0, pageSize:25, total:0, selected:null, overview:null};
  const money = n => new Intl.NumberFormat("en-IE",{style:"currency",currency:"EUR",maximumFractionDigits:0}).format(Number(n||0));
  const number = n => new Intl.NumberFormat("en-US").format(Number(n||0));
  const esc = v => String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const api = async (path, options={}) => {
    const response = await fetch(path,{...options,headers:{"X-API-Key":state.key,"Content-Type":"application/json",...(options.headers||{})}});
    if (!response.ok) { let message=`Request failed (${response.status})`;try{message=(await response.json()).detail||message}catch{};throw new Error(message); }
    return response.json();
  };
  const toast = msg => { $("toast").textContent=msg;$("toast").classList.add("show");setTimeout(()=>$("toast").classList.remove("show"),2600); };
  const connect = async () => {
    state.key=$("api-key").value.trim();
    if(!state.key){$("connect-error").textContent="Enter an API key to continue.";return;}
    try { await api("/v1/summary"); sessionStorage.setItem("spendlens-key",state.key);$("connect-overlay").classList.add("hidden");$("connection-dot").classList.remove("red");$("connection-label").textContent="Connected";await refreshAll(); }
    catch(e){$("connect-error").textContent=e.message;state.key="";}
  };
  const refreshAll = async () => {
    try {
      const [summary,overview,findings]=await Promise.all([api("/v1/summary"),api("/v1/analytics/overview"),api("/v1/findings?limit=100")]);
      state.overview=overview;state.findings=findings.items||[];
      $("total-spend").textContent=money(summary.total_spend);
      $("transaction-count").textContent=number(summary.transaction_count);
      const open=Object.entries(summary.findings_by_status||{}).filter(([k])=>["new","under_review"].includes(k)).reduce((a,[,v])=>a+v,0);
      $("open-findings").textContent=number(open);
      $("finding-types").textContent=number(Object.keys(summary.findings_by_type||{}).length);
      $("nav-count").textContent=number(state.findings.length);
      renderTrend(overview.monthly||[]);renderDepartments(overview.departments||[]);renderCategories(overview.categories||[]);renderLatest();
      renderFindings(); await loadTransactions();
    } catch(e){toast(e.message);if(/key|auth|credential/i.test(e.message)){ $("connect-overlay").classList.remove("hidden");$("connection-label").textContent="Disconnected";$("connection-dot").classList.add("red");}}
  };
  const renderTrend = rows => {
    if(!rows.length){$("trend-chart").innerHTML='<div class="empty">No monthly data available</div>';return;}
    const max=Math.max(...rows.map(x=>x.spend),1);
    $("trend-chart").innerHTML=rows.map(x=>`<div class="trend-col"><div class="trend-bar-wrap"><div class="trend-bar" style="height:${Math.max(3,x.spend/max*100)}%"><span>${money(x.spend)}</span></div></div><small>${esc(x.month)}</small></div>`).join("");
  };
  const renderDepartments = rows => {
    const max=Math.max(...rows.map(x=>x.spend),1);
    $("department-chart").innerHTML=rows.map(x=>`<div class="bar-row"><label title="${esc(x.department)}">${esc(x.department)}</label><div class="bar-track"><div class="bar-fill" style="width:${x.spend/max*100}%"></div></div><b>${money(x.spend)}</b></div>`).join("")||'<div class="empty">No department data</div>';
  };
  const renderCategories = rows => $("category-list").innerHTML=rows.map(x=>`<div class="category-item"><span>${esc(x.category)}</span><b>${money(x.spend)}</b></div>`).join("")||'<div class="empty">No category data</div>';
  const details = f => f.details||{};
  const merchant = f => details(f).merchant_name||details(f).merchant||details(f).merchant_id||f.finding_type.replaceAll("_"," ");
  const amount = f => details(f).amount??details(f).current_amount??details(f).new_amount??details(f).total_amount;
  const renderLatest = () => {
    const rows=state.findings.slice(0,5);
    $("latest-findings").innerHTML=rows.map(f=>`<div class="finding-line" data-id="${esc(f.finding_id)}"><div><div class="finding-title">${esc(merchant(f))}</div><div class="finding-meta">${esc(f.finding_type.replaceAll("_"," "))} · ${esc(f.finding_id.slice(0,12))}</div></div><div><div class="finding-amount">${amount(f)!=null?money(amount(f)):"—"}</div><div style="text-align:right;margin-top:5px"><span class="status ${esc(f.review_status)}">${esc(f.review_status.replaceAll("_"," "))}</span></div></div></div>`).join("")||'<div class="empty">No findings yet</div>';
    $("latest-findings").querySelectorAll("[data-id]").forEach(el=>el.addEventListener("click",()=>openFinding(el.dataset.id)));
  };
  const renderFindings = () => {
    const q=$("finding-search").value.toLowerCase(),status=$("finding-status").value;
    const rows=state.findings.filter(f=>(!status||f.review_status===status)&&[f.finding_id,f.finding_type,merchant(f)].join(" ").toLowerCase().includes(q));
    $("findings-table").innerHTML=rows.map(f=>`<tr><td><strong>${esc(f.finding_id.slice(0,15))}</strong><div class="finding-meta">${esc(f.last_seen_at||"")}</div></td><td>${esc(merchant(f))}<div class="finding-meta">${esc(f.finding_type.replaceAll("_"," "))}</div></td><td>${amount(f)!=null?money(amount(f)):"—"}</td><td>${number(f.occurrence_count||1)}</td><td><span class="status ${esc(f.review_status)}">${esc(f.review_status.replaceAll("_"," "))}</span></td><td><button class="secondary-btn small" data-open="${esc(f.finding_id)}">Review →</button></td></tr>`).join("")||'<tr><td colspan="6" class="empty">No matching findings</td></tr>';
    $("findings-table").querySelectorAll("[data-open]").forEach(el=>el.addEventListener("click",()=>openFinding(el.dataset.open)));
  };
  const loadTransactions = async () => {
    const dept=$("transaction-department").value,cat=$("transaction-category").value;
    const qs=new URLSearchParams({limit:state.pageSize,offset:state.page*state.pageSize});
    if(dept)qs.set("department",dept);if(cat)qs.set("category",cat);
    const search=$("transaction-search").value.trim();if(search)qs.set("q",search);
    const data=await api("/v1/transactions?"+qs.toString());state.transactions=data.items||[];state.total=data.total||0;
    const departments=(state.overview?.departments||[]).map(x=>x.department).sort();
    const categories=(state.overview?.categories||[]).map(x=>x.category).sort();
    if(!$("transaction-department").dataset.ready){$("transaction-department").innerHTML='<option value="">All departments</option>'+departments.map(x=>`<option>${esc(x)}</option>`).join("");$("transaction-department").dataset.ready="1";}
    if(!$("transaction-category").dataset.ready){$("transaction-category").innerHTML='<option value="">All categories</option>'+categories.map(x=>`<option>${esc(x)}</option>`).join("");$("transaction-category").dataset.ready="1";}
    renderTransactions();
  };
  const renderTransactions = () => {
    const q=$("transaction-search").value.toLowerCase();
    const rows=state.transactions.filter(x=>[x.transaction_id,x.merchant_name,x.employee_id,x.department,x.category].join(" ").toLowerCase().includes(q));
    $("transactions-table").innerHTML=rows.map(x=>`<tr><td>${esc(x.transaction_date)}</td><td><strong>${esc(x.merchant_name)}</strong><div class="finding-meta">${esc(x.merchant_id)}</div></td><td>${esc(x.department)}</td><td>${esc(x.category)}</td><td>${esc(x.employee_id)}</td><td class="right"><strong>${money(x.amount)}</strong></td></tr>`).join("")||'<tr><td colspan="6" class="empty">No matching transactions</td></tr>';
    $("transaction-page-label").textContent=`Showing ${state.total?state.page*state.pageSize+1:0}–${Math.min((state.page+1)*state.pageSize,state.total)} of ${number(state.total)}`;
    $("prev-page").disabled=state.page===0;$("next-page").disabled=(state.page+1)*state.pageSize>=state.total;
  };
  const openFinding = async id => {
    try{
      const f=await api(`/v1/findings/${encodeURIComponent(id)}`);state.selected=f;
      const d=details(f),amt=amount(f);
      $("finding-detail").innerHTML=`<div class="eyebrow">FINDING DETAIL</div><h2>${esc(merchant(f))}</h2><div class="detail-type">${esc(f.finding_type.replaceAll("_"," "))} · ${esc(f.finding_id)}</div><div class="detail-amount">${amt!=null?money(amt):"Amount not supplied"}</div><div class="detail-section"><h3>Signal context</h3><div class="detail-grid">${Object.entries(d).slice(0,10).map(([k,v])=>`<div class="detail-field"><small>${esc(k.replaceAll("_"," "))}</small><b>${esc(typeof v==="object"?JSON.stringify(v):v)}</b></div>`).join("")}</div></div><div class="detail-section"><h3>Review history</h3>${(f.events||[]).map(e=>`<div class="finding-meta" style="padding:6px 0">${esc(e.event_at)} · ${esc(e.old_status)} → ${esc(e.new_status)} · ${esc(e.reviewer||"")}${e.note?"<br>"+esc(e.note):""}</div>`).join("")||'<div class="finding-meta">No review events yet</div>'}</div><div class="detail-section"><h3>Update review status</h3><div class="review-form"><select id="review-status"><option value="new">New</option><option value="under_review">Under review</option><option value="confirmed">Confirmed</option><option value="dismissed">Dismissed</option><option value="resolved">Resolved</option></select><input id="reviewer-name" placeholder="Reviewer name"><textarea id="review-note" placeholder="Add investigation note (optional)"></textarea><button class="primary-btn" id="save-review">Save review update →</button></div></div>`;
      $("review-status").value=f.review_status;$("save-review").addEventListener("click",saveReview);
      $("drawer-backdrop").classList.remove("hidden");
    }catch(e){toast(e.message);}
  };
  const saveReview = async () => {
    if(!state.selected)return;
    const reviewer=$("reviewer-name").value.trim();if(reviewer.length<2){toast("Enter your reviewer name.");return;}
    try{
      await api(`/v1/findings/${encodeURIComponent(state.selected.finding_id)}/review`,{method:"PATCH",body:JSON.stringify({status:$("review-status").value,reviewer,note:$("review-note").value})});
      toast("Review update saved.");$("drawer-backdrop").classList.add("hidden");await refreshAll();
    }catch(e){toast(e.message);}
  };
  const showSection = id => {
    ["overview","findings","transactions"].forEach(x=>$(x).classList.toggle("hidden",x!==id));
    document.querySelectorAll(".nav-item").forEach(a=>a.classList.toggle("active",a.getAttribute("href")==="#"+id));
    $("crumb-title").textContent=id[0].toUpperCase()+id.slice(1);
  };
  document.querySelectorAll(".nav-item").forEach(a=>a.addEventListener("click",e=>{e.preventDefault();const id=a.getAttribute("href").slice(1);showSection(id);if(id==="transactions")loadTransactions();}));
  $("connect-btn").addEventListener("click",connect);$("api-key").addEventListener("keydown",e=>{if(e.key==="Enter")connect();});
  $("refresh-btn").addEventListener("click",refreshAll);$("findings-refresh").addEventListener("click",refreshAll);$("transactions-refresh").addEventListener("click",()=>loadTransactions());
  $("finding-search").addEventListener("input",renderFindings);$("finding-status").addEventListener("change",renderFindings);
  let searchTimer=null;
  $("transaction-search").addEventListener("input",()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{state.page=0;loadTransactions();},250);});
  ["transaction-department","transaction-category"].forEach(id=>$(id).addEventListener("change",()=>{state.page=0;loadTransactions();}));
  $("prev-page").addEventListener("click",()=>{if(state.page>0){state.page--;loadTransactions();}});
  $("next-page").addEventListener("click",()=>{if((state.page+1)*state.pageSize<state.total){state.page++;loadTransactions();}});
  $("drawer-close").addEventListener("click",()=>$("drawer-backdrop").classList.add("hidden"));
  $("drawer-backdrop").addEventListener("click",e=>{if(e.target===$("drawer-backdrop"))$("drawer-backdrop").classList.add("hidden");});
  const saved=sessionStorage.getItem("spendlens-key");if(saved){$("api-key").value=saved;connect();}
})();
