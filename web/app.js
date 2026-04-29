const canvas = document.getElementById("graph-canvas");
const ctx = canvas.getContext("2d");

const topStats = document.getElementById("top-stats");
const statsBox = document.getElementById("stats");
const detailBox = document.getElementById("detail-box");
const selectionHint = document.getElementById("selection-hint");
const eventList = document.getElementById("event-list");
const eventCount = document.getElementById("event-count");
const sourceList = document.getElementById("source-list");
const sourceCount = document.getElementById("source-count");
const personFocusButtons = document.getElementById("person-focus-buttons");

const typeColors = {
  Person: "#d96c3a",
  Organization: "#2f7f73",
  Place: "#5684d6",
  Device: "#7959c4",
  Concept: "#d4a027",
  Work: "#b25f90",
  EventNode: "#243746",
};

const PERSON_FOCUS_ORDER = [
  "全部",
  "Alan Turing",
  "Joan Clarke",
  "Alonzo Church",
  "Max Newman",
  "John von Neumann",
];

const graphState = {
  graph: null,
  nodes: [],
  edges: [],
  selectedNodeId: "",
  selectedEdgeId: "",
  focusNodeId: "",
  focusNeighborIds: [],
  activePersonLabel: "",
  animating: false,
  draggingNode: null,
  dragOffsetX: 0,
  dragOffsetY: 0,
  dragMoved: false,
};

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function formatScore(value) {
  return Number(value || 0).toFixed(2);
}

function parseJsonl(rawText) {
  return rawText
    .trim()
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

async function fetchJsonOrNull(url) {
  const response = await fetch(url);
  if (!response.ok) {
    return null;
  }
  return response.json();
}

function getCanvasSize() {
  const rect = canvas.getBoundingClientRect();
  return {
    width: rect.width || 860,
    height: rect.height || 520,
  };
}

function resizeCanvas() {
  const ratio = window.devicePixelRatio || 1;
  const size = getCanvasSize();
  canvas.width = size.width * ratio;
  canvas.height = size.height * ratio;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
}

function distance(a, b) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.sqrt(dx * dx + dy * dy);
}

function getNodeById(nodeId) {
  return graphState.nodes.find((node) => node.id === nodeId) || null;
}

function getPersonNodeByLabel(label) {
  return graphState.nodes.find((node) => node.type === "Person" && node.label === label) || null;
}

function collectNeighborIds(nodeId) {
  const ids = [];
  for (const edge of graphState.edges) {
    if (edge.source === nodeId) {
      ids.push(edge.target);
    } else if (edge.target === nodeId) {
      ids.push(edge.source);
    }
  }
  return [...new Set(ids)];
}

function selectView(viewName, updateHash = true) {
  for (const button of document.querySelectorAll(".tab-button")) {
    button.classList.toggle("active", button.dataset.view === viewName);
  }
  for (const panel of document.querySelectorAll(".view-panel")) {
    panel.classList.toggle("active", panel.dataset.panel === viewName);
  }
  if (updateHash) {
    window.history.replaceState(null, "", `#${viewName}`);
  }
  if (viewName === "graph") {
    resizeCanvas();
  }
}

function initTabs() {
  for (const button of document.querySelectorAll(".tab-button")) {
    button.addEventListener("click", () => selectView(button.dataset.view));
  }
}

function renderTopStats(report, graph) {
  const items = [
    `raw 文本 ${report.raw_text_count}`,
    `mention ${report.mention_count}`,
    `事件 ${graph.summary.event_count}`,
    `关系 ${graph.summary.relation_count}`,
  ];
  topStats.innerHTML = items.map((item) => `<span>${item}</span>`).join("");
}

function renderStats(summary) {
  statsBox.innerHTML = [
    `节点 ${summary.node_count}`,
    `边 ${summary.edge_count}`,
    `事件 ${summary.event_count}`,
    `关系 ${summary.relation_count}`,
  ]
    .map((item) => `<span>${item}</span>`)
    .join("");
}

