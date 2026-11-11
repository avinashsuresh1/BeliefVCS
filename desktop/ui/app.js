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
  chatHistory: [],
  isSending: false,
  pendingPropositions: [],
  modelConfig: {
    provider: "ollama",
    base_url: "http://localhost:11434/v1",
    api_key: "",
    model_name: "llama3",
    temperature: 0.2
  }
};

// Safe Tauri Invoke with Error Handling (No Fake Mocks)
async function tauriInvoke(cmd, args = {}) {
  let invoker = null;
  if (window.__TAURI__ && window.__TAURI__.core && typeof window.__TAURI__.core.invoke === "function") {
    invoker = window.__TAURI__.core.invoke;
  } else if (window.__TAURI_INTERNALS__ && typeof window.__TAURI_INTERNALS__.invoke === "function") {
    invoker = window.__TAURI_INTERNALS__.invoke;
  } else if (window.__TAURI__ && typeof window.__TAURI__.invoke === "function") {
    invoker = window.__TAURI__.invoke;
  }

  if (invoker) {
    return await invoker(cmd, args);
  }

  console.error(`[IPC Error] Desktop runtime (Rust/Tauri) not detected for '${cmd}'.`);
  throw new Error(
    `Native desktop backend is not connected. Please run the desktop application using 'cargo run' or './desktop/run.ps1'.`
  );
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

  const clearChatBtn = document.getElementById("clear-chat-btn");
  if (clearChatBtn) clearChatBtn.addEventListener("click", clearChat);

  const openIngestBtn = document.getElementById("open-ingest-modal-btn");
  if (openIngestBtn) openIngestBtn.addEventListener("click", () => openIngestModal());

  const closeIngestBtn = document.getElementById("close-ingest-modal-btn");
  if (closeIngestBtn) closeIngestBtn.addEventListener("click", closeIngestModal);

  const cancelIngestBtn = document.getElementById("cancel-ingest-btn");
  if (cancelIngestBtn) cancelIngestBtn.addEventListener("click", closeIngestModal);

  const distillBtn = document.getElementById("distill-btn");
  if (distillBtn) distillBtn.addEventListener("click", distillWithAI);

  const commitIngestBtn = document.getElementById("commit-ingest-btn");
  if (commitIngestBtn) commitIngestBtn.addEventListener("click", commitIngestToVault);

  const assessPropositionBtn = document.getElementById("assess-proposition-btn");
  if (assessPropositionBtn) assessPropositionBtn.addEventListener("click", assessProposition);

  const createHypothesisBtn = document.getElementById("create-hypothesis-btn");
  if (createHypothesisBtn) createHypothesisBtn.addEventListener("click", createHypothesisBranch);

  const runProbeBtn = document.getElementById("run-integrity-probe-btn");
  if (runProbeBtn) runProbeBtn.addEventListener("click", runKnowledgeIntegrityProbe);

  const mergeHypothesisBtn = document.getElementById("merge-hypothesis-btn");
  if (mergeHypothesisBtn) mergeHypothesisBtn.addEventListener("click", mergeHypothesisToMain);
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
  const syncStatus = document.getElementById("sync-status");
  try {
    const status = await tauriInvoke("get_vault_status", { vaultPath: state.vaultPath });
    state.currentBranch = status.current_branch;
    state.branches = status.branches;

    document.getElementById("active-branch-name").textContent = status.current_branch;
    document.getElementById("card-branch").textContent = status.current_branch;
    document.getElementById("card-branch-desc").textContent =
      status.current_branch === "main" ? "Accepted status quo" : "Isolated hypothesis";
    document.getElementById("hypothesis-workflow-controls").classList.toggle(
      "hidden",
      !status.current_branch.startsWith("hypothesis/")
    );
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
    syncStatus.textContent = "";
    syncStatus.className = "text-[10px] text-slate-400";

  } catch (err) {
    console.error("Sync error:", err);
    syncStatus.textContent = `Sync failed: ${err}`;
    syncStatus.className = "text-[10px] text-rose-400";
  }
}

