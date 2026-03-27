const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.protocol === 'file:';
const API_BASE = isLocal ? 'http://127.0.0.1:5000/api' : '/api';
let currentMode = 'enhance';
let selectedModel = 'auto';

document.addEventListener('DOMContentLoaded', () => {
  try {
    if (typeof lucide !== 'undefined') {
      lucide.createIcons();
    }
  } catch (e) {
    console.error('Failed to initialize icons:', e);
  }
  setupQuickActions();
  setupModelSelector();
  setupSidebarToggle();
  
  const apiInput = document.getElementById('api-key-input');
  if (apiInput) {
      apiInput.value = localStorage.getItem('promptx_api_key') || '';
      apiInput.addEventListener('input', (e) => localStorage.setItem('promptx_api_key', e.target.value));
  }
});

// Navigation
function setupSidebarToggle() {
  const sidebar = document.getElementById('sidebar');
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const sidebarClose = document.getElementById('sidebar-close');

  // Initial state based on screen size to prevent dual headers
  if (window.innerWidth > 1024) {
    if (!sidebar.classList.contains('hidden')) {
      sidebarToggle.classList.add('hidden-toggle');
    }
  } else {
    sidebar.classList.add('hidden');
    sidebarToggle.classList.remove('hidden-toggle');
  }
  
  sidebarToggle.addEventListener('click', () => {
    sidebar.classList.remove('hidden');
    sidebarToggle.classList.add('hidden-toggle');
  });
  
  sidebarClose.addEventListener('click', () => {
    sidebar.classList.add('hidden');
    sidebarToggle.classList.remove('hidden-toggle');
  });
  
  // Close sidebar when clicking outside on mobile
  document.addEventListener('click', (e) => {
    if (window.innerWidth <= 1024) {
      if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
        if (!sidebar.classList.contains('hidden')) {
          sidebar.classList.add('hidden');
          sidebarToggle.classList.remove('hidden-toggle');
        }
      }
    }
  });
}

function setupModelSelector() {
  const customSelect = document.getElementById('custom-model-select');
  if (!customSelect) return;
  const selected = customSelect.querySelector('.select-selected');
  const itemsContainer = customSelect.querySelector('.select-items');
  const items = itemsContainer.querySelectorAll('div');

  selected.addEventListener('click', (e) => {
    e.stopPropagation();
    itemsContainer.classList.toggle('select-hide');
    selected.classList.toggle('open');
  });

  items.forEach(item => {
    item.addEventListener('click', (e) => {
      e.stopPropagation();
      selectedModel = item.getAttribute('data-value');
      
      const iconClass = item.getAttribute('data-icon');
      const text = item.querySelector('span').textContent;
      
      selected.innerHTML = `<i data-lucide="${iconClass}"></i> <span>${text}</span> <i data-lucide="chevron-down" class="chevron"></i>`;
      try { if (typeof lucide !== 'undefined') lucide.createIcons(); } catch(err){}
      
      items.forEach(i => i.classList.remove('same-as-selected'));
      item.classList.add('same-as-selected');
      
      itemsContainer.classList.add('select-hide');
      selected.classList.remove('open');
      
      showToast('Model Changed', `Switched to ${text}`, 'success');
    });
  });

  document.addEventListener('click', () => {
    itemsContainer.classList.add('select-hide');
    selected.classList.remove('open');
  });
}

function setupNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  const newChatBtn = document.getElementById('new-chat-btn');
  
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      navItems.forEach(n => n.classList.remove('active'));
      item.classList.add('active');
      currentMode = item.getAttribute('data-mode');
      updateModeIndicator();
      
      if (currentMode === 'history') {
        showHistory();
      }
    });
  });
  
  newChatBtn.addEventListener('click', () => {
    document.getElementById('chat-messages').innerHTML = `
      <div class="welcome-screen" id="welcome-screen">
        <img src="Public/bot-img.png" alt="PromptX" class="welcome-logo">
        <h1>PROMPTX</h1>
        <p>Transform your prompts with AI</p>
        
        <div class="quick-actions">
          <button class="quick-action" data-action="enhance">
            <i data-lucide="sparkles"></i>
            <div>
              <strong>Enhance Prompt</strong>
              <span>Make it professional</span>
            </div>
          </button>
          <button class="quick-action" data-action="analyze">
            <i data-lucide="activity"></i>
            <div>
              <strong>Analyze Quality</strong>
              <span>Get detailed scores</span>
            </div>
          </button>
          <button class="quick-action" data-action="compare">
            <i data-lucide="git-compare"></i>
            <div>
              <strong>Compare Variations</strong>
              <span>A/B test prompts</span>
            </div>
          </button>
        </div>
      </div>
    `;
    try { if (typeof lucide !== 'undefined') lucide.createIcons(); } catch(e){}
    setupQuickActions();
  });
}

