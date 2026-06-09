// ==========================================================================
// Application State
// ==========================================================================

const state = {
  apiHost: localStorage.getItem('rag_api_host') || '',
  apiKey: localStorage.getItem('rag_api_key') || 'your_strong_api_key_here',
  documents: [],
  healthInterval: null
};

// Detect if running locally (localhost or 127.0.0.1)
function isLocalEnv() {
  return window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
}

// Compute API base path dynamically — returns null if no backend configured on remote deployment
function getApiUrl(endpoint) {
  let host = state.apiHost;
  if (!host) {
    if (isLocalEnv()) {
      // Local dev: use same origin if on port 8000, else default to backend port
      host = window.location.port && window.location.port !== '8000'
        ? 'http://localhost:8000'
        : window.location.origin;
    } else {
      // Deployed (Vercel, etc.) with no backend URL configured — cannot make API calls
      return null;
    }
  }
  const formattedHost = host.replace(/\/$/, '');
  const formattedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${formattedHost}${formattedEndpoint}`;
}

// Show a one-time banner when deployed without an API host configured
function showNoBannerConfigured() {
  if (document.getElementById('no-backend-banner')) return;
  const banner = document.createElement('div');
  banner.id = 'no-backend-banner';
  banner.style.cssText = `
    position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
    background: linear-gradient(90deg, #6366f1, #a855f7);
    color: white; padding: 12px 20px;
    display: flex; align-items: center; justify-content: space-between;
    font-family: Inter, sans-serif; font-size: 14px; font-weight: 500;
    box-shadow: 0 2px 12px rgba(99,102,241,0.4);
  `;
  banner.innerHTML = `
    <span>⚙️ <strong>Backend not configured.</strong> This app needs a backend API URL to work. Open Settings and enter your deployed API URL.</span>
    <button onclick="openSettings()" style="background:white;color:#6366f1;border:none;padding:6px 14px;border-radius:6px;font-weight:600;cursor:pointer;margin-left:16px;">Open Settings</button>
  `;
  document.body.prepend(banner);
}

// Request headers generator
function getHeaders(extraHeaders = {}) {
  return {
    'X-API-Key': state.apiKey,
    ...extraHeaders
  };
}

// ==========================================================================
// DOM Elements
// ==========================================================================

const dom = {
  // Sidebar
  dragZone: document.getElementById('drag-zone'),
  fileInput: document.getElementById('file-input'),
  docCount: document.getElementById('doc-count'),
  documentList: document.getElementById('document-list'),
  
  // Progress
  progressContainer: document.getElementById('upload-progress-container'),
  progressFilename: document.getElementById('upload-filename'),
  progressPercent: document.getElementById('upload-percent'),
  progressBar: document.getElementById('upload-progress-bar'),
  
  // Chat
  chatContainer: document.getElementById('chat-container'),
  welcomeScreen: document.getElementById('welcome-screen'),
  inputForm: document.getElementById('input-form'),
  queryInput: document.getElementById('query-input'),
  sendBtn: document.getElementById('send-btn'),
  
  // Headers & Badges
  dbStatus: document.getElementById('db-status'),
  llmStatus: document.getElementById('llm-status'),
  dbBadge: document.getElementById('db-badge'),
  llmBadge: document.getElementById('llm-badge'),
  
  // Settings Modal
  settingsToggle: document.getElementById('settings-toggle'),
  settingsModal: document.getElementById('settings-modal'),
  settingsClose: document.getElementById('settings-close'),
  settingsSave: document.getElementById('settings-save'),
  apiHostInput: document.getElementById('api-host-input'),
  apiKeyInput: document.getElementById('api-key-input'),
  togglePassword: document.getElementById('toggle-password'),
  
  // Toast container
  toastContainer: document.getElementById('toast-container')
};

// ==========================================================================
// Toast Notifications Utility
// ==========================================================================

function showToast(message, type = 'info', duration = 4000) {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  // Icon based on type
  let icon = '';
  if (type === 'success') {
    icon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
  } else if (type === 'error') {
    icon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
  } else {
    icon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="8"></line></svg>`;
  }

  toast.innerHTML = `
    ${icon}
    <span>${message}</span>
  `;
  
  dom.toastContainer.appendChild(toast);
  
  // Remove toast after duration
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(20px) scale(0.9)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// Helper: Format file size
function formatBytes(bytes, decimals = 1) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// ==========================================================================
// Health & Connection Checks
// ==========================================================================

async function checkHealth() {
  const url = getApiUrl('/health');
  if (!url) {
    showNoBannerConfigured();
    updateBadge(dom.dbBadge, dom.dbStatus, 'dot-red', 'dot-green', 'dot-yellow', 'No API');
    updateBadge(dom.llmBadge, dom.llmStatus, 'dot-red', 'dot-green', 'dot-yellow', 'No API');
    return;
  }
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error('Unhealthy status code');
    
    const data = await res.json();
    
    // Hide banner if it was showing
    const banner = document.getElementById('no-backend-banner');
    if (banner) banner.remove();
    
    // Update DB Badge
    if (data.database === 'connected') {
      updateBadge(dom.dbBadge, dom.dbStatus, 'dot-green', 'dot-red', 'dot-yellow', 'Connected');
    } else {
      updateBadge(dom.dbBadge, dom.dbStatus, 'dot-red', 'dot-green', 'dot-yellow', 'Disconnected');
    }
    
    // Update LLM Badge
    if (data.llm === 'available') {
      updateBadge(dom.llmBadge, dom.llmStatus, 'dot-green', 'dot-red', 'dot-yellow', 'Available');
    } else {
      updateBadge(dom.llmBadge, dom.llmStatus, 'dot-red', 'dot-green', 'dot-yellow', 'Unavailable');
    }
  } catch (error) {
    console.error('API health check failed:', error);
    updateBadge(dom.dbBadge, dom.dbStatus, 'dot-red', 'dot-green', 'dot-yellow', 'Offline');
    updateBadge(dom.llmBadge, dom.llmStatus, 'dot-red', 'dot-green', 'dot-yellow', 'Offline');
  }
}

