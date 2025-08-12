import os
import re
import logging
import json
from datetime import datetime
from urllib.parse import quote, urlparse

import requests
from flask import (
    Flask, request, send_from_directory, render_template_string,
    jsonify, make_response
)
from werkzeug.utils import secure_filename
from markupsafe import escape

# --- Configuration & Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

UPLOAD_FOLDER = "uploads"
DATA_FILE = "data.json"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024 * 1024  # 10GB limit

# --- Global State & Persistence ---
clipboard = []
files = []

def load_data():
    """Loads clipboard and file list from data.json."""
    global clipboard, files
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                clipboard = data.get('clipboard', [])
                files = data.get('files', [])
        except (json.JSONDecodeError, IOError) as e:
            logging.warning("Could not load %s: %s", DATA_FILE, e)

def save_data():
    """Saves the current clipboard and file list to data.json."""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({'clipboard': clipboard, 'files': files}, f, indent=2)
    except IOError as e:
        logging.error("Could not save %s: %s", DATA_FILE, e)

# Load data at startup
load_data()

# --- HTML/CSS/JS Template ---
HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>CopyCat</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://unpkg.com/feather-icons"></script>

<style>
/* --- Black Theme & UI Refresh --- */
:root {
  --font: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --bg: #000000; /* True black background */
  --card: #111111; /* Very dark charcoal for cards */
  --border: #2a2a2a;
  --text: #e5e7eb;
  --muted: #9ca3af;
  --accent: #0ea5e9; /* A vivid sky blue */
  --accent-hover: #38bdf8;
  --success: #22c55e;
  --danger: #ef4444;
  --danger-hover: #f87171;
  --btn-secondary-bg: #333333;
  --btn-secondary-hover: #444444;
  --shadow-color: rgba(0, 0, 0, 0.7);
  --shadow-accent-glow: rgba(14, 165, 233, 0.3);
  --highlight-bg: rgba(14, 165, 233, 0.15);
  --transition-fast: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

*, *::before, *::after { box-sizing: border-box; }

html { font-size: 16px; scroll-behavior: smooth; }

body {
  height: 100%;
  margin: 0;
  background-color: var(--bg);
  color: var(--text);
  font-family: var(--font);
  padding: 24px;
}

.container {
  max-width: 980px;
  margin: auto;
  display: grid;
  gap: 24px;
}

.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  box-shadow: 0 10px 30px var(--shadow-color);
  overflow: hidden;
  transition: var(--transition-fast);
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  font-weight: 600;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-body { padding: 20px; }

.btn {
  border: none;
  padding: 10px 16px;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
  font-family: var(--font);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: var(--transition-fast);
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.btn:hover { transform: translateY(-1px); box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
.btn:active { transform: translateY(0); }
.btn:disabled { cursor: not-allowed; opacity: 0.6; }
.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover:not(:disabled) { background: var(--accent-hover); }
.btn-secondary { background: var(--btn-secondary-bg); color: var(--text); }
.btn-secondary:hover:not(:disabled) { background: var(--btn-secondary-hover); }
.btn-danger { background: var(--danger); color: #fff; }
.btn-danger:hover:not(:disabled) { background: var(--danger-hover); }
.btn-sm { padding: 6px 10px; font-size: 0.875rem; border-radius: 8px; }

.form-control {
  background: #000000;
  border: 1px solid var(--border);
  padding: 10px 14px;
  border-radius: 10px;
  color: var(--text);
  width: 100%;
  font-family: var(--font);
  transition: var(--transition-fast);
}
.form-control:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--shadow-accent-glow);
}

#drop-zone {
  border: 2px dashed var(--border);
  padding: 32px;
  border-radius: 12px;
  text-align: center;
  color: var(--muted);
  transition: var(--transition-fast);
  cursor: pointer;
}
#drop-zone:hover { border-color: var(--accent); color: var(--accent); background: rgba(14, 165, 233, 0.05); }
#drop-zone.dragover {
  border-color: var(--accent);
  border-style: solid;
  color: var(--accent);
  background: rgba(14, 165, 233, 0.1);
  transform: scale(1.02);
}

