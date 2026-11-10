const fs = require('fs');
const path = require('path');

const OUT_DIR = __dirname;
const GRAPH_JSON_PATH = path.join(OUT_DIR, 'graph.json');
const LABELS_JSON_PATH = path.join(OUT_DIR, '.graphify_labels.json');
const LEARNING_JSON_PATH = path.join(OUT_DIR, '.graphify_learning.json');
const HTML_OUT_PATH = path.join(OUT_DIR, 'graph.html');
const HTML_TMP_PATH = path.join(OUT_DIR, '.graph.html.tmp');
const REPORT_PATH = path.join(OUT_DIR, 'GRAPH_REPORT.md');

const BYNAT_COMMUNITY_COLORS = [
  '#F9442A',
  '#FFF1DC',
  '#FF7849',
  '#FBBF24',
  '#38BDF8',
  '#34D399',
  '#FB7185',
  '#A78BFA',
  '#60A5FA',
  '#FCD34D',
  '#2DD4BF',
  '#F472B6',
  '#818CF8',
  '#4ADE80',
  '#FB923C',
  '#22D3EE',
  '#E879F9',
  '#A3E635',
  '#F87171',
  '#C084FC'
];

const RING_COLORS = {
  preferred: '#34D399',
  contested: '#FBBF24'
};

function sanitizeLabel(value) {
  return String(value == null ? '' : value)
    .replace(/[\u0000-\u001F\u007F-\u009F]/g, ' ')
    .trim();
}

