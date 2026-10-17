"""FORGE serve: единый локальный дашборд + JSON API по проекту.

Только чтение, только stdlib (`http.server`), только localhost.
Один экран: здоровье (audit), тренд качества, зависимости, секреты,
история конвейера, доска арены, окружение.

Запуск: `forge serve [dir] [--port 8099] [--open] [--watch 30]`
API:    GET /api/report[?deep=1]  ·  GET /api/health
"""
from __future__ import annotations

import json
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from forge.kit.report import full_report

PAGE = """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FORGE Serve</title>
<style>
*{margin:0;box-sizing:border-box}
body{background:#0b0d14;color:#e2e8f0;font-family:system-ui,Segoe UI,sans-serif;padding:24px}
a{color:#22d3ee}
header{display:flex;flex-wrap:wrap;gap:16px;align-items:baseline;margin-bottom:18px}
h1{font-size:24px}h1 span{color:#22d3ee}
.path{opacity:.6;font-size:12px}
.scorebox{margin-left:auto;display:flex;gap:18px;align-items:center}
.big{font-size:34px;font-weight:800}
.tabs{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px}
.tab{padding:7px 13px;border-radius:8px;background:#ffffff10;cursor:pointer;font-size:13px;
     border:1px solid transparent;user-select:none}
.tab.on{background:#22d3ee22;border-color:#22d3ee66;color:#a5f3fc}
.card{background:#ffffff08;border:1px solid #ffffff10;border-radius:12px;padding:16px;
      margin-bottom:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.k{opacity:.55;font-size:12px}
.v{font-size:22px;font-weight:700}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;opacity:.5;font-weight:600;padding:6px 8px;border-bottom:1px solid #22d3ee33}
td{padding:6px 8px;border-bottom:1px solid #ffffff10}
.ok{color:#4ade80;font-weight:700}.bad{color:#f87171;font-weight:700}
.med{color:#fbbf24;font-weight:700}.low{opacity:.6}
.chip{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;
      background:#ffffff12;margin:2px}
.bar{height:8px;border-radius:4px;background:#ffffff14;overflow:hidden;min-width:60px}
.bar>i{display:block;height:100%;background:#22d3ee}
.off{opacity:.45}
footer{opacity:.4;font-size:11px;margin-top:20px}
label{font-size:12px;opacity:.7;cursor:pointer}
</style></head><body>
<header>
  <div><h1>FORGE <span>Serve</span></h1><div class="path" id="path"></div></div>
  <div class="scorebox">
    <div><div class="k">Здоровье</div><div class="big" id="score">--</div></div>
    <div><div class="k">Вердикт</div><div class="v" id="verdict">--</div></div>
    <label><input type="checkbox" id="auto" checked> авто-обновление</label>
  </div>
</header>
<div class="tabs" id="tabs"></div>
<div id="view"></div>
<footer id="foot"></footer>
<script>
const TABS=["Обзор","Качество","Зависимости","Секреты","Конвейер","Арена","Окружение"];
let DATA=null,CUR=0;
const $=id=>document.getElementById(id);
const esc=s=>String(s==null?"":s);
function sevClass(s){return s==="high"?"bad":s==="medium"?"med":"low";}
function card(html){return '<div class="card">'+html+'</div>';}
function kv(items){return '<div class="grid">'+items.map(x=>
  '<div><div class="k">'+x[0]+'</div><div class="v">'+esc(x[1])+'</div></div>').join("")+'</div>';}
function table(cols,rows){return '<table><tr>'+cols.map(c=>'<th>'+c+'</th>').join("")+
  '</tr>'+rows.join("")+'</table>';}
function tabs(){ $("tabs").innerHTML=TABS.map((t,i)=>
  '<div class="tab'+(i===CUR?' on':'')+'" onclick="pick('+i+')">'+t+'</div>').join(""); }
function pick(i){CUR=i;tabs();render();}
function render(){
  if(!DATA){$("view").innerHTML="<div class=card>нет данных</div>";return;}
  const a=DATA.audit||{},sec=DATA.sections||{};
  const views=[vOverview,vQuality,vDeps,vSecrets,vPipe,vArena,vEnv];
  $("view").innerHTML=views[CUR](a,sec,DATA);
}
function vOverview(a,sec,D){
  const mp=sec.map||{},c=a.counts||{};
  let h=card(kv([["Балл",(D.score??"--")+"/100"],["Файлов",mp.files],
    ["Строк кода",mp.code_loc],["Языки",(mp.languages||[]).join(", ")],
    ["Открытий high",c.high],["medium",c.medium],["low",c.low]]));
  h+=card("<div class=k>Главные открытия</div>"+table(["Важность","Область","Деталь"],
    (D.findings||[]).map(f=>'<tr><td class="'+sevClass(f.severity)+'">'+f.severity+
      '</td><td>'+esc(f.area)+'</td><td>'+esc(f.detail)+'</td></tr>').join("")||
      '<tr><td colspan=3 class=ok>чисто</td></tr>'));
  return h;
}
function vQuality(a,sec,D){
  const q=sec.quality||{},tr=(D.quality||{}).trend||{},hist=(D.quality||{}).history||[];
  let h=card(kv([["Оценка",(q.score??"--")+"/100"],["Замечаний",q.issues],
    ["Тренд",(tr.direction||"flat")+" ("+(tr.delta>0?"+":"")+(tr.delta??0)+")"],
    ["Замеров",tr.samples??0]]));
  const tk=q.top_kinds||{};
  h+=card("<div class=k>Частые замечания</div>"+Object.entries(tk).map(([k,v])=>
    '<div style="margin:6px 0"><span class=chip>'+esc(k)+" x"+v+'</span></div>').join("")
    ||"<div class=ok>нет</div>");
  h+=sparkline(hist.map(x=>x.score??0));
  return h;
}
function sparkline(vals){
  if(vals.length<2)return card("<div class=k>История качества ещё копится</div>");
  const w=520,hgt=90,mn=Math.min(...vals,100),mx=100;
  const pts=vals.map((v,i)=>[i/(vals.length-1)*w, hgt-(v-mn)/((mx-mn)||1)*(hgt-10)-5]);
  const d=pts.map((p,i)=>(i?"L":"M")+p[0].toFixed(1)+" "+p[1].toFixed(1)).join(" ");
  return card('<div class=k>Динамика оценки (последние '+vals.length+')</div>'+
    '<svg width="100%" viewBox="0 0 '+w+' '+hgt+'" preserveAspectRatio="none">'+
    '<path d="'+d+'" fill="none" stroke="#22d3ee" stroke-width="2"/></svg>');
}
function vDeps(a,sec,D){
  const dp=sec.deps||{};
  let h=card(kv([["Зависимостей",dp.count],["Замечаний",dp.findings],
    ["Экосистемы",Object.keys(dp.by_ecosystem||{}).join(", ")]]));
  h+=card("<div class=k>По экосистемам</div>"+Object.entries(dp.by_ecosystem||{}).map(
    ([k,v])=>'<span class=chip>'+esc(k)+": "+v+'</span>').join("")||"<div class=off>нет</div>");
  return h;
}
function vSecrets(a,sec,D){
  const sc=sec.secrets||{},bs=sc.by_severity||{};
  let h=card(kv([["Найдено",sc.count],["high",bs.high||0],["medium",bs.medium||0],
    ["low",bs.low||0]]));
  const fs=(D.findings||[]).filter(f=>f.area==="secrets");
  h+=card("<div class=k>Утечки</div>"+table(["Важность","Деталь"],
    fs.map(f=>'<tr><td class="'+sevClass(f.severity)+'">'+f.severity+'</td><td>'+
      esc(f.detail)+'</td></tr>').join("")||'<tr><td colspan=2 class=ok>чисто</td></tr>'));
  return h;
}
function vPipe(a,sec,D){
  const rows=(D.pipe||[]).slice(-15).reverse();
  return card("<div class=k>Последние прогоны конвейера</div>"+table(
    ["Статус","Длительность, мс","Время"],
    rows.map(r=>'<tr><td class="'+(r.status==="SUCCESS"?"ok":"bad")+'">'+esc(r.status)+
      '</td><td>'+esc(r.duration_ms)+'</td><td>'+esc(r.at||r.ts||"")+'</td></tr>').join("")
    ||'<tr><td colspan=3 class=off>прогонов нет</td></tr>'));
}
function vArena(a,sec,D){
  const rows=D.arena||[];
  return card("<div class=k>Доска арены</div>"+table(
    ["Агент","Пройдено","Всего"],
    rows.slice(-15).reverse().map(r=>'<tr><td>'+esc(r.agent)+'</td><td class=ok>'+
      esc(r.passed??r.ok??0)+'</td><td>'+esc(r.total??r.tasks??"")+'</td></tr>').join("")
    ||'<tr><td colspan=3 class=off>пусто</td></tr>'));
}
function vEnv(a,sec,D){
  const doc=D.doctor||{},cap=doc.capabilities||{};
  let h=card(kv([["Инструментов",doc.available+"/"+doc.total],
    ["Языки",(cap.languages||[]).length],["Стадий конвейера",cap.stages],
    ["Генераторов",(cap.generators||[]).length]]));
  h+=card("<div class=k>Тулчейны</div>"+(doc.tools||[]).map(t=>
    '<span class="chip'+(t.present?"":" off")+'">'+(t.present?"+":"-")+" "+esc(t.name)+
    '</span>').join("")||"<div class=off>нет данных</div>");
  return h;
}
async function load(){
  try{
    let d=window.__FORGE_DATA__;
    if(!d){const r=await fetch("api/report?t="+Date.now());d=await r.json();}
    DATA=d;
    $("score").textContent=(DATA.score??"--");
    $("verdict").textContent=DATA.verdict||"--";
    $("path").textContent=DATA.root||"";
    $("foot").textContent="обновлено: "+(DATA.generated_at||"?")+
      (window.__FORGE_DATA__?" · статический отчёт (экспорт)":
       " · только чтение · forge serve");render();
  }catch(e){$("foot").textContent="ошибка связи: "+e;}
}
tabs();load();
if(!window.__FORGE_DATA__){
  $("auto").addEventListener("change",()=>{if($("auto").checked)load();});
  setInterval(()=>{if($("auto").checked)load();},15000);
}else{$("auto").parentElement.style.display="none";}
</script></body></html>"""