function updateModeIndicator() {
  const modeNames = {
    enhance: 'Enhance Mode',
    analyze: 'Analyze Mode',
    compare: 'Compare Mode',
    history: 'History Mode'
  };
  document.getElementById('mode-indicator').textContent = modeNames[currentMode];
}

// Chat Input
function setupChatInput() {
  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  
  chatInput.addEventListener('input', () => {
    sendBtn.disabled = !chatInput.value.trim();
    chatInput.style.height = 'auto';
    chatInput.style.height = chatInput.scrollHeight + 'px';
  });
  
  chatInput.addEventListener('keydown', (e) => {
    if ((e.key === 'Enter' || e.keyCode === 13) && !e.shiftKey) {
      e.preventDefault();
      if (chatInput.value.trim()) {
        handleSend();
      }
    }
  });
  
  sendBtn.addEventListener('click', handleSend);
}

async function handleSend() {
  const chatInput = document.getElementById('chat-input');
  const message = chatInput.value.trim();
  if (!message) return;
  
  hideWelcome();
  addUserMessage(message);
  autoSaveToHistory(message);
  
  chatInput.value = '';
  chatInput.style.height = 'auto';
  document.getElementById('send-btn').disabled = true;
  
  if (currentMode === 'enhance') {
    await handleEnhance(message);
  } else if (currentMode === 'analyze') {
    await handleAnalyze(message);
  } else if (currentMode === 'compare') {
    await handleCompare(message);
  }
}

function hideWelcome() {
  const welcome = document.getElementById('welcome-screen');
  if (welcome) welcome.remove();
}