function updateBadge(badgeEl, textEl, addClass, removeClass1, removeClass2, text) {
  const dotEl = badgeEl.querySelector('.status-dot');
  dotEl.classList.remove(removeClass1, removeClass2);
  dotEl.classList.add(addClass);
  textEl.textContent = text;
}

// ==========================================================================
// Document Actions (Fetch, Upload, Delete)
// ==========================================================================

async function fetchDocuments() {
  const url = getApiUrl('/documents');
  if (!url) {
    showNoBannerConfigured();
    renderEmptyState();
    return;
  }
  try {
    const response = await fetch(url, {
      headers: getHeaders()
    });
    
    if (response.status === 401) {
      showToast('Authentication failed. Please verify API key in Settings.', 'error');
      renderEmptyState();
      return;
    }
    
    if (!response.ok) {
      throw new Error(`Failed to fetch: ${response.statusText}`);
    }
    
    const data = await response.json();
    state.documents = data;
    renderDocumentsList();
  } catch (error) {
    console.error('Error listing documents:', error);
    showToast('Failed to retrieve knowledge sources.', 'error');
    renderEmptyState();
  }
}

function renderEmptyState() {
  dom.docCount.textContent = '0 files';
  dom.documentList.innerHTML = `
    <div class="list-empty-state">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        <polyline points="14 2 14 8 20 8"></polyline>
        <line x1="16" y1="13" x2="8" y2="13"></line>
        <line x1="16" y1="17" x2="8" y2="17"></line>
        <polyline points="10 9 9 9 8 9"></polyline>
      </svg>
      <p>No documents uploaded or auth error</p>
    </div>
  `;
}

