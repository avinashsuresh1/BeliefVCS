// Safe HTML Escaping Utility to prevent Stored XSS
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// App State
const state = {
  vaultPath: "knowledge_vault",
  currentBranch: "main",
  branches: ["main"],
  territories: [],
  commits: [],
  compilations: [],
  modelConfig: {
    provider: "ollama",
    base_url: "http://localhost:11434/v1",
    api_key: "",
    model_name: "llama3",
    temperature: 0.2
  }
};

// Safe Tauri Invoke with Browser Mock Fallback
async function tauriInvoke(cmd, args = {}) {
  if (window.__TAURI__ && window.__TAURI__.core && window.__TAURI__.core.invoke) {
    return await window.__TAURI__.core.invoke(cmd, args);
  } else {
    console.warn(`[Browser Mode] Mocking Tauri command: ${cmd}`, args);
    return mockInvoke(cmd, args);
  }
}

// Fallback Mock Data for UI Testing in standard browsers
function mockInvoke(cmd, args) {
  switch (cmd) {
    case "get_vault_status":
      return Promise.resolve({
        current_branch: state.currentBranch,
        branches: ["main", "hypothesis/playwright-stealth", "hypothesis/regex-parser"],
        total_territories: 2,
        total_commits: 4,
        total_compilations: 3
      });
    case "list_branches":
      return Promise.resolve(["main", "hypothesis/playwright-stealth", "hypothesis/regex-parser"]);
    case "get_territories":
      return Promise.resolve([
        {
          id: "1",
          territory: "Web Scraping",
          guide: "Use BeautifulSoup for static HTML. For SPAs, use [[Playwright]] to render JS.",
          treasures: [{ description: "Fast parsing", rationale: "No browser DOM overhead" }],
          dead_ends: [{ description: "Tried parsing HTML with Regex", rationale: "HTML is not regular" }],
          known_hazards: [{ description: "Sites might block automated browsers", rationale: null }],
          propositions: [],
          tags: ["web", "python"],
          wiki_links: ["Playwright"]
        },
        {
          id: "2",
          territory: "Playwright",
          guide: "Browser automation engine capable of running headless Chromium.",
          treasures: [{ description: "Bypasses Turnstile", rationale: "Masks webdriver property" }],
          dead_ends: [],
          known_hazards: [],
          propositions: [{ claim: "Playwright stealth masks webdriver flags", premises: [], rationale: null, status: "PROVEN" }],
          tags: ["automation", "browser"],
          wiki_links: []
        }
      ]);
    case "get_commit_history":
      return Promise.resolve([
        {
          id: "9fbc8e9d",
          branch: "main",
          message: "Deploy verified hypothesis: merge 'hypothesis/playwright-stealth' into 'main'",
          author_agent_id: "Agent_A",
          timestamp: Date.now() / 1000 - 300,
          has_evidence: true,
          evidence_exit_code: 0
        },
        {
          id: "c87dae2c",
          branch: "hypothesis/playwright-stealth",
          message: "Validated stealth plugin on Cloudflare Turnstile probe",
          author_agent_id: "Agent_A",
          timestamp: Date.now() / 1000 - 600,
          has_evidence: true,
          evidence_exit_code: 0
        }
      ]);
    case "get_compilations":
      return Promise.resolve([
        {
          branch: "hypothesis/playwright-stealth",
          passed: true,
          message: "Build SUCCESS: Hypothesis verified by probe test.",
          test_command: "python test_scraper_probe.py",
          exit_code: 0,
          proof_sound: true,
          violations: []
        },
        {
          branch: "hypothesis/regex-parser",
          passed: false,
          message: "Build FAILED (Proof Inconsistency): Contradicts established Dead End.",
          test_command: "python test_regex.py",
          exit_code: -1,
          proof_sound: false,
          violations: ["Contradicts established Dead End: 'Tried parsing HTML with Regex'"]
        }
      ]);
    case "get_knowledge_graph":
      return Promise.resolve({
        nodes: [
          { id: "Web Scraping", label: "Web Scraping", group: "territory" },
          { id: "Playwright", label: "Playwright", group: "axiom" }
        ],
        edges: [
          { source: "Web Scraping", target: "Playwright" }
        ]
      });
    case "test_model_connection":
      return Promise.resolve({
        connected: true,
        latency_ms: 42,
        message: `Connected to ${args.config.provider} (${args.config.model_name}) in 42ms`
      });
    case "send_agent_prompt":
      return Promise.resolve(`[Agent Response via ${args.config.provider}]: I searched the knowledge vault on '${state.currentBranch}'. Based on our proven axioms, I recommend using Playwright with stealth flags rather than regex.`);
    default:
      return Promise.reject("Unknown mock command");
  }
}