function addUserMessage(text) {
  const messagesContainer = document.getElementById('chat-messages');
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message user';
  messageDiv.innerHTML = `
    <div class="message-content">${escapeHtml(text)}</div>
    <div class="message-avatar">U</div>
  `;
  messagesContainer.appendChild(messageDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addAssistantMessage(content) {
  const messagesContainer = document.getElementById('chat-messages');
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message assistant';
  messageDiv.innerHTML = `
    <div class="message-avatar"><img src="Public/bot-img.png" alt="AI" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;"></div>
    <div class="message-content">${content}</div>
  `;
  messagesContainer.appendChild(messageDiv);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  try { if (typeof lucide !== 'undefined') lucide.createIcons(); } catch(e){}
  return messageDiv;
}

function addLoadingMessage() {
  const msg = addAssistantMessage('<div style="padding: 1rem;">Thinking...</div>');
  return msg;
}

// Enhance Mode
async function handleEnhance(prompt) {
  const loadingMsg = addLoadingMessage();
  
  try {
    const requestBody = { prompt };
    if (selectedModel !== 'auto') {
      requestBody.model = selectedModel;
    }
    
    const apiKey = document.getElementById('api-key-input')?.value || '';
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['X-API-Key'] = apiKey;
    
    const response = await fetch(`${API_BASE}/enhance`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(requestBody)
    });
    
    const result = await response.json();
    loadingMsg.remove();
    
    if (result.success) {
      const content = `
        <div class="analysis-card">
          <h3 style="margin-bottom: 1rem; color: var(--primary);">✨ Enhanced Prompt</h3>
          <div style="background: rgba(0,0,0,0.3); padding: 1.25rem; border-radius: 12px; margin-bottom: 1rem; line-height: 1.8;">
            ${renderMarkdown(result.enhanced)}
          </div>
          <div style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 1rem;">
            <span style="font-size: 0.85rem; color: var(--text-secondary);">
              🤖 Powered by ${result.model.toUpperCase()}
            </span>
            <span style="font-size: 0.85rem; color: var(--success);">
              📈 +${result.improvement} quality points
            </span>
          </div>
          <div class="message-actions">
            <button onclick="copyText(decodeURIComponent('${encodeURIComponent(result.enhanced).replace(/'/g, '%27')}'))">
              <i data-lucide="copy"></i> Copy
            </button>
            <button onclick="saveToHistory(decodeURIComponent('${encodeURIComponent(prompt).replace(/'/g, '%27')}'), decodeURIComponent('${encodeURIComponent(result.enhanced).replace(/'/g, '%27')}'))">
              <i data-lucide="bookmark"></i> Save
            </button>
          </div>
        </div>
      `;
      addAssistantMessage(content);
    } else {
      addAssistantMessage(`<div style="color: #ef4444; padding: 1rem;">❌ Error: ${escapeHtml(result.error || 'Failed to enhance prompt')}</div>`);
    }
  } catch (error) {
    loadingMsg.remove();
    addAssistantMessage('<div style="color: #ef4444; padding: 1rem;">❌ Failed to enhance prompt</div>');
  }
}

// Analyze Mode
async function handleAnalyze(prompt) {
  const loadingMsg = addLoadingMessage();
  
  try {
    const requestBody = { prompt };
    if (selectedModel !== 'auto') {
      requestBody.model = selectedModel;
    }
    
    const apiKey = document.getElementById('api-key-input')?.value || '';
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['X-API-Key'] = apiKey;
    
    const response = await fetch(`${API_BASE}/quality-heatmap`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(requestBody)
    });
    
    const result = await response.json();
    loadingMsg.remove();
    
    if (result.success) {
      const analysis = result.data;
      const metrics = analysis.metrics;
      
      const content = `
        <div class="analysis-card">
          <h3 style="margin-bottom: 1.5rem; color: var(--primary);">📊 Quality Analysis</h3>
          
          <div style="display: flex; gap: 2rem; justify-content: center; margin-bottom: 2rem; padding: 1.5rem; background: rgba(0,0,0,0.2); border-radius: 12px;">
            <div style="text-align: center;">
              <div style="font-size: 3rem; font-weight: 800; color: var(--primary);">${analysis.overall}</div>
              <div style="color: var(--text-secondary); font-size: 0.9rem;">Overall Score</div>
            </div>
            <div style="text-align: center;">
              <div style="font-size: 3rem; font-weight: 800; color: var(--primary);">${analysis.grade}</div>
              <div style="color: var(--text-secondary); font-size: 0.9rem;">Grade</div>
            </div>
          </div>
          
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
            ${Object.entries(metrics).map(([key, value]) => `
              <div style="background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 8px;">
                <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.5rem; text-transform: capitalize;">
                  ${key.replace('_', ' ')}
                </div>
                <div style="height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden; margin-bottom: 0.5rem;">
                  <div style="height: 100%; width: ${(value.score / 10) * 100}%; background: linear-gradient(90deg, var(--primary), #3b82f6); border-radius: 4px;"></div>
                </div>
                <div style="font-size: 1.1rem; font-weight: 700;">${value.score}/10</div>
              </div>
            `).join('')}
          </div>
          
          ${analysis.suggestions.length > 0 ? `
            <div style="background: rgba(139, 92, 246, 0.1); border: 1px solid var(--primary); border-radius: 12px; padding: 1.25rem;">
              <h4 style="margin-bottom: 1rem; color: var(--primary);">💡 Suggestions</h4>
              ${analysis.suggestions.map(sug => `
                <div style="margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border);">
                  <div style="font-weight: 600; color: var(--primary); margin-bottom: 0.5rem;">${sug.category}</div>
                  <div style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 0.5rem;">${sug.issue}</div>
                  <div style="color: var(--success); font-size: 0.9rem;">✅ ${sug.fix}</div>
                </div>
              `).join('')}
            </div>
          ` : '<div style="color: var(--success); padding: 1rem; text-align: center;">✅ Your prompt looks great!</div>'}
        </div>
      `;
      addAssistantMessage(content);
    } else {
      addAssistantMessage(`<div style="color: #ef4444; padding: 1rem;">❌ Error: ${escapeHtml(result.error || 'Failed to analyze prompt')}</div>`);
    }
  } catch (error) {
    loadingMsg.remove();
    addAssistantMessage('<div style="color: #ef4444; padding: 1rem;">❌ Failed to analyze prompt</div>');
  }
}