function renderDocumentsList() {
  dom.docCount.textContent = `${state.documents.length} file${state.documents.length === 1 ? '' : 's'}`;
  
  if (state.documents.length === 0) {
    renderEmptyState();
    return;
  }
  
  dom.documentList.innerHTML = '';
  
  state.documents.forEach(doc => {
    const docItem = document.createElement('div');
    docItem.className = 'document-item';
    docItem.dataset.id = doc.id;
    
    // Pick file type icon
    const ext = doc.filename.split('.').pop().toLowerCase();
    let fileIconSvg = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>';
    
    docItem.innerHTML = `
      <div class="doc-info">
        <div class="doc-icon">${fileIconSvg}</div>
        <div class="doc-details">
          <span class="doc-name" title="${doc.filename}">${doc.filename}</span>
          <span class="doc-meta">${formatBytes(doc.file_size || 0)}</span>
        </div>
      </div>
      <div class="doc-actions">
        <button class="delete-btn" onclick="deleteDocument('${doc.id}', '${doc.filename.replace(/'/g, "\\'")}')" title="Delete file">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            <line x1="10" y1="11" x2="10" y2="17"></line>
            <line x1="14" y1="11" x2="14" y2="17"></line>
          </svg>
        </button>
      </div>
    `;
    dom.documentList.appendChild(docItem);
  });
}

// Upload file implementation with XMLHttpRequest for progress tracking
function uploadFiles(files) {
  if (files.length === 0) return;
  
  // Process files sequentially or just upload the first for demo
  const file = files[0];
  
  // Size validation (10MB)
  if (file.size > 10 * 1024 * 1024) {
    showToast('File is too large. Max size allowed is 10MB.', 'error');
    return;
  }
  
  const formData = new FormData();
  formData.append('file', file);
  
  // Show progress container
  dom.progressContainer.style.display = 'block';
  dom.progressFilename.textContent = file.name;
  dom.progressPercent.textContent = '0%';
  dom.progressBar.style.width = '0%';
  
  const uploadUrl = getApiUrl('/documents/upload');
  if (!uploadUrl) {
    showNoBannerConfigured();
    showToast('No backend API configured. Open Settings and enter your API URL.', 'error');
    dom.progressContainer.style.display = 'none';
    return;
  }
  const xhr = new XMLHttpRequest();
  xhr.open('POST', uploadUrl);
  
  // Headers
  xhr.setRequestHeader('X-API-Key', state.apiKey);
  
  // Progress tracker
  xhr.upload.addEventListener('progress', (e) => {
    if (e.lengthComputable) {
      const percent = Math.round((e.loaded / e.total) * 100);
      dom.progressPercent.textContent = `${percent}%`;
      dom.progressBar.style.width = `${percent}%`;
    }
  });
  
  xhr.addEventListener('load', () => {
    dom.progressContainer.style.display = 'none';
    if (xhr.status >= 200 && xhr.status < 300) {
      const res = JSON.parse(xhr.responseText);
      showToast(`Successfully uploaded "${file.name}"! (${res.chunks_created} chunks)`, 'success');
      fetchDocuments();
    } else if (xhr.status === 401) {
      showToast('Upload failed: Unauthorized API Key.', 'error');
    } else {
      let errMsg = 'Upload failed.';
      try {
        const errObj = JSON.parse(xhr.responseText);
        errMsg = errObj.error?.message || errMsg;
      } catch(_) {}
      showToast(errMsg, 'error');
    }
  });
  
  xhr.addEventListener('error', () => {
    dom.progressContainer.style.display = 'none';
    showToast('Network error during file upload.', 'error');
  });
  
  xhr.send(formData);
}

// Delete file
async function deleteDocument(id, filename) {
  if (!confirm(`Are you sure you want to remove "${filename}" from the knowledge base?`)) {
    return;
  }
  
  try {
    const response = await fetch(getApiUrl(`/documents/${id}`), {
      method: 'DELETE',
      headers: getHeaders()
    });
    
    if (response.ok) {
      showToast(`Removed "${filename}"`, 'success');
      
      // Animate card out in UI before refresh
      const docItem = dom.documentList.querySelector(`[data-id="${id}"]`);
      if (docItem) {
        docItem.style.opacity = '0';
        docItem.style.transform = 'scale(0.9)';
        docItem.style.transition = 'all 0.3s ease';
        setTimeout(() => fetchDocuments(), 300);
      } else {
        fetchDocuments();
      }
    } else {
      let errMsg = 'Failed to delete file.';
      try {
        const res = await response.json();
        errMsg = res.error?.message || errMsg;
      } catch(_) {}
      showToast(errMsg, 'error');
    }
  } catch (error) {
    console.error('Error deleting document:', error);
    showToast('Network error while deleting.', 'error');
  }
}

