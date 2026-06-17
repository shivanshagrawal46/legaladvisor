# Premium B2B Marketing Website — Design System
### River Global · Supply Chain / Logistics · Built May 2026

Reference design language. Reuse for any premium corporate marketing site that needs:
minimalist, editorially sophisticated, credible, disciplined — think Maersk, DSV, Apple.

---

## 1. Stack

| Layer | Package | Version |
|---|---|---|
| Framework | `react` + `react-dom` | `^19` |
| Build | `vite` + `@vitejs/plugin-react` | `^8`, `^6` |
| Language | `typescript` | `~6` |
| UI library | `antd` | `^6` — Modal + message toast only, rest is custom CSS |
| Icons | `lucide-react` | `^1` — stroke-only, consistent weight |
| Animation | `framer-motion` | `^12` |
| Scroll trigger | `react-intersection-observer` | `^10` |
| Routing | `react-router-dom` | `^7` |

**`vite.config.ts`:**
```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({ plugins: [react()] });
```

**`tsconfig.json` minimum:**
```json
{ "compilerOptions": { "jsx": "react-jsx", "strict": true, "moduleResolution": "bundler" } }
```

**`src/vite-env.d.ts`** — required to suppress CSS import type errors:
```ts
/// <reference types="vite/client" />
```

---

## 2. Color System

```css
:root {
  /* Ink / paper — never pure black/white */
  --ink:       #0a0a0a;
  --ink-soft:  #1a1a1a;
  --paper:     #fafaf7;   /* warm off-white */
  --paper-2:   #f5f4ef;
  --paper-3:   #ebe9e2;

  /* Borders */
  --line:   #e5e3dc;
  --line-2: #d4d1c7;

  /* Muted text */
  --muted:   #6b6b66;
  --muted-2: #9a9994;

  /* Brand accent — deep ocean teal */
  --river:      #0e5560;   /* dark teal, headlines & emphasis */
  --river-soft: #1d8997;   /* mid teal, hover states, borders */
  --river-mist: #c8e0e3;   /* light teal — use this on dark backgrounds */

  /* Functional */
  --gold: #b8893b;
  --red:  #b1372a;

  --radius:    4px;
  --radius-lg: 12px;
}
```

**Rules:**
- On dark sections use `--river-mist` for teal, not `--river` (too dark to read)
- Alternate sections: light → dark → light → dark for visual rhythm
- Dark section: `background: var(--ink); color: var(--paper)`

---

## 3. Typography

**Fonts — two families only:**
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&display=swap');
/* JetBrains Mono via CDN for monospaced labels */
```

| Class | Role | Values |
|---|---|---|
| `body/html` | Body text | Inter 400, 15px, 1.65 lh |
| `.serif` | Italic accent words in headlines | Instrument Serif 400 |
| `.eyebrow` | Section labels | Inter 500, 11px, uppercase, 0.18em ls, muted |
| `.display` | Hero headline | `clamp(48px, 7vw, 96px)`, 500, −0.04em ls, 0.96 lh |
| `.h1` | Section headline | `clamp(36px, 5vw, 64px)`, 500, −0.03em ls, 1.02 lh |
| `.h2` | Sub-headline | `clamp(28px, 3.6vw, 44px)`, 500, −0.02em |
| `.lead` | Large body | `clamp(16px, 1.4vw, 19px)`, 400, 1.55 lh |
| `.body` | Descriptions | 15px, 1.65 lh, `var(--muted)` |
| `.mono` | Numbers, IDs, counters | JetBrains Mono, `font-feature-settings: "tnum"` |

**Headline editorial pattern — never all-sans. Break key word into italic serif teal:**
```jsx
<h2 className="h1">
  A growing catalogue of <br />
  <span className="serif" style={{ fontStyle:'italic', color:'var(--river-mist)' }}>traceable</span> materials.