function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function jsSafeJson(obj) {
  return JSON.stringify(obj).replace(/<\//g, '<\\/');
}

function readJsonIfExists(filePath, fallback) {
  try {
    if (fs.existsSync(filePath)) {
      return JSON.parse(fs.readFileSync(filePath, 'utf8'));
    }
  } catch (_) {}
  return fallback;
}

const FAVICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128"><rect width="128" height="128" rx="28" fill="#14213D"/><path d="M54 44A16 16 0 1 0 86 44A16 16 0 1 0 54 44Z" fill="#FFF1DC"/><path d="M34 74V40A30 30 0 0 1 94 40V74ZM54 44A16 16 0 1 0 86 44A16 16 0 1 0 54 44Z" fill="#F9442A" fill-rule="evenodd"/><path d="M24 74H28A14 14 0 0 1 42 88V104A14 14 0 0 1 28 118H24A14 14 0 0 1 10 104V88A14 14 0 0 1 24 74Z" fill="#FFF1DC"/><path d="M62 74H66A14 14 0 0 1 80 88V104A14 14 0 0 1 66 118H62A14 14 0 0 1 48 104V88A14 14 0 0 1 62 74Z" fill="#FFF1DC"/><path d="M100 74H104A14 14 0 0 1 118 88V104A14 14 0 0 1 104 118H100A14 14 0 0 1 86 104V88A14 14 0 0 1 100 74Z" fill="#FFF1DC"/><path d="M68.5 40.5A7.5 7.5 0 1 0 83.5 40.5A7.5 7.5 0 1 0 68.5 40.5Z" fill="#14213D"/></svg>`;

const BRAND_LOGO_DARK_SVG = `<svg class="brand-logo" xmlns="http://www.w3.org/2000/svg" viewBox="2 4 473 150" role="img" aria-labelledby="bynat-brand-title"><title id="bynat-brand-title">bynat</title><path d="M54 44A16 16 0 1 0 86 44A16 16 0 1 0 54 44Z" fill="#FFF1DC"/><path d="M34 74V40A30 30 0 0 1 94 40V74ZM54 44A16 16 0 1 0 86 44A16 16 0 1 0 54 44Z" fill="#F9442A" fill-rule="evenodd"/><path d="M24 74H28A14 14 0 0 1 42 88V104A14 14 0 0 1 28 118H24A14 14 0 0 1 10 104V88A14 14 0 0 1 24 74Z" fill="#FFF1DC"/><path d="M62 74H66A14 14 0 0 1 80 88V104A14 14 0 0 1 66 118H62A14 14 0 0 1 48 104V88A14 14 0 0 1 62 74Z" fill="#FFF1DC"/><path d="M100 74H104A14 14 0 0 1 118 88V104A14 14 0 0 1 104 118H100A14 14 0 0 1 86 104V88A14 14 0 0 1 100 74Z" fill="#FFF1DC"/><path d="M68.5 40.5A7.5 7.5 0 1 0 83.5 40.5A7.5 7.5 0 1 0 68.5 40.5Z" fill="#14213D"/><path d="M146 39.5L146 110.5A7.5 7.5 0 0 0 161 110.5L161 39.5A7.5 7.5 0 0 0 146 39.5Z" fill="#FFF1DC"/><path d="M146 88A30 30 0 1 0 206 88A30 30 0 1 0 146 88ZM161 88A15 15 0 1 0 191 88A15 15 0 1 0 161 88Z" fill="#FFF1DC" fill-rule="evenodd"/><path d="M216.67 68.61L237.17 113.61A7.5 7.5 0 0 0 250.83 107.39L230.33 62.39A7.5 7.5 0 0 0 216.67 68.61Z" fill="#FFF1DC"/><path d="M259.79 62.15L221.54 138.65A7.5 7.5 0 0 0 234.96 145.35L273.21 68.85A7.5 7.5 0 0 0 259.79 62.15Z" fill="#FFF1DC"/><path d="M284 65.5L284 110.5A7.5 7.5 0 0 0 299 110.5L299 65.5A7.5 7.5 0 0 0 284 65.5Z" fill="#FFF1DC"/><path d="M284 88A30 30 0 0 1 344 88A7.5 7.5 0 0 1 329 88A15 15 0 0 0 299 88A7.5 7.5 0 0 1 284 88Z" fill="#FFF1DC"/><path d="M329 88L329 110.5A7.5 7.5 0 0 0 344 110.5L344 88A7.5 7.5 0 0 0 329 88Z" fill="#FFF1DC"/><path d="M354 88A30 30 0 1 0 414 88A30 30 0 1 0 354 88ZM369 88A15 15 0 1 0 399 88A15 15 0 1 0 369 88Z" fill="#FFF1DC" fill-rule="evenodd"/><path d="M399 65.5L399 110.5A7.5 7.5 0 0 0 414 110.5L414 65.5A7.5 7.5 0 0 0 399 65.5Z" fill="#FFF1DC"/><path d="M433 49.5L433 98A7.5 7.5 0 0 0 448 98L448 49.5A7.5 7.5 0 0 0 433 49.5Z" fill="#FFF1DC"/><path d="M453 118A20 20 0 0 1 433 98A7.5 7.5 0 0 1 448 98A5 5 0 0 0 453 103A7.5 7.5 0 0 1 453 118Z" fill="#FFF1DC"/><path d="M453 118L458 118A7.5 7.5 0 0 0 458 103L453 103A7.5 7.5 0 0 0 453 118Z" fill="#FFF1DC"/><path d="M428 73L454 73A7.5 7.5 0 0 0 454 58L428 58A7.5 7.5 0 0 0 428 73Z" fill="#FFF1DC"/></svg>`;

const REPORT_DESIGN_SECTION_HEADER = '## Project Design & Styling Instructions (bynat Brand Theme)';

const REPORT_DESIGN_SECTION = `${REPORT_DESIGN_SECTION_HEADER}

> **Persistent Instruction for Agents & Maintainers:** Whenever \`graphify update .\`, \`graphify cluster-only\`, or \`graphify export html\` is executed on this repository, the knowledge graph visualization (\`graphify-out/graph.html\`) and this design specification section in \`graphify-out/GRAPH_REPORT.md\` **must** maintain the official \`bynat\` brand identity derived from \`assets/Full Logo/logo-dark.svg\`, \`assets/Logo/symbol-dark.svg\`, and \`assets/347981844.png\`.

### 1. Brand Color Tokens & Surface Hierarchy
- **Midnight Navy (\`#14213D\`)** — Primary brand background and eye-pupil tone from \`logo.svg\` / \`logo-dark.svg\`. Used as the radial center of the graph canvas, elevated inspector cards, and primary surface anchor.
- **Deepest Navy (\`#0B1324\` / \`#101B33\`)** — Outer canvas vignette (\`#0B1324\`) and sidebar container surface (\`#101B33\`), with \`#243863\` structural borders.
- **Bynat Vermilion (\`#F9442A\`)** — Primary brand accent from the \`bynat\` arch mark. Used for Community 0, primary focus rings, active checkboxes, God-node badges, hyperedge regions, and interactive highlights.
- **Warm Cream (\`#FFF1DC\`)** — Primary foreground and data-column pill color from \`logo-dark.svg\`. Used for primary typography, high-degree node labels, selected node highlights, and Community 1.
- **Muted Cream & Slate (\`#DFD0BA\` / \`#8FA4C7\`)** — Secondary body copy (\`#DFD0BA\`) and uppercase section headers, degree counters, and source-file metadata (\`#8FA4C7\`).

### 2. Visual Motifs & Typography
- **Brand Header & Favicon:** \`graphify-out/graph.html\` embeds \`assets/Full Logo/logo-dark.svg\` in \`#brand-header\` alongside a pill-shaped \`KNOWLEDGE GRAPH\` badge and uses \`assets/Logo/symbol-dark.svg\` on a \`#14213D\` rounded-square canvas as its inline SVG favicon.
- **Rounded Data-Column Pill Geometry:** Cards, search inputs, neighbor links, and badges use \`10px\`–\`14px\` / \`999px\` border radii echoing the three rounded vertical data-column pills (\`rx="14"\`) of the \`bynat\` symbol.
- **Typography:** \`Plus Jakarta Sans\` for UI controls and graph labels paired with \`JetBrains Mono\` for source file paths, line numbers, degree badges, and graph statistics.
- **Community Color Sequence:** Anchored by \`#F9442A\` (Vermilion) and \`#FFF1DC\` (Warm Cream), followed by a 20-color high-contrast palette tuned for legibility over \`#14213D\` Midnight Navy.

### 3. Automatic Maintenance Workflow during Updates
- **Custom Builder Hook (\`graphify-out/build_graph_html.js\`):** \`graphify\`'s \`to_html()\` exporter automatically detects and executes \`graphify-out/build_graph_html.js\` via Node.js whenever \`graphify update .\` or \`graphify export html\` runs.
- **Report Instruction Persistence:** \`graphify-out/build_graph_html.js\` also idempotently ensures this \`${REPORT_DESIGN_SECTION_HEADER}\` section remains present at the end of \`graphify-out/GRAPH_REPORT.md\` whenever the report is regenerated.
- **Manual Re-application Command:** If \`graph.html\` or \`GRAPH_REPORT.md\` is ever manually overwritten, run \`node graphify-out/build_graph_html.js\` (or \`graphify update .\`) to restore the full \`bynat\` brand theme and report instructions.
`;

function ensureReportDesignSection() {
  if (!fs.existsSync(REPORT_PATH)) {
    return;
  }
  const current = fs.readFileSync(REPORT_PATH, 'utf8');
  const idx = current.indexOf(REPORT_DESIGN_SECTION_HEADER);
  let baseText = idx !== -1 ? current.slice(0, idx).trimEnd() : current.trimEnd();
  const updated = `${baseText}\n\n${REPORT_DESIGN_SECTION}`;
  if (updated !== current) {
    fs.writeFileSync(REPORT_PATH, updated, 'utf8');
  }
}

function buildHtml() {
  if (!fs.existsSync(GRAPH_JSON_PATH)) {
    process.exit(1);
  }
  const graphData = JSON.parse(fs.readFileSync(GRAPH_JSON_PATH, 'utf8'));
  const savedLabels = readJsonIfExists(LABELS_JSON_PATH, {});
  const learningRaw = readJsonIfExists(LEARNING_JSON_PATH, {});
  const learningOverlay = (learningRaw && typeof learningRaw === 'object' && learningRaw.nodes)
    ? learningRaw.nodes
    : (learningRaw || {});

  const rawNodes = Array.isArray(graphData.nodes) ? graphData.nodes : [];
  const rawEdges = Array.isArray(graphData.links)
    ? graphData.links
    : (Array.isArray(graphData.edges) ? graphData.edges : []);
  const rawHyperedges = Array.isArray(graphData.hyperedges) ? graphData.hyperedges : [];

  const degreeMap = new Map();
  for (const n of rawNodes) {
    degreeMap.set(String(n.id), 0);
  }
  for (const e of rawEdges) {
    const u = String(e.source !== undefined ? e.source : e.from);
    const v = String(e.target !== undefined ? e.target : e.to);
    degreeMap.set(u, (degreeMap.get(u) || 0) + 1);
    degreeMap.set(v, (degreeMap.get(v) || 0) + 1);
  }

  let maxDeg = 1;
  for (const deg of degreeMap.values()) {
    if (deg > maxDeg) maxDeg = deg;
  }

  const sortedDegrees = Array.from(degreeMap.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);
  const godNodeIds = new Set(sortedDegrees.filter(([, d]) => d > 0).map(([id]) => id));

  const communityCounts = new Map();
  const communityNames = new Map();

  for (const [k, v] of Object.entries(savedLabels)) {
    const cid = Number(k);
    if (!Number.isNaN(cid) && v) {
      communityNames.set(cid, sanitizeLabel(v));
    }
  }

  for (const n of rawNodes) {
    const cid = typeof n.community === 'number' ? n.community : Number(n.community || 0);
    communityCounts.set(cid, (communityCounts.get(cid) || 0) + 1);
    if (!communityNames.has(cid) && n.community_name) {
      communityNames.set(cid, sanitizeLabel(n.community_name));
    }
  }

  const communitiesByConnectivity = Array.from(communityCounts.keys()).map(cid => {
    let totalDeg = 0;
    for (const n of rawNodes) {
      const nCid = typeof n.community === 'number' ? n.community : Number(n.community || 0);
      if (nCid === cid) {
        totalDeg += (degreeMap.get(String(n.id)) || 0);
      }
    }
    return { cid, count: communityCounts.get(cid) || 1, totalDeg };
  }).sort((a, b) => (b.totalDeg - a.totalDeg) || (b.count - a.count) || (a.cid - b.cid));

  const communityCenters = new Map();
  communitiesByConnectivity.forEach((item, idx) => {
    if (idx === 0) {
      communityCenters.set(item.cid, { x: 0, y: 0 });
      return;
    }
    const angle = idx * 2.399963229728653;
    const radius = 140 * Math.sqrt(idx);
    communityCenters.set(item.cid, {
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius
    });
  });

  const nodesByCommunity = new Map();
  for (const n of rawNodes) {
    const cid = typeof n.community === 'number' ? n.community : Number(n.community || 0);
    if (!nodesByCommunity.has(cid)) nodesByCommunity.set(cid, []);
    nodesByCommunity.get(cid).push(n);
  }

  const initialPos = new Map();
  for (const [cid, members] of nodesByCommunity.entries()) {
    const sortedMembers = members.slice().sort((a, b) => {
      return (degreeMap.get(String(b.id)) || 0) - (degreeMap.get(String(a.id)) || 0);
    });
    const center = communityCenters.get(cid) || { x: 0, y: 0 };
    sortedMembers.forEach((n, mIdx) => {
      if (mIdx === 0) {
        initialPos.set(String(n.id), { x: center.x, y: center.y });
      } else {
        const localAngle = mIdx * 2.399963229728653 + (cid * 0.5);
        const localRadius = 24 * Math.sqrt(mIdx);
        initialPos.set(String(n.id), {
          x: center.x + Math.cos(localAngle) * localRadius,
          y: center.y + Math.sin(localAngle) * localRadius
        });
      }
    });
  }

  const visNodes = rawNodes.map(n => {
    const nodeId = String(n.id);
    const cid = typeof n.community === 'number' ? n.community : Number(n.community || 0);
    const color = BYNAT_COMMUNITY_COLORS[((cid % BYNAT_COMMUNITY_COLORS.length) + BYNAT_COMMUNITY_COLORS.length) % BYNAT_COMMUNITY_COLORS.length];
    const label = sanitizeLabel(n.label || nodeId);
    const deg = degreeMap.get(nodeId) || 0;
    const isGod = godNodeIds.has(nodeId);
    const size = Number((10 + 32 * (deg / maxDeg)).toFixed(1));
    const fontSize = isGod ? 28 : (deg >= maxDeg * 0.08 ? 20 : 0);
    const commName = communityNames.get(cid) || sanitizeLabel(n.community_name || `Community ${cid}`);
    const sourceFile = sanitizeLabel(n.source_file || '');
    const sourceLoc = sanitizeLabel(n.source_location || '');
    const pos = initialPos.get(nodeId) || { x: 0, y: 0 };

    const nodeObj = {
      id: nodeId,
      label: label,
      x: Number(pos.x.toFixed(1)),
      y: Number(pos.y.toFixed(1)),
      color: {
        background: color,
        border: isGod ? '#FFF1DC' : color,
        highlight: { background: '#FFF1DC', border: '#F9442A' },
        hover: { background: color, border: '#FFF1DC' }
      },
      borderWidth: isGod ? 3 : 1.5,
      size: size,
      font: {
        size: fontSize,
        color: '#FFF1DC',
        face: 'Plus Jakarta Sans',
        strokeWidth: fontSize > 0 ? 4 : 0,
        strokeColor: '#0B1324'
      },
      title: escapeHtml(label),
      community: cid,
      community_name: commName,
      source_file: sourceFile,
      source_location: sourceLoc,
      file_type: sanitizeLabel(n.file_type || 'code'),
      degree: deg,
      is_god: isGod
    };

    const entry = learningOverlay && learningOverlay[nodeId];
    if (entry && typeof entry === 'object') {
      const status = sanitizeLabel(entry.status || '');
      const stale = Boolean(entry.stale);
      nodeObj.learning_status = status;
      nodeObj.learning_stale = stale;
      let ring = RING_COLORS[status];
      if (ring) {
        if (stale) {
          ring = '#8FA4C7';
          nodeObj.shapeProperties = { borderDashes: [4, 4] };
        }
        nodeObj.borderWidth = 3;
        nodeObj.color = {
          background: color,
          border: ring,
          highlight: { background: '#FFF1DC', border: '#F9442A' },
          hover: { background: color, border: ring }
        };
      }
    }

    return nodeObj;
  });

  const visEdges = rawEdges.map(e => {
    const confidence = sanitizeLabel(e.confidence || 'EXTRACTED');
    const relation = sanitizeLabel(e.relation || '');
    const fromId = String(e._src !== undefined ? e._src : (e.source !== undefined ? e.source : e.from));
    const toId = String(e._tgt !== undefined ? e._tgt : (e.target !== undefined ? e.target : e.to));
    const isExtracted = confidence === 'EXTRACTED';
    return {
      from: fromId,
      to: toId,
      label: relation,
      title: escapeHtml(`${relation} [${confidence}]`),
      dashes: !isExtracted,
      width: isExtracted ? 1.8 : 1.1,
      color: {
        color: isExtracted ? '#4B679B' : '#F9442A',
        highlight: '#F9442A',
        hover: '#FFF1DC',
        opacity: isExtracted ? 0.58 : 0.45
      },
      confidence: confidence
    };
  });

  const sortedCids = Array.from(communityCounts.keys()).sort((a, b) => a - b);
  const legendData = sortedCids.map(cid => {
    const color = BYNAT_COMMUNITY_COLORS[((cid % BYNAT_COMMUNITY_COLORS.length) + BYNAT_COMMUNITY_COLORS.length) % BYNAT_COMMUNITY_COLORS.length];
    const lbl = escapeHtml(communityNames.get(cid) || `Community ${cid}`);
    const count = communityCounts.get(cid) || 0;
    return { cid, color, label: lbl, count };
  });

  const faviconDataUri = `data:image/svg+xml;utf8,${encodeURIComponent(FAVICON_SVG)}`;
  const statsText = `${visNodes.length} nodes &middot; ${visEdges.length} edges &middot; ${sortedCids.length} communities`;

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>bynat · Knowledge Graph (graphify-out/graph.html)</title>
<link rel="icon" type="image/svg+xml" href="${faviconDataUri}">
<script src="https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"
        integrity="sha384-Ux6phic9PEHJ38YtrijhkzyJ8yQlH8i/+buBR8s3mAZOJrP1gwyvAcIYl3GWtpX1"
        crossorigin="anonymous"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bynat-navy-deep: #0B1324;
    --bynat-navy: #14213D;
    --bynat-navy-panel: #101B33;
    --bynat-navy-elevated: #182747;
    --bynat-navy-hover: #1F3259;
    --bynat-navy-border: #243863;
    --bynat-vermilion: #F9442A;
    --bynat-vermilion-hover: #FF5D45;
    --bynat-vermilion-soft: rgba(249, 68, 42, 0.16);
    --bynat-cream: #FFF1DC;
    --bynat-cream-muted: #DFD0BA;
    --bynat-slate: #8FA4C7;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bynat-navy-deep);
    color: var(--bynat-cream);
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    display: flex;
    height: 100vh;
    overflow: hidden;
  }
  #graph-stage {
    flex: 1;
    width: 100%;
    height: 100vh;
    position: relative;
    display: flex;
    overflow: hidden;
    background:
      radial-gradient(circle at 50% 48%, rgba(249, 68, 42, 0.06) 0%, rgba(20, 33, 61, 0.92) 46%, #0B1324 100%);
  }
  #graph-stage::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image: radial-gradient(rgba(255, 241, 220, 0.07) 1px, transparent 1px);
    background-size: 26px 26px;
    pointer-events: none;
    z-index: 0;
  }
  #graph {
    flex: 1;
    width: 100%;
    height: 100%;
    position: relative;
    z-index: 1;
  }
  #canvas-toolbar {
    position: absolute;
    left: 18px;
    bottom: 18px;
    z-index: 5;
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(16, 27, 51, 0.88);
    backdrop-filter: blur(8px);
    border: 1px solid var(--bynat-navy-border);
    border-radius: 14px;
    padding: 6px 10px;
    box-shadow: 0 10px 28px rgba(5, 10, 20, 0.55);
  }
  .toolbar-btn {
    background: var(--bynat-navy-elevated);
    color: var(--bynat-cream);
    border: 1px solid var(--bynat-navy-border);
    border-radius: 10px;
    padding: 5px 10px;
    font-size: 11px;
    font-weight: 600;
    font-family: inherit;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .toolbar-btn:hover {
    background: var(--bynat-vermilion);
    border-color: var(--bynat-vermilion);
    color: var(--bynat-cream);
  }
  #sidebar {
    width: 350px;
    background: var(--bynat-navy-panel);
    border-left: 1px solid var(--bynat-navy-border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-shadow: -10px 0 36px rgba(5, 10, 20, 0.65);
    z-index: 10;
  }
  #brand-header {
    padding: 16px 18px 14px 18px;
    border-bottom: 1px solid var(--bynat-navy-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    background: linear-gradient(180deg, #162544 0%, #14213D 100%);
  }
  .brand-logo {
    height: 34px;
    width: auto;
    display: block;
    flex-shrink: 0;
  }
  .brand-badge {
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    padding: 4px 10px;
    border-radius: 999px;
    background: var(--bynat-vermilion-soft);
    color: var(--bynat-cream);
    border: 1px solid rgba(249, 68, 42, 0.55);
    white-space: nowrap;
  }
  #search-wrap {
    padding: 14px 16px;
    border-bottom: 1px solid var(--bynat-navy-border);
    background: rgba(20, 33, 61, 0.55);
  }
  #search {
    width: 100%;
    background: var(--bynat-navy-elevated);
    border: 1.5px solid var(--bynat-navy-border);
    color: var(--bynat-cream);
    padding: 10px 13px;
    border-radius: 12px;
    font-size: 13px;
    font-family: inherit;
    outline: none;
    transition: all 0.15s ease;
  }
  #search::placeholder {
    color: var(--bynat-slate);
  }
  #search:focus {
    border-color: var(--bynat-vermilion);
    box-shadow: 0 0 0 3px var(--bynat-vermilion-soft);
  }
  #search-results {
    max-height: 180px;
    overflow-y: auto;
    padding: 6px 16px;
    border-bottom: 1px solid var(--bynat-navy-border);
    background: var(--bynat-navy);
    display: none;
  }
  .search-item {
    padding: 7px 10px;
    margin: 2px 0;
    cursor: pointer;
    border-radius: 9px;
    font-size: 12px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: var(--bynat-cream-muted);
    transition: background 0.12s ease, transform 0.1s ease;
  }
  .search-item:hover {
    background: var(--bynat-navy-hover);
    color: var(--bynat-cream);
    transform: translateX(2px);
  }
  #info-panel {
    padding: 16px;
    border-bottom: 1px solid var(--bynat-navy-border);
    min-height: 155px;
    background: var(--bynat-navy);
  }
  #info-panel h3 {
    font-size: 11px;
    color: var(--bynat-slate);
    margin-bottom: 10px;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  #info-panel h3::after {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--bynat-vermilion);
    box-shadow: 0 0 8px var(--bynat-vermilion);
  }
  #info-content {
    font-size: 12.5px;
    color: var(--bynat-cream-muted);
    line-height: 1.55;
  }
  #info-content .field {
    margin-bottom: 6px;
  }
  #info-content .node-title-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 8px;
  }
  #info-content .field b {
    color: var(--bynat-cream);
    font-size: 15px;
    font-weight: 700;
    word-break: break-word;
  }
  .god-badge {
    font-size: 9.5px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 2px 7px;
    border-radius: 999px;
    background: var(--bynat-vermilion);
    color: var(--bynat-cream);
  }
  .meta-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    margin-bottom: 8px;
  }
  .meta-pill {
    background: var(--bynat-navy-elevated);
    border: 1px solid var(--bynat-navy-border);
    border-radius: 10px;
    padding: 5px 8px;
    font-size: 11px;
  }
  .meta-pill .k {
    color: var(--bynat-slate);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    display: block;
  }
  .meta-pill .v {
    color: var(--bynat-cream);
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
  }
  .source-box {
    background: var(--bynat-navy-deep);
    border: 1px solid var(--bynat-navy-border);
    border-radius: 10px;
    padding: 6px 9px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--bynat-cream-muted);
    word-break: break-all;
    margin-bottom: 6px;
  }
  #info-content .empty {
    color: var(--bynat-slate);
    font-style: italic;
  }
  .neighbor-link {
    display: block;
    padding: 6px 9px;
    margin: 4px 0;
    border-radius: 9px;
    cursor: pointer;
    font-size: 12px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    border-left: 3.5px solid var(--bynat-vermilion);
    background: var(--bynat-navy-elevated);
    color: var(--bynat-cream-muted);
    transition: background 0.12s ease, transform 0.1s ease;
  }
  .neighbor-link:hover {
    background: var(--bynat-navy-hover);
    color: var(--bynat-cream);
    transform: translateX(3px);
  }
  #neighbors-list {
    max-height: 155px;
    overflow-y: auto;
    margin-top: 6px;
  }
  #legend-wrap {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
  }
  #legend-wrap h3 {
    font-size: 11px;
    color: var(--bynat-slate);
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    font-weight: 800;
  }
  .legend-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    cursor: pointer;
    border-radius: 10px;
    font-size: 12px;
    color: var(--bynat-cream-muted);
    transition: background 0.12s ease;
  }
  .legend-item:hover {
    background: var(--bynat-navy-elevated);
    color: var(--bynat-cream);
  }
  .legend-item.dimmed {
    opacity: 0.3;
  }
  .legend-dot {
    width: 11px;
    height: 11px;
    border-radius: 50%;
    flex-shrink: 0;
    box-shadow: 0 0 6px rgba(0, 0, 0, 0.45);
  }
  .legend-label {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .legend-count {
    color: var(--bynat-slate);
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
  }
  #stats {
    padding: 12px 16px;
    border-top: 1px solid var(--bynat-navy-border);
    font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
    color: var(--bynat-cream-muted);
    background: var(--bynat-navy-deep);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  #stats::before {
    content: 'bynat';
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 800;
    font-size: 10px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--bynat-vermilion);
    background: var(--bynat-vermilion-soft);
    padding: 2px 7px;
    border-radius: 999px;
  }
  #legend-controls {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 10px;
    padding: 4px 2px;
  }
  #legend-controls label {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
    color: var(--bynat-cream-muted);
    user-select: none;
  }
  #legend-controls label:hover {
    color: var(--bynat-cream);
  }
  .legend-cb, #select-all-cb {
    appearance: none;
    -webkit-appearance: none;
    width: 15px;
    height: 15px;
    border: 1.5px solid var(--bynat-navy-border);
    border-radius: 5px;
    background: var(--bynat-navy-deep);
    cursor: pointer;
    position: relative;
    flex-shrink: 0;
    transition: all 0.15s ease;
  }
  .legend-cb:checked, #select-all-cb:checked {
    background: var(--bynat-vermilion);
    border-color: var(--bynat-vermilion);
  }
  .legend-cb:checked::after, #select-all-cb:checked::after {
    content: '';
    position: absolute;
    left: 4.5px;
    top: 1.5px;
    width: 3.5px;
    height: 7px;
    border: solid var(--bynat-cream);
    border-width: 0 2px 2px 0;
    transform: rotate(45deg);
  }
  #select-all-cb:indeterminate {
    background: var(--bynat-vermilion);
    border-color: var(--bynat-vermilion);
  }
  #select-all-cb:indeterminate::after {
    content: '';
    position: absolute;
    left: 3px;
    top: 5.5px;
    width: 7px;
    height: 2px;
    background: var(--bynat-cream);
    border: none;
    transform: none;
  }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--bynat-navy-border); border-radius: 999px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--bynat-vermilion); }