// UI Initialization
document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initModelPresets();
  initEventListeners();
  syncVaultData();
});

// Tab Navigation
function initNavigation() {
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(tc => tc.classList.remove("active"));
      
      btn.classList.add("active");
      const tabId = `tab-${btn.dataset.tab}`;
      const tabEl = document.getElementById(tabId);
      if (tabEl) tabEl.classList.add("active");

      if (btn.dataset.tab === "graph") {
        renderKnowledgeGraph();
      }
    });
  });
}

// Event Listeners
function initEventListeners() {
  document.getElementById("refresh-btn").addEventListener("click", () => syncVaultData());
  
  const pathInput = document.getElementById("vault-path-input");
  pathInput.addEventListener("change", (e) => {
    state.vaultPath = e.target.value.trim();
    syncVaultData();
  });

  document.getElementById("test-connection-btn").addEventListener("click", testModelConnection);
  document.getElementById("send-agent-btn").addEventListener("click", sendAgentPrompt);
  document.getElementById("agent-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendAgentPrompt();
  });
}

// Model Presets
function initModelPresets() {
  const presets = {
    ollama: {
      provider: "ollama",
      base_url: "http://localhost:11434/v1",
      api_key: "",
      model_name: "llama3"
    },
    lmstudio: {
      provider: "lmstudio",
      base_url: "http://localhost:1234/v1",
      api_key: "",
      model_name: "local-model"
    },
    openai: {
      provider: "openai",
      base_url: "https://api.openai.com/v1",
      api_key: "",
      model_name: "gpt-4o"
    },
    gemini: {
      provider: "gemini",
      base_url: "https://generativelanguage.googleapis.com/v1beta/openai",
      api_key: "",
      model_name: "gemini-1.5-pro"
    },
    openrouter: {
      provider: "openrouter",
      base_url: "https://openrouter.ai/api/v1",
      api_key: "",
      model_name: "anthropic/claude-3.5-sonnet"
    }
  };

  document.querySelectorAll(".preset-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const p = presets[btn.dataset.preset];
      if (p) {
        document.getElementById("cfg-provider").value = p.provider;
        document.getElementById("cfg-url").value = p.base_url;
        document.getElementById("cfg-key").value = p.api_key;
        document.getElementById("cfg-model").value = p.model_name;
        updateModelFromInputs();
      }
    });
  });

  ["cfg-provider", "cfg-url", "cfg-key", "cfg-model"].forEach(id => {
    document.getElementById(id).addEventListener("input", updateModelFromInputs);
  });
}

function updateModelFromInputs() {
  state.modelConfig.provider = document.getElementById("cfg-provider").value.trim();
  state.modelConfig.base_url = document.getElementById("cfg-url").value.trim();
  state.modelConfig.api_key = document.getElementById("cfg-key").value.trim() || null;
  state.modelConfig.model_name = document.getElementById("cfg-model").value.trim();

  document.getElementById("sidebar-model-name").textContent = 
    `${state.modelConfig.provider} (${state.modelConfig.model_name})`;
}

// Sync All Vault Data
async function syncVaultData() {
  try {
    const status = await tauriInvoke("get_vault_status", { vaultPath: state.vaultPath });
    state.currentBranch = status.current_branch;
    state.branches = status.branches;

    document.getElementById("active-branch-name").textContent = status.current_branch;
    document.getElementById("card-branch").textContent = status.current_branch;
    document.getElementById("card-territories").textContent = status.total_territories;
    document.getElementById("card-commits").textContent = status.total_commits;
    document.getElementById("card-compilations").textContent = status.total_compilations;

    // Load sub-data
    renderBranchesList(status.branches);
    
    state.commits = await tauriInvoke("get_commit_history", { vaultPath: state.vaultPath });
    renderCommitsTimeline(state.commits);

    state.compilations = await tauriInvoke("get_compilations", { vaultPath: state.vaultPath });
    renderCompilations(state.compilations);

    state.territories = await tauriInvoke("get_territories", { 
      vaultPath: state.vaultPath, 
      branch: state.currentBranch 
    });
    renderTerritoriesGrid(state.territories);

  } catch (err) {
    console.error("Sync error:", err);
  }
}

