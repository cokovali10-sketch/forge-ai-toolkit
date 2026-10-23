"""CSS builder: one token block + effect-specific rules + motion rules."""
from __future__ import annotations

BASE = r"""
:root{
  --bg:__BG__; --bg2:__BG2__; --text:__TEXT__; --muted:__MUTED__;
  --accent:__ACCENT__; --accent2:__ACCENT2__; --surface:__SURFACE__;
  --border:__BORDER__; --btn-text:__BTN_TEXT__; --glow:__GLOW__;
  --radius:__RADIUS__; --display:__DISPLAY__; --body:__BODY__;
  --max:1140px; --ease:cubic-bezier(.22,1,.36,1);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--body);
  line-height:1.65;overflow-x:hidden;-webkit-font-smoothing:antialiased}
::selection{background:var(--accent);color:var(--btn-text)}
img{max-width:100%;display:block}
a{color:inherit;text-decoration:none}
h1,h2,h3{font-family:var(--display);line-height:1.05;letter-spacing:-.03em;
  margin:0;text-wrap:balance}
p{margin:0}
.skip{position:absolute;left:-999px;top:8px;z-index:99;padding:10px 16px;
  background:var(--accent);color:var(--btn-text);border-radius:8px}
.skip:focus{left:16px}
.bg{position:fixed;inset:0;z-index:0;overflow:hidden;pointer-events:none}
.bg>*{position:absolute}
.orb{border-radius:50%;filter:blur(72px);opacity:.55;animation:drift 20s
  ease-in-out infinite alternate}
.orb-1{width:46vw;height:46vw;left:-12vw;top:-14vw;background:var(--accent)}
.orb-2{width:38vw;height:38vw;right:-10vw;top:8vh;background:var(--accent2);
  animation-delay:-6s;animation-duration:26s}
.orb-3{width:32vw;height:32vw;left:32vw;bottom:-18vw;background:var(--accent);
  opacity:.35;animation-delay:-12s;animation-duration:32s}
.bg canvas{inset:0;width:100%;height:100%;opacity:.75}
.bg .grid{display:none;inset:0}
.nav{position:sticky;top:0;z-index:20;display:flex;align-items:center;
  justify-content:space-between;gap:22px;max-width:var(--max);margin:0 auto;
  padding:18px 24px;backdrop-filter:blur(14px)}
.nav::after{content:"";position:absolute;left:24px;right:24px;bottom:0;
  height:1px;background:var(--border);opacity:.6}
.brand{display:flex;align-items:center;gap:10px;font-family:var(--display);
  font-weight:700;letter-spacing:-.02em}
.mark{width:16px;height:16px;border-radius:4px;background:var(--accent);
  box-shadow:0 0 22px var(--glow);transform:rotate(45deg)}
.nav-links{display:flex;align-items:center;gap:22px;font-size:14px}
.nav-links a{opacity:.78;transition:opacity .2s ease,color .2s ease}
.nav-links a:hover{opacity:1;color:var(--accent)}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:9px;
  padding:13px 20px;border-radius:calc(var(--radius) * .6);font-weight:650;
  font-size:14px;border:1px solid transparent;cursor:pointer;
  transition:transform .25s var(--ease),background .2s ease,border-color .2s ease,
  box-shadow .25s ease;will-change:transform}
.btn-primary{background:var(--accent);color:var(--btn-text);
  box-shadow:0 12px 34px -14px var(--glow)}
.btn-primary:hover{box-shadow:0 18px 44px -14px var(--glow);
  transform:translateY(-2px)}
.btn-ghost{border-color:var(--border);background:var(--surface);
  color:var(--text)}
.btn-ghost:hover{border-color:var(--accent);color:var(--accent)}
main,footer,.nav{position:relative;z-index:2}
.hero{max-width:var(--max);margin:0 auto;padding:clamp(48px,8vw,104px) 24px
  80px;display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,.85fr);
  gap:clamp(28px,5vw,64px);align-items:center;min-height:78vh}
.eyebrow,.kicker{font-family:var(--body);font-size:12px;font-weight:700;
  letter-spacing:.18em;text-transform:uppercase;color:var(--accent)}
.hero h1{font-size:clamp(44px,7.3vw,88px);margin:18px 0 0}
.h1-anim{display:block}
.grad{background:linear-gradient(100deg,var(--accent),var(--accent2));
  -webkit-background-clip:text;background-clip:text;color:transparent;
  display:inline-block}
.lead{color:var(--muted);font-size:clamp(16px,1.6vw,19px);max-width:56ch;
  margin-top:22px}
.cta-row{display:flex;flex-wrap:wrap;gap:12px;margin-top:30px}
.hero-panel{position:relative;border:1px solid var(--border);
  background:var(--surface);border-radius:var(--radius);padding:18px;
  box-shadow:0 30px 90px -40px var(--glow);overflow:hidden}
.hero-panel::before{content:"";position:absolute;inset:0;z-index:0;
  background:radial-gradient(320px circle at var(--mx,50%) var(--my,50%),
  var(--glow),transparent 65%);opacity:.9;pointer-events:none}
.hero-panel>*{position:relative;z-index:1}
.panel-head{display:flex;align-items:center;gap:8px;padding-bottom:14px;
  border-bottom:1px solid var(--border);font-size:12px;color:var(--muted);
  font-family:var(--display)}
.dot{width:9px;height:9px;border-radius:50%;background:var(--accent);
  box-shadow:0 0 14px var(--glow)}
.panel-body{display:grid;gap:10px;padding-top:16px}
.panel-row{display:flex;justify-content:space-between;gap:12px;font-size:13px;
  color:var(--muted);padding:9px 11px;border:1px solid var(--border);
  border-radius:calc(var(--radius) * .45);background:var(--bg2)}
.panel-row b{color:var(--text);font-family:var(--display)}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;
  margin-top:6px}
.metric{padding:12px;border-radius:calc(var(--radius) * .45);
  background:var(--bg2);border:1px solid var(--border)}
.metric b{display:block;font-family:var(--display);font-size:22px;
  letter-spacing:-.04em}
.metric span{font-size:11px;color:var(--muted)}
.section{max-width:var(--max);margin:0 auto;padding:clamp(56px,7vw,96px) 24px}
.sec-head{max-width:70ch;margin-bottom:36px}
.sec-head h2{font-size:clamp(30px,4vw,48px);margin:12px 0 10px}
.sec-head p{color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.card{position:relative;padding:24px;border:1px solid var(--border);
  background:var(--surface);border-radius:var(--radius);overflow:hidden;
  transition:border-color .25s ease,transform .3s var(--ease);
  transform-style:preserve-3d;will-change:transform}
.card:hover{border-color:var(--accent)}
.card::after{content:"";position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(280px circle at var(--mx,50%) var(--my,50%),
  var(--glow),transparent 60%);opacity:0;transition:opacity .3s ease}
.card:hover::after{opacity:.55}
.icon{width:38px;height:38px;display:grid;place-items:center;
  border-radius:calc(var(--radius) * .5);border:1px solid var(--border);
  color:var(--accent);background:var(--bg2);margin-bottom:18px}
.icon svg{width:20px;height:20px}
.card h3{font-size:20px;margin-bottom:8px}
.card p{color:var(--muted);font-size:14px}
.gallery{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.shot{margin:0;border:1px solid var(--border);border-radius:var(--radius);
  overflow:hidden;background:var(--surface)}
.shot-ui{height:168px;padding:14px;display:flex;flex-direction:column;gap:9px;
  background:linear-gradient(150deg,var(--bg2),var(--bg));overflow:hidden;
  transform:translateY(var(--py,0))}
.shot-bar{display:flex;gap:6px;margin-bottom:4px}
.shot-bar i{width:8px;height:8px;border-radius:50%;background:var(--border);
  display:block}
.shot-bar i:first-child{background:var(--accent)}
.shot-line{height:11px;border-radius:99px;background:var(--border);opacity:.7}
.shot-line.w1{width:62%}.shot-line.w2{width:86%}.shot-line.w3{width:46%}
.shot-blob{margin-top:auto;height:64px;border-radius:calc(var(--radius) * .5);
  background:linear-gradient(120deg,var(--accent),var(--accent2));opacity:.8}
.shot figcaption{padding:16px;border-top:1px solid var(--border)}
.shot figcaption b{display:block;font-family:var(--display);font-size:15px}
.shot figcaption span{display:block;color:var(--muted);font-size:12px;
  margin-top:4px}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;
  border-top:1px solid var(--border);border-bottom:1px solid var(--border);
  padding-top:38px;padding-bottom:38px}
.stat b{display:block;font-family:var(--display);font-size:clamp(32px,4.4vw,54px);
  letter-spacing:-.05em;line-height:1}
.stat span{display:block;color:var(--muted);font-size:13px;margin-top:8px}
.cta{text-align:center;padding-top:80px;padding-bottom:96px}
.cta-card{max-width:760px;margin:0 auto;padding:clamp(30px,5vw,58px);
  border:1px solid var(--border);border-radius:calc(var(--radius) * 1.2);
  background:var(--surface);position:relative;overflow:hidden}
.cta-card::before{content:"";position:absolute;inset:-40%;z-index:0;
  background:conic-gradient(from 180deg,var(--accent),transparent 30%,
  var(--accent2),transparent 70%,var(--accent));opacity:.18;
  animation:spin 16s linear infinite;pointer-events:none}
.cta-card>*{position:relative;z-index:1}
.cta h2{font-size:clamp(28px,4vw,46px)}
.cta p{color:var(--muted);margin:14px auto 26px;max-width:52ch}
code{font-family:ui-monospace,'Cascadia Code',Consolas,monospace;font-size:.92em;
  padding:2px 7px;border-radius:6px;background:var(--bg2);
  border:1px solid var(--border)}
.footer{max-width:var(--max);margin:0 auto;padding:28px 24px 46px;
  border-top:1px solid var(--border);color:var(--muted);font-size:12px;
  display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
.cursor-glow{position:fixed;left:0;top:0;width:420px;height:420px;
  margin:-210px 0 0 -210px;border-radius:50%;pointer-events:none;z-index:1;
  background:radial-gradient(circle,var(--glow),transparent 62%);
  opacity:0;transition:opacity .4s ease;mix-blend-mode:screen}
.cursor-glow.on{opacity:.5}
.marquee{overflow:hidden;border-top:1px solid var(--border);
  border-bottom:1px solid var(--border);background:var(--bg2);
  font-family:var(--display);font-size:13px;letter-spacing:.16em;
  white-space:nowrap;padding:11px 0;position:relative;z-index:2}
.marquee-track{display:inline-flex;gap:24px;padding-left:24px;
  animation:marquee 22s linear infinite}
.glitch-line{font-family:var(--display);font-size:12px;letter-spacing:.28em;
  color:var(--accent);text-transform:uppercase;margin-top:16px;
  animation:flicker 4.5s infinite}
@keyframes drift{from{transform:translate3d(-3%,-2%,0) scale(1)}
  to{transform:translate3d(5%,4%,0) scale(1.12)}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes marquee{to{transform:translateX(-50%)}}
@keyframes flicker{0%,92%,100%{opacity:.72}94%{opacity:.28}96%{opacity:.9}}
@keyframes scan{from{transform:translateY(-100%)}to{transform:translateY(100%)}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}
.no-js [data-reveal]{opacity:1;transform:none}
.motion [data-reveal]{opacity:0;transform:translateY(22px);
  transition:opacity .75s var(--ease),transform .75s var(--ease)}
.motion [data-reveal].in{opacity:1;transform:none}
@media (max-width:900px){
  .hero{grid-template-columns:1fr;min-height:auto}
  .cards,.gallery{grid-template-columns:1fr 1fr}
  .stats{grid-template-columns:1fr 1fr}
}
@media (max-width:640px){
  .nav{padding:14px 16px}
  .nav-links{gap:14px}
  .nav-links a:not(.btn){display:none}
  .hero{padding-top:44px}
  .cards,.gallery,.stats{grid-template-columns:1fr}
  .cta{padding-top:56px}
}
@media (prefers-reduced-motion: reduce){
  html{scroll-behavior:auto}
  *,*::before,*::after{animation:none !important;transition:none !important}
  [data-reveal]{opacity:1 !important;transform:none !important}
  .cursor-glow{display:none}
}
"""