.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-radius: 10px;
  margin-bottom: 10px;
  background-color: transparent;
  border: 1px solid var(--border);
  transition: var(--transition-fast);
}
.list-item:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}
.list-item.current-message-highlight {
    border-color: var(--accent);
    background-color: var(--highlight-bg);
    box-shadow: 0 0 15px var(--shadow-accent-glow);
}


.file-list { list-style: none; padding: 0; margin: 0; }
.file-info { display: flex; align-items: center; gap: 12px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; max-width: 60%; }
.file-actions { display: flex; gap: 8px; align-items: center; }

#clipboard-list { max-height: 460px; overflow-y: auto; padding-right: 8px; }
.clipboard-item { align-items: flex-start; }

.clipboard-content { flex: 1; min-width: 0; }
.message-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.timestamp { color: var(--muted); font-size: 0.875rem; white-space: nowrap; }
.message-body { white-space: pre-wrap; word-wrap: break-word; color: var(--text); line-height: 1.5; }
.clipboard-actions { display: flex; flex-direction: column; gap: 8px; margin-left: 12px; align-items: flex-end; }
.clipboard-footer { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-top: 16px; }

#toast-container { position: fixed; right: 24px; top: 24px; z-index: 9999; display: flex; flex-direction: column; gap: 12px; }
.toast {
  min-width: 250px;
  padding: 12px 16px;
  border-radius: 10px;
  color: #fff;
  background: rgba(20, 20, 20, 0.7);
  backdrop-filter: blur(5px);
  box-shadow: 0 10px 30px var(--shadow-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-left: 4px solid;
}
.toast.success { border-color: var(--success); }
.toast.error { border-color: var(--danger); }

@media (max-width: 720px) {
  body { padding: 16px; }
  .container { gap: 16px; }
  .clipboard-actions { flex-direction: row; gap: 6px; margin-left: 6px; }
  .file-info { max-width: 50%; }
}
</style>
</head>
<body>
<div class="container">
  <div class="card">
    <div class="card-header"><i data-feather="clipboard"></i> Shared Clipboard</div>
    <div class="card-body">
      <div id="clipboard-list" aria-live="polite"></div>
      <div style="display:flex;gap:8px;margin-top:12px">
        <input id="clipboardInput" class="form-control" placeholder="Type text to share...">
        <button class="btn btn-primary" onclick="shareManualInput()" title="Share"><i data-feather="send"></i></button>
      </div>
      <div id="clipboard-status" style="margin-top:10px;color:var(--muted);font-size:.9rem">Click anywhere on the page to enable clipboard auto-sharing.</div>
      
      <div class="clipboard-footer">
        <button id="nextMessageBtn" class="btn btn-secondary" onclick="nextMessage()" disabled><i data-feather="arrow-down"></i> Next Message</button>
        <button class="btn btn-secondary" onclick="copySharedClipboard()"><i data-feather="copy"></i> Copy All</button>
        <button class="btn btn-danger" onclick="resetClipboard()"><i data-feather="trash-2"></i> Reset</button>
      </div>

    </div>
  </div>

  <div class="card">
    <div class="card-header"><i data-feather="upload-cloud"></i> File Hub</div>
    <div class="card-body">
      <div id="drop-zone" onclick="document.getElementById('file-input').click()">
        <input id="file-input" type="file" multiple style="display:none" onchange="handleFileSelect(this.files)">
        <i data-feather="upload" style="width:36px;height:36px"></i>
        <p style="color:var(--muted);margin:8px 0 0 0">Drag & drop files here, paste a file, or click to select.</p>
      </div>
      <div style="display:flex;gap:8px;margin-top:12px">
        <input id="url-input" class="form-control" placeholder="Or paste a file URL to upload...">
        <button class="btn btn-primary" onclick="uploadFromUrl()">Fetch</button>
      </div>
      <div id="upload-status" style="margin-top:10px;color:var(--accent);font-size:.9rem"></div>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><i data-feather="hard-drive"></i> Available Files</div>
    <div class="card-body">
      <ul id="fileList" class="file-list"></ul>
      <div style="margin-top:16px;text-align:right">
        <button class="btn btn-danger" onclick="resetFiles()"><i data-feather="trash-2"></i> Reset All Files</button>
      </div>
    </div>
  </div>
</div>

<div id="toast-container" aria-live="polite" aria-atomic="true"></div>

<script>
let lastLocalClipboard = "";
let clipboardAccessGranted = false;
let currentMessageIndex = -1; // For "Next Message" feature

function showToast(message, isError=false){
  const container = document.getElementById('toast-container');
  const div = document.createElement('div');
  div.className = 'toast ' + (isError ? 'error' : 'success');
  div.textContent = message;
  container.appendChild(div);
  setTimeout(()=>{ div.style.transition='opacity 0.28s'; div.style.opacity='0'; setTimeout(()=>div.remove(),320); }, 2200);
}

async function safeFetchJson(url, opts){
  try {
    const res = await fetch(url, opts);
    const json = await res.json().catch(()=>null);
    return { ok: res.ok, status: res.status, json };
  } catch (err) {
    console.error('fetch error', err);
    return { ok: false, status: 0, json: null };
  }
}

const dropZone = document.getElementById('drop-zone');
const urlInput = document.getElementById('url-input');
const uploadStatus = document.getElementById('upload-status');

function setUploadStatus(msg, isErr=false){
  uploadStatus.textContent = msg;
  uploadStatus.style.color = isErr ? 'var(--danger)' : 'var(--accent)';
  setTimeout(()=>{ if (uploadStatus.textContent === msg) uploadStatus.textContent = ''; }, 3000);
}

async function uploadFiles(files){
  if (!files || files.length === 0) return;
  const fd = new FormData();
  for (const f of files) fd.append('file', f);
  setUploadStatus(`Uploading ${files.length} file(s)...`);
  const res = await safeFetchJson('/', { method: 'POST', body: fd, cache: 'no-store' });
  if (res.ok) { setUploadStatus('Upload successful!'); document.getElementById('file-input').value=''; setTimeout(fetchFileList, 300); }
  else { setUploadStatus('Upload failed', true); console.error(res); }
}

function handleFileSelect(files){ uploadFiles(files); }

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', ()=> dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('dragover'); if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files); });

document.addEventListener('paste', e => {
  if (e.clipboardData && e.clipboardData.files && e.clipboardData.files.length) {
    e.preventDefault();
    uploadFiles(e.clipboardData.files);
    setUploadStatus('Pasted file uploaded!');
  }
});

async function uploadFromUrl(){
  const url = urlInput.value.trim();
  if (!url) return;
  setUploadStatus('Fetching file from URL...');
  const res = await safeFetchJson('/upload-from-url', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ url }),
    cache: 'no-store'
  });
  if (res.ok && res.json && res.json.filename) {
    setUploadStatus(`Downloaded: ${res.json.filename}`);
    urlInput.value = '';
    setTimeout(fetchFileList, 300);
  } else {
    setUploadStatus(res.json && res.json.error ? res.json.error : 'Download failed', true);
  }
}

