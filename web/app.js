const canvas = document.getElementById("graph-canvas");
const ctx = canvas.getContext("2d");
const detailBox = document.getElementById("detail-box");
const eventList = document.getElementById("event-list");
const statsBox = document.getElementById("stats");
const eventCount = document.getElementById("event-count");
const summaryBox = document.getElementById("summary-box");
const sourceList = document.getElementById("source-list");
const sourceCount = document.getElementById("source-count");
const processSteps = document.getElementById("process-steps");
const personFocusButtons = document.getElementById("person-focus-buttons");
const personFocusSummary = document.getElementById("person-focus-summary");
const disambiguationCasesBox = document.getElementById("disambiguation-cases");
const eventChainCasesBox = document.getElementById("event-chain-cases");

const PERSON_FOCUS_ORDER = [
  "Alan Turing",
  "Joan Clarke",
  "Alonzo Church",
  "Max Newman",
  "John von Neumann",
];

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
  animating: false,
  report: null,
  traceability: null,
  explainability: null,
  focusNodeId: "",
  focusNeighborIds: [],
  activePersonLabel: "",
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

function parseJsonl(rawText) {
  const trimmed = rawText.trim();
  if (!trimmed) {
    return [];
  }
  return trimmed
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function uniqueBy(items, keyBuilder) {
  const seen = new Set();
  const picked = [];
  for (const item of items) {
    const key = keyBuilder(item);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    picked.push(item);
  }
  return picked;
}

function getNodeById(nodeId) {
  return graphState.nodes.find((item) => item.id === nodeId) || null;
}

function getPersonNodeByLabel(label) {
  return graphState.nodes.find((item) => item.type === "Person" && item.label === label) || null;
}

function getFocusNodeSet() {
  const ids = [graphState.focusNodeId, ...graphState.focusNeighborIds].filter(Boolean);
  return new Set(ids);
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

function relationEdgesForNode(nodeId) {
  return graphState.edges.filter(
    (edge) =>
      edge.kind !== "event_participant" &&
      (edge.source === nodeId || edge.target === nodeId)
  );
}

function buildProcessData(report, traceability, mentions, linkedMentions, events) {
  const rawSamples = (traceability.texts || []).slice(0, 2).map((item) => ({
    label: item.text_id,
    value: item.source_title || "公开资料整理",
  }));

  const mentionSamples = uniqueBy(mentions, (item) => `${item.mention}-${item.entity_type}`)
    .slice(0, 3)
    .map((item) => ({
      label: item.mention,
      value: item.entity_type,
    }));

  const disambiguationSamples = linkedMentions
    .filter((item) => item.status === "linked" && (item.candidate_ids || []).length > 1)
    .sort((a, b) => (b.candidate_ids || []).length - (a.candidate_ids || []).length)
    .slice(0, 2)
    .map((item) => ({
      label: `${item.mention} -> ${item.canonical_name}`,
      value: `${item.candidate_ids.length} 个候选`,
    }));

  const eventPriority = {
    PublicationEvent: 1,
    EducationEvent: 2,
    InfluenceEvent: 3,
    WarWorkEvent: 4,
    ResearchEvent: 5,
    EmploymentEvent: 6,
  };
  const eventSamples = events
    .slice()
    .sort((a, b) => (eventPriority[a.event_type] || 99) - (eventPriority[b.event_type] || 99))
    .slice(0, 3)
    .map((item) => ({
      label: item.event_type,
      value: item.evidence,
    }));

  const relationSamples = [];
  for (const text of traceability.texts || []) {
    for (const relation of text.relations || []) {
      relationSamples.push({
        label: relation.triple,
        value: text.text_id,
      });
    }
  }

  return [
    {
      index: "01",
      title: "原始文本",
      total: `${report.raw_text_count} 份`,
      description: "先把公开资料整理成短文本，不直接手写结构化图谱。",
      samples: rawSamples,
    },
    {
      index: "02",
      title: "实体抽取",
      total: `${report.mention_count} 个 mention`,
      description: "用词典和正则抽人物、机构、地点、作品和时间。",
      samples: mentionSamples,
    },
    {
      index: "03",
      title: "实体消歧",
      total: `${report.linked_count} 个成功链接`,
      description: "对别名、上下文和类型打分，选标准实体。",
      samples: disambiguationSamples,
    },
    {
      index: "04",
      title: "事件抽取",
      total: `${report.event_count} 个事件`,
      description: "先抽求学、发表、研究、战争工作这些事件。",
      samples: eventSamples,
    },
    {
      index: "05",
      title: "关系抽取",
      total: `${report.relation_count} 条关系`,
      description: "再从事件和少量句式规则生成三元组。",
      samples: relationSamples.slice(0, 3),
    },
  ];
}

function formatScore(value) {
  return Number(value || 0).toFixed(2);
}

function renderProcessSteps(report, traceability, mentions, linkedMentions, events) {
  const steps = buildProcessData(report, traceability, mentions, linkedMentions, events);
  processSteps.innerHTML = steps
    .map(
      (step) => `
        <article class="process-step">
          <div class="process-index">${step.index}</div>
          <div class="process-main">
            <div class="process-topline">
              <span>${step.title}</span>
              <strong>${step.total}</strong>
            </div>
            <p>${step.description}</p>
            <ul class="process-list">
              ${(step.samples || [])
                .map(
                  (item) => `
                    <li>
                      <span>${item.label}</span>
                      <strong>${item.value}</strong>
                    </li>
                  `
                )
                .join("")}
            </ul>
          </div>
        </article>
      `
    )
    .join("");
}

function renderExplainability(explainability) {
  graphState.explainability = explainability;
  renderDisambiguationCases(explainability.disambiguation_cases || []);
  renderEventChainCases(explainability.event_relation_cases || []);
}

function renderDisambiguationCases(cases) {
  disambiguationCasesBox.innerHTML = "";

  for (const item of cases) {
    const card = document.createElement("article");
    card.className = "case-item";
    card.innerHTML = `
      <h4>${item.title}</h4>
      <p>${item.context}</p>
      <div class="case-meta">
        <span>${item.text_id} / 句子 ${item.sentence_id}</span>
        <span>最终选择：${item.selected_name}</span>
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
      <p>${item.selected_reason}</p>
      <button type="button" class="case-button">在图里看结果</button>
    `;

    const button = card.querySelector(".case-button");
    button.addEventListener("click", () => {
      const node = getNodeById(item.selected_entity_id);
      if (!node) {
        return;
      }
      if (node.type === "Person") {
        focusOnPerson(node.label);
        return;
      }
      graphState.selectedNodeId = node.id;
      graphState.selectedEdgeId = "";
      updateDetailForNode(node.id);
      updateActiveEventCard("");
    });

    disambiguationCasesBox.appendChild(card);
  }
}

function renderEventChainCases(cases) {
  eventChainCasesBox.innerHTML = "";

  for (const item of cases) {
    const participantText = (item.participants || [])
      .map((participant) => `${participant.role}: ${participant.name}`)
      .join(" / ");

    const card = document.createElement("article");
    card.className = "case-item";
    card.innerHTML = `
      <h4>${item.title}</h4>
      <p>${item.evidence}</p>
      <div class="case-meta">
        <span>${item.event_type}</span>
        <span>触发词：${item.trigger || "规则匹配"}</span>
      </div>
      <div class="chain-list">
        <div class="chain-row">
          <strong>事件层</strong>
          <span>${participantText || "无参与实体"}</span>
        </div>
        ${(item.relations || [])
          .map(
            (relation) => `
              <div class="chain-row selected">
                <strong>关系层</strong>
                <span>${relation.triple}</span>
              </div>
            `
          )
          .join("")}
      </div>
      <button type="button" class="case-button">在图里看这条事件</button>
    `;

    const button = card.querySelector(".case-button");
    button.addEventListener("click", () => {
      graphState.selectedNodeId = item.event_id;
      graphState.selectedEdgeId = "";
      updateDetailForNode(item.event_id);
      updateActiveEventCard(item.event_id);
    });

    eventChainCasesBox.appendChild(card);
  }
}

function updatePersonFocusSummary() {
  if (!graphState.focusNodeId) {
    personFocusSummary.innerHTML = `
      <strong>先挑一个人物看局部关系</strong>
      <p>这里会突出显示这个人物和一跳邻居，适合答辩时快速比较 Alan Turing、Joan Clarke、Alonzo Church、Max Newman 这些主体。</p>
    `;
    return;
  }

  const node = getNodeById(graphState.focusNodeId);
  if (!node) {
    return;
  }

  const relationCount = relationEdgesForNode(node.id).length;
  const relatedNodes = uniqueBy(
    graphState.edges
      .filter((edge) => edge.source === node.id || edge.target === node.id)
      .map((edge) => (edge.source === node.id ? edge.targetNode : edge.sourceNode))
      .filter((item) => item && item.type !== "EventNode"),
    (item) => item.id
  ).slice(0, 4);
  const relatedLabels = relatedNodes.map((item) => item.label).join("、") || "暂无";
  const textIds = (node.text_ids || []).slice(0, 4).join("、") || "暂无";

  personFocusSummary.innerHTML = `
    <strong>${node.label}</strong>
    <p>当前直接关联 ${relationCount} 条关系，出现在 ${(node.text_ids || []).length} 份原文里。切到这个视角后，可以更快看到这个人物在整张图里的局部位置。</p>
    <div class="focus-meta">
      <span>一跳邻居：${relatedLabels}</span>
      <span>原文片段：${textIds}</span>
    </div>
  `;
}

function clearPersonFocus() {
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
  if (graphState.activePersonLabel === label) {
    clearPersonFocus();
    return;
  }

  graphState.focusNodeId = node.id;
  graphState.focusNeighborIds = collectNeighborIds(node.id);
  graphState.activePersonLabel = label;
  graphState.selectedNodeId = node.id;
  graphState.selectedEdgeId = "";
  updateDetailForNode(node.id);
  updateActiveEventCard("");
  renderPersonFocusButtons();
}

function renderPersonFocusButtons() {
  personFocusButtons.innerHTML = "";

  const allButton = document.createElement("button");
  allButton.type = "button";
  allButton.className = `focus-button${graphState.activePersonLabel ? "" : " active"}`;
  allButton.textContent = "全部视角";
  allButton.addEventListener("click", () => {
    clearPersonFocus();
  });
  personFocusButtons.appendChild(allButton);

  for (const label of PERSON_FOCUS_ORDER) {
    const node = getPersonNodeByLabel(label);
    if (!node) {
      continue;
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = `focus-button${graphState.activePersonLabel === label ? " active" : ""}`;
    button.textContent = label;
    button.addEventListener("click", () => {
      focusOnPerson(label);
    });
    personFocusButtons.appendChild(button);
  }

  updatePersonFocusSummary();
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
  renderPersonFocusButtons();
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
  const eventItems = Object.entries(report.event_type_counts || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4);

  summaryBox.innerHTML = `
    <div class="summary-grid">
      <div class="summary-item"><span>原始文本</span><strong>${report.raw_text_count}</strong></div>
      <div class="summary-item"><span>抽到实体</span><strong>${report.linked_count}</strong></div>
      <div class="summary-item"><span>关系条数</span><strong>${report.relation_count}</strong></div>
      <div class="summary-item"><span>事件条数</span><strong>${report.event_count}</strong></div>
    </div>
    <p>现在网页同时支持“构建过程”“人物视角”“规则解释”三种讲法：既能看流程，也能看局部主体，还能直接拆解释案例。</p>
    <div>
      <p>常见关系：</p>
      <ul class="summary-list">
        ${relationItems.map(([name, count]) => `<li><span>${name}</span><strong>${count}</strong></li>`).join("")}
      </ul>
    </div>
    <div>
      <p>当前抽到的事件类型：</p>
      <ul class="summary-list">
        ${eventItems.map(([name, count]) => `<li><span>${name}</span><strong>${count}</strong></li>`).join("")}
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
    const relationText = (item.relations || [])
      .slice(0, 2)
      .map((relation) => `<li>${relation.triple}</li>`)
      .join("");
    const eventText = (item.events || [])
      .slice(0, 1)
      .map((event) => `<li>${event.event_type} · ${event.trigger}</li>`)
      .join("");

    const card = document.createElement("article");
    card.className = "source-card";
    card.innerHTML = `
      <h4>${item.text_id}</h4>
      <p>${item.source_title || "未记录来源标题"}</p>
      <p class="source-note">${item.note || "未记录说明"}</p>
      <p><a href="${item.source_url}" target="_blank" rel="noreferrer">查看来源链接</a></p>
      <div class="source-meta">
        <span>${item.mention_count} 个 mention</span>
        <span>${item.relation_count} 条关系</span>
        <span>${item.event_count} 个事件</span>
      </div>
      ${relationText ? `<ul class="mini-list">${relationText}</ul>` : ""}
      ${eventText ? `<ul class="mini-list">${eventText}</ul>` : ""}
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
  const focusActive = Boolean(graphState.focusNodeId);
  const focusSet = getFocusNodeSet();

  ctx.clearRect(0, 0, width, height);
  drawBackground(width, height);

  for (const edge of graphState.edges) {
    const active =
      edge.id === graphState.selectedEdgeId || edge.event_id === graphState.selectedNodeId;
    const edgeInFocus =
      !focusActive || (focusSet.has(edge.source) && focusSet.has(edge.target));

    if (active) {
      ctx.strokeStyle = "rgba(217, 108, 58, 0.92)";
      ctx.lineWidth = 2.4;
    } else if (!edgeInFocus) {
      ctx.strokeStyle = "rgba(30, 42, 51, 0.08)";
      ctx.lineWidth = 1;
    } else if (edge.kind === "event_participant") {
      ctx.strokeStyle = "rgba(36, 55, 70, 0.32)";
      ctx.lineWidth = 1.3;
    } else {
      ctx.strokeStyle = "rgba(86, 132, 214, 0.5)";
      ctx.lineWidth = 1.5;
    }

    ctx.beginPath();
    ctx.moveTo(edge.sourceNode.x, edge.sourceNode.y);
    ctx.lineTo(edge.targetNode.x, edge.targetNode.y);
    ctx.stroke();
  }

  for (const node of graphState.nodes) {
    const active = node.id === graphState.selectedNodeId;
    const nodeInFocus = !focusActive || focusSet.has(node.id);
    const color = typeColors[node.type] || "#60717d";
    const alpha = active ? 1 : nodeInFocus ? 0.94 : 0.22;

    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.beginPath();
    ctx.fillStyle = color;
    ctx.arc(node.x, node.y, active ? node.radius + 2 : node.radius, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#1e2a33";
    ctx.font = active ? "600 13px sans-serif" : "12px sans-serif";
    ctx.fillText(node.label, node.x + 12, node.y + 4);
    ctx.restore();
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
  const node = getNodeById(nodeId);
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
    if (node.type === "Person") {
      focusOnPerson(node.label);
      return;
    }

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
  const [
    graphResponse,
    reportResponse,
    traceResponse,
    explainResponse,
    mentionsResponse,
    linkedResponse,
  ] = await Promise.all([
    fetch("/data/output/graph.json"),
    fetch("/data/output/report.json"),
    fetch("/data/output/traceability.json"),
    fetch("/data/output/explainability.json"),
    fetch("/data/intermediate/mentions.jsonl"),
    fetch("/data/intermediate/linked_entities.jsonl"),
  ]);

  const graph = await graphResponse.json();
  const report = await reportResponse.json();
  const traceability = await traceResponse.json();
  const explainability = await explainResponse.json();
  const mentions = parseJsonl(await mentionsResponse.text());
  const linkedMentions = parseJsonl(await linkedResponse.text());

  prepareGraph(graph);
  renderSummary(report);
  renderSourceList(traceability);
  renderProcessSteps(report, traceability, mentions, linkedMentions, graph.events || []);
  renderExplainability(explainability);
}

boot().catch((error) => {
  detailBox.innerHTML = `<p>加载失败：${error.message}</p>`;
  processSteps.innerHTML = `<p>流程数据加载失败：${error.message}</p>`;
  personFocusSummary.innerHTML = `<p>人物视角加载失败：${error.message}</p>`;
  disambiguationCasesBox.innerHTML = `<p>规则解释加载失败：${error.message}</p>`;
  eventChainCasesBox.innerHTML = `<p>规则解释加载失败：${error.message}</p>`;
});
