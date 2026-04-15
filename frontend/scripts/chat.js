/* ============================
   PromptX Chat Page — JavaScript
   ============================ */

// Auto-detect API URL based on where the page is served from
const API_BASE = (function() {
  const loc = window.location;
  if (loc.protocol === 'file:') return 'http://127.0.0.1:8000/api';
  return `${loc.protocol}//${loc.hostname}:${loc.port || (loc.protocol === 'https:' ? '443' : '80')}/api`;
})();

let currentMode = 'enhance';
let selectedModel = 'gemini';
let currentChatId = null;
let chatSessions = [];

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => {
  try { if (typeof lucide !== 'undefined') lucide.createIcons(); } catch(e) {}
  
  loadChatSessions();
  setupSidebar();
  setupModes();
  setupModelSelector();
  setupChatInput();
  setupWelcomeCards();
  
  // Restore API key
  const apiInput = document.getElementById('api-key-input');
  if (apiInput) {
    apiInput.value = localStorage.getItem('promptx_api_key') || '';
    apiInput.addEventListener('input', (e) => localStorage.setItem('promptx_api_key', e.target.value));
  }
});

// ===== SIDEBAR =====
function setupSidebar() {
  const sidebar = document.getElementById('chat-sidebar');
  const toggle = document.getElementById('sidebar-toggle');
  const closeBtn = document.getElementById('sidebar-close');
  const newChatBtn = document.getElementById('new-chat-btn');
  
  toggle.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
  });
  
  closeBtn.addEventListener('click', () => {
    sidebar.classList.add('collapsed');
  });
  
  newChatBtn.addEventListener('click', () => {
    startNewChat();
  });
  
  // Check localStorage for sidebar state
  const sidebarState = localStorage.getItem('sidebarCollapsed');
  if (sidebarState === 'true') {
    sidebar.classList.add('collapsed');
  }
  
  // Save sidebar state on toggle
  const observer = new MutationObserver(() => {
    localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
  });
  observer.observe(sidebar, { attributes: true, attributeFilter: ['class'] });
}

// ===== MODES =====
function setupModes() {
  const modeItems = document.querySelectorAll('.mode-item');
  modeItems.forEach(item => {
    item.addEventListener('click', () => {
      modeItems.forEach(m => m.classList.remove('active'));
      item.classList.add('active');
      currentMode = item.getAttribute('data-mode');
      updateModeDisplay();
    });
  });
}

function updateModeDisplay() {
  const modeLabels = {
    enhance: 'Enhance Mode',
    analyze: 'Analyze Mode',
    compare: 'Compare Mode'
  };
  const label = modeLabels[currentMode] || 'Enhance Mode';
  
  document.getElementById('topbar-mode').textContent = label;
  document.getElementById('mode-indicator').textContent = label;
}

// ===== MODEL SELECTOR =====
function setupModelSelector() {
  const modelBtns = document.querySelectorAll('.model-option');
  const badge = document.getElementById('topbar-model-badge');

  const modelLabels = {
    gemini: 'Gemini 2.0',
    groq: 'Groq',
    nvidia: 'NVIDIA',
    mistral: 'Mistral',
    llama_405b: 'Llama 405B',
    glm: 'GLM 4.7',
    deepseek: 'DeepSeek',
    kimi: 'Kimi',
    kimi_think: 'Kimi',
    gpt_oss: 'GPT OSS'
  };
  
  modelBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      modelBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectedModel = btn.getAttribute('data-model');
      
      if (badge) badge.textContent = modelLabels[selectedModel] || selectedModel;
      
      showToast('Model changed', `Now using ${btn.textContent.trim()}`, 'success');
    });
  });
}

// ===== WELCOME CARDS & EXAMPLES =====
function setupWelcomeCards() {
  document.querySelectorAll('.welcome-card').forEach(card => {
    card.addEventListener('click', () => {
      const action = card.getAttribute('data-action');
      // Switch mode
      document.querySelectorAll('.mode-item').forEach(m => {
        m.classList.remove('active');
        if (m.getAttribute('data-mode') === action) m.classList.add('active');
      });
      currentMode = action;
      updateModeDisplay();
      document.getElementById('chat-input').focus();
    });
  });
}

function fillPrompt(text) {
  const input = document.getElementById('chat-input');
  input.value = text;
  input.dispatchEvent(new Event('input'));
  input.focus();
}

// ===== CHAT INPUT =====
function setupChatInput() {
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const charCount = document.getElementById('char-count');
  
  input.addEventListener('input', () => {
    sendBtn.disabled = !input.value.trim();
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 150) + 'px';
    charCount.textContent = `${input.value.length} chars`;
  });
  
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (input.value.trim()) handleSend();
    }
  });
  
  sendBtn.addEventListener('click', handleSend);
}