function renderMethodBoxes() {
  document.getElementById("entity-method-list").innerHTML = `
    <div class="method-item"><strong>词典匹配</strong><p>把种子知识库里的标准名和别名拿来扫描句子。</p></div>
    <div class="method-item"><strong>正则匹配</strong><p>用简单格式规则抽时间、书名和机构名。</p></div>
    <div class="method-item"><strong>重叠处理</strong><p>同一位置优先保留更长、更明确的 mention。</p></div>
  `;
  document.getElementById("event-method-list").innerHTML = `
    <div class="method-item"><strong>触发词</strong><p>发表、学习、工作、参与等词会触发不同事件。</p></div>
    <div class="method-item"><strong>参与实体</strong><p>按人物、机构、作品、设备等类型分配事件角色。</p></div>
    <div class="method-item"><strong>保留证据</strong><p>事件记录会保留原句，方便回溯。</p></div>
  `;
  document.getElementById("relation-method-list").innerHTML = `
    <div class="method-item"><strong>事件驱动</strong><p>PublicationEvent 生成 published，EducationEvent 生成 studied_at。</p></div>
    <div class="method-item"><strong>句式补充</strong><p>“位于”等稳定句式直接生成 located_in。</p></div>
    <div class="method-item"><strong>证据跟随</strong><p>每条边都带着 text_id、句子编号和证据句。</p></div>
  `;
}

function highlightSentence(text, mentions) {
  const ordered = (mentions || []).slice().sort((a, b) => a.start - b.start);
  let cursor = 0;
  let html = "";
  for (const mention of ordered) {
    html += text.slice(cursor, mention.start);
    html += `<span class="mention-mark" title="${mention.entity_type} / ${mention.rule_note}">${text.slice(
      mention.start,
      mention.end
    )}</span>`;
    cursor = mention.end;
  }
  html += text.slice(cursor);
  return html;
}