</h2>
```

**Teal italic period on card titles:**
```jsx
<h3>Silica Sand<span className="serif" style={{ color:'var(--river)', fontStyle:'italic' }}>.</span></h3>
```

**Font rendering:**
```css
* { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
body { font-feature-settings: "ss01", "cv01", "cv02"; }
```

---

## 4. Spacing & Layout

```css
.container { width:100%; max-width:1320px; margin:0 auto; padding:0 32px; }
.section       { padding: clamp(80px, 12vw, 160px) 0; }
.section-tight { padding: clamp(60px, 8vw, 100px)  0; }
```

**Standard section header — eyebrow + h1 left, description right:**
```jsx
<div style={{ display:'flex', alignItems:'flex-end', justifyContent:'space-between',
              flexWrap:'wrap', gap:24, marginBottom:48 }}>
  <div style={{ maxWidth:720 }}>
    <span className="eyebrow">01 — Section Name</span>
    <h2 className="h1" style={{ marginTop:24 }}>Headline text.</h2>
  </div>
  <p className="body" style={{ maxWidth:380 }}>Supporting description.</p>
</div>
```

**Spacing quick ref:**
- Grid gaps (dense cards): `12–16px`
- Grid gaps (feature grids): `24–48px`
- Card padding compact: `20–24px`
- Card padding standard: `28–32px`
- Border radius cards: `14px`, large panels: `16px`, pills/buttons: `999px`

---

## 5. Buttons

```css
.btn {
  display:inline-flex; align-items:center; gap:10px; padding:14px 22px;
  font-size:13px; font-weight:500; letter-spacing:0.02em;
  border:1px solid var(--ink); background:var(--ink); color:var(--paper);
  border-radius:999px; transition:all 0.3s cubic-bezier(0.22,1,0.36,1);
}
.btn:hover { transform:translateY(-1px); box-shadow:0 8px 24px rgba(0,0,0,0.12); }
.btn-ghost { background:transparent; color:var(--ink); }
.btn-ghost:hover { background:var(--ink); color:var(--paper); }
.btn-light { background:var(--paper); color:var(--ink); border-color:var(--paper); }
.btn-river { background:var(--river); border-color:var(--river); }
```

Always pair with `<ArrowUpRight size={14} />` from lucide-react.

---

## 6. Animation Patterns (Framer Motion)

**Scroll reveal — every section:**
```jsx
const { ref, inView } = useInView({ threshold:0.1, triggerOnce:true });
<motion.div ref={ref}
  initial={{ opacity:0, y:20 }}
  animate={inView ? { opacity:1, y:0 } : {}}
  transition={{ duration:0.6 }} />
```

**Stagger children:** add `delay: 0.05 * i` per item.

**Card hover lift:**
```jsx
style={{ transform: isHover ? 'translateY(-4px)' : 'translateY(0)',
         transition: 'transform 0.5s cubic-bezier(0.22,1,0.36,1)' }}
```

**Animated divider on hover:**
```jsx
<motion.div
  animate={{ width: isHover ? '64%' : '24%', backgroundColor: isHover ? 'var(--river)' : 'var(--line-2)' }}
  transition={{ duration:0.55, ease:[0.22,1,0.36,1] }}
  style={{ height:1.5 }} />
```

**Arrow pill rotation:**
```jsx
<motion.div animate={{ rotate: isHover ? 45 : 0 }} transition={{ duration:0.45, ease:[0.22,1,0.36,1] }}>
  <ArrowUpRight size={13} />
</motion.div>
```

**FilteredGrid with AnimatePresence:**
```jsx
<motion.div layout style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:12 }}>
  <AnimatePresence mode="popLayout">
    {items.map((item, i) => (
      <motion.div key={item.id} layout
        initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }}
        exit={{ opacity:0, y:-8 }} transition={{ duration:0.4, delay:i*0.03 }} />
    ))}
  </AnimatePresence>
