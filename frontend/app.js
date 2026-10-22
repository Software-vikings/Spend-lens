(() => {
  const $ = id => document.getElementById(id);
  const state = {key:"", findings:[], transactions:[], decisions:[], claims:[], policies:[], page:0, pageSize:25, total:0, findingPage:0, decisionPage:0, claimPage:0, queuePage:0, queueTotal:0, queueItems:[], findingTotal:0, decisionTotal:0, claimTotal:0, listPageSize:25, selected:null, overview:null, filters:{month:"",department:"",category:""}, filterOptions:null, currentSection:"overview"};
  const money = (n,currency="EUR") => {
    try{return new Intl.NumberFormat("en-IE",{style:"currency",currency,minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(n||0));}
    catch{return `${currency} ${Number(n||0).toFixed(2)}`;}
  };
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
      // Each chart keeps its own dimension available for selection. The other
      // active filters still apply, but a selected month must not erase other months.
      const trendQuery=new URLSearchParams(Object.entries(state.filters).filter(([k,v])=>k!=="month"&&v));
      const departmentQuery=new URLSearchParams(Object.entries(state.filters).filter(([k,v])=>k!=="department"&&v));
      const categoryQuery=new URLSearchParams(Object.entries(state.filters).filter(([k,v])=>k!=="category"&&v));
      const [summary,overview,trendData,departmentData,categoryData,findings,decisions,claims]=await Promise.all([
        api("/v1/summary"+suffix),api("/v1/analytics/overview"+suffix),
        api("/v1/analytics/overview"+(trendQuery.toString()?"?"+trendQuery:"")),
        api("/v1/analytics/overview"+(departmentQuery.toString()?"?"+departmentQuery:"")),
        api("/v1/analytics/overview"+(categoryQuery.toString()?"?"+categoryQuery:"")),
        api(`/v1/findings?limit=${state.listPageSize}&offset=${state.findingPage*state.listPageSize}${$("finding-status").value?"&status="+encodeURIComponent($("finding-status").value):""}`),api(`/v1/decisions?limit=${state.listPageSize}&offset=${state.decisionPage*state.listPageSize}`),api(`/v1/claims?limit=${state.listPageSize}&offset=${state.claimPage*state.listPageSize}${$("claim-status")?.value?"&status="+encodeURIComponent($("claim-status").value):""}`)
      ]);
      state.overview=overview;state.findings=findings.items||[];state.findingTotal=findings.total||0;state.decisions=decisions.items||[];state.decisionTotal=decisions.total||0;state.claims=claims.items||[];state.claimTotal=claims.total||0;
      $("decision-count").textContent=number(decisions.total||0);$("claim-count").textContent=number(claims.total||0);renderDecisions();renderClaims();updateListPagination();updateClaimPagination();
      $("total-spend").textContent=money(summary.total_spend);
      $("transaction-count").textContent=number(summary.transaction_count);
      const open=Object.entries(summary.findings_by_status||{}).filter(([k])=>["new","under_review"].includes(k)).reduce((a,[,v])=>a+v,0);
      $("open-findings").textContent=number(open);
      $("finding-types").textContent=number(Object.keys(summary.findings_by_type||{}).length);
      $("nav-count").textContent=number(state.findingTotal);
      renderTrend(trendData.monthly||[]);renderDepartments(departmentData.departments||[]);renderCategories(categoryData.categories||[]);renderLatest();
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
  const updateListPagination = () => {
    const findingStart=state.findingTotal?state.findingPage*state.listPageSize+1:0;
    const decisionStart=state.decisionTotal?state.decisionPage*state.listPageSize+1:0;
    $("finding-page-label").textContent=`Showing ${findingStart}–${Math.min((state.findingPage+1)*state.listPageSize,state.findingTotal)} of ${number(state.findingTotal)}`;
    $("decision-page-label").textContent=`Showing ${decisionStart}–${Math.min((state.decisionPage+1)*state.listPageSize,state.decisionTotal)} of ${number(state.decisionTotal)}`;
    $("finding-prev").disabled=state.findingPage===0;
    $("finding-next").disabled=(state.findingPage+1)*state.listPageSize>=state.findingTotal;
    $("decision-prev").disabled=state.decisionPage===0;
    $("decision-next").disabled=(state.decisionPage+1)*state.listPageSize>=state.decisionTotal;
  };
  const loadPolicies = async () => {
    const data=await api("/v1/policies");
    state.policies=data.items||[];
    $("policies-table").innerHTML=state.policies.map(p=>`<tr><td><strong>${esc(p.name)}</strong><div class="finding-meta">${esc(p.policy_id)}</div></td><td>${esc(p.version)}</td><td>${esc(new Date(p.created_at).toLocaleString())}</td><td>${esc(p.activated_at?new Date(p.activated_at).toLocaleString():"—")}</td><td><span class="status ${p.is_active?"confirmed":"new"}">${p.is_active?"ACTIVE":"INACTIVE"}</span></td><td><button class="secondary-btn small" data-policy-load="${esc(p.policy_id)}" data-policy-version="${esc(p.version)}">Load</button> ${p.is_active?"":`<button class="secondary-btn small" data-policy-activate="${esc(p.policy_id)}" data-policy-version="${esc(p.version)}">Activate</button>`}</td></tr>`).join("")||'<tr><td colspan="6" class="empty">No policy versions found</td></tr>';
  };
  const loadPolicyEditor = async (policyId,version) => {
    const policy=await api(`/v1/policies/${encodeURIComponent(policyId)}/${encodeURIComponent(version)}`);
    $("policy-editor").value=JSON.stringify(policy,null,2);
    $("policy-editor-status").textContent=`Loaded ${policyId} version ${version}. Change the version field before saving.`;
  };
  const updateClaimPagination = () => {
    const start=state.claimTotal?state.claimPage*state.listPageSize+1:0;
    $("claim-page-label").textContent=`Showing ${start}–${Math.min((state.claimPage+1)*state.listPageSize,state.claimTotal)} of ${number(state.claimTotal)}`;
    $("claim-prev").disabled=state.claimPage===0;
    $("claim-next").disabled=(state.claimPage+1)*state.listPageSize>=state.claimTotal;
  };
  const loadClaimPage = async () => {
    const qs=new URLSearchParams({limit:state.listPageSize,offset:state.claimPage*state.listPageSize});
    const status=$("claim-status").value;if(status)qs.set("status",status);
    const data=await api("/v1/claims?"+qs.toString());
    state.claims=data.items||[];state.claimTotal=data.total||0;
    $("claim-count").textContent=number(state.claimTotal);renderClaims();updateClaimPagination();
  };
  const renderClaims = () => {
    $("claims-table").innerHTML=state.claims.map(claim=>`<tr><td><strong>${esc(claim.claim_id)}</strong><div class="finding-meta">${esc(claim.latest_decision_id||"")}</div></td><td>${esc(claim.employee_id||"—")}</td><td>${esc(claim.merchant_name||"—")}</td><td>${esc(claim.department||"—")}</td><td>${money(claim.amount,claim.currency||"EUR")}</td><td><span class="decision-outcome ${esc((claim.current_status||"").toLowerCase())}">${esc((claim.current_status||"").replaceAll("_"," "))}</span></td><td>${esc(new Date(claim.updated_at).toLocaleString())}</td><td><button class="secondary-btn small" data-claim-id="${esc(claim.claim_id)}">Open →</button></td></tr>`).join("")||'<tr><td colspan="8" class="empty">No claims match this filter</td></tr>';
  };
  const openClaim = async id => {
    try{
      const claim=await api(`/v1/claims/${encodeURIComponent(id)}`);
      const assignable=["REVIEW","INSUFFICIENT_DATA"].includes(claim.current_status) && !["HUMAN_APPROVED","HUMAN_REJECTED"].includes(claim.resolution_status);
      const currentAssignment=claim.current_assignment;
      $("finding-detail").innerHTML=`<div class="eyebrow">EXPENSE CLAIM</div><h2>${esc(claim.merchant_name||"Claim")}</h2><div class="detail-type">${esc(claim.claim_id)}</div><div class="detail-amount">${money(claim.amount,claim.currency||"EUR")}</div><div class="detail-section"><h3>Current claim details</h3><div class="detail-grid">${Object.entries(claim.current_payload||{}).filter(([k])=>k!=="receipt").map(([k,v])=>`<div class="detail-field"><small>${esc(k.replaceAll("_"," "))}</small><b>${esc(typeof v==="object"?JSON.stringify(v):v)}</b></div>`).join("")}</div></div><div class="detail-section"><h3>Submission and decision history</h3>${claim.submissions.map(s=>`<div class="finding-line"><div><b>${esc(new Date(s.submitted_at).toLocaleString())}</b><div class="finding-meta">${esc(s.submission_id)}</div></div><button class="secondary-btn small" data-claim-decision="${esc(s.decision_id)}">Decision →</button></div>`).join("")}</div><div class="detail-section"><h3>Reviewer assignment &amp; SLA</h3><div class="finding-meta">${currentAssignment?"Current owner: "+esc(currentAssignment.assignee)+" · "+esc(currentAssignment.priority)+" · Due "+esc(new Date(currentAssignment.due_at).toLocaleString()):"Not currently assigned"}</div>${assignable?'<label for="claim-assignee">Assign to reviewer</label><input id="claim-assignee" maxlength="100" placeholder="Reviewer name"><label for="claim-assigned-by">Assigned by</label><input id="claim-assigned-by" maxlength="100" placeholder="Your name"><label for="claim-priority">Priority</label><select id="claim-priority"><option>NORMAL</option><option>LOW</option><option>HIGH</option><option>URGENT</option></select><label for="claim-sla-hours">SLA (hours)</label><input id="claim-sla-hours" type="number" min="1" max="720" value="24"><label for="claim-assignment-note">Assignment note (optional)</label><textarea id="claim-assignment-note" rows="2" maxlength="1000" placeholder="Handoff context"></textarea><button class="secondary-btn" id="claim-assignment-submit">'+(currentAssignment?'Reassign claim':'Assign claim')+'</button>':'<p class="field-note">Assignment is available only while this is an unresolved exception.</p>'}${(claim.assignment_history||[]).map(a=>'<div class="finding-line"><div><b>'+esc(a.assignee)+' · '+esc(a.priority)+'</b><div class="finding-meta">'+esc(a.assigned_by)+' · '+esc(new Date(a.created_at).toLocaleString())+' · '+esc(a.sla_hours)+'h SLA</div><div>'+esc(a.note||"No assignment note")+'</div></div></div>').join("")||'<p class="field-note">No assignment history recorded.</p>'}</div><div class="detail-section"><h3>Human exception resolution</h3><div class="finding-meta">Automated outcome: <b>${esc(claim.current_status)}</b> · Human status: <b>${esc(claim.resolution_status||"NOT REVIEWED")}</b></div>${["REVIEW","INSUFFICIENT_DATA"].includes(claim.current_status)?'<label for="claim-resolution-action">Analyst action</label><select id="claim-resolution-action"><option value="REQUEST_INFORMATION">Request information</option><option value="APPROVE">Approve exception</option><option value="REJECT">Reject claim</option></select><label for="claim-resolution-reviewer">Reviewer display name</label><input id="claim-resolution-reviewer" maxlength="100" placeholder="Your name"><label for="claim-resolution-reason">Reason (required)</label><textarea id="claim-resolution-reason" maxlength="2000" rows="3" placeholder="Explain the decision"></textarea><label for="claim-resolution-evidence">Evidence note (optional)</label><textarea id="claim-resolution-evidence" maxlength="4000" rows="2" placeholder="What was checked or requested"></textarea><button class="primary-btn" id="claim-resolution-submit">Record resolution</button>':'<p class="field-note">Human resolution is available only for REVIEW and INSUFFICIENT_DATA claims.</p>'}${(claim.resolution_history||[]).map(r=>'<div class="finding-line"><div><b>'+esc(r.action.replaceAll("_"," "))+' · '+esc(r.new_status)+'</b><div class="finding-meta">'+esc(r.reviewer)+' · '+esc(new Date(r.created_at).toLocaleString())+'</div><div>'+esc(r.reason)+'</div><div class="finding-meta">'+esc(r.evidence_note||"No evidence note")+'</div></div></div>').join("")||'<p class="field-note">No human resolution actions recorded.</p>'}</div><div class="detail-section"><h3>Receipt evidence metadata</h3>${claim.evidence.map(e=>`<div class="finding-line"><div><b>${esc(e.evidence_type)} · ${esc(e.evidence_status)}</b><div class="finding-meta">Reference: ${esc(e.evidence_ref||"Not supplied")} · Source: ${esc(e.source)}</div></div></div>`).join("")||'<div class="finding-meta">No receipt metadata recorded.</div>'}<p class="field-note">Metadata only. No receipt file is stored or verified.</p></div>`;
      $("drawer-backdrop").classList.remove("hidden");
      $("finding-detail").querySelectorAll("[data-claim-decision]").forEach(el=>el.addEventListener("click",async()=>{ $("drawer-backdrop").classList.add("hidden");await showDecision(el.dataset.claimDecision);showSection("decisions");}));
      const assignmentButton=$("claim-assignment-submit");
      if(assignmentButton)assignmentButton.addEventListener("click",async()=>{
        const payload={assignee:$("claim-assignee").value,assigned_by:$("claim-assigned-by").value,
          priority:$("claim-priority").value,sla_hours:Number($("claim-sla-hours").value),
          note:$("claim-assignment-note").value};
        try{await api("/v1/claims/"+encodeURIComponent(id)+"/assignment",{method:"POST",body:JSON.stringify(payload)});
          toast("Claim assignment saved.");await openClaim(id);await loadExceptionQueue();}
        catch(err){toast(err.message);}
      });
      const resolveButton=$("claim-resolution-submit");
      if(resolveButton)resolveButton.addEventListener("click",async()=>{
        const payload={action:$("claim-resolution-action").value,reviewer:$("claim-resolution-reviewer").value,
          reason:$("claim-resolution-reason").value,evidence_note:$("claim-resolution-evidence").value};
        try{await api("/v1/claims/"+encodeURIComponent(id)+"/resolution",{method:"POST",body:JSON.stringify(payload)});
          toast("Human resolution recorded.");await openClaim(id);await loadClaimPage();}
        catch(err){toast(err.message);}
      });
    }catch(e){toast(e.message);}
  };

  const renderExceptionQueue = () => {
    const rows=state.queueItems||[];
    const metrics=state.queueMetrics||{assigned:0,unassigned:0,overdue:0};
    $("queue-open-count").textContent=number(state.queueTotal);
    $("queue-assigned-count").textContent=number(metrics.assigned);
    $("queue-unassigned-count").textContent=number(metrics.unassigned);
    $("queue-overdue-count").textContent=number(metrics.overdue);
    $("queue-count").textContent=number(state.queueTotal);
    $("queue-table").innerHTML=rows.map(x=>{const due=x.due_at?new Date(x.due_at).toLocaleString():"Not assigned";return `<tr><td><strong>${esc(x.claim_id)}</strong><div class="finding-meta">${esc(x.employee_id||"")}</div></td><td>${esc(x.merchant_name||"—")}<div class="finding-meta">${esc(x.department||"—")}</div></td><td>${money(x.amount,x.currency||"EUR")}</td><td><span class="decision-outcome review">${esc((x.resolution_status||x.current_status).replaceAll("_"," "))}</span></td><td>${esc(x.assignee||"Unassigned")}</td><td><span class="priority-tag ${esc((x.priority||"UNASSIGNED").toLowerCase())}">${esc(x.priority||"UNASSIGNED")}</span></td><td><span class="${x.overdue?"sla-overdue":""}">${esc(due)}${x.overdue?" · OVERDUE":""}</span></td><td><button class="secondary-btn small" data-queue-claim="${esc(x.claim_id)}">Open →</button></td></tr>`;}).join("")||'<tr><td colspan="8" class="empty">No exceptions match these filters.</td></tr>';
    const start=state.queueTotal?state.queuePage*state.listPageSize+1:0;
    $("queue-page-label").textContent=`Showing ${start}–${Math.min((state.queuePage+1)*state.listPageSize,state.queueTotal)} of ${number(state.queueTotal)}`;
    $("queue-prev").disabled=state.queuePage===0;
    $("queue-next").disabled=(state.queuePage+1)*state.listPageSize>=state.queueTotal;
  };
  const loadExceptionQueue = async () => {
    const qs=new URLSearchParams({limit:state.listPageSize,offset:state.queuePage*state.listPageSize});
    const status=$("queue-status").value,assignee=$("queue-assignee").value.trim(),priority=$("queue-priority").value,overdue=$("queue-overdue").value;
    if(status)qs.set("status",status);if(assignee)qs.set("assignee",assignee);if(priority)qs.set("priority",priority);if(overdue!=="")qs.set("overdue",overdue);
    const data=await api("/v1/exception-queue?"+qs.toString());
    state.queueItems=data.items||[];state.queueTotal=data.total||0;state.queueMetrics=data.metrics||{assigned:0,unassigned:state.queueTotal,overdue:0};renderExceptionQueue();
  };
  const loadFindingPage = async () => {
    const status=$("finding-status").value;
    const qs=new URLSearchParams({limit:state.listPageSize,offset:state.findingPage*state.listPageSize});
    if(status)qs.set("status",status);
    const data=await api("/v1/findings?"+qs.toString());
    state.findings=data.items||[];state.findingTotal=data.total||0;renderFindings();updateListPagination();
  };
  const loadDecisionPage = async () => {
    const qs=new URLSearchParams({limit:state.listPageSize,offset:state.decisionPage*state.listPageSize});
    const data=await api("/v1/decisions?"+qs.toString());
    state.decisions=data.items||[];state.decisionTotal=data.total||0;
    $("decision-count").textContent=number(state.decisionTotal);renderDecisions();updateListPagination();
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
      const explanations={
        APPROVE:"Every applicable mandatory check passed under this policy version. This is a policy result, not proof that the underlying receipt is genuine.",
        REJECT:"At least one explicit hard-stop rule in the configured policy was violated. The failed rule is shown below.",
        REVIEW:"The claim has an exception or risk signal that the configured policy does not allow the system to resolve automatically.",
        INSUFFICIENT_DATA:"Required information or evidence is missing or invalid. The system cannot safely approve this claim."
      };
      $("decision-result").innerHTML=`<div class="decision-outcome large ${esc(d.outcome.toLowerCase())}">${esc(d.outcome.replaceAll("_"," "))}</div><h3>${esc(d.expense_id)}</h3><p class="decision-summary">${esc(explanations[d.outcome]||"Decision recorded.")}</p><div class="finding-meta">Policy ${esc(d.policy_id)} v${esc(d.policy_version)} · Engine v${esc(d.engine_version)} · ${esc(new Date(d.created_at).toLocaleString())}</div><div class="rule-results"><h4>Why the system reached this outcome</h4>${rules.map(r=>`<div class="rule-result"><div><b>${esc(r.label)}</b><span class="rule-status ${esc(r.status.toLowerCase())}">${esc(r.status.replaceAll("_"," "))}</span></div><p>${esc(r.explanation)}</p><small>${esc(r.rule_id)} · ${esc(JSON.stringify(r.evidence||{}))}</small></div>`).join("")}</div>`;
    } catch(e){toast(e.message);}
  };
  const renderTransactions = () => {
    const q=$("transaction-search").value.toLowerCase();
    const rows=state.transactions.filter(x=>[x.transaction_id,x.merchant_name,x.employee_id,x.department,x.category].join(" ").toLowerCase().includes(q));
    $("transactions-table").innerHTML=rows.map(x=>`<tr class="transaction-row" data-transaction-id="${esc(x.transaction_id)}" tabindex="0"><td>${esc(x.transaction_date)}</td><td><strong>${esc(x.merchant_name)}</strong><div class="finding-meta">${esc(x.merchant_id)}</div></td><td>${esc(x.department)}</td><td>${esc(x.category)}</td><td>${esc(x.employee_id)}</td><td class="right"><strong>${money(x.amount,x.currency)}</strong></td></tr>`).join("")||'<tr><td colspan="6" class="empty">No matching transactions</td></tr>';
    $("transactions-table").querySelectorAll("[data-transaction-id]").forEach(el=>{
      const open=()=>openTransaction(state.transactions.find(x=>x.transaction_id===el.dataset.transactionId));
      el.addEventListener("click",open);
      el.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();open();}});
    });
    $("transaction-page-label").textContent=`Showing ${state.total?state.page*state.pageSize+1:0}–${Math.min((state.page+1)*state.pageSize,state.total)} of ${number(state.total)}`;
    $("prev-page").disabled=state.page===0;$("next-page").disabled=(state.page+1)*state.pageSize>=state.total;
  };
  const openTransaction = async tx => {
    if(!tx)return;
    let context;
    try { context=await api(`/v1/transactions/${encodeURIComponent(tx.transaction_id)}`); }
    catch(e){toast(e.message);return;}
    const linked=context.related_findings||[];
    const fields=[
      ["Transaction reference",tx.transaction_id],["Date",tx.transaction_date],
      ["Merchant",tx.merchant_name],["Merchant reference",tx.merchant_id],
      ["Employee reference",tx.employee_id],["Department",tx.department],
      ["Category",tx.category],["Payment method",tx.payment_method],
      ["Currency",tx.currency]
    ];
    $("finding-detail").innerHTML=`<div class="eyebrow">LEDGER RECORD</div><h2>${esc(tx.merchant_name)}</h2><div class="detail-type">Transaction ${esc(tx.transaction_id)}</div><div class="detail-amount">${money(tx.amount,tx.currency)}</div><div class="detail-section"><h3>Transaction information</h3><div class="detail-grid">${fields.map(([k,v])=>`<div class="detail-field"><small>${esc(k)}</small><b>${esc(v??"Not recorded")}</b></div>`).join("")}</div></div><div class="detail-section"><h3>What this record means</h3><p class="decision-summary">This is a synthetic card/expense transaction record. It is not, by itself, an employee reimbursement claim and does not contain an attached receipt or approval decision.</p></div><div class="detail-section"><h3>Related findings <span class="subtle-tag">${linked.length}</span></h3>${linked.length?linked.map(f=>`<div class="finding-line"><div><div class="finding-title">${esc(f.title)}</div><div class="finding-meta">${esc(f.finding_type.replaceAll("_"," "))} · ${esc(f.finding_id.slice(0,12))}</div></div><div><span class="status ${esc(f.review_status)}">${esc(f.review_status.replaceAll("_"," "))}</span><div style="margin-top:6px"><button class="secondary-btn small" data-linked-finding="${esc(f.finding_id)}">Open finding →</button></div></div></div>`).join(""):'<div class="finding-meta">No findings are explicitly linked to this transaction.</div>'}<p class="field-note">Only exact transaction-ID relationships are shown. Similar amounts, merchants or dates are not treated as proof of a relationship.</p></div><div class="detail-section"><h3>Explore related spend</h3><button class="secondary-btn" id="transaction-context-filter">Filter dashboard to ${esc(tx.department)}</button></div>`;
    $("drawer-backdrop").classList.remove("hidden");
    $("finding-detail").querySelectorAll("[data-linked-finding]").forEach(el=>el.addEventListener("click",()=>openFinding(el.dataset.linkedFinding)));
    $("transaction-context-filter").addEventListener("click",()=>{ $("drawer-backdrop").classList.add("hidden");state.filters.department=tx.department;state.page=0;refreshAll().then(()=>showSection("overview"));});
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
    ["overview","findings","transactions","decisions","claims","queue","policies"].forEach(x=>$(x).classList.toggle("hidden",x!==id));
    document.querySelectorAll(".nav-item").forEach(a=>a.classList.toggle("active",a.getAttribute("href")==="#"+id));
    $("crumb-title").textContent=id[0].toUpperCase()+id.slice(1);
    if(id==="transactions")loadTransactions();
    if(id==="queue")loadExceptionQueue().catch(e=>toast(e.message));
    if(id==="policies")loadPolicies().catch(e=>toast(e.message));
  };
  document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener("click",e=>{
    const id=a.getAttribute("href").slice(1);
    if(["overview","findings","transactions","decisions","claims","policies"].includes(id)){e.preventDefault();showSection(id);}
  }));
  $("transaction-count-card").addEventListener("click",()=>showSection("transactions"));
  $("transaction-count-card").addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();showSection("transactions");}});
  $("view-filtered-transactions").addEventListener("click",()=>showSection("transactions"));
  $("clear-filters").addEventListener("click",async()=>{state.filters={month:"",department:"",category:""};state.page=0;await refreshAll();});
  $("decisions-table").addEventListener("click",e=>{const b=e.target.closest("[data-decision-id]");if(b)showDecision(b.dataset.decisionId);});
  $("claims-table").addEventListener("click",e=>{const b=e.target.closest("[data-claim-id]");if(b)openClaim(b.dataset.claimId);});
  $("queue-table").addEventListener("click",e=>{const b=e.target.closest("[data-queue-claim]");if(b)openClaim(b.dataset.queueClaim);});
  $("policies-refresh").addEventListener("click",()=>loadPolicies().catch(e=>toast(e.message)));
  $("policies-table").addEventListener("click",async e=>{
    const load=e.target.closest("[data-policy-load]");
    const activate=e.target.closest("[data-policy-activate]");
    try{
      if(load){const id=load.dataset.policyLoad,version=load.dataset.policyVersion;await loadPolicyEditor(id,version);}
      if(activate){const id=activate.dataset.policyActivate,version=activate.dataset.policyVersion;await api(`/v1/policies/${encodeURIComponent(id)}/${encodeURIComponent(version)}/activate`,{method:"POST"});toast("Policy version activated for future evaluations.");await loadPolicies();}
    }catch(err){toast(err.message);}
  });
  $("policy-save").addEventListener("click",async()=>{
    try{
      const policy=JSON.parse($("policy-editor").value);
      const result=await api("/v1/policies",{method:"POST",body:JSON.stringify(policy)});
      $("policy-editor-status").textContent=`Saved immutable version ${result.policy_id} ${result.version}. Activate it separately when authorised.`;
      toast("New policy version saved.");await loadPolicies();
    }catch(err){$("policy-editor-status").textContent=err.message;toast(err.message);}
  });

  $("claims-refresh").addEventListener("click",async()=>{try{state.claimPage=0;await loadClaimPage();}catch(e){toast(e.message);}});
  $("claim-status").addEventListener("change",async()=>{try{state.claimPage=0;await loadClaimPage();}catch(e){toast(e.message);}});
  $("claim-prev").addEventListener("click",async()=>{if(state.claimPage>0){state.claimPage--;try{await loadClaimPage();}catch(e){toast(e.message);}}});
  $("claim-next").addEventListener("click",async()=>{if((state.claimPage+1)*state.listPageSize<state.claimTotal){state.claimPage++;try{await loadClaimPage();}catch(e){toast(e.message);}}});

  $("decisions-refresh").addEventListener("click",async()=>{try{state.decisionPage=0;await loadDecisionPage();}catch(e){toast(e.message);}});
  let pendingIdempotencyKey=null;
  $("expense-evaluation-form").addEventListener("submit",async e=>{
    e.preventDefault();
    const form=new FormData(e.currentTarget);
    const amount=Number(form.get("amount"));
    const receiptStatus=String(form.get("receipt_status"));
    const receipt={provided:receiptStatus!=="missing",readable:receiptStatus==="provided",receipt_id:String(form.get("receipt_id")||"").trim()||null,total:String(form.get("receipt_total")||"").trim()||null};
    const expense={expense_id:String(form.get("expense_id")).trim(),employee_id:String(form.get("employee_id")).trim(),merchant_name:String(form.get("merchant_name")).trim(),department:String(form.get("department")).trim(),amount:amount,currency:form.get("currency"),category:form.get("category"),transaction_date:form.get("transaction_date"),business_purpose:String(form.get("business_purpose")).trim(),receipt,duplicate_suspected:form.get("duplicate_suspected")==="on"};
    try{
      pendingIdempotencyKey=pendingIdempotencyKey||crypto.randomUUID();
      const result=await api("/v1/expenses/evaluate",{method:"POST",headers:{"Idempotency-Key":pendingIdempotencyKey},body:JSON.stringify({expense})});
      $("decision-result").innerHTML='<div class="empty">Decision recorded. Loading rule-level explanation…</div>';
      state.decisionPage=0;await loadDecisionPage();
      await showDecision(result.decision_id);pendingIdempotencyKey=null;toast("Expense evaluated and decision saved.");
    }catch(err){toast(err.message==="Insufficient role"?"Expense evaluation requires an analyst API key. Reconnect with analyst access.":err.message);}
  });
  $("connect-btn").addEventListener("click",connect);
  $("expense-evaluation-form").addEventListener("input",e=>{if(e.target.matches("input,select,textarea"))e.target.classList.remove("field-invalid");});$("api-key").addEventListener("keydown",e=>{if(e.key==="Enter")connect();});
  $("refresh-btn").addEventListener("click",refreshAll);$("findings-refresh").addEventListener("click",refreshAll);$("transactions-refresh").addEventListener("click",()=>loadTransactions());
  $("finding-search").addEventListener("input",renderFindings);$("finding-status").addEventListener("change",()=>{state.findingPage=0;loadFindingPage().catch(e=>toast(e.message));});
  $("finding-prev").addEventListener("click",()=>{if(state.findingPage>0){state.findingPage--;loadFindingPage().catch(e=>toast(e.message));}});
  $("finding-next").addEventListener("click",()=>{if((state.findingPage+1)*state.listPageSize<state.findingTotal){state.findingPage++;loadFindingPage().catch(e=>toast(e.message));}});
  $("decision-prev").addEventListener("click",()=>{if(state.decisionPage>0){state.decisionPage--;loadDecisionPage().catch(e=>toast(e.message));}});
  $("decision-next").addEventListener("click",()=>{if((state.decisionPage+1)*state.listPageSize<state.decisionTotal){state.decisionPage++;loadDecisionPage().catch(e=>toast(e.message));}});
  let searchTimer=null;
  $("transaction-search").addEventListener("input",()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>{state.page=0;loadTransactions();},250);});
  $("transaction-month").addEventListener("change",()=>setFilter("month",$("transaction-month").value||state.filters.month));
  $("transaction-department").addEventListener("change",()=>setFilter("department",$("transaction-department").value||state.filters.department));
  $("transaction-category").addEventListener("change",()=>setFilter("category",$("transaction-category").value||state.filters.category));
  $("prev-page").addEventListener("click",()=>{if(state.page>0){state.page--;loadTransactions();}});
  $("next-page").addEventListener("click",()=>{if((state.page+1)*state.pageSize<state.total){state.page++;loadTransactions();}});

  $("queue-refresh").addEventListener("click",()=>loadExceptionQueue().catch(e=>toast(e.message)));
  ["queue-status","queue-priority","queue-overdue"].forEach(id=>$(id).addEventListener("change",()=>{state.queuePage=0;loadExceptionQueue().catch(e=>toast(e.message));}));
  let queueSearchTimer=null;
  $("queue-assignee").addEventListener("input",()=>{clearTimeout(queueSearchTimer);queueSearchTimer=setTimeout(()=>{state.queuePage=0;loadExceptionQueue().catch(e=>toast(e.message));},300);});
  $("queue-prev").addEventListener("click",()=>{if(state.queuePage>0){state.queuePage--;loadExceptionQueue().catch(e=>toast(e.message));}});
  $("queue-next").addEventListener("click",()=>{if((state.queuePage+1)*state.listPageSize<state.queueTotal){state.queuePage++;loadExceptionQueue().catch(e=>toast(e.message));}});
  $("drawer-close").addEventListener("click",()=>$("drawer-backdrop").classList.add("hidden"));
  $("drawer-backdrop").addEventListener("click",e=>{if(e.target===$("drawer-backdrop"))$("drawer-backdrop").classList.add("hidden");});
  const saved=sessionStorage.getItem("spendlens-key");if(saved){$("api-key").value=saved;connect();}
})();
