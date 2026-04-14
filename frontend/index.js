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
  
  setupNavbar();
  setupModeTabs();
  setupQuickActions();
  setupModelSelector();
  setupChatInput();
  setupScrollAnimations();
  setupMobileNav();
  
  const apiInput = document.getElementById('api-key-input');
  if (apiInput) {
    apiInput.value = localStorage.getItem('promptx_api_key') || '';
    apiInput.addEventListener('input', (e) => localStorage.setItem('promptx_api_key', e.target.value));
  }
});

// ===== NAVBAR =====
function setupNavbar() {
  const navbar = document.getElementById('navbar');
  let lastScroll = 0;
  
  window.addEventListener('scroll', () => {
    const currentScroll = window.scrollY;
    if (currentScroll > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
    lastScroll = currentScroll;
  });
  
  // Smooth scroll for nav links
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
      const targetId = link.getAttribute('href');
      if (targetId === '#') return;
      const target = document.querySelector(targetId);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
}

// ===== MOBILE NAV =====
function setupMobileNav() {
  const toggle = document.getElementById('nav-mobile-toggle');
  const navLinks = document.getElementById('nav-links');
  
  if (toggle && navLinks) {
    toggle.addEventListener('click', () => {
      navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
      navLinks.style.position = 'absolute';
      navLinks.style.top = '72px';
      navLinks.style.left = '0';
      navLinks.style.right = '0';
      navLinks.style.flexDirection = 'column';
      navLinks.style.background = 'rgba(3, 8, 5, 0.98)';
      navLinks.style.padding = '1rem';
      navLinks.style.borderBottom = '1px solid var(--border)';
      navLinks.style.backdropFilter = 'blur(20px)';
    });
  }
}

// ===== MODE TABS =====
function setupModeTabs() {
  const tabs = document.querySelectorAll('.app-mode-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentMode = tab.getAttribute('data-mode');
      updateModeIndicator();
    });
  });
}

// ===== SCROLL ANIMATIONS =====
function setupScrollAnimations() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  });
  
  document.querySelectorAll('.fade-in').forEach(el => {
    observer.observe(el);
  });
}

// ===== MODEL SELECTOR =====
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

function updateModeIndicator() {
  const modeNames = {
    enhance: 'Enhance Mode',
    analyze: 'Analyze Mode',
    compare: 'Compare Mode',
    history: 'History Mode'
  };
  const indicator = document.getElementById('mode-indicator');
  if (indicator) indicator.textContent = modeNames[currentMode];
}

// ===== CHAT INPUT =====
function setupChatInput() {
  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  
  if (!chatInput || !sendBtn) return;
  
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
  const msg = addAssistantMessage('<div style="padding: 0.75rem; display: flex; align-items: center; gap: 0.75rem;"><div class="typing-cursor" style="width: 3px; height: 16px;"></div> <span style="color: var(--text-secondary); font-size: 0.9rem;">Thinking...</span></div>');
  return msg;
}

// ===== ENHANCE MODE =====
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
          <div style="background: rgba(0,0,0,0.3); padding: 1.25rem; border-radius: 12px; margin-bottom: 1rem; line-height: 1.8; border: 1px solid var(--border);">
            ${renderMarkdown(result.enhanced)}
          </div>
          <div style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap;">
            <span style="font-size: 0.8rem; color: var(--text-secondary); background: var(--primary-light); padding: 0.25rem 0.75rem; border-radius: 100px; border: 1px solid var(--border);">
              🤖 ${result.model.toUpperCase()}
            </span>
            <span style="font-size: 0.8rem; color: var(--primary); background: var(--primary-light); padding: 0.25rem 0.75rem; border-radius: 100px; border: 1px solid var(--border);">
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
      addAssistantMessage(`<div style="color: var(--error); padding: 1rem;">❌ Error: ${escapeHtml(result.error || 'Failed to enhance prompt')}</div>`);
    }
  } catch (error) {
    loadingMsg.remove();
    addAssistantMessage('<div style="color: var(--error); padding: 1rem;">❌ Failed to enhance prompt. Check your connection.</div>');
  }
}