async function handleSend() {
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;
  
  // Start new session if needed
  if (!currentChatId) {
    currentChatId = Date.now().toString();
    chatSessions.unshift({
      id: currentChatId,
      title: message.substring(0, 50),
      messages: [],
      mode: currentMode,
      timestamp: Date.now()
    });
  }
  
  hideWelcome();
  addUserMessage(message);
  saveMsgToSession('user', message);
  
  input.value = '';
  input.style.height = 'auto';
  document.getElementById('send-btn').disabled = true;
  document.getElementById('char-count').textContent = '0 chars';
  
  if (currentMode === 'enhance') await handleEnhance(message);
  else if (currentMode === 'analyze') await handleAnalyze(message);
  else if (currentMode === 'compare') await handleCompare(message);
  
  saveChatSessions();
  renderHistory();
}

function hideWelcome() {
  const el = document.getElementById('welcome-screen');
  if (el) el.remove();
}

// ===== CHAT SESSIONS =====
function loadChatSessions() {
  try { chatSessions = JSON.parse(localStorage.getItem('promptx_sessions') || '[]'); } catch(e) { chatSessions = []; }
  renderHistory();
}

function saveChatSessions() {
  if (chatSessions.length > 30) chatSessions.length = 30;
  localStorage.setItem('promptx_sessions', JSON.stringify(chatSessions));
}

function saveMsgToSession(role, content) {
  const session = chatSessions.find(s => s.id === currentChatId);
  if (session) {
    session.messages.push({ role, content, timestamp: Date.now() });
  }
}

function renderHistory() {
  const list = document.getElementById('history-list');
  const empty = document.getElementById('history-empty');
  
  // Clear old items
  list.querySelectorAll('.history-item').forEach(el => el.remove());
  
  if (chatSessions.length === 0) {
    empty.style.display = 'block';
    return;
  }
  
  empty.style.display = 'none';
  
  chatSessions.forEach(session => {
    const btn = document.createElement('button');
    btn.className = `history-item${session.id === currentChatId ? ' active' : ''}`;
    btn.innerHTML = `<span class="history-icon">&gt;</span><span class="history-text">${escapeHtml(session.title)}</span>`;
    btn.addEventListener('click', () => loadSession(session.id));
    list.appendChild(btn);
  });
}

function loadSession(sessionId) {
  const session = chatSessions.find(s => s.id === sessionId);
  if (!session) return;
  
  currentChatId = sessionId;
  currentMode = session.mode || 'enhance';
  
  // Update mode UI
  document.querySelectorAll('.mode-item').forEach(m => {
    m.classList.remove('active');
    if (m.getAttribute('data-mode') === currentMode) m.classList.add('active');
  });
  updateModeDisplay();
  
  // Rebuild messages
  const container = document.getElementById('chat-messages');
  container.innerHTML = '';
  
  session.messages.forEach(msg => {
    if (msg.role === 'user') addUserMessage(msg.content);
    else addAssistantMessage(msg.content);
  });
  
  renderHistory();
}

function startNewChat() {
  currentChatId = null;
  const container = document.getElementById('chat-messages');
  container.innerHTML = `
    <div class="welcome-screen" id="welcome-screen">
      <img src="Public/bot-img.png" alt="PromptX" class="welcome-logo">
      <h1>PromptX</h1>
      <p>Pick a mode below, type your prompt, and hit send.</p>
      <div class="welcome-cards">
        <button class="welcome-card" data-action="enhance">
          <div class="wc-icon">✦</div>
          <div class="wc-text"><strong>Enhance Prompt</strong><span>Rewrite it to be clearer and more detailed</span></div>
        </button>
        <button class="welcome-card" data-action="analyze">
          <div class="wc-icon">◈</div>
          <div class="wc-text"><strong>Analyze Quality</strong><span>Get a score and tips to improve it</span></div>
        </button>
        <button class="welcome-card" data-action="compare">
          <div class="wc-icon">⇄</div>
          <div class="wc-text"><strong>Compare Versions</strong><span>See 3 different rewrites side by side</span></div>
        </button>
      </div>
      <div class="welcome-examples">
        <div class="examples-label">Try an example:</div>
        <button class="example-chip" onclick="fillPrompt('Write a blog post about artificial intelligence')">Write a blog about AI</button>
        <button class="example-chip" onclick="fillPrompt('Create a Python function to sort a list of dictionaries by key')">Sort list of dicts in Python</button>
        <button class="example-chip" onclick="fillPrompt('Design a marketing strategy for a SaaS product launch')">SaaS marketing strategy</button>
      </div>
    </div>
  `;
  setupWelcomeCards();
  renderHistory();
}