// Render Branches
function renderBranchesList(branches) {
  const container = document.getElementById("branches-list");
  container.innerHTML = "";

  branches.forEach(b => {
    const isActive = b === state.currentBranch;
    const safeBranch = escapeHtml(b);
    const button = document.createElement("button");
    button.type = "button";
    button.disabled = isActive;
    button.className = `w-full p-2.5 rounded-md border text-xs flex items-center justify-between font-mono ${
      isActive 
        ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300" 
        : "bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700"
    }`;
    button.innerHTML = `
      <div class="flex items-center space-x-2">
        <span class="w-2 h-2 rounded-full ${isActive ? 'bg-emerald-400' : 'bg-slate-600'}"></span>
        <span>${safeBranch}</span>
      </div>
      <span class="text-[10px] text-slate-500">${b.startsWith("hypothesis/") ? "Hypothesis" : "Status Quo"}</span>
    `;
    if (!isActive) {
      button.addEventListener("click", async () => {
        const status = document.getElementById("branch-status");
        status.textContent = `Switching to ${b}...`;
        try {
          await tauriInvoke("checkout_branch", { vaultPath: state.vaultPath, branch: b });
          status.textContent = "";
          status.className = "mt-1 text-[10px] text-slate-400";
          await syncVaultData();
        } catch (err) {
          status.textContent = `Branch switch failed: ${err}`;
          status.className = "mt-1 text-[10px] text-rose-400";
        }
      });
    }
    container.appendChild(button);
  });
}

async function createHypothesisBranch() {
  const input = document.getElementById("new-hypothesis-name");
  const status = document.getElementById("branch-status");
  const name = input.value.trim();
  if (!name) {
    status.textContent = "Enter a hypothesis name.";
    status.className = "mt-1 text-[10px] text-rose-400";
    return;
  }
  status.textContent = "Creating isolated branch...";
  status.className = "mt-1 text-[10px] text-indigo-300";
  try {
    await tauriInvoke("create_hypothesis_branch", {
      vaultPath: state.vaultPath,
      hypothesisName: name
    });
    input.value = "";
    status.textContent = "";
    await syncVaultData();
  } catch (err) {
    status.textContent = `Branch creation failed: ${err}`;
    status.className = "mt-1 text-[10px] text-rose-400";
  }
}

async function runKnowledgeIntegrityProbe() {
  const status = document.getElementById("hypothesis-workflow-status");
  const button = document.getElementById("run-integrity-probe-btn");
  button.disabled = true;
  status.textContent = "Checking record structure, IDs, statuses, and internal links...";
  status.className = "text-[11px] text-indigo-300";
  try {
    const result = await tauriInvoke("run_knowledge_integrity_probe", {
      vaultPath: state.vaultPath,
      branch: state.currentBranch
    });
    status.textContent = result.message;
    status.className = `text-[11px] ${result.passed ? "text-emerald-400" : "text-rose-400"}`;
    await syncVaultData();
  } catch (err) {
    status.textContent = `Probe failed to run: ${err}`;
    status.className = "text-[11px] text-rose-400";
  } finally {
    button.disabled = false;
  }
}