// Expose deleteDocument globally for inline HTML click events
window.deleteDocument = deleteDocument;

// ==========================================================================
// Chat Logic (Ask & Responses)
// ==========================================================================

async function sendQuery(query) {
  if (!query.trim()) return;
  
  // Hide Welcome Screen
  if (dom.welcomeScreen) {
    dom.welcomeScreen.remove();
    dom.welcomeScreen = null;
  }
  
  // Append User message in chat
  appendMessage('user', query);
  
  // Disable input & show typing loader
  dom.queryInput.value = '';
  dom.queryInput.disabled = true;
  dom.sendBtn.disabled = true;
  
  const loadingId = appendMessage('assistant', '', true);
  
  try {
    const response = await fetch(getApiUrl('/ask'), {
      method: 'POST',
      headers: getHeaders({
        'Content-Type': 'application/json'
      }),
      body: JSON.stringify({ question: query })
    });
    
    // Remove loading bubble
    removeMessage(loadingId);
    
    if (response.status === 401) {
      appendMessage('assistant', '⚠️ **Unauthorized**: Your API key is invalid. Please configure a valid `X-API-Key` in Settings.');
      showToast('Query failed: Invalid API key', 'error');
      return;
    }
    
    if (!response.ok) {
      let errText = 'An error occurred while answering your question.';
      try {
        const errorDetails = await response.json();
        errText = `⚠️ **Error**: ${errorDetails.error?.message || response.statusText}`;
      } catch(_) {}
      appendMessage('assistant', errText);
      return;
    }
    
    const data = await response.json();
    appendMessage('assistant', data.answer, false, data.sources);
  } catch (error) {
    console.error('Error asking question:', error);
    removeMessage(loadingId);
    appendMessage('assistant', '⚠️ **Connection Error**: Unable to reach the API server. Please make sure the backend server is running and configured correctly in settings.');
    showToast('Network error during question request.', 'error');
  } finally {
    dom.queryInput.disabled = false;
    dom.sendBtn.disabled = false;
    dom.queryInput.focus();
  }
}