</style>
</head>
<body>
<div id="graph-stage">
  <div id="graph"></div>
  <div id="canvas-toolbar">
    <button type="button" class="toolbar-btn" id="reset-view-btn">Reset View</button>
    <button type="button" class="toolbar-btn" id="toggle-physics-btn">Enable Physics</button>
  </div>
</div>
<div id="sidebar">
  <div id="brand-header">
    ${BRAND_LOGO_DARK_SVG}
    <span class="brand-badge">Knowledge Graph</span>
  </div>
  <div id="search-wrap">
    <input id="search" type="text" placeholder="Search bynat symbols, modules, docs..." autocomplete="off">
    <div id="search-results"></div>
  </div>
  <div id="info-panel">
    <h3>Node Inspector</h3>
    <div id="info-content"><span class="empty">Select any node on the canvas to inspect its module, community, and connections</span></div>
  </div>
  <div id="legend-wrap">
    <h3>Communities (${sortedCids.length})</h3>
    <div id="legend-controls">
      <label><input type="checkbox" id="select-all-cb" checked onchange="toggleAllCommunities(!this.checked)">Select All Communities</label>
    </div>
    <div id="legend"></div>
  </div>
  <div id="stats"><span>${statsText}</span></div>
</div>
<script>
const RAW_NODES = ${jsSafeJson(visNodes)};
const RAW_EDGES = ${jsSafeJson(visEdges)};
const LEGEND = ${jsSafeJson(legendData)};
const hyperedges = ${jsSafeJson(rawHyperedges)};

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