const clipboardStatus = document.getElementById('clipboard-status');

async function shareText(text){
  if (!text || !text.trim()) return;
  await safeFetchJson('/clipboard', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ text }), cache: 'no-store' });
}

async function shareManualInput(){
  const el = document.getElementById('clipboardInput');
  if (el.value && el.value.trim()) {
    await shareText(el.value);
    el.value = '';
  }
}

async function requestClipboardPermission(){
  try {
    await navigator.clipboard.readText();
    clipboardAccessGranted = true;
    clipboardStatus.textContent = 'Auto-sharing enabled.';
    clipboardStatus.style.color = 'var(--success)';
  } catch (e) {
    clipboardAccessGranted = false;
    clipboardStatus.textContent = 'Auto-sharing denied. Use manual input.';
    clipboardStatus.style.color = 'var(--danger)';
  }
}

async function autoShareClipboard(){
  if (!clipboardAccessGranted) return;
  try {
    const t = await navigator.clipboard.readText();
    if (t && t !== lastLocalClipboard) {
      lastLocalClipboard = t;
      await shareText(t);
    }
  } catch (e) { /* silent */ }
}

function copyText(text, statusEl){
  if (!navigator.clipboard) return;
  navigator.clipboard.writeText(text).then(()=> {
    const orig = statusEl.textContent;
    statusEl.textContent = 'Copied!';
    statusEl.style.color = 'var(--success)';
    setTimeout(()=> { statusEl.textContent = orig; statusEl.style.color = 'var(--accent)'; }, 1400);
  }).catch(err => console.error('copy fail', err));
}