// Compare Mode
async function handleCompare(prompt) {
  const loadingMsg = addLoadingMessage();
  
  try {
    const requestBody = { prompt, include_comparison: true };
    if (selectedModel !== 'auto') {
      requestBody.model = selectedModel;
    }
    
    const apiKey = document.getElementById('api-key-input')?.value || '';
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['X-API-Key'] = apiKey;
    
    const response = await fetch(`${API_BASE}/ab-test`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(requestBody)
    });
    
    const result = await response.json();
    loadingMsg.remove();
    
    if (result.success) {
      const comparison = result.data;
      
      const content = `
        <div class="analysis-card">
          <h3 style="margin-bottom: 1.5rem; color: var(--primary);">🧪 A/B Test Variations</h3>
          
          <div style="background: var(--primary-light); border: 1px solid var(--primary); border-radius: 12px; padding: 1rem; margin-bottom: 1.5rem;">
            <strong style="color: var(--primary);">🏆 Recommendation:</strong>
            <span style="color: var(--text-primary);"> ${comparison.recommendation.best_variation.toUpperCase()} - ${comparison.recommendation.reason}</span>
          </div>
          
          <div style="display: grid; gap: 1rem;">
            ${Object.entries(comparison.variations).map(([type, variation]) => `
              <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                  <h4 style="text-transform: capitalize;">${type === 'concise' ? '📝' : type === 'detailed' ? '📚' : '🏗️'} ${type}</h4>
                  <span style="font-size: 0.85rem; color: var(--text-secondary);">${variation.model || ''}</span>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 8px; margin-bottom: 1rem; line-height: 1.6;">
                  ${renderMarkdown(variation.text)}
                </div>
                <div style="display: flex; gap: 1.5rem; font-size: 0.85rem; color: var(--text-secondary);">
                  <span>Quality: <strong style="color: var(--primary);">${variation.quality.overall}/10</strong></span>
                  <span>Length: <strong style="color: var(--text-primary);">${variation.length} chars</strong></span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
      addAssistantMessage(content);
    } else {
      addAssistantMessage(`<div style="color: #ef4444; padding: 1rem;">❌ Error: ${escapeHtml(result.error || 'Failed to generate variations')}</div>`);
    }
  } catch (error) {
    loadingMsg.remove();
    addAssistantMessage('<div style="color: #ef4444; padding: 1rem;">❌ Failed to generate variations</div>');
  }
}

// History Mode
function showHistory() {
  const history = getSafeHistory();
  const messagesContainer = document.getElementById('chat-messages');
  messagesContainer.innerHTML = '';
  
  if (history.length === 0) {
    messagesContainer.innerHTML = `
      <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center;">
        <i data-lucide="clock" style="width: 64px; height: 64px; color: var(--text-secondary); opacity: 0.5; margin-bottom: 1rem;"></i>
        <h3 style="font-size: 1.25rem; margin-bottom: 0.5rem;">No history yet</h3>
        <p style="color: var(--text-secondary);">Saved prompts will appear here</p>
      </div>
    `;
    try { if (typeof lucide !== 'undefined') lucide.createIcons(); } catch(e){}
    return;
  }
  
  const content = `
    <div style="max-width: 900px; margin: 0 auto; width: 100%;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2 style="color: var(--primary); margin: 0;">📚 Prompt History</h2>
        <button onclick="exportHistory()" style="background: rgba(139, 92, 246, 0.2); border: 1px solid var(--primary); color: var(--primary); padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 0.5rem; transition: background 0.2s;" onmouseover="this.style.background='var(--primary)'; this.style.color='#fff';" onmouseout="this.style.background='rgba(139, 92, 246, 0.2)'; this.style.color='var(--primary)';">
          <i data-lucide="download" style="width: 16px; height: 16px;"></i> Export JSON
        </button>
      </div>
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        ${history.map(item => `
          <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; cursor: pointer; transition: all 0.3s;" 
               onmouseover="this.style.borderColor='var(--primary)'" 
               onmouseout="this.style.borderColor='var(--border)'"
               onclick="loadFromHistory('${item.id}')">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
              <strong style="color: var(--text-primary);">${escapeHtml(item.original.substring(0, 80))}...</strong>
              <button onclick="event.stopPropagation(); deleteFromHistory('${item.id}')" 
                      style="background: transparent; border: 1px solid var(--border); border-radius: 6px; padding: 0.25rem 0.5rem; color: var(--text-secondary); cursor: pointer;">
                <i data-lucide="trash-2" style="width: 14px; height: 14px;"></i>
              </button>
            </div>
            <div style="font-size: 0.85rem; color: var(--text-secondary);">${new Date(item.timestamp).toLocaleString()}</div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
  messagesContainer.innerHTML = content;
  try { if (typeof lucide !== 'undefined') lucide.createIcons(); } catch(e){}
}

