"use strict";
const main = document.querySelector("#main");
const dialog = document.querySelector("#dialog");
let workspace = null, signature = "", search = "", filter = "active", detailTab = "overview";
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const url = value => encodeURIComponent(value);
const date = value => new Date(value).toLocaleDateString(undefined, {month:"short", day:"numeric"});
const activityURL = (course, a) => `/activity/${url(course)}/${url(a.id)}/${url(a.version)}`;
const key = a => `${a.id}@${a.version}`;
const statusLabel = c => c.status !== "active" ? c.status[0].toUpperCase()+c.status.slice(1) : c.pending_count ? "Awaiting feedback" : c.confirmed ? "Learning in progress" : "Discovering your goal";

async function request(path, payload) {
  const response = await fetch(path, payload === undefined ? {} : {method:"POST",headers:{"Content-Type":"application/json","X-Harness-Token":workspace.token},body:JSON.stringify(payload)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "The workspace could not complete that request.");
  return result;
}
function toast(message) {
  const el = document.querySelector("#toast"); el.textContent = message; el.classList.add("visible");
  setTimeout(() => el.classList.remove("visible"), 3500);
}
function modal(content) { document.querySelector("#dialog-content").innerHTML = content; dialog.showModal(); }
document.querySelector(".dialog-close").onclick = () => dialog.close();
dialog.addEventListener("click", e => {if(e.target === dialog) {const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}});
async function copyText(value) {
  try {await navigator.clipboard.writeText(value); toast("Copied. Paste this into your agent conversation.");}
  catch {const el=document.querySelector("#handoff-text");if(el){el.focus();el.select();}toast("Select and copy the text to continue.");}
}
function handoff(course, concept) {
  const prompt = `Read the shared harness skills/learning-guide/SKILL.md. Use learn.py --courses ${JSON.stringify(workspace.courses_root)} resume ${course}. ${concept ? `I want to review ${concept}. Ask me to retrieve before showing the reference; inspect the exact evidence and adapt the support.` : "Continue my learning journey. Inspect pending submissions, due reviews and the checkpoint before choosing the next learning purpose."}`;
  modal(`<div class="eyebrow">CONTINUE THE CONVERSATION</div><h2 id="dialog-title">Pick up the thread.</h2><p>Your agent can recover the goal, exact work, feedback and next step from this course folder.</p><label class="label" for="handoff-text">Paste into your agent conversation</label><textarea class="field" id="handoff-text" rows="6">${esc(prompt)}</textarea><div class="dialog-actions"><button class="button" id="copy-handoff">Copy continuation prompt ↗</button></div>`);
  document.querySelector("#copy-handoff").onclick=()=>copyText(prompt);
}
function newJourney() {
  modal(`<div class="eyebrow">A NEW BEGINNING</div><h2 id="dialog-title">What would you like to learn?</h2><p>Save a starting point. Your agent will help clarify the goal, research material and build the journey with you.</p><form id="new-course"><label class="label" for="new-title">Journey name</label><input class="field" id="new-title" placeholder="English for academic writing" maxlength="300" required><label class="label" for="new-goal">What would you like to be able to do?</label><textarea class="field" id="new-goal" placeholder="Describe your goal in your own words…" required></textarea><label class="label" for="new-id">Folder name</label><input class="field" id="new-id" pattern="[a-z0-9][a-z0-9_-]{0,79}" placeholder="academic-writing" required><p class="field-hint">A folder inside your local courses directory. Starting knowledge stays unassessed.</p><p class="error" id="new-error" role="alert"></p><div class="dialog-actions"><button class="button" type="submit">Create journey <span>+</span></button></div></form>`);
  const title=document.querySelector("#new-title"),id=document.querySelector("#new-id");let edited=false;
  id.oninput=()=>edited=true;title.oninput=()=>{if(!edited)id.value=title.value.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,80);};
  document.querySelector("#new-course").onsubmit=async e=>{e.preventDefault();const button=e.target.querySelector("button");button.disabled=true;try {await request("/api/courses",{id:id.value,title:title.value,goal:document.querySelector("#new-goal").value});dialog.close();await refresh(true);handoff(id.value);}catch(error){document.querySelector("#new-error").textContent=error.message;}finally{button.disabled=false;}};
}
function progress(c) {
  const p=c.progress;
  if(!p.total)return `<div class="progress-label"><span>Scope is taking shape</span><b>Unassessed</b></div><div class="progress-track"></div><div class="progress-details">Your agent will build the capability map with you.</div>`;
  return `<div class="progress-label"><span>Independent evidence</span><b>${p.independent} <span>/ ${p.total} capabilities</span></b></div><div class="progress-track"><div class="progress-fill" style="width:${100*p.independent/p.total}%"></div></div><div class="progress-details">${p.practiced} practiced <span aria-hidden="true">·</span> ${p.delayed} checked after a delay <span aria-hidden="true">·</span> ${p.unassessed} unassessed</div>`;
}
function card(c,i) {
  const current=c.current_activity;
  return `<article class="course-card"><div class="card-top"><span class="course-symbol tone-${i%4}" aria-hidden="true">${["Aa","∿","⌘","◎"][i%4]}</span><span class="status ${c.pending_count?"pending":c.status!=="active"?"paused":""}">${esc(statusLabel(c))}</span></div><a href="/course/${url(c.id)}"><h3 class="course-title">${esc(c.title)}</h3></a><p class="course-goal">${esc(c.goal)}</p>${progress(c)}<div class="card-current"><span aria-hidden="true">↳</span><div><strong>${esc(current ? current.title : c.next_action)}</strong>${c.due_reviews.length?`<span class="due-label">${c.due_reviews.length} review${c.due_reviews.length===1?"":"s"} due</span>`:""}${c.fictional?'<span class="demo-label">FICTIONAL DEMO</span>':""}</div></div><div class="card-footer"><span class="card-date">Updated ${date(c.updated_at)}</span><a class="card-action" href="${current?activityURL(c.id,current):`/course/${url(c.id)}`}">${current?"Continue learning":"Open journey"} <span aria-hidden="true">↗</span></a></div></article>`;
}
function renderJourneys() {
  const courses=workspace.courses;
  const active=courses.filter(c=>c.status==="active"),due=courses.reduce((n,c)=>n+c.due_reviews.length,0),independent=courses.reduce((n,c)=>n+c.progress.independent,0);
  main.innerHTML=`<div class="eyebrow">MAKE ROOM FOR CURIOSITY</div><div class="page-heading"><div><h1>Your learning, in motion.</h1><p class="subtitle">A little practice, a new connection, a step further. Pick up where you left off.</p></div><button class="button" id="new-journey"><span aria-hidden="true">+</span> New journey</button></div>${workspace.errors.map(e=>`<div class="notice">Could not read ${esc(e.course)}: ${esc(e.error)}</div>`).join("")}<div class="metrics"><div class="metric"><span class="metric-icon" aria-hidden="true">▦</span><div><div class="metric-number">${active.length}<small>in progress</small></div><div class="metric-label">Active journeys</div></div></div><div class="metric"><span class="metric-icon" aria-hidden="true">↺</span><div><div class="metric-number">${due}<small>ready to revisit</small></div><div class="metric-label">Reviews due</div></div></div><div class="metric"><span class="metric-icon" aria-hidden="true">✧</span><div><div class="metric-number">${independent}<small>with evidence</small></div><div class="metric-label">Capabilities with independent evidence</div></div></div></div><div class="section-bar"><div class="section-title"><h2>Your journeys</h2><span class="count-label">${courses.length} total</span></div><div class="tools"><label class="sr-only" for="search">Search journeys</label><input class="search" id="search" type="search" placeholder="Search your journeys…" value="${esc(search)}"><label class="sr-only" for="filter">Journey status</label><select class="filter" id="filter"><option value="active">Active journeys</option><option value="all">All journeys</option><option value="paused">Paused</option><option value="archived">Archived</option></select></div></div><div id="course-list"></div>${due?`<a class="review-banner" href="/?view=reviews"><span class="review-banner-icon" aria-hidden="true">↺</span><div><h3>A good moment to reconnect.</h3><p>${due} topic${due===1?" is":"s are"} ready for a little retrieval practice. Try from memory before opening your notes.</p></div><span class="text-button">Visit review queue ↗</span></a>`:""}`;
  document.querySelector("#new-journey").onclick=newJourney;
  document.querySelector("#filter").value=filter;
  document.querySelector("#search").oninput=e=>{search=e.target.value;renderCards();};
  document.querySelector("#filter").onchange=e=>{filter=e.target.value;renderCards();};
  renderCards();
}
function renderCards() {
  const courses=workspace.courses.filter(c=>(filter==="all"||c.status===filter)&&`${c.title} ${c.goal}`.toLowerCase().includes(search.toLowerCase()));
  document.querySelector("#course-list").innerHTML=courses.length?`<div class="course-grid">${courses.map(card).join("")}</div>`:workspace.courses.length?`<div class="empty"><h2>No journeys in this view.</h2><p>Try another status or search term.</p></div>`:`<div class="empty"><div class="empty-symbol" aria-hidden="true">✳</div><h2>Every journey starts with a question.</h2><p>Create your first journey, or tell your agent what you want to learn. Your goals, work and next steps will find a home here.</p><button class="button" id="empty-create">Start a learning journey +</button></div>`;
  const button=document.querySelector("#empty-create");if(button)button.onclick=newJourney;
}
async function renderReviews() {
  const rows=[];
  for(const c of workspace.courses){for(const review of c.due_reviews)rows.push({c,review});}
  rows.sort((a,b)=>new Date(a.review.due_at)-new Date(b.review.due_at));
  main.innerHTML=`<div class="eyebrow">BRING IT BACK TO MIND</div><div class="page-heading"><div><h1>A little space. A stronger connection.</h1><p class="subtitle">Reconstruct an idea before reopening the explanation. Your agent will help with the next step.</p></div></div><div class="section-bar"><div class="section-title"><h2>Ready to revisit</h2><span class="count-label">${rows.length} topics</span></div></div>${rows.length?rows.map(({c,review},i)=>`<article class="review-row"><span class="course-symbol tone-${i%4}" aria-hidden="true">↺</span><div><h3>${esc(review.concept_title||review.concept_id)}</h3><p><a href="/course/${url(c.id)}">${esc(c.title)}</a> · Due ${date(review.due_at)}</p><p>${esc(review.prompt)}</p></div><button class="button secondary small" data-review="${esc(c.id)}" data-concept="${esc(review.concept_id)}">Review with agent ↗</button></article>`).join(""):`<div class="empty"><div class="empty-symbol">↺</div><h2>Room for something new.</h2><p>No reviews are due. Your saved review plans will appear here when it is time to retrieve.</p><a class="button secondary" href="/">Back to your journeys</a></div>`}`;
  main.querySelectorAll("[data-review]").forEach(b=>b.onclick=()=>handoff(b.dataset.review,b.dataset.concept));
}
async function renderCourse(id) {
  const data=await request(`/api/courses/${url(id)}`),c=data.summary;
  const activity=c.current_activity;
  main.innerHTML=`<div class="breadcrumb"><a href="/">Your journeys</a> <span aria-hidden="true"> / </span>${esc(c.title)}</div><div class="eyebrow">${esc(statusLabel(c))}${c.fictional?" · FICTIONAL DEMO":""}</div><div class="page-heading"><div><h1>${esc(c.title)}</h1><p class="subtitle">${esc(c.goal)}</p></div><button class="button" id="continue-chat">Continue with agent ↗</button></div><div class="tabs" role="tablist">${[["overview","Your next step"],["map","Capability map"],["evidence","Work & feedback"],["sources","Source material"]].map(([value,label])=>`<button role="tab" aria-selected="${value===detailTab}" class="${value===detailTab?"active":""}" data-tab="${value}">${label}</button>`).join("")}</div><div class="detail-layout"><div id="detail-content"></div><aside class="detail-aside"><section class="panel"><h2>A picture of progress</h2>${progress(c)}<p>These dimensions overlap. Evidence supports specific capabilities; opening lessons and running examples do not establish understanding.</p><div class="panel-label">CURRENT SCOPE</div><div class="panel-value">${c.progress.total} required capabilities · revision ${c.scope_version}</div></section><section class="panel"><div class="panel-label">CONTINUITY</div><p>Your goal, activities and evidence live in this journey’s folder.</p><button class="text-button" id="copy-resume">Copy continuation prompt ↗</button><div class="panel-label">JOURNEY STATUS</div><button class="text-button" id="pause-course">${c.status==="active"?"Pause this journey":"Resume this journey"}</button></section></aside></div>`;
  document.querySelector("#continue-chat").onclick=()=>handoff(id);
  document.querySelector("#copy-resume").onclick=()=>handoff(id);
  document.querySelector("#pause-course").onclick=async()=>{try{await request(`/api/courses/${url(id)}/status`,{status:c.status==="active"?"paused":"active",reason:"Learner changed the journey status in the dashboard"});await refresh(true);}catch(e){toast(e.message);}};
  main.querySelectorAll("[data-tab]").forEach(b=>b.onclick=()=>{detailTab=b.dataset.tab;renderCourse(id).catch(showError);});
  const target=document.querySelector("#detail-content");
  if(detailTab==="overview")target.innerHTML=`<section class="panel"><div class="eyebrow">THE NEXT USEFUL STEP</div><h2 style="margin-top:10px">${esc(activity?.title||c.next_action)}</h2><p>${esc(activity?.instruction||"Your journey starts in conversation. Ask your agent to clarify your goal, inspect suitable material and choose a useful starting point.")}</p>${activity?`<a class="button" href="${activityURL(id,activity)}">Open activity ↗</a>`:""}${data.plan?`<div class="panel-label">WHY THIS, NOW?</div><div class="panel-value">${esc(data.plan.why)}</div><div class="panel-label">SUPPORT AVAILABLE</div><div class="panel-value">${esc(data.plan.support)}</div><div class="panel-label">WHAT WOULD JUSTIFY LESS HELP?</div><div class="panel-value">${esc(data.plan.fade_check)}</div>`:""}</section>${c.pending_count?`<section class="panel"><h2>Your work is ready for feedback.</h2><p>${c.pending_count} saved submission${c.pending_count===1?"":"s"} waiting. Return to your agent conversation to inspect and discuss the exact work.</p><button class="button secondary" id="pending-chat">Copy feedback handoff ↗</button></section>`:""}${data.checkpoint?`<section class="panel"><h2>Where you left off</h2><p>${esc(data.checkpoint.summary)}</p><div class="panel-label">NEXT ACTION</div><div class="panel-value">${esc(data.checkpoint.next_action)}</div>${data.checkpoint.draft?`<blockquote class="path">${esc(data.checkpoint.draft)}</blockquote>`:""}</section>`:""}`;
  if(detailTab==="map")target.innerHTML=`<section class="panel"><h2>A growing map of understanding</h2><p>${esc(data.graph.rationale)} Required scope may change as your goal develops. Unassessed means there is no saved judgment.</p>${data.graph.nodes.length?data.graph.nodes.map(n=>{const l=data.learner[n.id]||{};return `<div class="capability"><span class="capability-icon">${l.independent?"✓":"·"}</span><div><h3>${esc(n.title)}</h3><p>${esc(n.target_capability)}</p><div class="tags">${[l.practiced?"Practiced":null,l.independent?"Independent evidence":null,l.supported?"With support":null,l.transfer?"Changed context":null,l.delayed?"Delayed recall":null,!l.last_evidence?"Unassessed":null,n.provisional?"Provisional mapping":null].filter(Boolean).map(t=>`<span class="tag ${t==="Unassessed"?"muted":""}">${esc(t)}</span>`).join("")}</div>${n.requires.length?`<p class="field-hint">Builds on: ${n.requires.map(esc).join(", ")}</p>`:""}</div></div>`;}).join(""):"<p>Your agent will build a provisional map as the goal and sources become clearer.</p>"}</section>`;
  if(detailTab==="evidence")target.innerHTML=`<section class="panel"><h2>Your work & feedback</h2>${data.pending.length?data.pending.map(s=>`<div class="evidence-item"><h3>Saved response · awaiting agent feedback</h3><small>${esc(s.activity)} · ${date(s.at)}</small><blockquote>${esc(s.answer)}</blockquote><small>Assistance: ${esc(s.assistance.join(", ")||"declared unassisted")}</small></div>`).join(""):""}${data.assessments.slice().reverse().map(a=>`<div class="evidence-item"><h3>Feedback · ${date(a.at)}</h3><p>${esc(a.feedback)}</p><small>${esc(a.limitations)}</small></div>`).join("")}${!data.pending.length&&!data.assessments.length?"<p>No submissions yet. Your actual responses and separately recorded judgments will appear here.</p>":""}</section><section class="panel"><h2>Activity library</h2>${data.activities.length?data.activities.slice().reverse().map(a=>`<div class="evidence-item"><h3><a href="${activityURL(id,a)}">${esc(a.title)} ↗</a></h3><small>${esc(a.surface)} · ${esc(a.purpose)} · ${esc(a.version)}</small><p>${esc(a.why)}</p></div>`).join(""):"<p>Activities will be created as they become useful.</p>"}</section>`;
  if(detailTab==="sources")target.innerHTML=`<section class="panel"><h2>Grounded in real material</h2><p>Your agent records what it inspected, why it matters and the limits of each source.</p>${data.resources.length?data.resources.map(r=>`<article class="source-card"><h3>${r.url.startsWith("http")?`<a href="${esc(r.url)}" target="_blank" rel="noreferrer">${esc(r.title)} ↗</a>`:esc(r.title)}</h3><p>${esc(r.why)}</p><p>${esc(r.inspection_notes)}</p><small>${esc(r.limitations||"")}</small></article>`).join(""):"<p>No inspected resources recorded yet. Research can grow alongside the learning journey.</p>"}</section>`;
  const pending=document.querySelector("#pending-chat");if(pending)pending.onclick=()=>handoff(id);
}
function showError(error) {main.innerHTML=`<div class="notice" role="alert">${esc(error.message)}</div><a class="button secondary" href="/">Back to workspace</a>`;}
async function refresh(force=false) {
  try {
    const next=await request("/api/workspace"); workspace=next;
    document.querySelector("#connection").textContent="Saved on this computer";
    const due=next.courses.reduce((n,c)=>n+c.due_reviews.length,0);document.querySelector("#review-count").textContent=due;
    const view=new URLSearchParams(location.search).get("view");
    document.querySelectorAll("[data-nav]").forEach(a=>a.classList.toggle("active",a.dataset.nav===(view==="reviews"?"reviews":"journeys")));
    const current=JSON.stringify(next.courses.map(c=>[c.id,c.revision,c.due_reviews.length]));
    if(!force&&(current===signature||dialog.open))return;
    signature=current;
    const parts=location.pathname.split("/").filter(Boolean);
    if(parts[0]==="course"&&parts[1])await renderCourse(decodeURIComponent(parts[1]));
    else if(view==="reviews")await renderReviews();else renderJourneys();
  } catch(error){document.querySelector("#connection").textContent="Connection unavailable";if(!workspace)showError(error);}
}
document.querySelector("#today").textContent=new Date().toLocaleDateString(undefined,{weekday:"short",month:"short",day:"numeric"});
document.querySelector("#workspace-info").onclick=()=>modal(`<div class="eyebrow">A THREAD BETWEEN SESSIONS</div><h2 id="dialog-title">Your learning has a home.</h2><p>This dashboard reads course-local records. Your agent provides teaching, research, diagnosis and feedback in conversation.</p><ul class="workspace-info-list"><li>Activities can use HTML, Markdown, notebooks, audio, video or other supported material.</li><li>Submitted work and assistance are preserved. Feedback is recorded separately.</li><li>Reviews are invitations to retrieve, not mastery badges.</li><li>Copy a continuation prompt to resume with a fresh agent session.</li></ul><p class="path">${esc(workspace?.courses_root||"")}</p>`);
refresh();setInterval(()=>{if(!document.hidden)refresh();},4000);