</motion.div>
```

**Standard ease everywhere:** `[0.22, 1, 0.36, 1]` — spring-like cubic bezier.

---

## 7. Card Design Anatomy

Every card follows the same 6-part interior structure:

```
[Identifier chip (formula/icon)] ........... [Arrow pill — rotates 45° on hover]
[Tag — 10px uppercase 0.18em category label]
[Title h3 — with italic serif teal period]
[Animated divider — grows 24%→64% on hover]
[Description — 2-line clamp, muted color]
---border---
[Mono counter 01/12] ........ [Hover-reveal CTA → View specs]
```

**Light card shell:**
```jsx
style={{
  background: 'var(--paper)',
  border: `1px solid ${isHover ? 'var(--ink)' : 'var(--line)'}`,
  borderRadius: 14, padding:'22px 22px 18px', minHeight:300,
  position:'relative', overflow:'hidden',
  transform: isHover ? 'translateY(-5px)' : 'translateY(0)',
  boxShadow: isHover ? '0 20px 50px -24px rgba(14,85,96,0.22)' : 'none',
  transition:'transform 0.5s cubic-bezier(0.22,1,0.36,1), box-shadow 0.5s, border-color 0.4s',
}}
```

**Dark card shell:**
```jsx
style={{
  background: isHover
    ? 'linear-gradient(180deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))'
    : 'rgba(255,255,255,0.025)',
  border: `1px solid ${isHover ? 'rgba(255,255,255,0.22)' : 'rgba(255,255,255,0.07)'}`,
  borderRadius:14, padding:'20px 20px 16px', minHeight:240,
  boxShadow: isHover ? '0 18px 40px -22px rgba(29,137,151,0.32)' : 'none',
  transition:'transform 0.5s cubic-bezier(0.22,1,0.36,1), box-shadow 0.5s, border-color 0.4s, background 0.4s',
}}
```

**Ghost icon overlay (light cards):**
```jsx
<div style={{
  position:'absolute', bottom:-22, right:-22, pointerEvents:'none',
  opacity: isHover ? 0.075 : 0.045,
  transform: isHover ? 'rotate(-6deg) scale(1.05)' : 'none',
  transition:'opacity 0.5s, transform 0.5s',
}}>
  <Icon size={170} strokeWidth={0.9} />
</div>
```

**Dark card hover radial glow:**
```jsx
<div style={{
  position:'absolute', inset:0, pointerEvents:'none',
  background:'radial-gradient(120% 80% at 0% 0%, rgba(29,137,151,0.18) 0%, transparent 55%)',
  opacity: isHover ? 1 : 0, transition:'opacity 0.5s',
}} />
```

---

## 8. Grid Column Configs (this project)

| Section | Columns |
|---|---|
| Industries | `repeat(3, 1fr)` |
| Products | `repeat(4, 1fr)` |
| Values | `repeat(4, 1fr)` |
| Contact cards | `repeat(4, 1fr)` |
| Network locations | `repeat(4, 1fr)` |
| Capabilities / features | `repeat(auto-fit, minmax(300px, 1fr))` |

Responsive: always add `@media (max-width: 900px)` → 2 cols, `(max-width: 560px)` → 1 col.

---

## 9. Eyebrow CSS

```css
.eyebrow {
  font-size:11px; font-weight:500; text-transform:uppercase;
  letter-spacing:0.18em; color:var(--muted);
  display:inline-flex; align-items:center; gap:10px;
}
.eyebrow::before { content:''; width:24px; height:1px; background:var(--muted); }
/* Dark variant */
.dark .eyebrow { color:rgba(255,255,255,0.55); }
.dark .eyebrow::before { background:rgba(255,255,255,0.4); }
```

---

## 10. Filter Tab Bar (dark sections)

```jsx
<div style={{
  display:'flex', gap:6, flexWrap:'wrap',
  borderTop:'1px solid rgba(255,255,255,0.08)',
  borderBottom:'1px solid rgba(255,255,255,0.08)',
  padding:'12px 0', alignItems:'center', justifyContent:'space-between',
}}>
  <div style={{ display:'flex', gap:6 }}>
    {tabs.map(tab => {
      const active = activeCat === tab.id;
      return (
        <button style={{
          background: active ? 'var(--paper)' : 'transparent',
          color: active ? 'var(--ink)' : 'rgba(255,255,255,0.65)',
          border: `1px solid ${active ? 'var(--paper)' : 'rgba(255,255,255,0.12)'}`,
          padding:'7px 14px', borderRadius:999, fontSize:11.5, fontWeight:500,
        }}>{tab.label}</button>
      );
    })}
  </div>
  <div className="mono" style={{ fontSize:10.5, color:'rgba(255,255,255,0.4)', letterSpacing:'0.1em' }}>
    12 ITEMS · UPDATED 05/26
  </div>
