"""The single-file Studio UI. No build step, no CDN, no telemetry."""

STUDIO_HTML = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FORGE Studio</title>
<style>
:root{
  --bg:#070b14; --bg2:#0b1120; --panel:rgba(255,255,255,.045);
  --panel2:rgba(255,255,255,.07); --line:rgba(255,255,255,.09);
  --txt:#e8edf7; --mut:#8b97ad; --dim:#5d6a80;
  --cy:#22d3ee; --vi:#8b5cf6; --pk:#f472b6;
  --ok:#34d399; --warn:#fbbf24; --bad:#fb7185;
  --r:16px; --mono:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;
}
*{box-sizing:border-box}
html,body{height:100%}
body{
  margin:0;color:var(--txt);background:var(--bg);
  font:14px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  -webkit-font-smoothing:antialiased;overflow:hidden;
}
body::before{
  content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(900px 600px at 12% -10%,rgba(34,211,238,.16),transparent 60%),
    radial-gradient(800px 600px at 96% 8%,rgba(139,92,246,.16),transparent 60%),
    radial-gradient(700px 500px at 50% 110%,rgba(244,114,182,.08),transparent 60%);
}
body::after{
  content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.35;
  background-image:linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.025) 1px,transparent 1px);
  background-size:44px 44px;
  mask-image:radial-gradient(ellipse at 50% 0%,#000 30%,transparent 78%);
}
button,input,select,textarea{font:inherit;color:inherit}
button{cursor:pointer;border:0;background:none}
a{color:var(--cy);text-decoration:none}
a:hover{text-decoration:underline}
::selection{background:rgba(34,211,238,.28)}
::-webkit-scrollbar{width:10px;height:10px}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,.13);border-radius:9px;border:2px solid transparent;background-clip:content-box}
.app{position:relative;z-index:1;display:grid;grid-template-columns:290px minmax(0,1fr);height:100vh}

/* rail */
.rail{display:flex;flex-direction:column;min-height:0;padding:18px 14px 12px;
  background:linear-gradient(180deg,rgba(11,17,32,.82),rgba(7,11,20,.72));
  border-right:1px solid var(--line);backdrop-filter:blur(18px)}
.brand{display:flex;align-items:center;gap:11px;padding:2px 6px 18px}
.logo{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;
  font:800 17px/1 var(--mono);color:#04121a;
  background:linear-gradient(135deg,var(--cy),#a5f3fc 40%,var(--vi));
  box-shadow:0 0 26px rgba(34,211,238,.35);animation:pulse 4.5s ease-in-out infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 22px rgba(34,211,238,.3)}50%{box-shadow:0 0 38px rgba(139,92,246,.42)}}
.brand b{display:block;letter-spacing:.16em;font-size:14px}
.brand span{display:block;color:var(--mut);font:11px/1.4 var(--mono);letter-spacing:.2em;text-transform:uppercase}
.rail-head{display:flex;align-items:center;gap:8px;padding:0 8px 8px;
  color:var(--mut);font:11px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase}
.rail-head .n{margin-left:auto;padding:2px 7px;border-radius:20px;background:var(--panel2);color:var(--txt)}
.projects{flex:1;min-height:0;overflow:auto;display:flex;flex-direction:column;gap:5px;padding:2px}
.proj{width:100%;text-align:left;display:grid;grid-template-columns:26px minmax(0,1fr) auto;
  gap:9px;align-items:center;padding:9px 10px;border-radius:12px;border:1px solid transparent;
  transition:background .16s,border-color .16s,transform .16s}
.proj:hover{background:var(--panel);transform:translateX(2px)}
.proj.on{background:linear-gradient(90deg,rgba(34,211,238,.13),rgba(139,92,246,.09));border-color:rgba(34,211,238,.3)}
.proj .ico{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;
  font:600 11px/1 var(--mono);background:var(--panel2);color:var(--mut)}