function renderEntityExtractionCase(cases) {
  const box = document.getElementById("entity-extraction-case");
  const item = (cases || [])[0];
  if (!item) {
    box.innerHTML = "<p>没有可展示的实体抽取案例。</p>";
    return;
  }

  box.innerHTML = `
    <div class="card-head">
      <h3>${item.title}</h3>
      <span>${item.text_id} / 句子 ${item.sentence_id}</span>
    </div>
    <div class="raw-sentence">${highlightSentence(item.context, item.mentions)}</div>
    <div class="case-list">
      ${(item.mentions || [])
        .map(
          (mention) => `
            <div class="case-item">
              <h4>${mention.mention}</h4>
              <div class="case-meta">
                <span>${mention.entity_type}</span>
                <span>${mention.rule_note}</span>
                <span>位置 ${mention.start}-${mention.end}</span>
              </div>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function renderFormula(formula) {
  const box = document.getElementById("formula-box");
  box.innerHTML = `
    score = ${formula.alias_weight} * alias + ${formula.context_keyword_weight} * context + ${formula.type_prior_weight} * type
    <br>分数最高的候选实体会作为标准实体。
  `;
}

function renderDisambiguationCases(cases) {
  const box = document.getElementById("disambiguation-cases");
  box.innerHTML = "";

  for (const item of (cases || []).slice(0, 2)) {
    const card = document.createElement("article");
    card.className = "case-item";
    card.innerHTML = `
      <h4>${item.title}</h4>
      <p>${item.context}</p>
      <div class="case-meta">
        <span>最终选择：${item.selected_name}</span>
        <span>${item.text_id} / 句子 ${item.sentence_id}</span>
      </div>
      <div class="score-table">
        ${(item.candidates || [])
          .map(
            (candidate) => `
              <div class="score-row${candidate.entity_id === item.selected_entity_id ? " selected" : ""}">
                <strong>${candidate.canonical_name}</strong>
                <div class="score-values">
                  <span>alias ${formatScore(candidate.alias_score)}</span>
                  <span>context ${formatScore(candidate.context_keyword_score)}</span>
                  <span>type ${formatScore(candidate.type_prior_score)}</span>
                  <span>final ${formatScore(candidate.final_score)}</span>
                </div>
              </div>
            `
          )
          .join("")}
      </div>
      <button type="button" class="case-button" data-node-id="${item.selected_entity_id}">在图里看结果</button>
    `;
    card.querySelector("button").addEventListener("click", () => {
      selectView("graph");
      selectNode(item.selected_entity_id);
    });
    box.appendChild(card);
  }
}

function renderEventExtractionCase(cases) {
  const box = document.getElementById("event-extraction-case");
  const item = (cases || [])[0];
  if (!item) {
    box.innerHTML = "<p>没有可展示的事件抽取案例。</p>";
    return;
  }

  const participantText = (item.participants || [])
    .map((participant) => `${participant.role}: ${participant.name}`)
    .join(" / ");

  box.innerHTML = `
    <div class="card-head">
      <h3>${item.title}</h3>
      <span>${item.event_type}</span>
    </div>
    <div class="raw-sentence">${item.evidence}</div>
    <div class="flow-list">
      <div class="flow-row"><strong>1. 找触发词</strong><p>${item.trigger || "规则匹配"}</p></div>
      <div class="flow-row"><strong>2. 找参与实体</strong><p>${participantText || "无参与实体"}</p></div>
      <div class="flow-row selected"><strong>3. 形成事件记录</strong><p>${item.event_id} / ${item.event_type}</p></div>
    </div>
    <button type="button" class="case-button" id="event-case-button">在图里看这条事件</button>
  `;
  document.getElementById("event-case-button").addEventListener("click", () => {
    selectView("graph");
    selectNode(item.event_id);
  });
}

function renderRelationExtractionCase(cases) {
  const box = document.getElementById("relation-extraction-case");
  const item = (cases || [])[0];
  if (!item) {
    box.innerHTML = "<p>没有可展示的关系抽取案例。</p>";
    return;
  }

  box.innerHTML = `
    <div class="card-head">
      <h3>${item.title}</h3>
      <span>${item.method}</span>
    </div>
    <div class="raw-sentence">${item.evidence}</div>
    <div class="flow-list">
      <div class="flow-row"><strong>1. 头实体</strong><p>${item.head_name} (${item.head_type})</p></div>
      <div class="flow-row"><strong>2. 关系规则</strong><p>${item.relation}，触发词：${item.trigger || "事件类型"}</p></div>
      <div class="flow-row"><strong>3. 尾实体</strong><p>${item.tail_name} (${item.tail_type})</p></div>
      <div class="flow-row selected"><strong>4. 三元组</strong><p>${item.triple}</p></div>
    </div>
    <button type="button" class="case-button" id="relation-case-button">在图里看这条边</button>
  `;
  document.getElementById("relation-case-button").addEventListener("click", () => {
    selectView("graph");
    selectEdge(item.relation_id);
  });
}

function prepareGraph(graph) {
  const size = getCanvasSize();
  graphState.graph = graph;
  graphState.nodes = graph.nodes.map((node, index) => ({
    ...node,
    x: size.width * (0.18 + (index % 7) * 0.105),
    y: size.height * (0.18 + ((index * 3) % 8) * 0.09),
    vx: 0,
    vy: 0,
    radius: node.type === "EventNode" ? 10 : 8,
  }));

  graphState.edges = graph.edges.map((edge) => ({
    ...edge,
    sourceNode: graphState.nodes.find((node) => node.id === edge.source),
    targetNode: graphState.nodes.find((node) => node.id === edge.target),
  }));

  renderStats(graph.summary);
  renderPersonFocusButtons();
  renderEventCards(graph.events || []);

  if (!graphState.animating) {
    graphState.animating = true;
    requestAnimationFrame(tick);
  }
}

function renderPersonFocusButtons() {
  personFocusButtons.innerHTML = "";
  for (const label of PERSON_FOCUS_ORDER) {
    if (label !== "全部" && !getPersonNodeByLabel(label)) {
      continue;
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = `focus-button${graphState.activePersonLabel === label || (!graphState.activePersonLabel && label === "全部") ? " active" : ""}`;
    button.textContent = label;
    button.addEventListener("click", () => {
      if (label === "全部") {
        clearFocus();
      } else {
        focusOnPerson(label);
      }
    });
    personFocusButtons.appendChild(button);
  }
}

function clearFocus() {
  graphState.focusNodeId = "";
  graphState.focusNeighborIds = [];
  graphState.activePersonLabel = "";
  renderPersonFocusButtons();
}

function focusOnPerson(label) {
  const node = getPersonNodeByLabel(label);
  if (!node) {
    return;
  }
  graphState.focusNodeId = node.id;
  graphState.focusNeighborIds = collectNeighborIds(node.id);
  graphState.activePersonLabel = label;
  selectNode(node.id);
  renderPersonFocusButtons();
}

function renderEventCards(events) {
  eventCount.textContent = `${events.length} 条`;
  eventList.innerHTML = "";
  for (const event of events) {
    const card = document.createElement("article");
    card.className = "event-card";
    card.dataset.eventId = event.event_id;
    const participants = (event.participants || []).map((item) => item.name).join(" / ");
    card.innerHTML = `
      <h4>${event.event_type}</h4>
      <p>${event.text_id} · ${event.trigger || "规则匹配"}</p>
      <div class="evidence">${event.evidence}</div>
      <div class="tag-row"><span>${participants || "无参与实体"}</span></div>
    `;
    card.addEventListener("click", () => selectNode(event.event_id));
    eventList.appendChild(card);
  }
}

function renderSourceList(traceability) {
  const texts = traceability.texts || [];
  sourceCount.textContent = `${texts.length} 份`;
  sourceList.innerHTML = "";
  for (const item of texts.slice(0, 8)) {
    const card = document.createElement("article");
    card.className = "source-card";
    card.innerHTML = `
      <h4>${item.text_id}</h4>
      <p>${item.source_title || "公开资料整理"}</p>
      <div class="tag-row">
        <span>${item.mention_count} mention</span>
        <span>${item.event_count} 事件</span>
        <span>${item.relation_count} 关系</span>
      </div>
      ${item.source_url ? `<p><a href="${item.source_url}" target="_blank" rel="noreferrer">来源链接</a></p>` : ""}
    `;
    sourceList.appendChild(card);
  }
}

function tick() {
  if (!graphState.graph) {
    return;
  }

  const size = getCanvasSize();
  const centerX = size.width / 2;
  const centerY = size.height / 2;

  for (const node of graphState.nodes) {
    if (node === graphState.draggingNode) {
      continue;
    }
    node.vx += (centerX - node.x) * 0.0007;
    node.vy += (centerY - node.y) * 0.0007;
  }

  for (let i = 0; i < graphState.nodes.length; i += 1) {
    for (let j = i + 1; j < graphState.nodes.length; j += 1) {
      const a = graphState.nodes[i];
      const b = graphState.nodes[j];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.max(22, Math.sqrt(dx * dx + dy * dy));
      const force = 1050 / (dist * dist);
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      if (a !== graphState.draggingNode) {
        a.vx -= fx;
        a.vy -= fy;
      }
      if (b !== graphState.draggingNode) {
        b.vx += fx;
        b.vy += fy;
      }
    }
  }

  for (const edge of graphState.edges) {
    const dx = edge.targetNode.x - edge.sourceNode.x;
    const dy = edge.targetNode.y - edge.sourceNode.y;
    const dist = Math.max(30, Math.sqrt(dx * dx + dy * dy));
    const ideal = edge.kind === "event_participant" ? 88 : 122;
    const spring = (dist - ideal) * 0.0023;
    const fx = (dx / dist) * spring;
    const fy = (dy / dist) * spring;
    if (edge.sourceNode !== graphState.draggingNode) {
      edge.sourceNode.vx += fx;
      edge.sourceNode.vy += fy;
    }
    if (edge.targetNode !== graphState.draggingNode) {
      edge.targetNode.vx -= fx;
      edge.targetNode.vy -= fy;
    }
  }

  for (const node of graphState.nodes) {
    if (node === graphState.draggingNode) {
      continue;
    }
    node.vx *= 0.87;
    node.vy *= 0.87;
    node.x = clamp(node.x + node.vx, 30, size.width - 30);
    node.y = clamp(node.y + node.vy, 30, size.height - 30);
  }

  draw();
  requestAnimationFrame(tick);
}

function draw() {
  const size = getCanvasSize();
  const focusSet = new Set([graphState.focusNodeId, ...graphState.focusNeighborIds].filter(Boolean));
  const focusActive = Boolean(graphState.focusNodeId);
  const selectedNode = graphState.selectedNodeId;

  ctx.clearRect(0, 0, size.width, size.height);
  drawBackground(size.width, size.height);

  for (const edge of graphState.edges) {
    const selected = edge.id === graphState.selectedEdgeId;
    const relatedToSelectedNode =
      selectedNode && (edge.source === selectedNode || edge.target === selectedNode || edge.event_id === selectedNode);
    const inFocus = !focusActive || (focusSet.has(edge.source) && focusSet.has(edge.target));

    if (selected || relatedToSelectedNode) {
      ctx.strokeStyle = "rgba(217, 108, 58, 0.92)";
      ctx.lineWidth = selected ? 2.8 : 2;
    } else if (!inFocus || selectedNode) {
      ctx.strokeStyle = "rgba(34, 46, 55, 0.08)";
      ctx.lineWidth = 1;
    } else if (edge.kind === "event_participant") {
      ctx.strokeStyle = "rgba(36, 55, 70, 0.28)";
      ctx.lineWidth = 1.2;
    } else {
      ctx.strokeStyle = "rgba(75, 127, 208, 0.5)";
      ctx.lineWidth = 1.5;
    }

    ctx.beginPath();
    ctx.moveTo(edge.sourceNode.x, edge.sourceNode.y);
    ctx.lineTo(edge.targetNode.x, edge.targetNode.y);
    ctx.stroke();
  }

  for (const node of graphState.nodes) {
    const active = node.id === graphState.selectedNodeId;
    const related = graphState.focusNeighborIds.includes(node.id) || node.id === graphState.focusNodeId;
    const dimmedByFocus = focusActive && !related;
    const dimmedBySelection =
      selectedNode &&
      !active &&
      !graphState.edges.some((edge) => edge.source === selectedNode && edge.target === node.id || edge.target === selectedNode && edge.source === node.id);
    const color = typeColors[node.type] || "#60717d";

    ctx.save();
    ctx.globalAlpha = dimmedByFocus || dimmedBySelection ? 0.22 : 0.96;
    ctx.beginPath();
    ctx.fillStyle = color;
    ctx.arc(node.x, node.y, active ? node.radius + 3 : node.radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#1e2a33";
    ctx.font = active ? "600 13px sans-serif" : "12px sans-serif";
    ctx.fillText(node.label, node.x + 12, node.y + 4);
    ctx.restore();
  }
}

function drawBackground(width, height) {
  ctx.save();
  ctx.strokeStyle = "rgba(34, 46, 55, 0.05)";
  ctx.lineWidth = 1;
  for (let x = 40; x < width; x += 40) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }
  for (let y = 40; y < height; y += 40) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
  ctx.restore();
}

function findNodeAt(x, y) {
  for (let index = graphState.nodes.length - 1; index >= 0; index -= 1) {
    const node = graphState.nodes[index];
    if (distance({ x, y }, node) <= node.radius + 8) {
      return node;
    }
  }
  return null;
}

function pointToSegmentDistance(px, py, ax, ay, bx, by) {
  const abx = bx - ax;
  const aby = by - ay;
  const apx = px - ax;
  const apy = py - ay;
  const ab2 = abx * abx + aby * aby;
  const t = ab2 === 0 ? 0 : clamp((apx * abx + apy * aby) / ab2, 0, 1);
  const cx = ax + abx * t;
  const cy = ay + aby * t;
  return Math.sqrt((px - cx) ** 2 + (py - cy) ** 2);
}

function findEdgeAt(x, y) {
  for (const edge of graphState.edges) {
    const dist = pointToSegmentDistance(
      x,
      y,
      edge.sourceNode.x,
      edge.sourceNode.y,
      edge.targetNode.x,
      edge.targetNode.y
    );
    if (dist <= 6) {
      return edge;
    }
  }
  return null;
}

function selectNode(nodeId) {
  const node = getNodeById(nodeId);
  if (!node) {
    return;
  }
  graphState.selectedNodeId = nodeId;
  graphState.selectedEdgeId = "";
  selectionHint.textContent = "已选节点";
  updateDetailForNode(nodeId);
  updateActiveEventCard(node.type === "EventNode" ? node.id : "");
}

function selectEdge(edgeId) {
  const edge = graphState.edges.find((item) => item.id === edgeId);
  if (!edge) {
    return;
  }
  graphState.selectedNodeId = "";
  graphState.selectedEdgeId = edgeId;
  selectionHint.textContent = "已选关系";
  updateDetailForEdge(edgeId);
  updateActiveEventCard(edge.event_id || "");
}

function updateDetailForNode(nodeId) {
  const node = getNodeById(nodeId);
  if (!node) {
    return;
  }
  const relatedEdges = graphState.edges.filter(
    (edge) => edge.source === nodeId || edge.target === nodeId || edge.event_id === nodeId
  );
  const neighborItems = relatedEdges.slice(0, 8).map((edge) => {
    const other = edge.source === nodeId ? edge.targetNode : edge.sourceNode;
    return `<div class="mini-card"><strong>${edge.label}</strong><p>${other ? other.label : edge.targetNode.label}</p></div>`;
  });
  const evidenceItems = (node.evidence_samples || [])
    .slice(0, 3)
    .map(
      (item) => `
        <div class="detail-evidence-card">
          <strong>${item.text_id} / 句子 ${item.sentence_id}</strong>
          <p>${item.evidence}</p>
          ${item.source_url ? `<a class="source-link" href="${item.source_url}" target="_blank" rel="noreferrer">来源链接</a>` : ""}
        </div>
      `
    )
    .join("");

  detailBox.innerHTML = `
    <div class="title">${node.label}</div>
    <span class="meta">${node.type}</span>
    <p>${node.description || node.evidence || "暂无额外描述。"}</p>
    <p>直接连边：${relatedEdges.length} 条</p>
    <div class="case-list">${neighborItems.join("") || "<p>暂无相邻节点。</p>"}</div>
    ${evidenceItems ? `<div class="case-list">${evidenceItems}</div>` : ""}
  `;
}

function updateDetailForEdge(edgeId) {
  const edge = graphState.edges.find((item) => item.id === edgeId);
  if (!edge) {
    return;
  }
  detailBox.innerHTML = `
    <div class="title">${edge.sourceNode.label} -> ${edge.targetNode.label}</div>
    <span class="meta">${edge.label}</span>
    <p>边类型：${edge.kind}</p>
    <p>原文位置：${edge.text_id || "未记录"} / 句子 ${edge.sentence_id || "-"}</p>
    <div class="evidence">${edge.evidence || "暂无证据句。"}</div>
    ${edge.source_url ? `<a class="source-link" href="${edge.source_url}" target="_blank" rel="noreferrer">来源链接</a>` : ""}
  `;
}

function updateActiveEventCard(eventId) {
  for (const card of eventList.querySelectorAll(".event-card")) {
    card.classList.toggle("active", card.dataset.eventId === eventId);
  }
}

function canvasPoint(event) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  };
}