// ===== ANALYZE MODE =====
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
          
          <div style="display: flex; gap: 2rem; justify-content: center; margin-bottom: 2rem; padding: 1.5rem; background: rgba(0,0,0,0.3); border-radius: 12px; border: 1px solid var(--border);">
            <div style="text-align: center;">
              <div style="font-size: 2.5rem; font-weight: 800; color: var(--primary); text-shadow: 0 0 20px rgba(0,255,65,0.3);">${analysis.overall}</div>
              <div style="color: var(--text-secondary); font-size: 0.85rem;">Overall Score</div>
            </div>
            <div style="text-align: center;">
              <div style="font-size: 2.5rem; font-weight: 800; color: var(--primary); text-shadow: 0 0 20px rgba(0,255,65,0.3);">${analysis.grade}</div>
              <div style="color: var(--text-secondary); font-size: 0.85rem;">Grade</div>
            </div>
          </div>
          
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; margin-bottom: 1.5rem;">
            ${Object.entries(metrics).map(([key, value]) => `
              <div style="background: rgba(0,0,0,0.3); padding: 0.85rem; border-radius: 8px; border: 1px solid var(--border);">
                <div style="font-size: 0.78rem; color: var(--text-secondary); margin-bottom: 0.4rem; text-transform: capitalize;">
                  ${key.replace('_', ' ')}
                </div>
                <div style="height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; margin-bottom: 0.4rem;">
                  <div style="height: 100%; width: ${(value.score / 10) * 100}%; background: linear-gradient(90deg, var(--primary), var(--accent)); border-radius: 3px; box-shadow: 0 0 8px rgba(0,255,65,0.3);"></div>
                </div>
                <div style="font-size: 1rem; font-weight: 700; color: var(--primary);">${value.score}/10</div>
              </div>
            `).join('')}
          </div>
          
          ${analysis.suggestions.length > 0 ? `
            <div style="background: var(--primary-light); border: 1px solid var(--border); border-radius: 12px; padding: 1.15rem;">
              <h4 style="margin-bottom: 0.75rem; color: var(--primary); font-size: 0.95rem;">💡 Suggestions</h4>
              ${analysis.suggestions.map(sug => `
                <div style="margin-bottom: 0.75rem; padding-bottom: 0.75rem; border-bottom: 1px solid var(--border);">
                  <div style="font-weight: 600; color: var(--primary); margin-bottom: 0.3rem; font-size: 0.85rem;">${sug.category}</div>
                  <div style="color: var(--text-secondary); font-size: 0.82rem; margin-bottom: 0.3rem;">${sug.issue}</div>
                  <div style="color: var(--success); font-size: 0.82rem;">✅ ${sug.fix}</div>
                </div>
              `).join('')}
            </div>
          ` : '<div style="color: var(--success); padding: 1rem; text-align: center;">✅ Your prompt looks great!</div>'}
        </div>
      `;
      addAssistantMessage(content);
    } else {
      addAssistantMessage(`<div style="color: var(--error); padding: 1rem;">❌ Error: ${escapeHtml(result.error || 'Failed to analyze prompt')}</div>`);
    }
  } catch (error) {
    loadingMsg.remove();
    addAssistantMessage('<div style="color: var(--error); padding: 1rem;">❌ Failed to analyze prompt</div>');
  }
}

// ===== COMPARE MODE =====
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
          
          <div style="background: var(--primary-light); border: 1px solid var(--border); border-radius: 12px; padding: 1rem; margin-bottom: 1.5rem;">
            <strong style="color: var(--primary);">🏆 Recommendation:</strong>
            <span style="color: var(--text-primary);"> ${comparison.recommendation.best_variation.toUpperCase()} — ${comparison.recommendation.reason}</span>
          </div>
          
          <div style="display: grid; gap: 0.75rem;">
            ${Object.entries(comparison.variations).map(([type, variation]) => `
              <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 12px; padding: 1.15rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
                  <h4 style="text-transform: capitalize; font-size: 0.95rem;">${type === 'concise' ? '📝' : type === 'detailed' ? '📚' : '🏗️'} ${type}</h4>
                  <span style="font-size: 0.78rem; color: var(--text-secondary);">${variation.model || ''}</span>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 0.85rem; border-radius: 8px; margin-bottom: 0.75rem; line-height: 1.6; font-size: 0.88rem; border: 1px solid var(--border);">
                  ${renderMarkdown(variation.text)}
                </div>
                <div style="display: flex; gap: 1.25rem; font-size: 0.8rem; color: var(--text-secondary);">
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
      addAssistantMessage(`<div style="color: var(--error); padding: 1rem;">❌ Error: ${escapeHtml(result.error || 'Failed to generate variations')}</div>`);
    }
  } catch (error) {
    loadingMsg.remove();
    addAssistantMessage('<div style="color: var(--error); padding: 1rem;">❌ Failed to generate variations</div>');
  }
}

// ===== QUICK ACTIONS =====
function setupQuickActions() {
  document.querySelectorAll('.quick-action').forEach(btn => {
    btn.addEventListener('click', () => {
      const action = btn.getAttribute('data-action');
      // Update mode tabs
      const tabs = document.querySelectorAll('.app-mode-tab');
      tabs.forEach(t => {
        t.classList.remove('active');
        if (t.getAttribute('data-mode') === action) {
          t.classList.add('active');
        }
      });
      currentMode = action;
      updateModeIndicator();
      document.getElementById('chat-input').focus();
    });
  });
}

// ===== UTILITY FUNCTIONS =====
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

function copyCodeSnippet() {
  const code = `# pip install promptx-py
from promptx import PromptX

app = PromptX(api_key="px-YOUR_API_KEY")

# Enhance a prompt:
result = app.enhance('Write a blog post about AI')

# Analyze prompt quality:
score = app.analyze(result.enhanced)
print(score.overall)  # → 9.2/10`;
  
  copyText(code);
}

function fallbackCopyTextToClipboard(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
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
  if (history.length > 0 && history[0].original === original) return;
  history.unshift({
    id: Date.now().toString(),
    original,
    enhanced: '',
    timestamp: Date.now()
  });
  if (history.length > 50) history.length = 50;
  localStorage.setItem('promptHistory', JSON.stringify(history));
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