// ===== MESSAGE RENDERING =====
function addUserMessage(text) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'message user';

  // Render URLs as clickable link previews inside the user bubble
  const urls = extractUrls(text);
  let displayHtml = escapeHtml(text);
  urls.forEach(url => {
    const domain = getDomain(url);
    const favicon = getFaviconUrl(url);
    const chip = `<a href="${escapeHtml(url)}" target="_blank" rel="noopener" class="url-inline-chip">` +
      (favicon ? `<img src="${favicon}" width="14" height="14" style="border-radius:2px;flex-shrink:0;" onerror="this.style.display='none'">` : '🌐') +
      `<span>${escapeHtml(domain)}</span><span style="opacity:0.5;font-size:0.65rem;">↗</span></a>`;
    displayHtml = displayHtml.replace(escapeHtml(url), chip);
  });

  div.innerHTML = `
    <div class="message-content">${displayHtml}</div>
    <div class="message-avatar">U</div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function addAssistantMessage(content) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'message assistant';
  div.innerHTML = `
    <div class="message-avatar"><img src="Public/bot-img.png" alt="AI" style="width:100%;height:100%;object-fit:cover;border-radius:10px;"></div>
    <div class="message-content">${content}</div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  try { if (typeof lucide !== 'undefined') lucide.createIcons(); } catch(e) {}
  return div;
}