async function mergeHypothesisToMain() {
  const status = document.getElementById("hypothesis-workflow-status");
  if (!window.confirm(
    `Integrate the current branch (${state.currentBranch}) into main? This updates knowledge records but does not promote propositions.`
  )) {
    return;
  }

  const button = document.getElementById("merge-hypothesis-btn");
  button.disabled = true;
  status.textContent = "Checking probe freshness and merge conflicts...";
  status.className = "text-[11px] text-indigo-300";
  try {
    const result = await tauriInvoke("merge_hypothesis_to_main", {
      vaultPath: state.vaultPath,
      sourceBranch: state.currentBranch
    });
    status.textContent = result;
    status.className = "text-[11px] text-emerald-400";
    await syncVaultData();
  } catch (err) {
    status.textContent = `Integration blocked: ${err}`;
    status.className = "text-[11px] text-rose-400";
  } finally {
    button.disabled = false;
  }
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
    const buildLabel = c.validation_profile
      ? `STRUCTURAL CHECK ${isSuccess ? "PASSED" : "FAILED"}`
      : `PROBE ${isSuccess ? "PASSED" : "FAILED"}`;
    const violations = c.proof_violations || [];
    const violationsHtml = violations.map(v => `<div>• ${escapeHtml(v)}</div>`).join("");
    const candidateConflicts = (c.candidate_conflicts || []).map(id => escapeHtml(id)).join(", ");
    const supportingIds = (c.supporting_ids || []).map(id => escapeHtml(id)).join(", ");
    const counterevidenceIds = (c.counterevidence_ids || []).map(id => escapeHtml(id)).join(", ");
    const proofVerdict = escapeHtml(c.proof_verdict || "UNRESOLVED");

    const card = document.createElement("div");
    card.className = `panel border-l-4 ${isSuccess ? 'border-l-emerald-500' : 'border-l-rose-500'} space-y-2`;
    
    card.innerHTML = `
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono ${
            isSuccess ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
          }">
            ${buildLabel}
          </span>
          <span class="font-mono text-xs text-slate-300 font-semibold">${safeBranch}</span>
        </div>
        <span class="text-xs font-mono text-slate-400">Exit Code: ${safeExit}</span>
      </div>

      <div class="text-xs text-slate-200">${safeMsg}</div>

      ${c.proof_verdict ? `
        <div class="p-2.5 rounded bg-slate-950/80 border border-slate-800 text-[11px] space-y-1">
          <div class="flex items-center justify-between font-medium">
            <span class="text-slate-400">Natural-language assessment (advisory)</span>
            <span class="text-amber-300 font-mono">${proofVerdict}</span>
          </div>
          ${violations.length > 0 ? `
            <div class="text-amber-300/90 pl-2 border-l border-amber-500/30 space-y-0.5">
              ${violationsHtml}
            </div>
          ` : ""}
          ${candidateConflicts ? `<div class="text-slate-400">Possible conflicts to review: ${candidateConflicts}</div>` : ""}
          ${supportingIds ? `<div class="text-slate-400">Supporting IDs: ${supportingIds}</div>` : ""}
          ${counterevidenceIds ? `<div class="text-slate-400">Counterevidence IDs: ${counterevidenceIds}</div>` : ""}
          <div class="text-slate-500">This assessment is not a proof or a truth determination.</div>
        </div>
      ` : ''}

      ${safeCmd ? `
        <div class="text-[11px] font-mono bg-slate-950 p-2 rounded text-slate-400 border border-slate-900">
          $ ${safeCmd}
        </div>
      ` : ''}
      ${c.validation_profile ? `
        <div class="text-[10px] text-slate-500">Profile: ${escapeHtml(c.validation_profile)}. Structural evidence only; this does not establish semantic truth.</div>
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
        <div class="text-[10px] text-indigo-300 font-bold uppercase font-mono">Recorded proposition (${escapeHtml(p.status)})</div>
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
          <span class="text-[10px] font-semibold text-indigo-400 uppercase tracking-wide">Propositions (status is not proof)</span>
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
      circle.setAttribute("r", node.group === "proposition" ? "18" : "14");
      circle.setAttribute("fill", node.group === "proposition" ? "#10b981" : "#6366f1");
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

// Send Agent Prompt via Cockpit (Supports Multi-Turn Follow-Ups)
async function sendAgentPrompt() {
  if (state.isSending) return;

  const input = document.getElementById("agent-input");
  const sendBtn = document.getElementById("send-agent-btn");
  const prompt = input.value.trim();
  if (!prompt) return;

  state.isSending = true;
  input.disabled = true;
  sendBtn.disabled = true;
  sendBtn.textContent = "Thinking...";

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

  // Track user turn in history
  state.chatHistory.push({ role: "user", content: prompt });

  try {
    const response = await tauriInvoke("send_agent_prompt", {
      config: state.modelConfig,
      prompt,
      history: state.chatHistory.slice(0, -1),
      vaultPath: state.vaultPath
    });

    state.chatHistory.push({ role: "assistant", content: response });

    agentDiv.innerHTML = `
      <span class="role">${safeProvider} Agent</span>
      <p class="whitespace-pre-wrap">${escapeHtml(response)}</p>
      <div class="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
        <span class="text-slate-500 font-mono text-[10px]">Context: ${escapeHtml(state.currentBranch)}</span>
        <button class="save-to-vault-btn px-2 py-0.5 rounded text-[10px] bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-slate-700/80 cursor-pointer">
          💾 Save to Knowledge Vault
        </button>
      </div>
    `;

    // Hook up Save to Knowledge Vault button on message
    const saveBtn = agentDiv.querySelector(".save-to-vault-btn");
    if (saveBtn) {
      saveBtn.addEventListener("click", () => {
        openIngestModal({
          guide: response,
          rawText: `User query: ${prompt}\n\nAgent response:\n${response}`,
          commitMessage: `Ingest agent discovery from prompt: ${prompt.slice(0, 40)}...`
        });
      });
    }

    chatContainer.scrollTop = chatContainer.scrollHeight;
    syncVaultData();
  } catch (err) {
    console.error("Chat error:", err);
    agentDiv.innerHTML = `<span class="role text-rose-400">Error</span><p class="text-rose-400">${escapeHtml(err)}</p>`;
  } finally {
    state.isSending = false;
    input.disabled = false;
    sendBtn.disabled = false;
    sendBtn.textContent = "Send to Agent";
    input.focus();
  }
}

// Clear Chat History
function clearChat() {
  state.chatHistory = [];
  const chatContainer = document.getElementById("chat-messages");
  chatContainer.innerHTML = `
    <div class="agent-msg">
      <span class="role">System</span>
      <p>Conversation history reset. Agent runtime initialized with world model context from <code>${escapeHtml(state.currentBranch)}</code>. Ready to accept instructions.</p>
    </div>
  `;
}

// Ingestion & Territory Mapping Modal
function openIngestModal(prefill = null) {
  const modal = document.getElementById("ingest-modal");
  modal.classList.remove("hidden");
  modal.classList.add("flex");

  document.getElementById("ingest-status-msg").textContent = "";
  state.pendingPropositions = [];
  document.getElementById("proposition-claim").value = "";
  document.getElementById("proposition-premises").value = "";
  document.getElementById("proposition-rationale").value = "";
  document.getElementById("proposition-assessment").textContent = "";
  document.getElementById("proposition-assessment").classList.add("hidden");
  document.getElementById("distilled-propositions").textContent = "";
  document.getElementById("distilled-propositions").classList.add("hidden");

  if (prefill) {
    document.getElementById("ingest-raw-text").value = prefill.rawText || "";
    document.getElementById("ingest-territory").value = prefill.territory || "";
    document.getElementById("ingest-guide").value = prefill.guide || "";
    document.getElementById("ingest-tags").value = prefill.tags ? prefill.tags.join(", ") : "general";
    document.getElementById("ingest-commit-msg").value = prefill.commitMessage || "";
  } else {
    document.getElementById("ingest-raw-text").value = "";
    document.getElementById("ingest-territory").value = "";
    document.getElementById("ingest-guide").value = "";
    document.getElementById("ingest-treasures").value = "";
    document.getElementById("ingest-dead-ends").value = "";
    document.getElementById("ingest-hazards").value = "";
    document.getElementById("ingest-tags").value = "general";
    document.getElementById("ingest-commit-msg").value = "";
  }
}

function closeIngestModal() {
  const modal = document.getElementById("ingest-modal");
  modal.classList.add("hidden");
  modal.classList.remove("flex");
}

async function distillWithAI() {
  const rawText = document.getElementById("ingest-raw-text").value.trim();
  const statusMsg = document.getElementById("ingest-status-msg");
  const distillBtn = document.getElementById("distill-btn");

  if (!rawText) {
    statusMsg.textContent = "Please enter some unstructured notes or error logs first.";
    statusMsg.className = "text-xs text-rose-400";
    return;
  }

  statusMsg.textContent = "Distilling unstructured data with AI model...";
  statusMsg.className = "text-xs text-indigo-400 animate-pulse";
  distillBtn.disabled = true;

  try {
    const distilled = await tauriInvoke("distill_unstructured_text", {
      config: state.modelConfig,
      rawText
    });

    state.pendingPropositions = (distilled.propositions || []).map(p => ({
      id: p.id || "",
      claim: p.claim || "",
      premises: p.premises || [],
      rationale: p.rationale || "",
      status: "CONJECTURE"
    }));
    renderDistilledPropositions();
    if (state.pendingPropositions.length > 0) {
      const first = state.pendingPropositions[0];
      document.getElementById("proposition-claim").value = first.claim;
      document.getElementById("proposition-premises").value = first.premises.join("\n");
      document.getElementById("proposition-rationale").value = first.rationale;
    }

    document.getElementById("ingest-territory").value = distilled.territory || "";
    document.getElementById("ingest-guide").value = distilled.guide || "";
    document.getElementById("ingest-tags").value = (distilled.tags || []).join(", ");
    document.getElementById("ingest-commit-msg").value = distilled.commit_message || `Map territory: ${distilled.territory}`;

    if (distilled.treasures && distilled.treasures.length > 0) {
      document.getElementById("ingest-treasures").value = distilled.treasures
        .map(t => `${t.description}${t.rationale ? ' - ' + t.rationale : ''}`)
        .join("\n");
    }

    if (distilled.dead_ends && distilled.dead_ends.length > 0) {
      document.getElementById("ingest-dead-ends").value = distilled.dead_ends
        .map(d => `${d.description}${d.rationale ? ' - ' + d.rationale : ''}`)
        .join("\n");
    }

    if (distilled.known_hazards && distilled.known_hazards.length > 0) {
      document.getElementById("ingest-hazards").value = distilled.known_hazards
        .map(h => `${h.description}${h.rationale ? ' - ' + h.rationale : ''}`)
        .join("\n");
    }

    statusMsg.textContent = "✓ Successfully distilled! Review fields below and commit.";
    statusMsg.className = "text-xs text-emerald-400";
  } catch (err) {
    statusMsg.textContent = `Distillation error: ${err}`;
    statusMsg.className = "text-xs text-rose-400";
  } finally {
    distillBtn.disabled = false;
  }
}

function renderDistilledPropositions() {
  const container = document.getElementById("distilled-propositions");
  if (!state.pendingPropositions.length) {
    container.textContent = "";
    container.classList.add("hidden");
    return;
  }
  container.classList.remove("hidden");
  container.innerHTML = `<div class="font-medium text-indigo-300 mb-1">Distilled claims (saved as conjectures)</div>` +
    state.pendingPropositions.map(p =>
      `<div class="py-1"><span class="text-slate-200">${escapeHtml(p.claim)}</span>` +
      `${p.rationale ? `<div class="text-slate-500">${escapeHtml(p.rationale)}</div>` : ""}</div>`
    ).join("");
}

async function assessProposition() {
  const claim = document.getElementById("proposition-claim").value.trim();
  const result = document.getElementById("proposition-assessment");
  const btn = document.getElementById("assess-proposition-btn");
  if (!claim) {
    result.textContent = "Enter a claim before assessing it.";
    result.classList.remove("hidden");
    return;
  }

  btn.disabled = true;
  result.textContent = "Analyzing cited support and counterevidence...";
  result.classList.remove("hidden");
  try {
    const assessment = await tauriInvoke("assess_proposition", {
      config: state.modelConfig,
      vaultPath: state.vaultPath,
      branch: state.currentBranch,
      claim,
      premises: document.getElementById("proposition-premises").value
        .split("\n").map(line => line.trim()).filter(Boolean),
      rationale: document.getElementById("proposition-rationale").value.trim()
    });
    result.textContent = [
      `Advisory assessment: ${assessment.assessment} (not proof)`,
      assessment.reasoning,
      `Supporting territory IDs: ${assessment.supporting_ids.join(", ") || "none"}`,
      `Counterevidence territory IDs: ${assessment.counterevidence_ids.join(", ") || "none"}`,
      `Assumptions: ${assessment.assumptions.join("; ") || "none listed"}`,
      `Testable predictions: ${assessment.testable_predictions.join("; ") || "none listed"}`
    ].join("\n");
  } catch (err) {
    result.textContent = `Assessment error: ${err}`;
  } finally {
    btn.disabled = false;
  }
}

async function commitIngestToVault() {
  const territory = document.getElementById("ingest-territory").value.trim();
  const guide = document.getElementById("ingest-guide").value.trim();
  const tagsStr = document.getElementById("ingest-tags").value.trim();
  const commitMsg = document.getElementById("ingest-commit-msg").value.trim();
  const statusMsg = document.getElementById("ingest-status-msg");

  if (!territory || !guide) {
    statusMsg.textContent = "Territory name and Guide are required.";
    statusMsg.className = "text-xs text-rose-400";
    return;
  }

  function parseLines(str) {
    return str
      .split("\n")
      .map(line => line.trim())
      .filter(line => line.length > 0)
      .map(line => {
        if (line.includes(" - ")) {
          const parts = line.split(" - ");
          return { description: parts[0].trim(), rationale: parts[1].trim() };
        }
        return { description: line, rationale: null };
      });
  }

  const treasures = parseLines(document.getElementById("ingest-treasures").value);
  const dead_ends = parseLines(document.getElementById("ingest-dead-ends").value);
  const known_hazards = parseLines(document.getElementById("ingest-hazards").value);
  const tags = tagsStr.split(",").map(t => t.trim()).filter(t => t.length > 0);
  const claim = document.getElementById("proposition-claim").value.trim();
  const premises = document.getElementById("proposition-premises").value
    .split("\n").map(line => line.trim()).filter(Boolean);
  const rationale = document.getElementById("proposition-rationale").value.trim();
  const propositions = state.pendingPropositions.map(p => ({
    ...p,
    status: "CONJECTURE"
  }));
  if (claim && !propositions.some(p => p.claim === claim)) {
    propositions.push({
      id: "",
      claim,
      premises,
      rationale: rationale || null,
      status: "CONJECTURE"
    });
  }

  const input = {
    id: null,
    territory,
    guide,
    treasures,
    dead_ends,
    known_hazards,
    propositions,
    tags,
    author_agent_id: "User",
    branch: state.currentBranch,
    commit_message: commitMsg || `Map territory: ${territory}`
  };

  statusMsg.textContent = "Saving to knowledge vault...";
  statusMsg.className = "text-xs text-indigo-400";

  try {
    const id = await tauriInvoke("save_territory", {
      vaultPath: state.vaultPath,
      input
    });

    closeIngestModal();
    await syncVaultData();
  } catch (err) {
    statusMsg.textContent = `Error saving territory: ${err}`;
    statusMsg.className = "text-xs text-rose-400";
  }
}