const nodesDS = new vis.DataSet(RAW_NODES.map(n => {
  const item = {
    id: n.id,
    label: n.label,
    x: n.x,
    y: n.y,
    color: n.color,
    borderWidth: n.borderWidth,
    size: n.size,
    font: n.font,
    title: n.title,
    _community: n.community,
    _community_name: n.community_name,
    _source_file: n.source_file,
    _source_location: n.source_location,
    _file_type: n.file_type,
    _degree: n.degree,
    _is_god: n.is_god
  };
  if (n.shapeProperties) item.shapeProperties = n.shapeProperties;
  return item;
}));

const edgesDS = new vis.DataSet(RAW_EDGES.map((e, i) => ({
  id: i,
  from: e.from,
  to: e.to,
  label: '',
  title: e.title,
  dashes: e.dashes,
  width: e.width,
  color: e.color,
  arrows: { to: { enabled: true, scaleFactor: 0.48 } }
})));

const container = document.getElementById('graph');
const network = new vis.Network(container, { nodes: nodesDS, edges: edgesDS }, {
  layout: {
    improvedLayout: false
  },
  physics: {
    enabled: false,
    solver: 'barnesHut',
    barnesHut: {
      gravitationalConstant: -3500,
      centralGravity: 0.25,
      springLength: 110,
      springConstant: 0.04,
      damping: 0.35,
      avoidOverlap: 0.5
    },
    stabilization: false
  },
  interaction: {
    hover: true,
    tooltipDelay: 90,
    hideEdgesOnDrag: true,
    navigationButtons: false,
    keyboard: false
  },
  nodes: { shape: 'dot', borderWidth: 1.5 },
  edges: { smooth: { type: 'continuous', roundness: 0.18 }, selectionWidth: 2.8 }
});