canvas.addEventListener("mousedown", (event) => {
  const point = canvasPoint(event);
  const node = findNodeAt(point.x, point.y);
  if (!node) {
    return;
  }
  graphState.draggingNode = node;
  graphState.dragOffsetX = point.x - node.x;
  graphState.dragOffsetY = point.y - node.y;
  graphState.dragMoved = false;
  node.vx = 0;
  node.vy = 0;
  canvas.classList.add("dragging");
});

canvas.addEventListener("mousemove", (event) => {
  if (!graphState.draggingNode) {
    return;
  }
  const point = canvasPoint(event);
  const size = getCanvasSize();
  const node = graphState.draggingNode;
  node.x = clamp(point.x - graphState.dragOffsetX, 30, size.width - 30);
  node.y = clamp(point.y - graphState.dragOffsetY, 30, size.height - 30);
  node.vx = 0;
  node.vy = 0;
  graphState.dragMoved = true;
});

function releaseDrag() {
  graphState.draggingNode = null;
  canvas.classList.remove("dragging");
}

canvas.addEventListener("mouseup", releaseDrag);
canvas.addEventListener("mouseleave", releaseDrag);

canvas.addEventListener("click", (event) => {
  if (graphState.dragMoved) {
    graphState.dragMoved = false;
    return;
  }
  const point = canvasPoint(event);
  const node = findNodeAt(point.x, point.y);
  if (node) {
    if (node.type === "Person") {
      focusOnPerson(node.label);
    } else {
      selectNode(node.id);
    }
    return;
  }
  const edge = findEdgeAt(point.x, point.y);
  if (edge) {
    selectEdge(edge.id);
  }
});