// Quick Actions
function setupQuickActions() {
  document.querySelectorAll('.quick-action').forEach(btn => {
    btn.addEventListener('click', () => {
      const action = btn.getAttribute('data-action');
      document.querySelector(`.nav-item[data-mode="${action}"]`).click();
      document.getElementById('chat-input').focus();
    });
  });
  // Ensure icons are rendered
  setTimeout(() => lucide.createIcons(), 100);
}

// Utility Functions
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => {
      showToast('Copied!', 'Text copied to clipboard', 'success');
    }).catch(err => {
      console.error('Failed to copy text: ', err);
      fallbackCopyTextToClipboard(text);
    });
  } else {
    fallbackCopyTextToClipboard(text);
  }
}

function fallbackCopyTextToClipboard(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  
  // Avoid scrolling to bottom
  textArea.style.top = "0";
  textArea.style.left = "0";
  textArea.style.position = "fixed";

  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();

  try {
    const successful = document.execCommand('copy');
    if (successful) {
      showToast('Copied!', 'Text copied to clipboard', 'success');
    } else {
      showToast('Error', 'Failed to copy text', 'error');
    }
  } catch (err) {
    console.error('Fallback: Oops, unable to copy', err);
    showToast('Error', 'Failed to copy text', 'error');
  }

  document.body.removeChild(textArea);
}

function saveToHistory(original, enhanced) {
  const history = getSafeHistory();
  // Don't save duplicate bookmarks
  if (!history.find(h => h.original === original && h.enhanced === enhanced)) {
    history.unshift({
      id: Date.now().toString(),
      original,
      enhanced,
      timestamp: Date.now()
    });
    localStorage.setItem('promptHistory', JSON.stringify(history));
  }
  showToast('Saved!', 'Prompt saved to history', 'success');
}

function autoSaveToHistory(original) {
  const history = getSafeHistory();
  // Avoid saving same prompt consecutively
  if (history.length > 0 && history[0].original === original) return;
  
  history.unshift({
    id: Date.now().toString(),
    original,
    enhanced: '',
    timestamp: Date.now()
  });
  // Keep only last 50 prompts
  if (history.length > 50) history.length = 50;
  localStorage.setItem('promptHistory', JSON.stringify(history));
}

function loadFromHistory(id) {
  const history = getSafeHistory();
  const item = history.find(h => h.id === id);
  if (item) {
    document.querySelector('.nav-item[data-mode="enhance"]').click();
    document.getElementById('chat-input').value = item.original;
    document.getElementById('send-btn').disabled = false;
    showToast('Loaded', 'Prompt loaded from history', 'success');
  }
}

function deleteFromHistory(id) {
  const history = getSafeHistory();
  const updated = history.filter(h => h.id !== id);
  localStorage.setItem('promptHistory', JSON.stringify(updated));
  showHistory();
  showToast('Deleted', 'Prompt removed from history', 'success');
}

function showToast(title, message, type = 'success') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      <div class="toast-description">${message}</div>
    </div>
  `;
  
  container.appendChild(toast);
  
  setTimeout(() => {
    toast.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function getSafeHistory() {
  try { return JSON.parse(localStorage.getItem('promptHistory') || '[]'); } 
  catch(e) { return []; }
}

function renderMarkdown(text) {
  if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
    return DOMPurify.sanitize(marked.parse(text));
  }
  return escapeHtml(text);
}

function exportHistory() {
  const history = getSafeHistory();
  if (history.length === 0) return showToast('Error', 'No history to export', 'error');
  
  const blob = new Blob([JSON.stringify(history, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `promptx_history_${new Date().toISOString().split('T')[0]}.json`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('Exported!', 'History downloaded successfully', 'success');
}
