const canvas = document.getElementById("graph-canvas");
const ctx = canvas.getContext("2d");
const detailBox = document.getElementById("detail-box");
const eventList = document.getElementById("event-list");
const statsBox = document.getElementById("stats");
const eventCount = document.getElementById("event-count");
const summaryBox = document.getElementById("summary-box");
const sourceList = document.getElementById("source-list");
const sourceCount = document.getElementById("source-count");

const typeColors = {
  Person: "#d96c3a",
  Organization: "#2f7f73",
  Place: "#5684d6",
  Device: "#7959c4",
  Concept: "#d4a027",
  Work: "#b25f90",
  Event: "#bb4d4d",
  EventNode: "#243746",
};

const graphState = {
  graph: null,
  nodes: [],
  edges: [],
  selectedNodeId: "",
  selectedEdgeId: "",
  hoveredNodeId: "",
  animating: false,
  report: null,
  traceability: null,
};

function resizeCanvas() {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * ratio;
  canvas.height = rect.height * ratio;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
}

function distance(a, b) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.sqrt(dx * dx + dy * dy);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function prepareGraph(graph) {
  const width = canvas.getBoundingClientRect().width;
  const height = canvas.getBoundingClientRect().height;

  graphState.graph = graph;
  graphState.nodes = graph.nodes.map((node, index) => ({
    ...node,
    x: width * (0.2 + (index % 7) * 0.1),
    y: height * (0.2 + ((index * 3) % 9) * 0.08),
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
  renderEventCards(graph.events);
  if (!graphState.animating) {
    graphState.animating = true;
    requestAnimationFrame(tick);
  }
}

function renderStats(summary) {
  statsBox.innerHTML = "";
  const stats = [
    `节点 ${summary.node_count}`,
    `边 ${summary.edge_count}`,
    `事件 ${summary.event_count}`,
    `关系 ${summary.relation_count}`,
  ];
  for (const item of stats) {
    const tag = document.createElement("span");
    tag.textContent = item;
    statsBox.appendChild(tag);
  }
}

function renderSummary(report) {
  graphState.report = report;
  const relationItems = Object.entries(report.relation_type_counts || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4);
  const textItems = (report.text_statistics || [])
    .slice()
    .sort((a, b) => b.relation_count - a.relation_count || b.event_count - a.event_count)
    .slice(0, 3);

  summaryBox.innerHTML = `
    <div class="summary-grid">
      <div class="summary-item"><span>原始文本</span><strong>${report.raw_text_count}</strong></div>
      <div class="summary-item"><span>抽到实体</span><strong>${report.linked_count}</strong></div>
      <div class="summary-item"><span>关系条数</span><strong>${report.relation_count}</strong></div>
      <div class="summary-item"><span>事件条数</span><strong>${report.event_count}</strong></div>
    </div>
    <p>展示链路：原始文本 -> 实体抽取 -> 实体消歧 -> 事件抽取 -> 关系抽取 -> 图谱展示。</p>
    <div>
      <p>出现最多的关系：</p>
      <ul class="summary-list">
        ${relationItems.map(([name, count]) => `<li><span>${name}</span><strong>${count}</strong></li>`).join("")}
      </ul>
    </div>
    <div>
      <p>信息量较多的原文片段：</p>
      <ul class="summary-list">
        ${textItems.map((item) => `<li><span>${item.text_id}</span><strong>${item.relation_count} 条关系 / ${item.event_count} 个事件</strong></li>`).join("")}
      </ul>
    </div>
  `;
}

function renderSourceList(traceability) {
  graphState.traceability = traceability;
  const texts = traceability.texts || [];
  sourceCount.textContent = `${texts.length} 份`;
  sourceList.innerHTML = "";

  for (const item of texts) {
    const card = document.createElement("article");
    card.className = "source-card";
    card.innerHTML = `
      <h4>${item.text_id}</h4>
      <p>${item.source_title || "未记录来源标题"}</p>
      <p><a href="${item.source_url}" target="_blank" rel="noreferrer">查看来源链接</a></p>
      <div class="source-meta">
        <span>${item.mention_count} 个 mention</span>
        <span>${item.relation_count} 条关系</span>
        <span>${item.event_count} 个事件</span>
      </div>
    `;
    sourceList.appendChild(card);
  }
}

function renderEventCards(events) {
  eventCount.textContent = `${events.length} 条`;
  eventList.innerHTML = "";

  for (const event of events) {
    const card = document.createElement("article");
    card.className = "event-card";
    card.dataset.eventId = event.event_id;

    const participants = event.participants.map((item) => item.name).join(" / ");
    const timeText = event.time || "未标出时间";

    card.innerHTML = `
      <h4>${event.event_type}</h4>
      <p class="event-meta">${event.text_id} · ${timeText}</p>
      <div class="evidence">${event.evidence}</div>
      <div class="event-tags">
        <span>${event.trigger || "规则匹配"}</span>
        <span>${participants || "无参与实体"}</span>
      </div>
    `;

    card.addEventListener("click", () => {
      graphState.selectedNodeId = event.event_id;
      graphState.selectedEdgeId = "";
      updateDetailForNode(event.event_id);
      updateActiveEventCard(event.event_id);
    });

    eventList.appendChild(card);
  }
}

function updateActiveEventCard(eventId) {
  for (const card of eventList.querySelectorAll(".event-card")) {
    card.classList.toggle("active", card.dataset.eventId === eventId);
  }
}

function tick() {
  if (!graphState.graph) {
    return;
  }

  const width = canvas.getBoundingClientRect().width;
  const height = canvas.getBoundingClientRect().height;
  const centerX = width / 2;
  const centerY = height / 2;

  for (const node of graphState.nodes) {
    node.vx += (centerX - node.x) * 0.0008;
    node.vy += (centerY - node.y) * 0.0008;
  }

  for (let i = 0; i < graphState.nodes.length; i += 1) {
    for (let j = i + 1; j < graphState.nodes.length; j += 1) {
      const a = graphState.nodes[i];
      const b = graphState.nodes[j];
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.max(20, Math.sqrt(dx * dx + dy * dy));
      const force = 1200 / (dist * dist);
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      a.vx -= fx;
      a.vy -= fy;
      b.vx += fx;
      b.vy += fy;
    }
  }

  for (const edge of graphState.edges) {
    const dx = edge.targetNode.x - edge.sourceNode.x;
    const dy = edge.targetNode.y - edge.sourceNode.y;
    const dist = Math.max(30, Math.sqrt(dx * dx + dy * dy));
    const ideal = edge.kind === "event_participant" ? 95 : 130;
    const spring = (dist - ideal) * 0.0024;
    const fx = (dx / dist) * spring;
    const fy = (dy / dist) * spring;
    edge.sourceNode.vx += fx;
    edge.sourceNode.vy += fy;
    edge.targetNode.vx -= fx;
    edge.targetNode.vy -= fy;
  }

  for (const node of graphState.nodes) {
    node.vx *= 0.88;
    node.vy *= 0.88;
    node.x = clamp(node.x + node.vx, 36, width - 36);
    node.y = clamp(node.y + node.vy, 36, height - 36);
  }

  draw();
  requestAnimationFrame(tick);
}

function draw() {
  const width = canvas.getBoundingClientRect().width;
  const height = canvas.getBoundingClientRect().height;
  ctx.clearRect(0, 0, width, height);

  drawBackground(width, height);

  for (const edge of graphState.edges) {
    const active = edge.id === graphState.selectedEdgeId || edge.event_id === graphState.selectedNodeId;
    ctx.strokeStyle = active ? "rgba(217, 108, 58, 0.9)" : edge.kind === "event_participant"
      ? "rgba(36, 55, 70, 0.25)"
      : "rgba(86, 132, 214, 0.32)";
    ctx.lineWidth = active ? 2.4 : 1.2;
    ctx.beginPath();
    ctx.moveTo(edge.sourceNode.x, edge.sourceNode.y);
    ctx.lineTo(edge.targetNode.x, edge.targetNode.y);
    ctx.stroke();
  }

  for (const node of graphState.nodes) {
    const active = node.id === graphState.selectedNodeId;
    const color = typeColors[node.type] || "#60717d";
    ctx.beginPath();
    ctx.fillStyle = color;
    ctx.globalAlpha = active ? 1 : 0.9;
    ctx.arc(node.x, node.y, active ? node.radius + 2 : node.radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;

    ctx.fillStyle = "#1e2a33";
    ctx.font = active ? "600 13px sans-serif" : "12px sans-serif";
    ctx.fillText(node.label, node.x + 12, node.y + 4);
  }
}

function drawBackground(width, height) {
  ctx.save();
  ctx.strokeStyle = "rgba(30, 42, 51, 0.05)";
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
  for (const node of graphState.nodes) {
    if (distance({ x, y }, node) <= node.radius + 6) {
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

function updateDetailForNode(nodeId) {
  const node = graphState.nodes.find((item) => item.id === nodeId);
  if (!node) {
    return;
  }

  const relatedEdges = graphState.edges.filter(
    (edge) => edge.source === nodeId || edge.target === nodeId || edge.event_id === nodeId
  );

  const evidenceList = (node.evidence_samples || [])
    .map(
      (item) => `
        <div class="detail-evidence-card">
          <strong>${item.text_id} / 句子 ${item.sentence_id}</strong>
          <p>${item.evidence}</p>
          ${item.source_url ? `<a class="source-link" href="${item.source_url}" target="_blank" rel="noreferrer">${item.source_title || "查看来源"}</a>` : ""}
        </div>
      `
    )
    .join("");

  detailBox.innerHTML = `
    <div class="title">${node.label}</div>
    <span class="meta">${node.type}</span>
    <p>${node.description || "暂无额外描述。"}</p>
    ${node.evidence ? `<div class="evidence">${node.evidence}</div>` : ""}
    ${node.source_url ? `<a class="source-link" href="${node.source_url}" target="_blank" rel="noreferrer">${node.source_title || "查看来源"}</a>` : ""}
    <p>相关边数：${relatedEdges.length}</p>
    ${node.text_ids ? `<p>出现原文：${node.text_ids.join("、")}</p>` : ""}
    ${evidenceList ? `<div class="detail-evidence-list">${evidenceList}</div>` : ""}
  `;
}

function updateDetailForEdge(edgeId) {
  const edge = graphState.edges.find((item) => item.id === edgeId);
  if (!edge) {
    return;
  }

  detailBox.innerHTML = `
    <div class="title">${edge.sourceNode.label} → ${edge.targetNode.label}</div>
    <span class="meta">${edge.label}</span>
    <p>边类型：${edge.kind}</p>
    <p>原文位置：${edge.text_id || "未记录"} / 句子 ${edge.sentence_id || "-"}</p>
    <div class="evidence">${edge.evidence || "暂无证据句。"}</div>
    ${edge.source_url ? `<a class="source-link" href="${edge.source_url}" target="_blank" rel="noreferrer">${edge.source_title || "查看来源"}</a>` : ""}
  `;
}

canvas.addEventListener("click", (event) => {
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;

  const node = findNodeAt(x, y);
  if (node) {
    graphState.selectedNodeId = node.id;
    graphState.selectedEdgeId = "";
    updateDetailForNode(node.id);
    updateActiveEventCard(node.type === "EventNode" ? node.id : "");
    return;
  }

  const edge = findEdgeAt(x, y);
  if (edge) {
    graphState.selectedEdgeId = edge.id;
    graphState.selectedNodeId = "";
    updateDetailForEdge(edge.id);
    updateActiveEventCard(edge.event_id || "");
  }
});

window.addEventListener("resize", () => {
  resizeCanvas();
});

async function boot() {
  resizeCanvas();
  const [graphResponse, reportResponse, traceResponse] = await Promise.all([
    fetch("/data/output/graph.json"),
    fetch("/data/output/report.json"),
    fetch("/data/output/traceability.json"),
  ]);
  const graph = await graphResponse.json();
  const report = await reportResponse.json();
  const traceability = await traceResponse.json();
  prepareGraph(graph);
  renderSummary(report);
  renderSourceList(traceability);
}

boot().catch((error) => {
  detailBox.innerHTML = `<p>加载失败：${error.message}</p>`;
});
