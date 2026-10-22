(() => {
  const $ = id => document.getElementById(id);
  const state = {key:"", findings:[], transactions:[], decisions:[], page:0, pageSize:25, total:0, selected:null, overview:null, filters:{month:"",department:"",category:""}, filterOptions:null, currentSection:"overview"};
  const money = n => new Intl.NumberFormat("en-IE",{style:"currency",currency:"EUR",maximumFractionDigits:0}).format(Number(n||0));
  const number = n => new Intl.NumberFormat("en-US").format(Number(n||0));
  const esc = v => String(v ?? "").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const filterQuery = () => {
    const qs = new URLSearchParams();
    Object.entries(state.filters).forEach(([key,value])=>{if(value)qs.set(key,value);});
    return qs.toString();
  };
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
  const loadFilterOptions = async () => {
    if(state.filterOptions)return;
    const base=await api("/v1/analytics/overview");
    state.filterOptions={
      months:(base.monthly||[]).map(x=>x.month),
      departments:(base.departments||[]).map(x=>x.department),
      categories:(base.categories||[]).map(x=>x.category)
    };
    $("transaction-month").innerHTML='<option value="">All months</option>'+state.filterOptions.months.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join("");
    $("transaction-department").innerHTML='<option value="">All departments</option>'+state.filterOptions.departments.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join("");
    $("transaction-category").innerHTML='<option value="">All categories</option>'+state.filterOptions.categories.map(x=>`<option value="${esc(x)}">${esc(x)}</option>`).join("");
  };
  const renderFilterState = () => {
    const labels=[];
    if(state.filters.month)labels.push(`Month: ${state.filters.month}`);
    if(state.filters.department)labels.push(`Department: ${state.filters.department}`);
    if(state.filters.category)labels.push(`Category: ${state.filters.category}`);
    $("filter-summary").textContent=labels.length?`Filtered by ${labels.join(" · ")} · Findings remain workspace-wide`:"Showing all available transaction data";
    $("clear-filters").disabled=!labels.length;
    $("transaction-month").value=state.filters.month;
    $("transaction-department").value=state.filters.department;
    $("transaction-category").value=state.filters.category;
  };
  const setFilter = async (type,value) => {
    if(!(type in state.filters))return;
    state.filters[type]=state.filters[type]===value?"":value;
    state.page=0;
    await refreshAll();
  };
  const refreshAll = async () => {
    try {
      await loadFilterOptions();
      const qs=filterQuery();
      const suffix=qs?`?${qs}`:"";
      const [summary,overview,findings,decisions]=await Promise.all([api("/v1/summary"+suffix),api("/v1/analytics/overview"+suffix),api("/v1/findings?limit=100"),api("/v1/decisions?limit=100")]);
      state.overview=overview;state.findings=findings.items||[];state.decisions=decisions.items||[];
      $("decision-count").textContent=number(decisions.total||0);renderDecisions();
      $("total-spend").textContent=money(summary.total_spend);
      $("transaction-count").textContent=number(summary.transaction_count);
      const open=Object.entries(summary.findings_by_status||{}).filter(([k])=>["new","under_review"].includes(k)).reduce((a,[,v])=>a+v,0);
      $("open-findings").textContent=number(open);
      $("finding-types").textContent=number(Object.keys(summary.findings_by_type||{}).length);
      $("nav-count").textContent=number(state.findings.length);
      renderTrend(overview.monthly||[]);renderDepartments(overview.departments||[]);renderCategories(overview.categories||[]);renderLatest();
      renderFindings();renderFilterState();await loadTransactions();
    } catch(e){toast(e.message);if(/key|auth|credential/i.test(e.message)){ $("connect-overlay").classList.remove("hidden");$("connection-label").textContent="Disconnected";$("connection-dot").classList.add("red");}}
  };
  const renderTrend = rows => {
    if(!rows.length){$("trend-chart").innerHTML='<div class="empty">No monthly data available</div>';return;}
    const max=Math.max(...rows.map(x=>x.spend),1);
    $("trend-chart").innerHTML=rows.map(x=>`<button type="button" class="trend-col chart-select ${state.filters.month===x.month?"selected":""}" data-filter-type="month" data-filter-value="${esc(x.month)}" aria-pressed="${state.filters.month===x.month}"><span class="trend-bar-wrap"><span class="trend-bar" style="height:${Math.max(3,x.spend/max*100)}%"><span>${money(x.spend)}</span></span></span><small>${esc(x.month)}</small></button>`).join("");
  };
  const renderDepartments = rows => {
    const max=Math.max(...rows.map(x=>x.spend),1);
    $("department-chart").innerHTML=rows.map(x=>`<button type="button" class="bar-row chart-select ${state.filters.department===x.department?"selected":""}" data-filter-type="department" data-filter-value="${esc(x.department)}" aria-pressed="${state.filters.department===x.department}"><span class="bar-label" title="${esc(x.department)}">${esc(x.department)}</span><span class="bar-track"><span class="bar-fill" style="width:${x.spend/max*100}%"></span></span><b>${money(x.spend)}</b></button>`).join("")||'<div class="empty">No department data</div>';
  };
  const renderCategories = rows => $("category-list").innerHTML=rows.map(x=>`<button type="button" class="category-item chart-select ${state.filters.category===x.category?"selected":""}" data-filter-type="category" data-filter-value="${esc(x.category)}" aria-pressed="${state.filters.category===x.category}"><span>${esc(x.category)}</span><b>${money(x.spend)}</b></button>`).join("")||'<div class="empty">No category data</div>';
  ["trend-chart","department-chart","category-list"].forEach(id=>$(id).addEventListener("click",e=>{
    const target=e.target.closest("[data-filter-type]");
    if(target)setFilter(target.dataset.filterType,target.dataset.filterValue);
  }));
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
    const qs=new URLSearchParams({limit:state.pageSize,offset:state.page*state.pageSize});
    Object.entries(state.filters).forEach(([key,value])=>{if(value)qs.set(key,value);});
    const search=$("transaction-search").value.trim();if(search)qs.set("q",search);
    const data=await api("/v1/transactions?"+qs.toString());state.transactions=data.items||[];state.total=data.total||0;
    renderTransactions();
  };
  const renderDecisions = () => {
    $("decisions-table").innerHTML=state.decisions.map(d=>`<tr><td><strong>${esc(d.expense_id)}</strong><div class="finding-meta">${esc(d.decision_id.slice(0,12))}</div></td><td><span class="decision-outcome ${esc(d.outcome.toLowerCase())}">${esc(d.outcome.replaceAll("_"," "))}</span></td><td>${esc(d.policy_id)} · ${esc(d.policy_version)}</td><td>${esc(new Date(d.created_at).toLocaleString())}</td><td><button class="secondary-btn small" data-decision-id="${esc(d.decision_id)}">Details →</button></td></tr>`).join("")||'<tr><td colspan="5" class="empty">No decisions have been evaluated yet</td></tr>';
  };
  const showDecision = async id => {
    try {
      const d=await api(`/v1/decisions/${encodeURIComponent(id)}`);
      const rules=d.evaluation.evaluated_rules||[];
      $("decision-result").innerHTML=`<div class="decision-outcome large ${esc(d.outcome.toLowerCase())}">${esc(d.outcome.replaceAll("_"," "))}</div><h3>${esc(d.expense_id)}</h3><p>${esc(d.evaluation.decision_explanation)}</p><div class="finding-meta">Policy ${esc(d.policy_id)} v${esc(d.policy_version)} · Engine v${esc(d.engine_version)}</div><div class="rule-results">${rules.map(r=>`<div class="rule-result"><div><b>${esc(r.label)}</b><span class="rule-status ${esc(r.status.toLowerCase())}">${esc(r.status)}</span></div><p>${esc(r.explanation)}</p><small>${esc(r.rule_id)} · ${esc(JSON.stringify(r.evidence||{}))}</small></div>`).join("")}</div>`;
    } catch(e){toast(e.message);}
  };
  const renderTransactions = () => {
    const q=$("transaction-search").value.toLowerCase();
    const rows=state.transactions.filter(x=>[x.transaction_id,x.merchant_name,x.employee_id,x.department,x.category].join(" ").toLowerCase().includes(q));
    $("transactions-table").innerHTML=rows.map(x=>`<tr class="transaction-row" data-transaction-id="${esc(x.transaction_id)}" tabindex="0"><td>${esc(x.transaction_date)}</td><td><strong>${esc(x.merchant_name)}</strong><div class="finding-meta">${esc(x.merchant_id)}</div></td><td>${esc(x.department)}</td><td>${esc(x.category)}</td><td>${esc(x.employee_id)}</td><td class="right"><strong>${money(x.amount)}</strong></td></tr>`).join("")||'<tr><td colspan="6" class="empty">No matching transactions</td></tr>';
    $("transactions-table").querySelectorAll("[data-transaction-id]").forEach(el=>el.addEventListener("click",()=>openTransaction(state.transactions.find(x=>x.transaction_id===el.dataset.transactionId))));
    $("transaction-page-label").textContent=`Showing ${state.total?state.page*state.pageSize+1:0}–${Math.min((state.page+1)*state.pageSize,state.total)} of ${number(state.total)}`;
    $("prev-page").disabled=state.page===0;$("next-page").disabled=(state.page+1)*state.pageSize>=state.total;
  };
  const openTransaction = tx => {
    if(!tx)return;
    $("finding-detail").innerHTML=`<div class="eyebrow">TRANSACTION DETAIL</div><h2>${esc(tx.merchant_name)}</h2><div class="detail-type">${esc(tx.transaction_id)} · ${esc(tx.transaction_date)}</div><div class="detail-amount">${money(tx.amount)}</div><div class="detail-section"><h3>Transaction context</h3><div class="detail-grid">${Object.entries(tx).map(([k,v])=>`<div class="detail-field"><small>${esc(k.replaceAll("_"," "))}</small><b>${esc(v)}</b></div>`).join("")}</div></div><button class="secondary-btn" id="transaction-context-filter">Filter dashboard to this department</button>`;
    $("drawer-backdrop").classList.remove("hidden");
    $("transaction-context-filter").addEventListener("click",()=>{ $("drawer-backdrop").classList.add("hidden");setFilter("department",tx.department);showSection("overview");});
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
    state.currentSection=id;
    ["overview","findings","transactions","decisions"].forEach(x=>$(x).classList.toggle("hidden",x!==id));
    document.querySelectorAll(".nav-item").forEach(a=>a.classList.toggle("active",a.getAttribute("href")==="#"+id));
    $("crumb-title").textContent=id[0].toUpperCase()+id.slice(1);
    if(id==="transactions")loadTransactions();
  };
  document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener("click",e=>{
    const id=a.getAttribute("href").slice(1);
    if(["overview","findings","transactions","decisions"].includes(id)){e.preventDefault();showSection(id);}
  }));
  $("transaction-count-card").addEventListener("click",()=>showSection("transactions"));
  $("transaction-count-card").addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();showSection("transactions");}});
  $("view-filtered-transactions").addEventListener("click",()=>showSection("transactions"));
  $("clear-filters").addEventListener("click",async()=>{state.filters={month:"",department:"",category:""};state.page=0;await refreshAll();});
  $("decisions-table").addEventListener("click",e=>{const b=e.target.closest("[data-decision-id]");if(b)showDecision(b.dataset.decisionId);});
  $("decisions-refresh").addEventListener("click",async()=>{try{const d=await api("/v1/decisions?limit=100");state.decisions=d.items||[];renderDecisions();$("decision-count").textContent=number(d.total||0);}catch(e){toast(e.message);}});
  $("expense-evaluation-form").addEventListener("submit",async e=>{
    e.preventDefault();
    const form=new FormData(e.currentTarget);
    const amount=Number(form.get("amount"));
    const receiptProvided=form.get("receipt_provided")==="on";
    const expense={expense_id:String(form.get("expense_id")).trim(),amount:amount,currency:"EUR",category:form.get("category"),transaction_date:form.get("transaction_date"),business_purpose:String(form.get("business_purpose")).trim(),receipt:receiptProvided?{provided:true,readable:true,total:String(form.get("receipt_total")||"")}:{provided:false},duplicate_suspected:false};
    try{
      const result=await api("/v1/expenses/evaluate",{method:"POST",body:JSON.stringify({expense})});
      $("decision-result").innerHTML='<div class="empty">Evaluation saved. Loading rule-level explanation…</div>';
      const list=await api("/v1/decisions?limit=100");state.decisions=list.items||[];renderDecisions();$("decision-count").textContent=number(list.total||0);
      await showDecision(result.decision_id);toast("Expense evaluated and decision saved.");
    }catch(err){toast(err.message);}
  });
  $("connect-btn").addEventListener("click",connect);$("api-key").addEventListener("keydown",e=>{if(e.key==="Enter")connect();});
  $("refresh-btn").addEventListener("click",refreshAll);$("findings-refresh").addEventListener("click",refreshAll);$("transactions-refresh").addEventListener("click",()=>loadTransactions());
  $("finding-search").addEventListener("input",renderFindings);$("finding-status").addEventListener("change",renderFindings);
  let searchTimer=null;
  $("transaction-search").addEventListener("input",()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{state.page=0;loadTransactions();},250);});
  $("transaction-month").addEventListener("change",()=>setFilter("month",$("transaction-month").value||state.filters.month));
  $("transaction-department").addEventListener("change",()=>setFilter("department",$("transaction-department").value||state.filters.department));
  $("transaction-category").addEventListener("change",()=>setFilter("category",$("transaction-category").value||state.filters.category));
  $("prev-page").addEventListener("click",()=>{if(state.page>0){state.page--;loadTransactions();}});
  $("next-page").addEventListener("click",()=>{if((state.page+1)*state.pageSize<state.total){state.page++;loadTransactions();}});
  $("drawer-close").addEventListener("click",()=>$("drawer-backdrop").classList.add("hidden"));
  $("drawer-backdrop").addEventListener("click",e=>{if(e.target===$("drawer-backdrop"))$("drawer-backdrop").classList.add("hidden");});
  const saved=sessionStorage.getItem("spendlens-key");if(saved){$("api-key").value=saved;connect();}
})();