.proj.on .ico{background:rgba(34,211,238,.17);color:var(--cy)}
.proj .nm{font-weight:600;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.proj .pt{color:var(--dim);font:10px/1.35 var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.proj .sc{font:600 11px/1 var(--mono);color:var(--mut);padding:3px 6px;border-radius:7px;background:var(--panel2)}
.proj .sc.good{color:var(--ok);background:rgba(52,211,153,.12)}
.proj .sc.mid{color:var(--warn);background:rgba(251,191,36,.12)}
.proj .sc.bad{color:var(--bad);background:rgba(251,113,133,.12)}
.add{display:grid;grid-template-columns:minmax(0,1fr) 34px;gap:7px;margin:10px 2px 0;
  padding-top:12px;border-top:1px solid var(--line)}
.add input{grid-column:1/-1;width:100%;padding:9px 11px;border-radius:10px;
  border:1px solid var(--line);background:rgba(0,0,0,.25);outline:none;font-size:12px}
.add input:focus{border-color:rgba(34,211,238,.55);box-shadow:0 0 0 3px rgba(34,211,238,.1)}
.add .row{grid-column:1/-1;display:grid;grid-template-columns:minmax(0,1fr) 34px;gap:7px}
.add .go{width:34px;height:34px;border-radius:10px;border:1px solid rgba(34,211,238,.4);
  background:rgba(34,211,238,.12);color:var(--cy);font-size:18px;line-height:1}
.add .go:hover{background:rgba(34,211,238,.2)}
.rail-foot{display:flex;align-items:center;gap:7px;padding:12px 9px 0;margin-top:8px;
  border-top:1px solid var(--line);color:var(--dim);font:10px/1.4 var(--mono)}
.rail-foot .dot{width:7px;height:7px;border-radius:50%;background:var(--ok);box-shadow:0 0 9px var(--ok)}
.rail-foot .p{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;direction:rtl;text-align:left}

/* main */
.main{min-width:0;min-height:0;display:flex;flex-direction:column;overflow:hidden}
.top{display:flex;align-items:flex-start;gap:22px;padding:24px 30px 18px}
.eyebrow{color:var(--cy);font:10px/1 var(--mono);letter-spacing:.24em;margin-bottom:8px}
h1{margin:0;font-size:clamp(22px,2.6vw,32px);line-height:1.12;letter-spacing:-.02em}
.path{margin-top:7px;color:var(--dim);font:11px/1.4 var(--mono);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:62vw}
.actions{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}
.btn{padding:9px 14px;border-radius:11px;border:1px solid var(--line);
  background:var(--panel);font-size:12.5px;font-weight:600;transition:.16s;white-space:nowrap}
.btn:hover{background:var(--panel2);border-color:rgba(255,255,255,.18)}
.btn:disabled{opacity:.42;cursor:not-allowed}
.btn.primary{background:linear-gradient(135deg,rgba(34,211,238,.95),rgba(139,92,246,.95));
  color:#06111f;border-color:transparent;box-shadow:0 8px 24px rgba(34,211,238,.18)}
.btn.primary:hover{filter:brightness(1.07)}
.btn.danger{color:var(--bad);border-color:rgba(251,113,133,.28)}
.btn.danger:hover{background:rgba(251,113,133,.1)}
.tabs{display:flex;gap:4px;padding:0 26px;border-bottom:1px solid var(--line);overflow-x:auto}
.tabs button{padding:11px 14px 13px;color:var(--mut);font-size:12.5px;font-weight:600;
  border-bottom:2px solid transparent;white-space:nowrap;transition:.16s}
.tabs button:hover{color:var(--txt)}
.tabs button.on{color:var(--txt);border-bottom-color:var(--cy)}
.content{flex:1;min-height:0;overflow:auto;padding:20px 26px 40px;scroll-behavior:smooth}
.grid{display:grid;gap:14px}
.g2{grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}
.g3{grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}
.g4{grid-template-columns:repeat(auto-fit,minmax(165px,1fr))}
.card{padding:16px 18px;border-radius:var(--r);background:linear-gradient(180deg,rgba(255,255,255,.055),rgba(255,255,255,.025));
  border:1px solid var(--line);box-shadow:0 16px 40px rgba(0,0,0,.18)}
.card h3{margin:0 0 12px;font-size:12px;letter-spacing:.13em;text-transform:uppercase;color:var(--mut);font-weight:700}
.card .big{font-size:30px;font-weight:750;letter-spacing:-.03em;line-height:1}
.card .sub{color:var(--dim);font:11px/1.5 var(--mono);margin-top:7px}
.kpi{position:relative;overflow:hidden}
.kpi::after{content:"";position:absolute;right:-24px;top:-24px;width:90px;height:90px;border-radius:50%;
  background:radial-gradient(circle,rgba(34,211,238,.14),transparent 70%)}
.kpi .big small{font-size:12px;color:var(--mut);font-weight:500;margin-left:3px}
.hero{display:grid;grid-template-columns:auto minmax(0,1fr);gap:22px;align-items:center;
  padding:20px 22px;border-radius:20px;border:1px solid var(--line);
  background:linear-gradient(120deg,rgba(34,211,238,.09),rgba(139,92,246,.07) 55%,rgba(255,255,255,.025))}
.ring{--p:0;position:relative;width:112px;height:112px;border-radius:50%;display:grid;place-items:center;
  background:conic-gradient(var(--cy) calc(var(--p)*1%),rgba(255,255,255,.08) 0);
  transition:background .6s}
.ring::before{content:"";position:absolute;inset:9px;border-radius:50%;background:var(--bg2)}
.ring .v{position:relative;font:750 30px/1 var(--mono);letter-spacing:-.04em}
.ring .v small{font-size:10px;color:var(--mut);margin-left:1px}
.ring .cap{position:absolute;bottom:20px;color:var(--dim);font:9px/1 var(--mono);letter-spacing:.14em}
.verdict{display:inline-flex;align-items:center;gap:7px;padding:5px 10px;border-radius:20px;
  font:600 11px/1 var(--mono);letter-spacing:.06em;text-transform:uppercase}
.v-good{background:rgba(52,211,153,.13);color:var(--ok);border:1px solid rgba(52,211,153,.28)}
.v-mid{background:rgba(251,191,36,.12);color:var(--warn);border:1px solid rgba(251,191,36,.3)}
.v-bad{background:rgba(251,113,133,.12);color:var(--bad);border:1px solid rgba(251,113,133,.3)}
.v-none{background:var(--panel2);color:var(--mut);border:1px solid var(--line)}
.hero h2{margin:0 0 6px;font-size:18px;letter-spacing:-.01em}
.hero .meta{color:var(--mut);font-size:12px;display:flex;gap:14px;flex-wrap:wrap;margin-top:10px}
.hero .meta b{color:var(--txt);font-weight:600}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{padding:4px 9px;border-radius:8px;background:var(--panel2);border:1px solid var(--line);
  font:10.5px/1.4 var(--mono);color:var(--mut)}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{text-align:left;padding:8px 10px;color:var(--dim);font:10px/1.4 var(--mono);
  letter-spacing:.12em;text-transform:uppercase;border-bottom:1px solid var(--line)}
td{padding:8px 10px;border-bottom:1px solid rgba(255,255,255,.05);vertical-align:top}
tr:last-child td{border-bottom:0}
.sev{font:700 10px/1 var(--mono);text-transform:uppercase;padding:4px 7px;border-radius:6px;white-space:nowrap}
.sev-high{background:rgba(251,113,133,.15);color:var(--bad)}
.sev-medium{background:rgba(251,191,36,.13);color:var(--warn)}
.sev-low{background:rgba(34,211,238,.12);color:var(--cy)}
.mono{font-family:var(--mono);font-size:11.5px}
.mut{color:var(--mut)}
.dim{color:var(--dim)}
.ok{color:var(--ok)} .bad{color:var(--bad)} .warn{color:var(--warn)}
.toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.toolbar .sp{margin-left:auto}
.spark{display:block;width:100%;height:78px}
.stages{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
.stage{padding:13px 14px;border-radius:13px;border:1px solid var(--line);background:var(--panel);
  position:relative;overflow:hidden;transition:.18s}
.stage:hover{transform:translateY(-2px);border-color:rgba(255,255,255,.16)}
.stage .st{display:flex;align-items:center;gap:7px;font:600 10.5px/1 var(--mono);letter-spacing:.08em;text-transform:uppercase}
.stage .st i{width:7px;height:7px;border-radius:50%;background:var(--dim);flex:0 0 auto}
.stage .nm{font-weight:650;margin:9px 0 3px;font-size:13px}
.stage .nt{color:var(--dim);font-size:11px;line-height:1.45}
.stage.s-PASS,.stage.s-SUCCESS{border-color:rgba(52,211,153,.3)}
.stage.s-PASS .st i,.stage.s-SUCCESS .st i{background:var(--ok);box-shadow:0 0 10px var(--ok)}
.stage.s-FAILED,.stage.s-ERROR{border-color:rgba(251,113,133,.34)}
.stage.s-FAILED .st i,.stage.s-ERROR .st i{background:var(--bad);box-shadow:0 0 10px var(--bad)}
.stage.s-SKIPPED .st i{background:var(--warn)}
.stage.s-RUNNING .st i{background:var(--cy);animation:blink 1s infinite}
.stage.s-RUNNING{border-color:rgba(34,211,238,.45)}
@keyframes blink{50%{opacity:.25}}
.stage .ms{position:absolute;right:12px;top:11px;color:var(--dim);font:10px/1 var(--mono)}
.btn-run{position:relative;overflow:hidden}
.btn-run.run::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.35),transparent);
  animation:sweep 1.1s infinite}
@keyframes sweep{from{transform:translateX(-100%)}to{transform:translateX(100%)}}
form.gen{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.field{display:flex;flex-direction:column;gap:6px}
.field label{color:var(--mut);font:10px/1 var(--mono);letter-spacing:.13em;text-transform:uppercase}
.field input,.field select,.field textarea{padding:10px 11px;border-radius:10px;border:1px solid var(--line);
  background:rgba(0,0,0,.24);outline:none;font-size:12.5px;min-width:0}
.field input:focus,.field select:focus,.field textarea:focus{border-color:rgba(34,211,238,.5);
  box-shadow:0 0 0 3px rgba(34,211,238,.09)}
.field .hint{color:var(--dim);font-size:10.5px}
.field.wide{grid-column:1/-1}
.hide{display:none!important}
.preview-frame{width:100%;height:520px;border:1px solid var(--line);border-radius:14px;background:#fff}
.result{padding:14px 16px;border-radius:13px;border:1px solid rgba(52,211,153,.3);
  background:linear-gradient(120deg,rgba(52,211,153,.09),rgba(34,211,238,.05));margin-top:14px}
.result h4{margin:0 0 8px;font-size:13px}
.empty{display:grid;place-items:center;height:60vh;text-align:center;gap:10px;color:var(--mut)}
.empty .orb{width:90px;height:90px;border-radius:50%;display:grid;place-items:center;font:700 30px/1 var(--mono);
  color:var(--cy);background:radial-gradient(circle at 35% 30%,rgba(34,211,238,.24),rgba(139,92,246,.08));
  border:1px solid rgba(34,211,238,.24);box-shadow:0 0 60px rgba(34,211,238,.14)}
.skeleton{height:96px;border-radius:var(--r);border:1px solid var(--line);position:relative;overflow:hidden;
  background:var(--panel)}
.skeleton::after{content:"";position:absolute;inset:0;transform:translateX(-100%);
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.07),transparent);animation:sh 1.2s infinite}
@keyframes sh{to{transform:translateX(100%)}}
.toast{position:fixed;right:22px;bottom:22px;z-index:50;padding:12px 16px;border-radius:12px;
  background:rgba(11,17,32,.96);border:1px solid rgba(52,211,153,.36);color:var(--txt);
  box-shadow:0 18px 50px rgba(0,0,0,.5);opacity:0;transform:translateY(12px);
  transition:.22s;pointer-events:none;max-width:420px;font-size:12.5px}
.toast.on{opacity:1;transform:none}
.toast.bad{border-color:rgba(251,113,133,.5)}
@media (max-width:900px){
  .app{grid-template-columns:1fr;grid-template-rows:auto minmax(0,1fr)}
  .rail{flex-direction:row;align-items:center;gap:10px;padding:10px 12px;border-right:0;border-bottom:1px solid var(--line)}
  .brand{padding:0}.brand div:last-child{display:none}
  .rail-head,.rail-foot{display:none}
  .projects{flex-direction:row;overflow-x:auto;overflow-y:hidden}
  .proj{min-width:170px}
  .add{margin:0;padding:0;border:0;grid-template-columns:minmax(0,150px) 34px}
  .add .row{grid-column:auto}
  .top{flex-direction:column;gap:12px;padding:16px 16px 12px}
  .actions{margin:0;justify-content:flex-start}
  .path{max-width:88vw}
  .content{padding:14px 14px 30px}
  .tabs{padding:0 10px}
}
@media (prefers-reduced-motion:reduce){
  *{animation:none!important;transition:none!important;scroll-behavior:auto!important}
}
</style>
</head>
<body>
<div class="app">
  <aside class="rail">
    <div class="brand">
      <div class="logo">F</div>
      <div><b>FORGE</b><span>Studio</span></div>
    </div>
    <div class="rail-head">Проекты <span class="n" id="count">0</span></div>
    <div class="projects" id="projects"></div>
    <form class="add" id="add">
      <input id="new-path" placeholder="D:\путь\к\проекту" autocomplete="off">
      <div class="row">
        <input id="new-name" placeholder="Имя (необязательно)" autocomplete="off">
        <button class="go" type="submit" title="Добавить">+</button>
      </div>
    </form>
    <div class="rail-foot"><span class="dot"></span><span class="p" id="forge-root">forge</span></div>
  </aside>
  <main class="main">
    <header class="top">
      <div style="min-width:0">
        <div class="eyebrow">ПРОЕКТ</div>
        <h1 id="title">Выберите проект</h1>
        <div class="path" id="path">Добавьте папку слева, чтобы начать</div>
      </div>
      <div class="actions">
        <button class="btn primary btn-run" id="run" disabled>▶ Пайплайн</button>
        <a class="btn" id="export" href="#" style="display:none">↓ HTML</a>
        <button class="btn danger" id="remove" disabled>Удалить</button>
      </div>
    </header>
    <nav class="tabs" id="tabs">
      <button data-tab="overview" class="on">Обзор</button>
      <button data-tab="pipeline">Пайплайн</button>
      <button data-tab="quality">Качество</button>
      <button data-tab="generate">Генератор</button>
      <button data-tab="reports">Отчёты</button>
    </nav>
    <section class="content" id="content"></section>
  </main>
</div>
<div class="toast" id="toast"></div>
<script>
'use strict';
const $ = s => document.querySelector(s);
const S = {studio:null, sel:'', report:null, tab:'overview', stages:[], history:[],
  lastRun:{}, lastDuration:0, running:false, loading:false, error:'',
  gen:{kind:'web', name:'Forge Site', preset:'aurora', lang:'ru', tagline:'', out:'', package:'com.forge.demo', command:'hello'},
  genResult:null};

const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmtMs = ms => ms == null ? '—' : (ms >= 1000 ? (ms/1000).toFixed(1) + ' с' : ms + ' мс');
const fmtScore = v => (v === null || v === undefined || v === '') ? '—' : v;
const clsScore = v => v == null ? '' : v >= 90 ? 'good' : v >= 70 ? 'mid' : 'bad';
const clsSev = s => s === 'high' ? 'sev sev-high' : s === 'medium' ? 'sev sev-medium' : 'sev sev-low';
const verdictCls = v => !v ? 'v-none' : /отлич|отлично|A\+|A\b|ready|clean|good/i.test(v) ? 'v-good'
  : /критич|bad|fail|D\b|F\b/i.test(v) ? 'v-bad' : 'v-mid';

function toast(msg, bad){
  const el = $('#toast');
  el.textContent = msg;
  el.classList.toggle('bad', !!bad);
  el.classList.add('on');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.remove('on'), 4200);
}
async function api(path, opts){
  const init = Object.assign({headers:{'Content-Type':'application/json'}}, opts || {});
  const r = await fetch(path, init);
  let d;
  try { d = await r.json(); } catch(e){ throw new Error('HTTP ' + r.status); }
  if(!r.ok || d.ok === false) throw new Error(d.error || ('HTTP ' + r.status));
  return d;
}
function item(){
  if(!S.studio || !S.sel) return null;
  return S.studio.projects.find(p => p.path === S.sel) || null;
}
function ring(score){
  const v = Math.max(0, Math.min(100, Number(score) || 0));
  return '<div class="ring" style="--p:' + v + '"><div class="v">' + v + '<small>/100</small></div><div class="cap">SCORE</div></div>';
}
function emptyBox(txt){
  return '<div class="empty"><div class="orb">F</div><div><b>Проект не выбран</b><div class="dim" style="margin-top:6px">' + esc(txt) + '</div></div></div>';
}
function skeleton(n){
  return '<div class="grid g3">' + Array.from({length:n||6}, () => '<div class="skeleton"></div>').join('') + '</div>';
}
function sparkline(vals){
  if(!vals || vals.length < 2) return '<div class="dim" style="padding:10px 0">История ещё копится — запустите пайплайн.</div>';
  const w = 640, h = 78, mn = Math.min.apply(null, vals);
  const mx = Math.max.apply(null, vals.concat([100]));
  const pts = vals.map((v,i) => [i/(vals.length-1)*w, h - (v-mn)/((mx-mn)||1)*(h-12) - 6]);
  const d = pts.map((p,i) => (i?'L':'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
  return '<svg class="spark" viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none">' +
    '<defs><linearGradient id="sg" x1="0" x2="1"><stop stop-color="#22d3ee"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs>' +
    '<path d="' + d + '" fill="none" stroke="url(#sg)" stroke-width="2.2"/></svg>';
}

function renderRail(){
  const box = $('#projects');
  const list = S.studio ? S.studio.projects : [];
  $('#count').textContent = list.length;
  $('#forge-root').textContent = S.studio ? S.studio.forge_root : 'forge';
  if(!list.length){
    box.innerHTML = '<div class="dim" style="padding:14px 8px;font-size:12px">Пока пусто. Добавьте папку проекта.</div>';
    return;
  }
  box.innerHTML = list.map(p => {
    const on = p.path === S.sel;
    const sc = p.score == null ? '<span class="sc">—</span>' :
      '<span class="sc ' + clsScore(p.score) + '">' + esc(p.score) + '</span>';
    const name = p.name || p.path.split(/[\\/]/).pop();
    return '<button class="proj' + (on?' on':'') + '" data-path="' + esc(p.path) + '">' +
      '<span class="ico">' + esc((name[0]||'?').toUpperCase()) + '</span>' +
      '<span style="min-width:0"><span class="nm">' + esc(name) + '</span>' +
      '<span class="pt">' + esc(p.path) + '</span></span>' + sc + '</button>';
  }).join('');
}

function renderTop(){
  const it = item();
  $('#title').textContent = it ? (it.name || it.path.split(/[\\/]/).pop()) : 'Выберите проект';
  $('#path').textContent = it ? it.path : 'Добавьте папку слева, чтобы начать';
  const run = $('#run');
  run.disabled = !it || S.running;
  run.textContent = S.running ? '● Идёт прогон…' : '▶ Пайплайн';
  run.classList.toggle('run', S.running);
  $('#remove').disabled = !it || S.running;
  const ex = $('#export');
  ex.style.display = it ? '' : 'none';
  if(it) ex.href = '/api/report/html?project=' + encodeURIComponent(it.path);
}

function render(){
  renderTop();
  const c = $('#content');
  if(!S.sel){ c.innerHTML = emptyBox('Добавьте существующую папку проекта через форму слева.'); return; }
  if(S.error){ c.innerHTML = '<div class="card"><h3>Ошибка</h3><div class="bad">' + esc(S.error) + '</div></div>'; return; }
  if(S.loading || !S.report){ c.innerHTML = skeleton(8); return; }
  const views = {overview:vOverview, pipeline:vPipeline, quality:vQuality, generate:vGenerate, reports:vReports};
  c.innerHTML = (views[S.tab] || vOverview)();
  if(S.tab === 'generate') syncGen();
}

function vOverview(){
  const D = S.report, sec = D.sections || {};
  const sc = D.score, vd = D.verdict || '';
  const sc2 = sec.secrets || {}, dp = sec.deps || {}, q = sec.quality || {}, ts = sec.tests || {};
  const stc = sec.structure || {};
  const trend = (D.quality || {}).trend || {};
  const pipe = D.pipe || [];
  const last = pipe.length ? pipe[pipe.length-1] : null;
  const findings = D.findings || [];
  return '' +
  '<div class="hero">' + ring(sc) +
    '<div><span class="verdict ' + verdictCls(vd) + '">' + esc(vd || 'без вердикта') + '</span>' +
      '<h2 style="margin-top:12px">' + esc(D.root || (item() && item().path) || '') + '</h2>' +
      '<div class="meta">' +
        '<span><b>' + fmtScore(D.files) + '</b> файлов</span>' +
        '<span><b>' + fmtScore(D.code_loc) + '</b> строк кода</span>' +
        '<span><b>' + (D.languages || []).length + '</b> языков</span>' +
        '<span>отчёт: <b>' + esc(D.generated_at || '—') + '</b></span>' +
      '</div>' +
      '<div class="chips" style="margin-top:12px">' + (D.languages || []).map(x => '<span class="chip">' + esc(x) + '</span>').join('') +
      (stc.build_system ? '<span class="chip">build: ' + esc(stc.build_system) + '</span>' : '') + '</div>' +
    '</div></div>' +
  '<div class="grid g4" style="margin-top:14px">' +
    '<div class="card kpi"><h3>Секреты</h3><div class="big ' + ((sc2.count||0)>0?'warn':'ok') + '">' + fmtScore(sc2.count) + '<small>находок</small></div><div class="sub">high: ' + ((sc2.by_severity||{}).high||0) + ' · medium: ' + ((sc2.by_severity||{}).medium||0) + '</div></div>' +
    '<div class="card kpi"><h3>Зависимости</h3><div class="big">' + fmtScore(dp.count) + '<small>пакетов</small></div><div class="sub">' + fmtScore(dp.findings) + ' замечаний</div></div>' +
    '<div class="card kpi"><h3>Качество кода</h3><div class="big">' + fmtScore(q.score) + '<small>/100</small></div><div class="sub">' + fmtScore(q.issues) + ' замечаний · тренд ' + esc(trend.direction || 'flat') + '</div></div>' +
    '<div class="card kpi"><h3>Тесты</h3><div class="big ' + (ts.ok ? 'ok' : 'mut') + '">' + (ts.ok ? 'OK' : (ts.ran ? 'FAIL' : '—')) + '</div><div class="sub">' + esc(ts.kind || 'не обнаружены') + '</div></div>' +
  '</div>' +
  '<div class="grid g2" style="margin-top:14px">' +
    '<div class="card"><h3>Главные находки</h3>' + findingsTable(findings) + '</div>' +
    '<div class="card"><h3>Последний прогон</h3>' + (last ?
      '<div class="big" style="font-size:20px">' + esc(last.status || '—') + '</div>' +
      '<div class="sub">' + esc(last.when || last.timestamp || '') + ' · ' + fmtMs(last.duration_ms) + '</div>' +
      '<div class="sub">этапов: ' + ((last.stages || []).length || '—') + '</div>'
      : '<div class="dim">Пайплайн ещё не запускался.</div>') +
      '<div class="sub" style="margin-top:14px">Окружение: <b>' + ((D.doctor || {}).available || 0) + '/' + ((D.doctor || {}).total || 0) + '</b> инструментов</div>' +
    '</div>' +
  '</div>';
}
function findingsTable(list){
  if(!list.length) return '<div class="ok" style="padding:8px 0">Чисто. Находок нет.</div>';
  return '<table><thead><tr><th>Важность</th><th>Область</th><th>Деталь</th></tr></thead><tbody>' +
    list.slice(0,30).map(f => '<tr><td><span class="' + clsSev(f.severity) + '">' + esc(f.severity) + '</span></td><td class="mono">' + esc(f.area) + '</td><td>' + esc(f.detail) + '</td></tr>').join('') +
    '</tbody></table>';
}

function vPipeline(){
  const last = S.lastRun || {};
  const cards = (S.stages || []).map(s => {
    const e = last[s.name];
    const st = e ? e.status : (S.running ? 'PENDING' : '—');
    const ms = e && e.duration_ms != null ? fmtMs(e.duration_ms) : '';
    const cls = st === 'PENDING' ? 's-RUNNING' : ('s-' + st);
    return '<div class="stage ' + cls + '"><div class="st"><i></i>' + esc(st) + '</div>' +
      '<div class="ms">' + esc(ms) + '</div><div class="nm">' + esc(s.title) + '</div>' +
      '<div class="nt">' + esc(s.notes || '') + ' · ' + esc(s.timeout_s) + 'с' + (s.heavy ? ' · тяжёлая' : '') + '</div></div>';
  }).join('');
  const hist = (S.history || []).slice(0, 12);
  return '<div class="toolbar"><div class="mut">Этапы конвейера</div>' +
    (S.lastDuration ? '<span class="chip">' + fmtMs(S.lastDuration) + '</span>' : '') +
    '<div class="sp"></div><button class="btn primary" id="run2"' + (S.running||!S.sel?' disabled':'') + '>' +
      (S.running ? '● Выполняется…' : '▶ Запустить') + '</button></div>' +
    (S.stages.length ? '<div class="stages">' + cards + '</div>' : skeleton(4)) +
    '<div class="card" style="margin-top:16px"><h3>История прогонов</h3>' +
      (hist.length ? '<table><thead><tr><th>Когда</th><th>Статус</th><th>Длительность</th><th>Этапы</th></tr></thead><tbody>' +
        hist.map(h => '<tr><td class="mono">' + esc(h.when || h.timestamp || h.at || '—') + '</td><td><span class="verdict ' + (h.status === 'SUCCESS' ? 'v-good' : 'v-bad') + '">' + esc(h.status || '—') + '</span></td><td class="mono">' + fmtMs(h.duration_ms) + '</td><td class="mut">' + esc((h.stages || []).length || '—') + '</td></tr>').join('') +
        '</tbody></table>' : '<div class="dim">Пока нет записей. Запустите пайплайн.</div>') +
    '</div>';
}

function vQuality(){
  const D = S.report, sec = D.sections || {};
  const q = sec.quality || {}, tr = (D.quality || {}).trend || {};
  const hist = (D.quality || {}).history || [];
  const kinds = q.top_kinds || {};
  const counts = D.counts || {};
  return '<div class="grid g3">' +
    '<div class="card"><h3>Оценка</h3><div class="big">' + fmtScore(q.score) + '<small>/100</small></div><div class="sub">' + fmtScore(q.issues) + ' замечаний</div></div>' +
    '<div class="card"><h3>Тренд</h3><div class="big" style="font-size:22px">' + esc(tr.direction || 'flat') + '</div><div class="sub">Δ ' + (tr.delta > 0 ? '+' : '') + fmtScore(tr.delta) + ' · замеров ' + fmtScore(tr.samples) + '</div></div>' +
    '<div class="card"><h3>Находки</h3><div class="big" style="font-size:22px"><span class="bad">' + (counts.high||0) + '</span> / <span class="warn">' + (counts.medium||0) + '</span> / <span class="ok">' + (counts.low||0) + '</span></div><div class="sub">high / medium / low</div></div>' +
  '</div>' +
  '<div class="grid g2" style="margin-top:14px">' +
    '<div class="card"><h3>Динамика оценки</h3>' + sparkline(hist.map(x => x.score || 0)) + '</div>' +
    '<div class="card"><h3>Частые замечания</h3>' + (Object.keys(kinds).length ?
      '<div class="chips">' + Object.entries(kinds).map(([k,v]) => '<span class="chip">' + esc(k) + ' × ' + esc(v) + '</span>').join('') + '</div>' :
      '<div class="dim">Нет данных.</div>') + '</div>' +
  '</div>' +
  '<div class="card" style="margin-top:14px"><h3>Все находки</h3>' + findingsTable(D.findings || []) + '</div>';
}

function vGenerate(){
  const caps = (S.studio && S.studio.capabilities) || {};
  const presets = caps.presets || ['aurora'];
  const g = S.gen;
  const res = S.genResult;
  const out = res ? ('<div class="result"><h4>Готово: ' + esc(res.kind) + '</h4>' +
    '<div class="mono dim" style="word-break:break-all">' + esc(res.out) + '</div>' +
    (res.kind === 'web' && res.result ?
      '<div style="margin-top:8px" class="mut">Оценка сайта: <b class="ok">' + esc(res.result.score) + '/100</b> · пресет ' + esc(res.result.preset_title || res.result.preset) + '</div>' +
      '<div class="chips" style="margin-top:10px"><a class="btn" target="_blank" rel="noopener" href="/preview?root=' + encodeURIComponent(res.out) + '&file=index.html">Открыть превью</a></div>' : '') +
    (res.result && res.result.files ? (function(){
      const fs = res.result.files;
      const arr = Array.isArray(fs) ? fs : Object.keys(fs || {});
      return '<div class="chips" style="margin-top:10px">' + arr.map(f => '<span class="chip">' + esc(f) + '</span>').join('') + '</div>';
    })() : '') +
    '</div>') : '';
  return '<div class="card"><h3>Генератор</h3>' +
    '<form class="gen" id="gen-form">' +
      '<div class="field"><label>Тип</label><select id="gen-kind"><option value="web"' + (g.kind==='web'?' selected':'') + '>Сайт (Web Studio)</option><option value="paper"' + (g.kind==='paper'?' selected':'') + '>Paper-плагин</option></select></div>' +
      '<div class="field"><label>Имя</label><input id="gen-name" value="' + esc(g.name) + '"></div>' +
      '<div class="field web-only"><label>Пресет</label><select id="gen-preset">' + presets.map(p => '<option value="' + esc(p) + '"' + (p===g.preset?' selected':'') + '>' + esc(p) + '</option>').join('') + '</select></div>' +
      '<div class="field web-only"><label>Язык</label><select id="gen-lang"><option value="ru"' + (g.lang==='ru'?' selected':'') + '>RU</option><option value="en"' + (g.lang==='en'?' selected':'') + '>EN</option></select></div>' +
      '<div class="field web-only wide"><label>Слоган</label><input id="gen-tagline" value="' + esc(g.tagline) + '" placeholder="Короткая фраза для hero-секции"></div>' +
      '<div class="field paper-only"><label>Package</label><input id="gen-package" value="' + esc(g.package) + '"></div>' +
      '<div class="field paper-only"><label>Команда</label><input id="gen-command" value="' + esc(g.command) + '"></div>' +
      '<div class="field wide"><label>Куда (пусто = автоматически)</label><input id="gen-out" value="' + esc(g.out) + '" placeholder="D:\проект\site"><div class="hint">Только внутри зарегистрированного проекта или studio-workspace.</div></div>' +
      '<div class="field wide" style="flex-direction:row;align-items:center;gap:12px"><button class="btn primary" type="submit" id="gen-go">Сгенерировать</button><span class="dim" id="gen-status"></span></div>' +
    '</form>' + out +
  '</div>';
}
function syncGen(){
  const kind = ($('#gen-kind') || {}).value || S.gen.kind;
  document.querySelectorAll('.web-only').forEach(el => el.classList.toggle('hide', kind !== 'web'));
  document.querySelectorAll('.paper-only').forEach(el => el.classList.toggle('hide', kind !== 'paper'));
}

function vReports(){
  const D = S.report, doc = D.doctor || {};
  const tools = doc.tools || [];
  return '<div class="grid g3">' +
    '<div class="card"><h3>Экспорт</h3><div class="chips" style="flex-direction:column;align-items:flex-start">' +
      '<a class="btn" href="/api/report/html?project=' + encodeURIComponent(S.sel) + '">↓ Скачать HTML-отчёт</a>' +
      '<a class="btn" target="_blank" rel="noopener" href="/api/report?project=' + encodeURIComponent(S.sel) + '&deep=1">Открыть JSON</a>' +
    '</div><div class="sub">Автономный HTML содержит все данные внутри.</div></div>' +
    '<div class="card"><h3>Окружение</h3><div class="big" style="font-size:22px">' + (doc.available || 0) + ' / ' + (doc.total || 0) + '</div><div class="sub">инструментов доступно</div></div>' +
    '<div class="card"><h3>Проект</h3><div class="mono dim" style="word-break:break-all">' + esc(S.sel) + '</div><div class="sub">отчёт: ' + esc(D.generated_at || '—') + '</div></div>' +
  '</div>' +
  '<div class="card" style="margin-top:14px"><h3>Инструменты</h3>' +
    (tools.length ? '<table><thead><tr><th>Инструмент</th><th>Доступен</th><th>Версия</th></tr></thead><tbody>' +
      tools.map(t => '<tr><td class="mono">' + esc(t.name) + '</td><td>' + (t.present ? '<span class="ok">да</span>' : '<span class="dim">нет</span>') + '</td><td class="dim mono">' + esc(t.version || '—') + '</td></tr>').join('') +
      '</tbody></table>' : '<div class="dim">Нет данных.</div>') +
  '</div>' +
  '<div class="card" style="margin-top:14px"><h3>Сырой отчёт</h3><details><summary class="mut">Показать JSON</summary>' +
    '<pre class="mono" style="white-space:pre-wrap;word-break:break-word;max-height:420px;overflow:auto">' + esc(JSON.stringify(D, null, 2)) + '</pre></details></div>';
}

async function loadStudio(){
  const d = await api('/api/studio');
  S.studio = d;
  if(!S.sel || !d.projects.some(p => p.path === S.sel)) S.sel = d.selected || (d.projects[0] && d.projects[0].path) || '';
  renderRail();
  renderTop();
}
async function loadReport(deep){
  if(!S.sel) return;
  S.loading = true; S.error = ''; render();
  try{
    const d = await api('/api/report?project=' + encodeURIComponent(S.sel) + (deep ? '&deep=1' : ''));
    S.report = d;
    await loadStudio();
  }catch(e){ S.error = e.message; }
  finally{ S.loading = false; render(); }
}
async function loadStages(){
  if(S.stages.length) return;
  try{ S.stages = (await api('/api/pipeline/stages')).stages || []; }catch(e){}
}
async function loadHistory(){
  if(!S.sel) return;
  try{ S.history = (await api('/api/pipeline/history?project=' + encodeURIComponent(S.sel))).history || []; }catch(e){ S.history = []; }
}
async function selectProject(path){
  if(S.running) return;
  try{ await api('/api/select', {method:'POST', body:JSON.stringify({path})}); }catch(e){ toast(e.message, true); return; }
  S.sel = path; S.report = null; S.lastRun = {}; S.lastDuration = 0; S.history = []; S.genResult = null;
  renderRail(); render();
  await loadReport();
}
async function runPipeline(){
  if(!S.sel || S.running) return;
  S.running = true; S.lastRun = {}; S.lastDuration = 0; render();
  toast('Пайплайн запущен…');
  try{
    const d = await api('/api/pipeline/run', {method:'POST', body:JSON.stringify({project:S.sel})});
    const rep = d.report || {};
    S.lastRun = {};
    (rep.stages || []).forEach(s => S.lastRun[s.name] = s);
    S.lastDuration = rep.duration_ms || 0;
    toast('Пайплайн: ' + (rep.status || '?') + ' за ' + fmtMs(S.lastDuration), rep.status !== 'SUCCESS');
    await loadHistory();
    S.running = false;
    await loadReport(true);
  }catch(e){
    S.running = false; toast(e.message, true); render();
  }
}

document.addEventListener('click', e => {
  const p = e.target.closest('.proj');
  if(p){ selectProject(p.dataset.path); return; }
  const tab = e.target.closest('#tabs button');
  if(tab){
    document.querySelectorAll('#tabs button').forEach(b => b.classList.toggle('on', b === tab));
    S.tab = tab.dataset.tab; render();
    if(S.tab === 'pipeline'){ Promise.all([loadStages(), loadHistory()]).then(render); }
    return;
  }
  if(e.target.closest('#run') || e.target.closest('#run2')) runPipeline();
});
document.addEventListener('change', e => {
  if(e.target.id === 'gen-kind'){ S.gen.kind = e.target.value; syncGen(); }
});
document.addEventListener('submit', async e => {
  if(e.target.id !== 'gen-form') return;
  e.preventDefault();
  const val = id => { const el = $('#' + id); return el ? el.value.trim() : ''; };
  const g = {kind: val('gen-kind') || 'web', name: val('gen-name') || 'Forge Site',
    preset: val('gen-preset') || 'aurora', lang: val('gen-lang') || 'ru',
    tagline: val('gen-tagline'), out: val('gen-out'),
    package: val('gen-package') || 'com.forge.demo', command: val('gen-command') || 'hello'};
  S.gen = g;
  const btn = $('#gen-go'); if(btn) btn.disabled = true;
  const st = $('#gen-status'); if(st) st.textContent = 'Генерирую…';
  try{
    const d = await api('/api/gen', {method:'POST', body:JSON.stringify(Object.assign({project:S.sel}, g))});
    S.genResult = d;
    toast('Сгенерировано: ' + d.out);
    render();
  }catch(err){ toast(err.message, true); if(st) st.textContent = err.message; if(btn) btn.disabled = false; }
});
$('#add').addEventListener('submit', async e => {
  e.preventDefault();
  const path = $('#new-path').value.trim();
  const name = $('#new-name').value.trim();
  if(!path){ toast('Укажите путь к папке проекта', true); return; }
  try{
    const d = await api('/api/projects', {method:'POST', body:JSON.stringify({path, name})});
    $('#new-path').value = ''; $('#new-name').value = '';
    S.sel = d.project.path; S.report = null; S.lastRun = {};
    await loadStudio(); render(); await loadReport();
    toast('Проект добавлен: ' + d.project.name);
  }catch(err){ toast(err.message, true); }
});
$('#remove').addEventListener('click', async () => {
  const it = item(); if(!it || S.running) return;
  if(!confirm('Убрать проект из Studio? Файлы на диске останутся.')) return;
  try{
    await api('/api/projects/remove', {method:'POST', body:JSON.stringify({path:it.path})});
    S.sel = ''; S.report = null; S.lastRun = {}; S.history = []; S.genResult = null;
    await loadStudio(); render(); if(S.sel) await loadReport();
    toast('Проект убран из списка');
  }catch(err){ toast(err.message, true); }
});
window.addEventListener('keydown', e => {
  if((e.ctrlKey || e.metaKey) && e.key === 'Enter'){ e.preventDefault(); runPipeline(); }
});

(async function boot(){
  render();
  try{
    await loadStudio();
    if(S.sel) await loadReport(); else render();
    if(S.studio) loadStages().then(render);
  }catch(e){
    S.error = e.message; render();
  }
})();
</script>
</body>
</html>
"""