</div>
```

---

## 11. SVG Network Map — Airline-Ad Style

Compact square panel (`aspectRatio: 1/1`, ~40% container width). High concave arcs only:

```js
// Control point forced to bow upward
const nx = -dy / dist, ny = dx / dist;
const sign = ny > 0 ? -1 : 1;
const offset = dist * 0.38;
const cx = midX + nx * offset * sign;
const cy = midY + ny * offset * sign;
const d = `M ${a.x} ${a.y} Q ${cx} ${cy} ${b.x} ${b.y}`;
```

Route draw animation: `pathLength: 0→1`, ease `[0.22,1,0.36,1]`, staggered `delay: 0.08*i`.

Traveling pulse beads via SVG `<animateMotion>` along route path + glow filter:
```jsx
<circle r="0.9" fill="#73e6f5">
  <animateMotion dur="4.2s" repeatCount="indefinite" path={route.d} />
  <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.85;1" dur="4.2s" repeatCount="indefinite" />
</circle>
```

Hub tiers: **primary** (pulsing halo + sonar ring), **support** (soft halo), **partner** (white dot).

Label legibility trick (labels on dark maps):
```jsx
style={{ paintOrder:'stroke', stroke:'rgba(8,8,8,0.85)', strokeWidth:0.55, strokeLinejoin:'round' }}
```

---

## 12. Modal Pattern (Ant Design)

```jsx
<Modal open={!!selected} onCancel={onClose} footer={null} width={820}
  closable={false} centered
  styles={{ body:{padding:0}, mask:{background:'rgba(10,10,10,0.7)', backdropFilter:'blur(8px)'} }}>
```

Add editorial top band for document credibility:
```jsx
<div style={{ padding:'14px 28px', background:'var(--ink)', color:'var(--paper)',
              fontSize:10.5, letterSpacing:'0.18em', textTransform:'uppercase', fontWeight:600,
              display:'flex', justifyContent:'space-between' }}>
  <span>Company Name · Document Type</span>
  <span className="mono">DOC-ID-001</span>
</div>
```

---

## 13. Ant Design CSS Overrides

```css
.ant-modal-content { background:var(--paper)!important; border-radius:16px!important; padding:0!important; overflow:hidden; }
.ant-input, .ant-input-affix-wrapper {
  border-radius:0!important; border:none!important;
  border-bottom:1px solid var(--line)!important;
  background:transparent!important; padding:12px 0!important; box-shadow:none!important;
}
.ant-select-selector {
  border-radius:0!important; border:none!important;
  border-bottom:1px solid var(--line)!important;
  background:transparent!important; box-shadow:none!important;
}
*:focus { outline:none; }
*:focus-visible { outline:2px solid var(--river); outline-offset:2px; }
```

---

## 14. Tone & Copy Rules

- Headlines: statement + serif italic accent word + closing teal period
- No exclamation marks. No marketing superlatives.
- Numbers: realistic and defensible (e.g. "11+ countries", "6 sectors", "25–28 routes")
- CTAs: `"Request Sourcing"`, `"Send an email"`, `"Inquire about X"` — direct, operational
- Section descriptions: max 380px wide, 14–15px, `var(--muted)`, 1.65 lh
- Banned words: "world-class", "cutting-edge", "seamless", "revolutionary", "best-in-class"

---

## 15. Quick-Start Checklist for a New Site

- [ ] `npm install react react-dom framer-motion lucide-react react-intersection-observer antd @vitejs/plugin-react`
- [ ] `npm install -D typescript @types/react @types/react-dom vite`
- [ ] Copy CSS variables, type system, layout helpers, button classes into `index.css`
- [ ] Add Google Fonts `<link>` for Inter + Instrument Serif in `index.html`
- [ ] Create `src/vite-env.d.ts` with `/// <reference types="vite/client" />`
- [ ] Build `SplashScreen` component, 2000–2700ms timeout in `App.tsx`
- [ ] Alternate section backgrounds: paper → ink → paper → ink
- [ ] Every section: numbered eyebrow + h1 with serif italic accent + body description right
- [ ] Every card: identifier top-left, arrow pill top-right, animated divider, mono counter bottom
- [ ] All scroll reveals: `useInView({ threshold:0.1, triggerOnce:true })` + Framer `y:20→0`
- [ ] All buttons include `<ArrowUpRight size={14} />` icon
- [ ] Run `npx tsc --noEmit` to verify types before shipping