// ===== URL DETECTION =====
const URL_REGEX = /https?:\/\/[^\s<>"']+|www\.[^\s<>"']+/gi;

function addLoadingMessage() {
  return addAssistantMessage(`
    <div class="typing-dots">
      <span></span><span></span><span></span>
    </div>
  `);
}

function extractUrls(text) {
  const matches = text.match(URL_REGEX) || [];
  return matches.map(u => u.startsWith('http') ? u : `https://${u}`);
}

function getDomain(url) {
  try { return new URL(url).hostname.replace('www.', ''); } catch { return url; }
}

function getFaviconUrl(url) {
  try {
    const origin = new URL(url).origin;
    return `https://www.google.com/s2/favicons?domain=${origin}&sz=32`;
  } catch { return null; }
}

// ===== THINKING PROGRESS UI =====
function addThinkingMessage(steps) {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'message assistant thinking-msg';
  div.innerHTML = `
    <div class="message-avatar"><img src="Public/bot-img.png" alt="AI" style="width:100%;height:100%;object-fit:cover;border-radius:10px;"></div>
    <div class="message-content thinking-content">
      <div class="thinking-header">
        <div class="thinking-spinner"></div>
        <span class="thinking-title">Analyzing...</span>
      </div>
      <div class="thinking-steps" id="thinking-steps-${div.id || Date.now()}">
        ${steps.map((s, i) => `
          <div class="thinking-step" data-step="${i}">
            <span class="step-icon">○</span>
            <span class="step-text">${s}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;

  // Give the steps div a stable ID
  const stepsEl = div.querySelector('.thinking-steps');
  stepsEl.id = `ts-${Date.now()}`;
  div._stepsId = stepsEl.id;

  return div;
}

function activateThinkingStep(thinkingDiv, stepIndex, status = 'active') {
  // status: 'active' | 'done' | 'error'
  const steps = thinkingDiv.querySelectorAll('.thinking-step');
  steps.forEach((s, i) => {
    if (i < stepIndex) {
      s.querySelector('.step-icon').textContent = '✓';
      s.classList.remove('active', 'error');
      s.classList.add('done');
    } else if (i === stepIndex) {
      s.querySelector('.step-icon').textContent = status === 'error' ? '✗' : '◉';
      s.classList.remove('done', 'error');
      s.classList.add(status === 'error' ? 'error' : 'active');
    }
  });
  const titleEl = thinkingDiv.querySelector('.thinking-title');
  if (titleEl) {
    const texts = thinkingDiv.querySelectorAll('.thinking-step .step-text');
    if (texts[stepIndex]) titleEl.textContent = texts[stepIndex].textContent;
  }
  thinkingDiv.closest('.chat-messages-area, #chat-messages').scrollTop = 99999;
}

// ===== ENHANCE =====
async function handleEnhance(prompt) {
  const urls = extractUrls(prompt);
  const isUrlRequest = urls.length > 0;

  // For URL requests show a richer thinking UI
  let loadingMsg;
  if (isUrlRequest) {
    const domain = getDomain(urls[0]);
    loadingMsg = addThinkingMessage([
      `Connecting to ${domain}`,
      `Crawling pages (features, pricing, docs, API...)`,
      `Searching web for tech stack & documentation`,
      `Synthesising deep analysis with AI`,
    ]);
    activateThinkingStep(loadingMsg, 0);
  } else {
    loadingMsg = addLoadingMessage();
  }

  try {
    const body = { prompt };
    if (selectedModel !== 'auto') body.model = selectedModel;

    const apiKey = document.getElementById('api-key-input')?.value || '';
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['X-API-Key'] = apiKey;

    // Simulate step progression for URL requests (backend is synchronous)
    let stepTimer;
    if (isUrlRequest) {
      let step = 0;
      stepTimer = setInterval(() => {
        step = Math.min(step + 1, 3);
        activateThinkingStep(loadingMsg, step);
      }, 4000);
    }

    const res = await fetch(`${API_BASE}/enhance`, {
      method: 'POST', headers, body: JSON.stringify(body)
    });
    const result = await res.json();

    if (stepTimer) clearInterval(stepTimer);
    loadingMsg.remove();

    if (result.success) {
      // ── Welcome / greeting ──────────────────────────────────────────────
      if (result.type === 'welcome') {
        const html = `<div class="welcome-reply">${renderMarkdown(result.enhanced)}</div>`;
        addAssistantMessage(html);
        saveMsgToSession('assistant', html);
        return;
      }

      // ── URL / website analysis ──────────────────────────────────────────
      if (result.type === 'url_analysis') {
        const url = result.url;
        const domain = getDomain(url);
        const favicon = getFaviconUrl(url);
        const pagesScraped = result.pages_scraped || 0;
        const totalChars = result.total_chars || result.char_count || 0;
        const rawText = result.enhanced || '';

        // ── Page chips ──────────────────────────────────────────────────
        const pageChips = (result.pages || []).map(p => {
          const path = (() => { try { return new URL(p.url).pathname || '/'; } catch { return '/'; } })();
          return `<a href="${escapeHtml(p.url)}" target="_blank" rel="noopener" class="page-chip" title="${escapeHtml(p.url)}">
            <img src="https://www.google.com/s2/favicons?domain=${escapeHtml(p.url)}&sz=16" width="12" height="12" style="border-radius:2px;flex-shrink:0;" onerror="this.style.display='none'">
            <span>${escapeHtml(path === '/' ? domain : path)}</span>
          </a>`;
        }).join('');

        // ── Split the AI response into named sections ───────────────────
        // Sections are delimited by ## or # headings
        function splitSections(text) {
          const lines = text.split('\n');
          const sections = [];
          let current = { level: 2, title: 'Overview', body: [] };
          let hasHeaders = false;
          
          for (const line of lines) {
            const h1 = line.match(/^#\s+(.+)/);
            const h2 = line.match(/^##\s+(.+)/);
            const h3 = line.match(/^###\s+(.+)/);
            
            if (h1 || h2 || h3) {
              hasHeaders = true;
              if (current && current.body.join('').trim().length > 0) sections.push(current);
              current = { level: 2, title: (h1 || h2 || h3)[1].trim(), body: [] };
            } else if (current) {
              current.body.push(line);
            }
          }
          
          if (current && current.body.join('').trim().length > 0) sections.push(current);
          return sections;
        }

        // ── Detect if a section is the "How to Build" or "AI Prompts" section
        function isBuildSection(title) {
          const t = title.toLowerCase();
          return t.includes('how to build') || t.includes('build this') || t.includes('step-by-step');
        }
        function isAgentSection(title) {
          const t = title.toLowerCase();
          return t.includes('ai agent') || t.includes('ready prompt') || t.includes('copy & use') || t.includes('copy and use');
        }
        function isFeatureSection(title) {
          const t = title.toLowerCase();
          return t.includes('feature') || t.includes('functionality');
        }

        // ── Build use-case diagram from feature list ────────────────────
        function buildUseCaseDiagram(text) {
          // Extract bullet points that look like features
          const features = [];
          const lines = text.split('\n');
          for (const line of lines) {
            const m = line.match(/^[-*•]\s+\*{0,2}([^*\n:]{4,60})\*{0,2}/);
            if (m) features.push(m[1].trim().replace(/[^a-zA-Z0-9 &]/g, '').trim());
          }
          const top = features.slice(0, 10);
          if (top.length < 3) return '';
          const nodes = top.map((f, i) => `  User --> F${i}["${f}"]`).join('\n');
          return 'flowchart TD\n  User(["👤 User"])\n' + nodes;
        }

        const sections = splitSections(rawText);

        // ── Render each section as a card ───────────────────────────────
        let sectionsHtml = '';
        let buildHtml = '';
        let agentHtml = '';
        let featureDiagram = '';

        for (const sec of sections) {
          const bodyText = sec.body.join('\n');
          const rendered = renderMarkdown(bodyText);

          if (isAgentSection(sec.title)) {
            // AI Agent prompts — special styling
            agentHtml += `
              <div class="analysis-section agent-section">
                <div class="section-heading agent-heading">
                  <span class="section-emoji">🤖</span>
                  <span>${escapeHtml(sec.title)}</span>
                </div>
                <div class="agent-section-body">${rendered}</div>
              </div>`;
          } else if (isBuildSection(sec.title)) {
            buildHtml += `
              <div class="analysis-section build-section">
                <div class="section-heading build-heading">
                  <span class="section-emoji">🏗️</span>
                  <span>${escapeHtml(sec.title)}</span>
                </div>
                <div class="build-section-body">${rendered}</div>
              </div>`;
          } else if (isFeatureSection(sec.title)) {
            if (!featureDiagram) featureDiagram = buildUseCaseDiagram(bodyText);
            sectionsHtml += `
              <details class="analysis-section feature-section" open>
                <summary class="section-heading feature-heading">
                  <span class="section-emoji">✨</span>
                  <span>${escapeHtml(sec.title)}</span>
                  <span class="section-toggle">▾</span>
                </summary>
                <div class="section-body">${rendered}</div>
              </details>`;
          } else {
            // Generic collapsible section
            const emoji = sec.title.match(/^[\u{1F300}-\u{1FFFF}🌐✨🏗️🔌📡🎨📊🔐⚠️💡]/u)?.[0] || '📌';
            sectionsHtml += `
              <details class="analysis-section" open>
                <summary class="section-heading">
                  <span class="section-emoji">${emoji}</span>
                  <span>${escapeHtml(sec.title.replace(/^[\u{1F300}-\u{1FFFF}🌐✨🏗️🔌📡🎨📊🔐⚠️💡]\s*/u, ''))}</span>
                  <span class="section-toggle">▾</span>
                </summary>
                <div class="section-body">${rendered}</div>
              </details>`;
          }
        }

        // ── Use-case diagram block ──────────────────────────────────────
        // We render it directly into a <pre class="mermaid"> to avoid DOMPurify stripping the mermaid script/classes
        const diagramHtml = featureDiagram ? `
          <div class="analysis-section diagram-section">
            <div class="section-heading diagram-heading">
              <span class="section-emoji">📐</span>
              <span>Use Case Diagram</span>
            </div>
            <div class="section-body"><pre class="mermaid" style="background:transparent;border:none;">\n${featureDiagram}\n</pre></div>
          </div>` : '';

        const html = `
          <div class="analysis-card url-analysis-card">

            <!-- ── Site header ── -->
            <div class="url-site-header">
              <div class="url-site-info">
                ${favicon ? `<img src="${favicon}" width="22" height="22" class="url-favicon" onerror="this.style.display='none'">` : ''}
                <div>
                  <div class="url-site-title">${escapeHtml(result.page_title || result.site_title || domain)}</div>
                  <a href="${escapeHtml(url)}" target="_blank" rel="noopener" class="url-site-link">${escapeHtml(url)}</a>
                </div>
              </div>
              <div class="url-badges">
                <span class="url-badge badge-cyan">🌐 Deep Analysis</span>
                <span class="url-badge badge-mono">${result.model.toUpperCase()}</span>
              </div>
            </div>

            <!-- ── Stats row ── -->
            <div class="url-stats-row">
              <div class="url-stat">
                <span class="url-stat-value">${pagesScraped}</span>
                <span class="url-stat-label">pages crawled</span>
              </div>
              <div class="url-stat">
                <span class="url-stat-value">${totalChars > 0 ? (totalChars/1000).toFixed(0)+'k' : '—'}</span>
                <span class="url-stat-label">chars read</span>
              </div>
              <div class="url-stat">
                <span class="url-stat-value">${domain}</span>
                <span class="url-stat-label">domain</span>
              </div>
            </div>

            <!-- ── Pages crawled chips ── -->
            ${pageChips ? `
            <div class="url-pages-section">
              <div class="url-pages-label">Pages crawled</div>
              <div class="url-pages-chips">${pageChips}</div>
            </div>` : ''}

            ${result.scrape_error ? `<div class="url-scrape-warning">⚠️ Could not scrape live content — analysis from web search only</div>` : ''}

            <!-- ── Analysis sections ── -->
            <div class="url-analysis-body">
              ${sectionsHtml}
              ${diagramHtml}

              ${buildHtml ? `
              <div class="build-divider">
                <span>🏗️ HOW TO BUILD THIS</span>
              </div>
              ${buildHtml}` : ''}

              ${agentHtml ? `
              <div class="build-divider agent-divider">
                <span>🤖 AI AGENT READY PROMPTS</span>
              </div>
              ${agentHtml}` : ''}
            </div>

            <!-- ── Actions ── -->
            <div class="message-actions" style="padding:0 1.25rem 1rem;">
              <button onclick="copyText(decodeURIComponent('${encodeURIComponent(rawText).replace(/'/g, '%27')}'))">
                <i data-lucide="copy"></i> Copy Full Analysis
              </button>
              <a href="${escapeHtml(url)}" target="_blank" rel="noopener" class="url-visit-btn">
                <i data-lucide="external-link"></i> Open Site
              </a>
            </div>
          </div>
        `;
        addAssistantMessage(html);
        saveMsgToSession('assistant', html);
        try { if (typeof lucide !== 'undefined') lucide.createIcons(); } catch(e) {}
        try { if (window.mermaid) mermaid.run({ querySelector: '.mermaid' }); } catch(e) {}
        return;
      }

      // ── Deep research ───────────────────────────────────────────────────
      if (result.type === 'deep_research') {
        const html = `
          <div class="analysis-card">
            <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:1rem;flex-wrap:wrap;">
              <span style="font-size:0.75rem;font-weight:700;color:#f97316;background:rgba(249,115,22,0.1);padding:0.25rem 0.75rem;border-radius:100px;border:1px solid rgba(249,115,22,0.3);">🔬 Deep Research</span>
              <span style="font-size:0.72rem;color:var(--text-secondary);background:var(--primary-light);padding:0.2rem 0.65rem;border-radius:100px;border:1px solid var(--border);font-family:var(--font-mono);">${result.model.toUpperCase()}</span>
              <span style="font-size:0.72rem;color:var(--text-secondary);background:var(--primary-light);padding:0.2rem 0.65rem;border-radius:100px;border:1px solid var(--border);font-family:var(--font-mono);">${result.classification.category.toUpperCase()}</span>
            </div>
            ${result.analysis ? `
            <details style="margin-bottom:1rem;">
              <summary style="cursor:pointer;font-size:0.78rem;color:var(--text-muted);padding:0.5rem;background:rgba(0,0,0,0.2);border-radius:6px;border:1px solid var(--border);">📋 Request Analysis (expand)</summary>
              <div style="padding:0.75rem;background:rgba(0,0,0,0.15);border-radius:0 0 6px 6px;font-size:0.82rem;color:var(--text-secondary);line-height:1.6;border:1px solid var(--border);border-top:none;">${renderMarkdown(result.analysis)}</div>
            </details>` : ''}
            <div style="line-height:1.8;">${renderMarkdown(result.enhanced)}</div>
            <div class="message-actions" style="margin-top:1rem;">
              <button onclick="copyText(decodeURIComponent('${encodeURIComponent(result.enhanced).replace(/'/g, '%27')}'))">
                <i data-lucide="copy"></i> Copy Full Answer
              </button>
            </div>
          </div>
        `;
        addAssistantMessage(html);
        saveMsgToSession('assistant', html);
        try { if (typeof lucide !== 'undefined') lucide.createIcons(); } catch(e) {}
        return;
      }

      // ── Standard enhancement ────────────────────────────────────────────
      const html = `
        <div class="analysis-card">
          <h3 style="margin-bottom:1rem;color:var(--primary);font-family:var(--font-mono);font-size:0.9rem;">[&gt;_] Enhanced Prompt</h3>
          <div style="background:rgba(0,0,0,0.3);padding:1.15rem;border-radius:10px;margin-bottom:1rem;line-height:1.75;border:1px solid var(--border);">
            ${renderMarkdown(result.enhanced)}
          </div>
          <div style="display:flex;gap:0.5rem;align-items:center;margin-bottom:0.85rem;flex-wrap:wrap;">
            <span style="font-size:0.72rem;color:var(--text-secondary);background:var(--primary-light);padding:0.2rem 0.65rem;border-radius:100px;border:1px solid var(--border);font-family:var(--font-mono);">${result.model.toUpperCase()}</span>
            <span style="font-size:0.72rem;color:var(--text-secondary);background:var(--primary-light);padding:0.2rem 0.65rem;border-radius:100px;border:1px solid var(--border);font-family:var(--font-mono);">${result.classification.category.toUpperCase()}</span>
            <span style="font-size:0.72rem;color:var(--primary);background:var(--primary-light);padding:0.2rem 0.65rem;border-radius:100px;border:1px solid var(--border);font-family:var(--font-mono);">${result.original_score.quality} → ${result.enhanced_score.quality} (+${result.improvement} pts)</span>
          </div>
          <div class="message-actions">
            <button onclick="copyText(decodeURIComponent('${encodeURIComponent(result.enhanced).replace(/'/g, '%27')}'))">
              <i data-lucide="copy"></i> Copy
            </button>
          </div>
        </div>
      `;
      addAssistantMessage(html);
      saveMsgToSession('assistant', html);
    } else {
      const errHtml = `<div class="error-msg">${escapeHtml(result.error || 'Enhancement failed')}</div>`;
      addAssistantMessage(errHtml);
      saveMsgToSession('assistant', errHtml);
    }
  } catch (error) {
    if (loadingMsg) loadingMsg.remove();
    const errHtml = `<div class="error-msg">Connection failed — is the server running at ${API_BASE}?</div>`;
    addAssistantMessage(errHtml);
    saveMsgToSession('assistant', errHtml);
  }
}

// ===== ANALYZE =====
async function handleAnalyze(prompt) {
  const loadingMsg = addLoadingMessage();

  try {
    const body = { prompt };
    if (selectedModel !== 'auto') body.model = selectedModel;

    const apiKey = document.getElementById('api-key-input')?.value || '';
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['X-API-Key'] = apiKey;

    const res = await fetch(`${API_BASE}/quality-heatmap`, {
      method: 'POST', headers, body: JSON.stringify(body)
    });
    const result = await res.json();
    loadingMsg.remove();

    if (result.success) {
      const a = result.data;
      const m = a.metrics;
      const html = `
        <div class="analysis-card">
          <h3 style="margin-bottom:1.25rem;color:var(--primary);font-family:var(--font-mono);font-size:0.9rem;">[///] Quality Analysis</h3>
          <div style="display:flex;gap:2rem;justify-content:center;margin-bottom:1.5rem;padding:1.25rem;background:rgba(0,0,0,0.3);border-radius:10px;border:1px solid var(--border);">
            <div style="text-align:center;">
              <div style="font-size:2.2rem;font-weight:800;color:var(--primary);font-family:var(--font-display);text-shadow:0 0 20px rgba(0,255,65,0.3);">${a.overall}</div>
              <div style="color:var(--text-muted);font-size:0.72rem;font-family:var(--font-mono);">SCORE</div>
            </div>
            <div style="text-align:center;">
              <div style="font-size:2.2rem;font-weight:800;color:var(--primary);font-family:var(--font-display);text-shadow:0 0 20px rgba(0,255,65,0.3);">${a.grade}</div>
              <div style="color:var(--text-muted);font-size:0.72rem;font-family:var(--font-mono);">GRADE</div>
            </div>
          </div>
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0.6rem;margin-bottom:1.25rem;">
            ${Object.entries(m).map(([k,v]) => `
              <div style="background:rgba(0,0,0,0.3);padding:0.75rem;border-radius:8px;border:1px solid var(--border);">
                <div style="font-size:0.68rem;color:var(--text-muted);margin-bottom:0.35rem;text-transform:uppercase;font-family:var(--font-mono);">${k.replace('_',' ')}</div>
                <div style="height:5px;background:rgba(255,255,255,0.05);border-radius:3px;overflow:hidden;margin-bottom:0.35rem;">
                  <div style="height:100%;width:${(v.score/10)*100}%;background:linear-gradient(90deg,var(--primary),var(--accent));border-radius:3px;box-shadow:0 0 8px rgba(0,255,65,0.3);"></div>
                </div>
                <div style="font-size:0.9rem;font-weight:700;color:var(--primary);font-family:var(--font-mono);">${v.score}/10</div>
              </div>
            `).join('')}
          </div>
          ${a.suggestions.length > 0 ? `
            <div style="background:var(--primary-light);border:1px solid var(--border);border-radius:10px;padding:1rem;">
              <h4 style="margin-bottom:0.6rem;color:var(--primary);font-size:0.8rem;font-family:var(--font-mono);">[TIP] Suggestions</h4>
              ${a.suggestions.map(s => `
                <div style="margin-bottom:0.6rem;padding-bottom:0.6rem;border-bottom:1px solid var(--border);">
                  <div style="font-weight:600;color:var(--primary);margin-bottom:0.25rem;font-size:0.78rem;">${s.category}</div>
                  <div style="color:var(--text-secondary);font-size:0.76rem;margin-bottom:0.25rem;">${s.issue}</div>
                  <div style="color:var(--success);font-size:0.76rem;font-family:var(--font-mono);">[FIX] ${s.fix}</div>
                </div>
              `).join('')}
            </div>
          ` : '<div style="color:var(--success);padding:0.75rem;text-align:center;font-family:var(--font-mono);font-size:0.85rem;">[OK] Your prompt looks great!</div>'}
        </div>
      `;
      addAssistantMessage(html);
      saveMsgToSession('assistant', html);
    } else {
      const errHtml = `<div style="color:var(--error);padding:0.75rem;font-family:var(--font-mono);font-size:0.85rem;">[ERR] ${escapeHtml(result.error || 'Analysis failed')}</div>`;
      addAssistantMessage(errHtml);
      saveMsgToSession('assistant', errHtml);
    }
  } catch (error) {
    loadingMsg.remove();
    const errHtml = `<div style="color:var(--error);padding:0.75rem;font-family:var(--font-mono);font-size:0.85rem;">[ERR] Connection failed</div>`;
    addAssistantMessage(errHtml);
    saveMsgToSession('assistant', errHtml);
  }
}

// ===== COMPARE =====
async function handleCompare(prompt) {
  const loadingMsg = addLoadingMessage();

  try {
    const body = { prompt, include_comparison: true };
    if (selectedModel !== 'auto') body.model = selectedModel;

    const apiKey = document.getElementById('api-key-input')?.value || '';
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['X-API-Key'] = apiKey;

    const res = await fetch(`${API_BASE}/ab-test`, {
      method: 'POST', headers, body: JSON.stringify(body)
    });
    const result = await res.json();
    loadingMsg.remove();

    if (result.success) {
      const c = result.data;
      const icons = { concise: '[MIN]', detailed: '[MAX]', structured: '[SYS]' };
      const html = `
        <div class="analysis-card">
          <h3 style="margin-bottom:1.25rem;color:var(--primary);font-family:var(--font-mono);font-size:0.9rem;">[&lt;&gt;] A/B Test Results</h3>
          <div style="background:var(--primary-light);border:1px solid var(--border);border-radius:10px;padding:0.85rem;margin-bottom:1.25rem;font-family:var(--font-mono);font-size:0.8rem;">
            <strong style="color:var(--primary);">[BEST]</strong>
            <span style="color:var(--text-primary);"> ${c.recommendation.best_variation.toUpperCase()} — ${c.recommendation.reason}</span>
          </div>
          <div style="display:grid;gap:0.6rem;">
            ${Object.entries(c.variations).map(([type, v]) => `
              <div style="background:rgba(0,0,0,0.3);border:1px solid var(--border);border-radius:10px;padding:1rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.6rem;">
                  <h4 style="text-transform:uppercase;font-size:0.85rem;font-family:var(--font-mono);color:var(--primary);">${icons[type]||'[VAR]'} ${type}</h4>
                  <span style="font-size:0.68rem;color:var(--text-muted);font-family:var(--font-mono);">${v.model||''}</span>
                </div>
                <div style="background:rgba(0,0,0,0.3);padding:0.75rem;border-radius:8px;margin-bottom:0.6rem;line-height:1.6;font-size:0.82rem;border:1px solid var(--border);">
                  ${renderMarkdown(v.text)}
                </div>
                <div style="display:flex;gap:1rem;font-size:0.72rem;color:var(--text-muted);font-family:var(--font-mono);">
                  <span>QUALITY: <strong style="color:var(--primary);">${v.quality.overall}/10</strong></span>
                  <span>LENGTH: <strong style="color:var(--text-primary);">${v.length}</strong></span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
      addAssistantMessage(html);
      saveMsgToSession('assistant', html);
    } else {
      const errHtml = `<div style="color:var(--error);padding:0.75rem;font-family:var(--font-mono);font-size:0.85rem;">[ERR] ${escapeHtml(result.error || 'Compare failed')}</div>`;
      addAssistantMessage(errHtml);
      saveMsgToSession('assistant', errHtml);
    }
  } catch (error) {
    loadingMsg.remove();
    const errHtml = `<div style="color:var(--error);padding:0.75rem;font-family:var(--font-mono);font-size:0.85rem;">[ERR] Connection failed</div>`;
    addAssistantMessage(errHtml);
    saveMsgToSession('assistant', errHtml);
  }
}

// ===== UTILITIES =====
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function renderMarkdown(text) {
  if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
    return DOMPurify.sanitize(marked.parse(text));
  }
  return escapeHtml(text);
}

function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => {
      showToast('[OK] Copied', 'Text copied to clipboard', 'success');
    }).catch(() => fallbackCopy(text));
  } else {
    fallbackCopy(text);
  }
}

function fallbackCopy(text) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0;';
  document.body.appendChild(ta);
  ta.focus(); ta.select();
  try { document.execCommand('copy'); showToast('[OK] Copied', 'Text copied', 'success'); }
  catch(e) { showToast('[ERR]', 'Copy failed', 'error'); }
  document.body.removeChild(ta);
}

function showToast(title, message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<div class="toast-content"><div class="toast-title">${title}</div><div class="toast-description">${message}</div></div>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}