async function copySharedClipboard(){
  const items = document.querySelectorAll('.clipboard-item');
  const all = Array.from(items).map(i => i.dataset.message).join('\\n');
  if (all) copyText(all, clipboardStatus);
}

async function resetClipboard(){
  await safeFetchJson('/reset-clipboard', { method: 'POST', cache: 'no-store' });
  showToast('Clipboard cleared');
  setTimeout(fetchClipboardFromServer, 200);
}

async function deleteClipboardEntry(index){
  const res = await safeFetchJson('/clipboard/delete', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ index }), cache: 'no-store' });
  if (res.ok) { showToast('Message deleted'); setTimeout(fetchClipboardFromServer, 120); }
  else { showToast('Delete failed', true); setTimeout(fetchClipboardFromServer, 200); }
}

function nextMessage() {
    const messages = document.querySelectorAll('.clipboard-item');
    if (messages.length === 0) return;

    // Remove highlight from the old message
    if (currentMessageIndex >= 0 && messages[currentMessageIndex]) {
        messages[currentMessageIndex].classList.remove('current-message-highlight');
    }

    // Move to the next index, looping back to 0 if at the end
    currentMessageIndex++;
    if (currentMessageIndex >= messages.length) {
        currentMessageIndex = 0;
    }

    // Scroll to and highlight the new message
    const nextMsg = messages[currentMessageIndex];
    if (nextMsg) {
        nextMsg.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        nextMsg.classList.add('current-message-highlight');
    }
}

async function fetchClipboardFromServer(){
  const r = await safeFetchJson('/clipboard', { cache: 'no-store' });
  if (!r.json) return;
  const arr = r.json.accumulated_text || [];
  const list = document.getElementById('clipboard-list');
  const nextBtn = document.getElementById('nextMessageBtn');
  const newHash = JSON.stringify(arr);

  if (list.dataset.hash === newHash) return;
  
  list.dataset.hash = newHash;
  list.innerHTML = '';
  currentMessageIndex = -1; // Reset index on refresh
  nextBtn.disabled = arr.length === 0;

  const re = /^\[([^\]]+)\]\s*([\s\S]*)$/;

  arr.slice().reverse().forEach((fullText, revIdx) => {
    const origIndex = arr.length - 1 - revIdx;
    let timestamp = '[?]';
    let message = fullText;
    const m = fullText.match(re);
    if (m) { timestamp = `[${m[1]}]`; message = m[2]; }

    const item = document.createElement('div');
    item.className = 'clipboard-item list-item';
    item.dataset.message = message;
    item.dataset.index = origIndex;
    
    const content = document.createElement('div');
    content.className = 'clipboard-content';
    const header = document.createElement('div');
    header.className = 'message-header';
    const ts = document.createElement('div');
    ts.className = 'timestamp';
    ts.textContent = timestamp;
    header.appendChild(ts);
    content.appendChild(header);
    const body = document.createElement('div');
    body.className = 'message-body';
    body.textContent = message;
    content.appendChild(body);
    const actions = document.createElement('div');
    actions.className = 'clipboard-actions';
    const copyBtn = document.createElement('button');
    copyBtn.className = 'btn btn-secondary btn-sm';
    copyBtn.title = 'Copy';
    copyBtn.innerHTML = '<i data-feather="copy"></i>';
    copyBtn.onclick = () => copyText(message, clipboardStatus);
    const delBtn = document.createElement('button');
    delBtn.className = 'btn btn-danger btn-sm';
    delBtn.title = 'Delete';
    delBtn.innerHTML = '<i data-feather="trash-2"></i>';
    delBtn.onclick = () => { delBtn.disabled = true; deleteClipboardEntry(origIndex); };
    actions.appendChild(copyBtn);
    actions.appendChild(delBtn);
    item.appendChild(content);
    item.appendChild(actions);
    list.appendChild(item);
  });
  feather.replace();
}