// Append messages to stream
function appendMessage(sender, text, isLoading = false, sources = []) {
  const messageId = `msg-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
  const messageEl = document.createElement('div');
  messageEl.className = `message ${sender}`;
  messageEl.id = messageId;
  
  const avatarText = sender === 'user' ? 'U' : 'AI';
  
  let bubbleContent = '';
  if (isLoading) {
    bubbleContent = `
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    `;
  } else {
    // Format paragraph breaks
    bubbleContent = text.split('\n\n')
      .map(p => `<p>${escapeHtml(p).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</p>`)
      .join('');
  }
  
  messageEl.innerHTML = `
    <div class="avatar">${avatarText}</div>
    <div class="message-content">
      <div class="bubble">${bubbleContent}</div>
      ${renderSources(sources)}
    </div>
  `;
  
  dom.chatContainer.appendChild(messageEl);
  scrollToBottom();
  
  return messageId;
}

function removeMessage(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

// Render source document snippets
function renderSources(sources) {
  if (!sources || sources.length === 0) return '';
  
  const accordionId = `acc-${Date.now()}-${Math.floor(Math.random()*1000)}`;
  const listItems = sources.map(src => `
    <div class="source-item">
      <div class="source-name">${escapeHtml(src.document || 'Unknown Document')}</div>
      <div class="source-snippet">"${escapeHtml(src.chunk || '')}"</div>
    </div>
  `).join('');
  
  return `
    <div class="sources-drawer">
      <div class="sources-header" onclick="toggleSources('${accordionId}', this)">
        <svg class="chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" style="transition: transform 0.2s ease;">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
        <span>Reference Sources (${sources.length})</span>
      </div>
      <div class="sources-list" id="${accordionId}" style="display: none;">
        ${listItems}
      </div>
    </div>
  `;
}

// Toggle reference accordion
function toggleSources(id, headerEl) {
  const list = document.getElementById(id);
  const chevron = headerEl.querySelector('.chevron');
  if (list.style.display === 'none') {
    list.style.display = 'flex';
    chevron.style.transform = 'rotate(90deg)';
  } else {
    list.style.display = 'none';
    chevron.style.transform = 'rotate(0deg)';
  }
  scrollToBottom();
}
window.toggleSources = toggleSources; // Export globally

// Scroll chat container
function scrollToBottom() {
  setTimeout(() => {
    dom.chatContainer.scrollTop = dom.chatContainer.scrollHeight;
  }, 50);
}

// Basic HTML sanitizer to prevent injection
function escapeHtml(unsafe) {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Prompt suggestions click handler
function useSuggestion(prompt) {
  sendQuery(prompt);
}
window.useSuggestion = useSuggestion; // Export globally

// ==========================================================================
// Settings Modal & Password Toggle
// ==========================================================================

function openSettings() {
  dom.apiHostInput.value = state.apiHost;
  dom.apiKeyInput.value = state.apiKey;
  dom.settingsModal.style.display = 'flex';
}

function closeSettings() {
  dom.settingsModal.style.display = 'none';
}

function saveSettings() {
  const newHost = dom.apiHostInput.value.trim();
  const newKey = dom.apiKeyInput.value.trim();
  
  state.apiHost = newHost;
  state.apiKey = newKey;
  
  if (newHost) {
    localStorage.setItem('rag_api_host', newHost);
  } else {
    localStorage.removeItem('rag_api_host');
  }
  
  localStorage.setItem('rag_api_key', newKey);
  
  closeSettings();
  showToast('Settings saved successfully.', 'success');
  
  // Re-run checks
  checkHealth();
  fetchDocuments();
}

function togglePasswordVisibility() {
  const type = dom.apiKeyInput.getAttribute('type') === 'password' ? 'text' : 'password';
  dom.apiKeyInput.setAttribute('type', type);
}

// ==========================================================================
// Event Listeners & Bootstrapping
// ==========================================================================

function setupEventListeners() {
  // Form submission
  dom.inputForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const query = dom.queryInput.value;
    sendQuery(query);
  });
  
  // Settings trigger
  dom.settingsToggle.addEventListener('click', openSettings);
  dom.settingsClose.addEventListener('click', closeSettings);
  dom.settingsSave.addEventListener('click', saveSettings);
  dom.togglePassword.addEventListener('click', togglePasswordVisibility);
  
  // Close modal when clicking background
  dom.settingsModal.addEventListener('click', (e) => {
    if (e.target === dom.settingsModal) closeSettings();
  });
  
  // Drag and drop events
  dom.dragZone.addEventListener('click', () => dom.fileInput.click());
  
  dom.fileInput.addEventListener('change', (e) => {
    uploadFiles(e.target.files);
  });
  
  ['dragenter', 'dragover'].forEach(eventName => {
    dom.dragZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dom.dragZone.classList.add('dragover');
    }, false);
  });
  
  ['dragleave', 'drop'].forEach(eventName => {
    dom.dragZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dom.dragZone.classList.remove('dragover');
    }, false);
  });
  
  dom.dragZone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    uploadFiles(files);
  }, false);
}

// Initialize Application
function init() {
  setupEventListeners();
  
  // Initial checkups
  checkHealth();
  fetchDocuments();
  
  // Start health checks interval (every 10 seconds)
  state.healthInterval = setInterval(checkHealth, 10000);
}

document.addEventListener('DOMContentLoaded', init);