_cache: dict = {"at": 0.0, "root": None, "data": None}
_lock = threading.Lock()


def _report(root: str, deep: bool, ttl: float) -> dict:
    now = time.time()
    with _lock:
        fresh = (_cache["data"] is not None and _cache["root"] == root
                 and not deep and now - _cache["at"] < ttl)
        if fresh:
            return _cache["data"]
    data = full_report(root, deep=deep)
    with _lock:
        _cache.update({"at": now, "root": root, "data": data})
    return data


class _Handler(BaseHTTPRequestHandler):
    root = "."
    ttl = 20.0

    def log_message(self, *a) -> None:  # тихо
        pass

    def _send(self, body: bytes, ctype: str, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - http.server convention
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/api/health":
            data = _report(self.root, False, self.ttl)
            body = json.dumps({"ok": data.get("ok", False),
                               "score": data.get("score"),
                               "verdict": data.get("verdict"),
                               "generated_at": data.get("generated_at")},
                              ensure_ascii=False).encode()
            self._send(body, "application/json")
            return
        if u.path == "/api/report":
            data = _report(self.root, bool(q.get("deep")), self.ttl)
            self._send(json.dumps(data, ensure_ascii=False).encode(),
                       "application/json")
            return
        if u.path in ("/", "/index.html"):
            self._send(PAGE.encode(), "text/html")
            return
        self._send(b'{"ok":false,"error":"not found"}', "application/json", 404)


def render_static(report: dict) -> str:
    """Тот же дашборд, но одним автономным HTML-файлом (данные внутри)."""
    payload = (json.dumps(report, ensure_ascii=False)
               .replace("</", "<\\/").replace("<!--", "<\\!--"))
    inject = f"<script>window.__FORGE_DATA__={payload};</script>"
    return PAGE.replace("<script>", inject + "<script>", 1)


def serve(root: str, port: int = 8099, open_browser: bool = False,
          watch: float = 0.0, ttl: float = 20.0) -> int:
    """Поднять дашборд. `watch` > 0 — фоновая пересборка отчёта каждые N сек."""
    base = str(Path(root).resolve())
    _Handler.root = base
    _Handler.ttl = ttl
    stop = threading.Event()
    if watch and watch > 0:
        def _bg() -> None:
            while not stop.wait(watch):
                try:
                    _report(base, False, 0.0)
                except Exception:
                    pass
        threading.Thread(target=_bg, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    url = f"http://127.0.0.1:{srv.server_port}/"
    print(f"FORGE Serve: {url}  (проект: {base}; Ctrl+C — стоп)")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        srv.server_close()
    return 0