async function fetchFileList(){
  const r = await safeFetchJson('/files', { cache: 'no-store' });
  if (!r.json) return;
  const files = r.json.files || [];
  const list = document.getElementById('fileList');
  const newHash = JSON.stringify(files);
  if (list.dataset.hash === newHash) return;
  list.dataset.hash = newHash;
  list.innerHTML = '';

  files.forEach(file => {
    const li = document.createElement('li');
    li.className = 'list-item';
    const info = document.createElement('div');
    info.className = 'file-info';
    const icon = document.createElement('i'); icon.setAttribute('data-feather','file-text');
    info.appendChild(icon);
    const span = document.createElement('span'); span.textContent = file;
    info.appendChild(span);
    const actions = document.createElement('div');
    actions.className = 'file-actions';
    const dl = document.createElement('a');
    dl.className = 'btn btn-primary btn-sm';
    dl.href = `/uploads/${encodeURIComponent(file)}`;
    dl.setAttribute('download', file);
    dl.title = 'Download';
    dl.innerHTML = '<i data-feather="download"></i>';
    const view = document.createElement('a');
    view.className = 'btn btn-secondary btn-sm';
    view.href = `/view/${encodeURIComponent(file)}`;
    view.target = '_blank';
    view.title = 'View';
    view.innerHTML = '<i data-feather="eye"></i>';
    const delBtn = document.createElement('button');
    delBtn.className = 'btn btn-danger btn-sm';
    delBtn.title = 'Delete';
    delBtn.innerHTML = '<i data-feather="trash-2"></i>';
    delBtn.onclick = async () => {
      delBtn.disabled = true;
      const res = await safeFetchJson(`/delete/${encodeURIComponent(file)}`, { method: 'POST' });
      if (res.ok) { showToast(`Deleted: ${file}`); setTimeout(fetchFileList, 200); }
      else { showToast('Delete failed', true); delBtn.disabled = false; }
    };
    actions.appendChild(dl);
    actions.appendChild(view);
    actions.appendChild(delBtn);
    li.appendChild(info);
    li.appendChild(actions);
    list.appendChild(li);
  });
  feather.replace();
}

async function resetFiles(){
  const res = await safeFetchJson('/reset-files', { method: 'POST', cache: 'no-store' });
  if (res.ok) { showToast('All files removed'); setTimeout(fetchFileList, 300); }
  else { showToast('Reset failed', true); }
}

document.addEventListener('DOMContentLoaded', () => {
  feather.replace();
  document.getElementById('clipboardInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); shareManualInput(); }
  });
  document.body.addEventListener('click', requestClipboardPermission, { once: true });
  fetchClipboardFromServer();
  fetchFileList();
});