window.addEventListener("resize", resizeCanvas);

async function boot() {
  initTabs();
  const initialView = window.location.hash.replace("#", "");
  if (["entity", "disambiguation", "event", "relation", "graph"].includes(initialView)) {
    selectView(initialView, false);
  }
  renderMethodBoxes();
  resizeCanvas();

  const [
    graphResponse,
    reportResponse,
    traceResponse,
    explainResponse,
    evaluation,
    mentionsResponse,
    linkedResponse,
  ] = await Promise.all([
    fetch("/data/output/graph.json"),
    fetch("/data/output/report.json"),
    fetch("/data/output/traceability.json"),
    fetch("/data/output/explainability.json"),
    fetchJsonOrNull("/data/output/evaluation_summary.json"),
    fetch("/data/intermediate/mentions.jsonl"),
    fetch("/data/intermediate/linked_entities.jsonl"),
  ]);

  const graph = await graphResponse.json();
  const report = await reportResponse.json();
  const traceability = await traceResponse.json();
  const explainability = await explainResponse.json();
  parseJsonl(await mentionsResponse.text());
  parseJsonl(await linkedResponse.text());

  renderTopStats(report, graph);
  renderFormula(explainability.scoring_formula || {});
  renderEntityExtractionCase(explainability.entity_extraction_cases || []);
  renderDisambiguationCases(explainability.disambiguation_cases || []);
  renderEventExtractionCase(explainability.event_extraction_cases || explainability.event_relation_cases || []);
  renderRelationExtractionCase(explainability.relation_extraction_cases || []);
  renderSourceList(traceability);
  prepareGraph(graph);

  if (evaluation) {
    topStats.insertAdjacentHTML(
      "beforeend",
      `<span>人工检查 ${Math.round((evaluation.entity_linking_accuracy || 0) * 100)}%</span>`
    );
  }
}

boot().catch((error) => {
  topStats.innerHTML = `<span>加载失败：${error.message}</span>`;
  detailBox.innerHTML = `<p>加载失败：${error.message}</p>`;
});