// Render Branches
function renderBranchesList(branches) {
  const container = document.getElementById("branches-list");
  container.innerHTML = "";

  branches.forEach(b => {
    const isActive = b === state.currentBranch;
    const safeBranch = escapeHtml(b);
    const div = document.createElement("div");
    div.className = `p-2.5 rounded-md border text-xs flex items-center justify-between font-mono ${
      isActive 
        ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" 
        : "bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700"
    }`;
    div.innerHTML = `
      <div class="flex items-center space-x-2">
        <span class="w-2 h-2 rounded-full ${isActive ? 'bg-emerald-400' : 'bg-slate-600'}"></span>
        <span>${safeBranch}</span>
      </div>
      <span class="text-[10px] text-slate-500">${b.startsWith("hypothesis/") ? "Hypothesis" : "Status Quo"}</span>
    `;
    container.appendChild(div);
  });
}

// Render Commits Timeline
function renderCommitsTimeline(commits) {
  const container = document.getElementById("commits-timeline");
  container.innerHTML = "";

  if (commits.length === 0) {
    container.innerHTML = `<div class="text-xs text-slate-500 p-4 text-center">No belief commits recorded yet.</div>`;
    return;
  }

  commits.forEach(c => {
    const d = new Date(c.timestamp * 1000);
    const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const safeId = escapeHtml(c.id ? c.id.substring(0, 8) : "");
    const safeBranch = escapeHtml(c.branch);
    const safeMsg = escapeHtml(c.message);
    const safeAuthor = escapeHtml(c.author_agent_id || 'Autonomous');
    const safeExit = escapeHtml(c.evidence_exit_code ?? 0);

    const card = document.createElement("div");
    card.className = "p-3 bg-slate-900/80 rounded-md border border-slate-800 text-xs space-y-1.5";
    card.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">${safeId}</span>
        <span class="text-[11px] text-slate-500 font-mono">${safeBranch} • ${timeStr}</span>
      </div>
      <p class="text-slate-200 font-medium">${safeMsg}</p>
      <div class="flex items-center justify-between text-[11px] pt-1">
        <span class="text-slate-400">Agent: <span class="text-indigo-400">${safeAuthor}</span></span>
        ${c.has_evidence 
          ? `<span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-mono text-[10px] border border-emerald-500/20">Evidence Exit: ${safeExit}</span>` 
          : `<span class="text-slate-500 text-[10px]">No probe attached</span>`}
      </div>
    `;
    container.appendChild(card);
  });
}

// Render Cognitive CI/CD Compilations
function renderCompilations(compilations) {
  const container = document.getElementById("compilations-container");
  container.innerHTML = "";

  if (compilations.length === 0) {
    container.innerHTML = `<div class="panel text-xs text-slate-500 p-6 text-center">No hypothesis compilations recorded yet.</div>`;
    return;
  }

  compilations.forEach(c => {
    const isSuccess = c.passed;
    const safeBranch = escapeHtml(c.branch);
    const safeMsg = escapeHtml(c.message);
    const safeExit = escapeHtml(c.exit_code);
    const safeCmd = escapeHtml(c.test_command || "");
    const violations = c.violations || [];
    const violationsHtml = violations.map(v => `<div>• ${escapeHtml(v)}</div>`).join("");

    const card = document.createElement("div");
    card.className = `panel border-l-4 ${isSuccess ? 'border-l-emerald-500' : 'border-l-rose-500'} space-y-2`;
    
    card.innerHTML = `
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono ${
            isSuccess ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
          }">
            ${isSuccess ? 'BUILD SUCCESS' : 'BUILD FAILED'}
          </span>
          <span class="font-mono text-xs text-slate-300 font-semibold">${safeBranch}</span>
        </div>
        <span class="text-xs font-mono text-slate-400">Exit Code: ${safeExit}</span>
      </div>

      <div class="text-xs text-slate-200">${safeMsg}</div>

      ${c.proof_sound !== null && c.proof_sound !== undefined ? `
        <div class="p-2.5 rounded bg-slate-950/80 border border-slate-800 text-[11px] space-y-1">
          <div class="flex items-center justify-between font-medium">
            <span class="text-slate-400">Stage 1: Proof Theory Consistency</span>
            <span class="${c.proof_sound ? 'text-emerald-400' : 'text-rose-400'} font-mono">
              ${c.proof_sound ? 'SOUND' : 'UNSOUND (Contradiction)'}
            </span>
          </div>
          ${violations.length > 0 ? `
            <div class="text-rose-400/90 pl-2 border-l border-rose-500/30 space-y-0.5">
              ${violationsHtml}
            </div>
          ` : `<div class="text-slate-500">Logically consistent with existing main axioms and dead ends.</div>`}
        </div>
      ` : ''}

      ${safeCmd ? `
        <div class="text-[11px] font-mono bg-slate-950 p-2 rounded text-slate-400 border border-slate-900">
          $ ${safeCmd}
        </div>
      ` : ''}
    `;
    container.appendChild(card);
  });
}

// Render Territories Grid
function renderTerritoriesGrid(territories) {
  const container = document.getElementById("territories-grid");
  container.innerHTML = "";

  if (territories.length === 0) {
    container.innerHTML = `<div class="col-span-2 panel text-xs text-slate-500 p-8 text-center">No territories mapped on this branch yet.</div>`;
    return;
  }

  territories.forEach(t => {
    const card = document.createElement("div");
    card.className = "panel space-y-3";

    const safeTerritory = escapeHtml(t.territory);
    const safeGuide = escapeHtml(t.guide);
    const tags = t.tags || [];
    const tagsHtml = tags.map(tag => `<span class="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px] font-mono">${escapeHtml(tag)}</span>`).join("");

    let treasuresHtml = (t.treasures || []).map(tr => 
      `<li class="text-emerald-400/90 text-xs"><b>${escapeHtml(tr.description)}</b> ${tr.rationale ? `<span class="text-slate-400 text-[11px]">(${escapeHtml(tr.rationale)})</span>` : ''}</li>`
    ).join("");

    let deadEndsHtml = (t.dead_ends || []).map(de => 
      `<li class="text-rose-400/90 text-xs"><b>${escapeHtml(de.description)}</b> ${de.rationale ? `<span class="text-slate-400 text-[11px]">(${escapeHtml(de.rationale)})</span>` : ''}</li>`
    ).join("");

    let axiomsHtml = (t.propositions || []).map(p => 
      `<div class="p-2 rounded bg-indigo-950/40 border border-indigo-500/30 text-xs">
        <div class="text-[10px] text-indigo-300 font-bold uppercase font-mono">Axiom (${escapeHtml(p.status)})</div>
        <div class="text-slate-200">${escapeHtml(p.claim)}</div>
       </div>`
    ).join("");

    card.innerHTML = `
      <div class="flex items-center justify-between border-b border-slate-800 pb-2">
        <h3 class="text-sm font-semibold text-white">${safeTerritory}</h3>
        <div class="flex space-x-1">
          ${tagsHtml}
        </div>
      </div>

      <div class="text-xs text-slate-300 bg-slate-900/50 p-2.5 rounded border border-slate-800/80">
        <span class="text-slate-400 font-semibold block text-[10px] uppercase">Guide</span>
        ${safeGuide}
      </div>

      ${t.treasures && t.treasures.length > 0 ? `
        <div>
          <span class="text-[10px] font-semibold text-emerald-400 uppercase tracking-wide">Treasures (Proven Successes)</span>
          <ul class="list-disc pl-4 space-y-1 mt-1">${treasuresHtml}</ul>
        </div>
      ` : ''}

      ${t.dead_ends && t.dead_ends.length > 0 ? `
        <div>
          <span class="text-[10px] font-semibold text-rose-400 uppercase tracking-wide">Dead Ends (Documented Failures)</span>
          <ul class="list-disc pl-4 space-y-1 mt-1">${deadEndsHtml}</ul>
        </div>
      ` : ''}

      ${t.propositions && t.propositions.length > 0 ? `
        <div class="space-y-1">
          <span class="text-[10px] font-semibold text-indigo-400 uppercase tracking-wide">Proven Axioms</span>
          ${axiomsHtml}
        </div>
      ` : ''}
    `;
    container.appendChild(card);
  });
}

// Render Knowledge Graph via SVG
async function renderKnowledgeGraph() {
  const svg = document.getElementById("knowledge-graph-svg");
  svg.innerHTML = "";

  try {
    const graphData = await tauriInvoke("get_knowledge_graph", { 
      vaultPath: state.vaultPath, 
      branch: state.currentBranch 
    });

    if (graphData.nodes.length === 0) {
      svg.innerHTML = `<text x="50%" y="50%" fill="#64748b" text-anchor="middle" font-size="12">No graph nodes discovered.</text>`;
      return;
    }

    const width = svg.clientWidth || 800;
    const height = svg.clientHeight || 500;

    // Position nodes radially or in grid
    const nodeMap = {};
    const radius = Math.min(width, height) / 3;
    const centerX = width / 2;
    const centerY = height / 2;
    const count = graphData.nodes.length;

    graphData.nodes.forEach((node, i) => {
      const angle = (i / count) * 2 * Math.PI;
      const x = count === 1 ? centerX : centerX + radius * Math.cos(angle);
      const y = count === 1 ? centerY : centerY + radius * Math.sin(angle);
      nodeMap[node.id] = { x, y, ...node };
    });

    // Draw Edges
    graphData.edges.forEach(edge => {
      const src = nodeMap[edge.source];
      const tgt = nodeMap[edge.target];
      if (src && tgt) {
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", src.x);
        line.setAttribute("y1", src.y);
        line.setAttribute("x2", tgt.x);
        line.setAttribute("y2", tgt.y);
        line.setAttribute("stroke", "#4f46e5");
        line.setAttribute("stroke-width", "2");
        line.setAttribute("stroke-dasharray", "4");
        line.setAttribute("opacity", "0.6");
        svg.appendChild(line);
      }
    });

    // Draw Nodes
    Object.values(nodeMap).forEach(node => {
      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.setAttribute("class", "cursor-pointer");

      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", node.x);
      circle.setAttribute("cy", node.y);
      circle.setAttribute("r", node.group === "axiom" ? "18" : "14");
      circle.setAttribute("fill", node.group === "axiom" ? "#10b981" : "#6366f1");
      circle.setAttribute("stroke", "#0f172a");
      circle.setAttribute("stroke-width", "3");

      const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
      text.setAttribute("x", node.x);
      text.setAttribute("y", node.y + 28);
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("fill", "#e2e8f0");
      text.setAttribute("font-size", "11");
      text.setAttribute("font-weight", "600");
      text.textContent = node.label;

      g.appendChild(circle);
      g.appendChild(text);
      svg.appendChild(g);
    });

  } catch (err) {
    console.error("Graph rendering error:", err);
  }
}

// Test Model Connection
async function testModelConnection() {
  const badge = document.getElementById("conn-result-badge");
  const dot = document.getElementById("sidebar-model-dot");
  badge.textContent = "Connecting to endpoint...";
  badge.className = "text-xs text-amber-400";

  try {
    const res = await tauriInvoke("test_model_connection", { config: state.modelConfig });
    if (res.connected) {
      badge.textContent = `✓ ${res.message}`;
      badge.className = "text-xs text-emerald-400 font-medium";
      dot.className = "w-2 h-2 rounded-full bg-emerald-500 shadow-md shadow-emerald-500/50";
    } else {
      badge.textContent = `✗ ${res.message}`;
      badge.className = "text-xs text-rose-400";
      dot.className = "w-2 h-2 rounded-full bg-rose-500";
    }
  } catch (err) {
    badge.textContent = `Error: ${err}`;
    badge.className = "text-xs text-rose-400";
    dot.className = "w-2 h-2 rounded-full bg-rose-500";
  }
}

// Send Agent Prompt via Cockpit
async function sendAgentPrompt() {
  const input = document.getElementById("agent-input");
  const prompt = input.value.trim();
  if (!prompt) return;

  const chatContainer = document.getElementById("chat-messages");

  // User Message
  const userDiv = document.createElement("div");
  userDiv.className = "user-msg";
  userDiv.innerHTML = `<span class="role">User</span><p>${escapeHtml(prompt)}</p>`;
  chatContainer.appendChild(userDiv);

  input.value = "";
  chatContainer.scrollTop = chatContainer.scrollHeight;

  // Placeholder Agent Message
  const agentDiv = document.createElement("div");
  agentDiv.className = "agent-msg";
  const safeProvider = escapeHtml(state.modelConfig.provider);
  agentDiv.innerHTML = `<span class="role">${safeProvider} Agent</span><p class="text-slate-400 animate-pulse">Consulting status quo on '${escapeHtml(state.currentBranch)}'...</p>`;
  chatContainer.appendChild(agentDiv);
  chatContainer.scrollTop = chatContainer.scrollHeight;

  try {
    const response = await tauriInvoke("send_agent_prompt", {
      config: state.modelConfig,
      prompt,
      vaultPath: state.vaultPath
    });

    agentDiv.innerHTML = `<span class="role">${safeProvider} Agent</span><p class="whitespace-pre-wrap">${escapeHtml(response)}</p>`;
    chatContainer.scrollTop = chatContainer.scrollHeight;

    // Refresh vault data in case agent modified anything
    syncVaultData();
  } catch (err) {
    agentDiv.innerHTML = `<span class="role text-rose-400">Error</span><p class="text-rose-400">${escapeHtml(err)}</p>`;
  }
}