setInterval(autoShareClipboard, 2000);
setInterval(fetchClipboardFromServer, 2000);
setInterval(fetchFileList, 2000);
</script>
</body>
</html>
"""

# --- Backend Routes ---

def get_unique_filename(folder, filename):
    """Generates a unique filename to avoid overwrites."""
    safe_name = secure_filename(filename)
    if not safe_name:
        safe_name = "unnamed_file"
    base, ext = os.path.splitext(safe_name)
    candidate = safe_name
    i = 1
    while os.path.exists(os.path.join(folder, candidate)):
        candidate = f"{base}_{i}{ext}"
        i += 1
    return candidate

@app.route("/", methods=["GET", "POST"])
def index():
    global files
    if request.method == "POST":
        uploaded_files = request.files.getlist("file")
        for file in uploaded_files:
            if file and file.filename:
                unique_name = get_unique_filename(app.config["UPLOAD_FOLDER"], file.filename)
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
                file.save(save_path)
                if unique_name not in files:
                    files.append(unique_name)
                logging.info("Uploaded file saved: %s", unique_name)
        save_data()
        return jsonify({"status": "success"}), 200
    return render_template_string(HTML_TEMPLATE)

@app.route("/upload-from-url", methods=["POST"])
def upload_from_url():
    global files
    data = request.get_json(silent=True) or {}
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL is missing."}), 400
    try:
        with requests.get(url, stream=True, timeout=15) as r:
            r.raise_for_status()
            filename = ""
            cd = r.headers.get("content-disposition")
            if cd:
                matches = re.findall(r"filename\*=UTF-8''([^;\s]+)", cd)
                if matches:
                    filename = matches[0].strip('"\'')
                else:
                    m = re.search(r'filename=([^;\n]+)', cd)
                    if m:
                        filename = m.group(1).strip(' "\'')
            if not filename:
                path = urlparse(url).path
                filename = os.path.basename(path) or "downloaded_file"
            unique_name = get_unique_filename(app.config["UPLOAD_FOLDER"], filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            if unique_name not in files:
                files.append(unique_name)
            save_data()
            logging.info("Downloaded from URL saved: %s", unique_name)
            return jsonify({"status": "success", "filename": unique_name}), 200
    except requests.exceptions.RequestException as e:
        logging.error("Download failed for URL %s: %s", url, e)
        return jsonify({"error": "Failed to download from URL."}), 500
    except Exception:
        logging.exception("Unexpected error during URL upload")
        return jsonify({"error": "An unexpected error occurred."}), 500

@app.route("/uploads/<path:filename>")
def download_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)

@app.route("/inline/<path:filename>")
def inline_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/view/<path:filename>")
def view_file(filename):
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(file_path):
        return "File not found", 404

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    text_exts = ["txt", "py", "log", "csv", "json", "js", "html", "css", "cpp", "c", "java", "rb", "php", "sh", "go", "rs", "md"]
    image_exts = ["png", "jpg", "jpeg", "gif", "bmp", "svg", "webp"]
    office_exts = ["doc", "docx", "rtf", "ppt", "pptx", "xls", "xlsx"]

    # Common "Download" fallback page
    def show_download_page(reason=""):
        safe_name = escape(filename)
        download_url = f"/uploads/{quote(filename)}"
        return f'<body style="background-color: #000; color: #eee; font-family: sans-serif; text-align: center; padding-top: 50px;"><h2>Preview not available</h2><p>{reason}</p><p><a href="{download_url}" style="color: #0ea5e9;" download>Download File: {safe_name}</a></p></body>'

    if ext in text_exts:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            safe_content = escape(content)
            return f'<pre style="color:#e0e0e0;background:#0b0c0d;padding:20px;white-space:pre-wrap;word-wrap:break-word;">{safe_content}</pre>'
        except Exception:
            return "Could not decode this text file as UTF-8.", 500
    elif ext in image_exts:
        return f'<body style="background:#000;margin:0;display:flex;align-items:center;justify-content:center;height:100vh;"><img src="/inline/{quote(filename)}" style="max-width:100%;max-height:100%;"></body>'
    elif ext == "pdf":
        return f'<iframe src="/inline/{quote(filename)}" width="100%" height="100%" style="border:none;"></iframe>'
    elif ext in office_exts:
        # This will always attempt to use the Microsoft viewer.
        # It requires the server to be on a public IP to work.
        file_url = quote(request.url_root + f"inline/{filename}", safe=":/")
        viewer_url = f"https://view.officeapps.live.com/op/embed.aspx?src={file_url}"
        return f'<iframe src="{viewer_url}" width="100%" height="100%" frameborder="0">This browser does not support inline frames.</iframe>'
    else:
        return show_download_page()

@app.route("/delete/<path:filename>", methods=["POST"])
def delete_file(filename):
    global files
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            os.remove(file_path)
            if filename in files:
                files.remove(filename)
            save_data()
            logging.info("Deleted file: %s (client %s)", filename, request.remote_addr)
            return jsonify({"status": "success", "filename": filename}), 200
        except Exception:
            logging.exception("Failed to delete file")
            return jsonify({"status": "error", "error": "Unable to delete file"}), 500
    else:
        if filename in files:
            files.remove(filename)
            save_data()
        return jsonify({"status": "error", "error": "File not found"}), 404

@app.route("/clipboard", methods=["GET", "POST"])
def handle_clipboard():
    global clipboard
    if request.method == "POST":
        data = request.get_json(silent=True)
        if data and "text" in data and data["text"].strip():
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            clipboard.append(f"[{timestamp}] {data['text']}")
            if len(clipboard) > 100:
                clipboard.pop(0)
            save_data()
            return jsonify({"status": "success"}), 200
        return jsonify({"status": "error", "message": "No text provided"}), 400
    else:
        resp = make_response(jsonify({"accumulated_text": clipboard}))
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return resp

@app.route("/clipboard/delete", methods=["POST"])
def delete_clipboard_entry():
    global clipboard
    data = request.get_json(silent=True) or {}
    if "index" not in data:
        return jsonify({"status": "error", "error": "Missing index"}), 400
    try:
        idx = int(data["index"])
        if 0 <= idx < len(clipboard):
            removed = clipboard.pop(idx)
            save_data()
            logging.info("Clipboard entry deleted by %s: %s", request.remote_addr, removed)
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "error", "error": "Index out of range"}), 404
    except (ValueError, TypeError):
        return jsonify({"status": "error", "error": "Invalid index"}), 400

@app.route("/reset-clipboard", methods=["POST"])
def reset_clipboard_route():
    global clipboard
    clipboard.clear()
    save_data()
    logging.info("Clipboard reset by %s", request.remote_addr)
    return jsonify({"status": "success"}), 200

@app.route("/reset-files", methods=["POST"])
def reset_files_route():
    global files
    removed_count = 0
    for filename in list(files):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
            files.remove(filename)
            removed_count += 1
        except Exception as e:
            logging.error("Could not remove file %s during reset: %s", filename, e)
    save_data()
    logging.info("Reset files called by %s, removed %d files", request.remote_addr, removed_count)
    return jsonify({"status": "success", "removed_count": removed_count}), 200

@app.route("/files")
def files_endpoint():
    disk_files = set(os.listdir(UPLOAD_FOLDER))
    memory_files = set(files)
    if disk_files != memory_files:
        logging.warning("Syncing file list: disk and memory are out of sync.")
        files[:] = sorted(list(disk_files))
        save_data()
    resp = make_response(jsonify(files=files))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp

if __name__ == "__main__":
    logging.info("--- CopyCat Server ---")
    logging.info("Access from any device on your network via http://<YOUR_IP_ADDRESS>:5000")
    logging.info("--------------------")
    app.run(debug=False, host="0.0.0.0", port=5000)