network.fit({ animation: false });

let physicsEnabled = false;
const togglePhysicsBtn = document.getElementById('toggle-physics-btn');
if (togglePhysicsBtn) {
  togglePhysicsBtn.addEventListener('click', () => {
    physicsEnabled = !physicsEnabled;
    network.setOptions({ physics: { enabled: physicsEnabled } });
    togglePhysicsBtn.textContent = physicsEnabled ? 'Freeze Layout' : 'Enable Physics';
  });
}

const resetViewBtn = document.getElementById('reset-view-btn');
if (resetViewBtn) {
  resetViewBtn.addEventListener('click', () => {
    network.fit({ animation: { duration: 350, easingFunction: 'easeInOutQuad' } });
  });
}

function showInfo(nodeId) {
  const n = nodesDS.get(nodeId);
  if (!n) return;
  const neighborIds = network.getConnectedNodes(nodeId);
  const neighborItems = neighborIds.map(nid => {
    const nb = nodesDS.get(nid);
    const color = nb ? nb.color.background : '#F9442A';
    return \`<span class="neighbor-link" style="border-left-color:\${esc(color)}" data-nid="\${esc(nid)}">\${esc(nb ? nb.label : nid)}</span>\`;
  }).join('');
  const sourceDisplay = n._source_file
    ? (n._source_location ? \`\${n._source_file}:\${n._source_location}\` : n._source_file)
    : '-';
  document.getElementById('info-content').innerHTML = \`
    <div class="field node-title-row">
      <b>\${esc(n.label)}</b>
      \${n._is_god ? '<span class="god-badge">God Node</span>' : ''}
    </div>
    <div class="meta-grid">
      <div class="meta-pill"><span class="k">Type</span><span class="v">\${esc(n._file_type || 'unknown')}</span></div>
      <div class="meta-pill"><span class="k">Degree</span><span class="v">\${n._degree} edges</span></div>
    </div>
    <div class="field">Community: <strong style="color:#FFF1DC">\${esc(n._community_name)}</strong></div>
    <div class="source-box">\${esc(sourceDisplay)}</div>
    \${neighborIds.length ? \`<div class="field" style="margin-top:8px;color:#8FA4C7;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em">Connected Nodes (\${neighborIds.length})</div><div id="neighbors-list">\${neighborItems}</div>\` : ''}
  \`;
}

function focusNode(nodeId) {
  network.focus(nodeId, { scale: 1.4, animation: true });
  network.selectNodes([nodeId]);
  showInfo(nodeId);
}

document.addEventListener('click', e => {
  const el = e.target.closest('.neighbor-link');
  if (el && el.dataset.nid !== undefined) focusNode(el.dataset.nid);
});

let hoveredNodeId = null;
network.on('hoverNode', params => {
  hoveredNodeId = params.node;
  container.style.cursor = 'pointer';
});
network.on('blurNode', () => {
  hoveredNodeId = null;
  container.style.cursor = 'default';
});
container.addEventListener('click', () => {
  if (hoveredNodeId !== null) {
    showInfo(hoveredNodeId);
    network.selectNodes([hoveredNodeId]);
  }
});
network.on('click', params => {
  if (params.nodes.length > 0) {
    showInfo(params.nodes[0]);
  } else if (hoveredNodeId === null) {
    document.getElementById('info-content').innerHTML = '<span class="empty">Select any node on the canvas to inspect its module, community, and connections</span>';
  }
});

const searchInput = document.getElementById('search');
const searchResults = document.getElementById('search-results');
searchInput.addEventListener('input', () => {
  const q = searchInput.value.toLowerCase().trim();
  searchResults.innerHTML = '';
  if (!q) { searchResults.style.display = 'none'; return; }
  const matches = RAW_NODES.filter(n =>
    n.label.toLowerCase().includes(q) ||
    (n.source_file && n.source_file.toLowerCase().includes(q)) ||
    (n.community_name && n.community_name.toLowerCase().includes(q))
  ).slice(0, 24);
  if (!matches.length) { searchResults.style.display = 'none'; return; }
  searchResults.style.display = 'block';
  matches.forEach(n => {
    const el = document.createElement('div');
    el.className = 'search-item';
    el.textContent = n.source_file ? \`\${n.label} · \${n.source_file}\` : n.label;
    el.style.borderLeft = \`3px solid \${n.color.background}\`;
    el.style.paddingLeft = '8px';
    el.onclick = () => {
      network.focus(n.id, { scale: 1.5, animation: true });
      network.selectNodes([n.id]);
      showInfo(n.id);
      searchResults.style.display = 'none';
      searchInput.value = '';
    };
    searchResults.appendChild(el);
  });
});
document.addEventListener('click', e => {
  if (!searchResults.contains(e.target) && e.target !== searchInput)
    searchResults.style.display = 'none';
});

const hiddenCommunities = new Set();
const selectAllCb = document.getElementById('select-all-cb');

function updateSelectAllState() {
  const total = LEGEND.length;
  const hidden = hiddenCommunities.size;
  selectAllCb.checked = hidden === 0;
  selectAllCb.indeterminate = hidden > 0 && hidden < total;
}

function toggleAllCommunities(hide) {
  document.querySelectorAll('.legend-item').forEach(item => {
    hide ? item.classList.add('dimmed') : item.classList.remove('dimmed');
  });
  document.querySelectorAll('.legend-cb').forEach(cb => {
    cb.checked = !hide;
  });
  LEGEND.forEach(c => {
    if (hide) hiddenCommunities.add(c.cid); else hiddenCommunities.delete(c.cid);
  });
  const updates = RAW_NODES.map(n => ({ id: n.id, hidden: hide }));
  nodesDS.update(updates);
  updateSelectAllState();
}

const legendEl = document.getElementById('legend');
LEGEND.forEach(c => {
  const item = document.createElement('div');
  item.className = 'legend-item';
  const cb = document.createElement('input');
  cb.type = 'checkbox';
  cb.className = 'legend-cb';
  cb.checked = true;
  cb.addEventListener('change', (e) => {
    e.stopPropagation();
    if (cb.checked) {
      hiddenCommunities.delete(c.cid);
      item.classList.remove('dimmed');
    } else {
      hiddenCommunities.add(c.cid);
      item.classList.add('dimmed');
    }
    const updates = RAW_NODES
      .filter(n => n.community === c.cid)
      .map(n => ({ id: n.id, hidden: !cb.checked }));
    nodesDS.update(updates);
    updateSelectAllState();
  });
  item.innerHTML = \`<div class="legend-dot" style="background:\${c.color}"></div>
    <span class="legend-label">\${c.label}</span>
    <span class="legend-count">\${c.count}</span>\`;
  item.prepend(cb);
  item.onclick = (e) => {
    if (e.target === cb) return;
    cb.checked = !cb.checked;
    cb.dispatchEvent(new Event('change'));
  };
  legendEl.appendChild(item);
});

function convexHull(pts) {
  const p = pts.slice().sort((a, b) => (a.x - b.x) || (a.y - b.y));
  if (p.length < 3) return p;
  const cross = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
  const build = seq => {
    const out = [];
    for (const q of seq) {
      while (out.length >= 2 && cross(out[out.length - 2], out[out.length - 1], q) <= 0) out.pop();
      out.push(q);
    }
    out.pop();
    return out;
  };
  const hull = build(p).concat(build(p.slice().reverse()));
  return hull.length >= 3 ? hull : p;
}

network.on('afterDrawing', function(ctx) {
  hyperedges.forEach(h => {
    const positions = (h.nodes || [])
      .map(nid => network.getPositions([nid])[nid])
      .filter(p => p !== undefined);
    if (positions.length < 2) return;
    ctx.save();
    ctx.globalAlpha = 0.14;
    ctx.fillStyle = '#F9442A';
    ctx.strokeStyle = '#F9442A';
    ctx.lineWidth = 2;
    ctx.beginPath();
    const cx = positions.reduce((s, p) => s + p.x, 0) / positions.length;
    const cy = positions.reduce((s, p) => s + p.y, 0) / positions.length;
    const hull = convexHull(positions);
    const expanded = hull.map(p => ({
      x: cx + (p.x - cx) * 1.15,
      y: cy + (p.y - cy) * 1.15
    }));
    ctx.moveTo(expanded[0].x, expanded[0].y);
    expanded.slice(1).forEach(p => ctx.lineTo(p.x, p.y));
    ctx.closePath();
    ctx.fill();
    ctx.globalAlpha = 0.45;
    ctx.stroke();
    ctx.globalAlpha = 0.9;
    ctx.fillStyle = '#FFF1DC';
    ctx.font = 'bold 11px Plus Jakarta Sans, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(h.label || '', cx, cy - 5);
    ctx.restore();
  });
});
</script>
</body>
</html>`;

  fs.writeFileSync(HTML_TMP_PATH, html, 'utf8');
  fs.renameSync(HTML_TMP_PATH, HTML_OUT_PATH);
  ensureReportDesignSection();
}

buildHtml();