EFFECTS = {
    "aurora": r"""
.effect-aurora .orb-1{background:radial-gradient(circle at 30% 30%,var(--accent),transparent 68%)}
.effect-aurora .orb-2{background:radial-gradient(circle at 60% 40%,var(--accent2),transparent 66%)}
.effect-aurora .hero-panel{backdrop-filter:blur(16px) saturate(140%)}
""",
    "neon": r"""
.effect-neon .bg .grid{display:block;
  background-image:linear-gradient(var(--border) 1px,transparent 1px),
  linear-gradient(90deg,var(--border) 1px,transparent 1px);
  background-size:64px 64px;opacity:.22;
  mask-image:radial-gradient(circle at 50% 20%,#000 20%,transparent 75%)}
.effect-neon .bg::after{content:"";position:absolute;inset:0;
  background:repeating-linear-gradient(0deg,rgba(255,255,255,.04) 0 1px,
  transparent 1px 3px);mix-blend-mode:overlay;animation:scan 9s linear infinite}
.effect-neon .hero h1{text-shadow:0 0 24px var(--glow),0 0 64px var(--glow)}
.effect-neon .grad{filter:drop-shadow(0 0 18px var(--glow))}
.effect-neon .card:hover{box-shadow:0 0 0 1px var(--accent),0 0 34px var(--glow)}
""",
    "glass": r"""
.effect-glass .orb{filter:blur(90px);opacity:.6}
.effect-glass .hero-panel,.effect-glass .card,.effect-glass .cta-card{
  backdrop-filter:blur(20px) saturate(150%);-webkit-backdrop-filter:blur(20px) saturate(150%)}
.effect-glass .hero-panel{background:linear-gradient(145deg,
  rgba(255,255,255,.12),rgba(255,255,255,.03))}
.effect-glass .card{background:linear-gradient(150deg,
  rgba(255,255,255,.1),rgba(255,255,255,.025))}
""",
    "brut": r"""
.effect-brut{--radius:0px}
.effect-brut .orb{display:none}
.effect-brut .nav{backdrop-filter:none;border-bottom:2px solid var(--border)}
.effect-brut .nav::after{display:none}
.effect-brut .hero-panel,.effect-brut .card,.effect-brut .shot,
.effect-brut .cta-card{box-shadow:8px 8px 0 var(--border);border-width:2px}
.effect-brut .btn{border-width:2px;border-color:var(--border);
  box-shadow:4px 4px 0 var(--border);text-transform:uppercase;
  letter-spacing:.08em}
.effect-brut .btn:hover{transform:translate(-2px,-2px);
  box-shadow:6px 6px 0 var(--border)}
.effect-brut .mark{border-radius:0;background:var(--text)}
.effect-brut .panel-row,.effect-brut .metric{border-width:2px}
.effect-brut .cta-card::before{display:none}
""",
    "minimal": r"""
.effect-minimal .orb{opacity:.16;filter:blur(110px)}
.effect-minimal .bg canvas{display:none}
.effect-minimal .hero-panel,.effect-minimal .card,.effect-minimal .cta-card{
  box-shadow:0 1px 0 var(--border),0 24px 60px -50px rgba(0,0,0,.35)}
.effect-minimal .card::after{display:none}
.effect-minimal .mark{box-shadow:none}
""",
    "crt": r"""
.effect-crt .bg::after{content:"";position:absolute;inset:0;z-index:5;
  pointer-events:none;
  background:repeating-linear-gradient(0deg,rgba(0,0,0,.22) 0 1px,
  transparent 1px 3px);opacity:.55}
.effect-crt .bg::before{content:"";position:absolute;inset:0;z-index:4;
  pointer-events:none;background:radial-gradient(ellipse at center,
  transparent 55%,rgba(0,0,0,.55) 100%)}
.effect-crt .hero h1{text-shadow:0 0 16px var(--glow),2px 0 0 var(--accent2)}
.effect-crt .grad{text-shadow:none}
.effect-crt .card,.effect-crt .hero-panel{border-style:dashed}
""",
}


def build(preset: dict) -> str:
    c = preset["colors"]
    css = (BASE
           .replace("__BG__", c["bg"]).replace("__BG2__", c["bg2"])
           .replace("__TEXT__", c["text"]).replace("__MUTED__", c["muted"])
           .replace("__ACCENT__", c["accent"])
           .replace("__ACCENT2__", c["accent2"])
           .replace("__SURFACE__", c["surface"])
           .replace("__BORDER__", c["border"])
           .replace("__BTN_TEXT__", c["btn_text"])
           .replace("__GLOW__", c["glow"])
           .replace("__RADIUS__", preset["radius"])
           .replace("__DISPLAY__", preset["display"])
           .replace("__BODY__", preset["body"]))
    return css + EFFECTS.get(preset["effect"], "")
