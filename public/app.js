// --- CONSTANTS ---
const OFFICE_EXTENSIONS = ['docx', 'docm', 'dotm', 'dotx', 'xlsx', 'xlsb', 'xls', 'xlsm', 'pptx', 'ppsx', 'ppt', 'pps', 'pptm', 'potm', 'ppam', 'potx', 'ppsm', 'rtf'];
const IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'];
const CODE_EXTENSIONS = ['java', 'py', 'c', 'cpp', 'cs', 'rb', 'go', 'js', 'ts', 'html', 'css', 'xml', 'json', 'sh', 'bat'];
const TEXT_EXTENSIONS = ['txt', 'md', 'csv'];

// --- DOM Elements ---
const clipboardInput = document.getElementById('clipboardInput');
const shareBtn = document.getElementById('shareBtn');
const clipboardList = document.getElementById('clipboard-list');
const resetClipboardBtn = document.getElementById('resetClipboardBtn');
const clipboardStatus = document.getElementById('clipboard-status');
const clipboardTitleInput = document.getElementById('clipboardTitleInput');
const nextMessageBtn = document.getElementById('nextMessageBtn');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileList = document.getElementById('fileList');
const resetFilesBtn = document.getElementById('resetFilesBtn');
const uploadStatus = document.getElementById('upload-status');
const urlInput = document.getElementById('url-input');
const urlUploadBtn = document.getElementById('url-upload-btn');
const renameContainer = document.getElementById('rename-container');
const renameInput = document.getElementById('rename-input');
const renameTitle = document.getElementById('rename-title');
const confirmUploadBtn = document.getElementById('confirm-upload-btn');
const cancelUploadBtn = document.getElementById('cancel-upload-btn');
const clipboardSearchInput = document.getElementById('clipboardSearchInput');

let supabase;
let currentMessageIndex = -1;
let filesToUploadQueue = [];
let lastClipboardText = '';

// --- UTILITY FUNCTIONS ---
function showToast(message, isError = false) {
    const container = document.getElementById('toast-container');
    const div = document.createElement('div');
    div.className = 'toast ' + (isError ? 'error' : 'success');
    div.textContent = message;
    container.appendChild(div);
    setTimeout(() => {
        div.style.transition = 'opacity 0.28s';
        div.style.opacity = '0';
        setTimeout(() => div.remove(), 3200);
    }, 2200);
}

function escapeHTML(str) {
  if (!str) return '';
  return str.toString().replace(/[&<>"']/g, match => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[match]));
}

function setUploadStatus(msg, isErr = false) {
    uploadStatus.textContent = msg;
    uploadStatus.style.color = isErr ? 'var(--danger)' : 'var(--accent)';
    setTimeout(() => { if (uploadStatus.textContent === msg) uploadStatus.textContent = ''; }, 3000);
}

function copyText(text) {
    if (!navigator.clipboard) return;
    navigator.clipboard.writeText(text).then(() => showToast('Copied to clipboard!')).catch(err => console.error('Copy failed', err));
}

function formatTimestamp(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true });
}

function dataURLtoFile(dataurl, filename) {
    var arr = dataurl.split(','), mime = arr[0].match(/:(.*?);/)[1],
        bstr = atob(arr[1]), n = bstr.length, u8arr = new Uint8Array(n);
    while(n--) u8arr[n] = bstr.charCodeAt(n);
    return new File([u8arr], filename, {type:mime});
}

function filterMessages() {
    const searchTerm = clipboardSearchInput.value.toLowerCase();
    const messages = clipboardList.querySelectorAll('.list-item.clipboard-item');
    
    messages.forEach(message => {
        const titleElement = message.querySelector('.message-title');
        const contentElement = message.querySelector('.message-body code');
        
        const title = titleElement ? titleElement.textContent.toLowerCase() : '';
        const content = contentElement ? contentElement.textContent.toLowerCase() : '';
        
        if (title.includes(searchTerm) || content.includes(searchTerm)) {
            message.style.display = ''; // Show the message
        } else {
            message.style.display = 'none'; // Hide the message
        }
    });
}

// --- CLIPBOARD FEATURE ---
async function fetchMessages() {
    const { data, error } = await supabase.from('messages').select('*').order('created_at', { ascending: false }).limit(100);
    if (error) { console.error('Error fetching messages:', error); return; }

    currentMessageIndex = -1;
    clipboardList.innerHTML = '';

    data.forEach(msg => {
        const listItem = document.createElement('div');
        listItem.className = 'list-item clipboard-item';
        const titleHTML = msg.title ? `<div class="message-title">${escapeHTML(msg.title)}</div>` : '';
        listItem.innerHTML = `<div class="clipboard-content"><div class="message-header">${titleHTML}<div class="timestamp">${formatTimestamp(msg.created_at)}</div></div><div class="message-body"><pre><code></code></pre></div></div><div class="clipboard-actions"></div>`;
        listItem.querySelector('.message-body code').textContent = msg.content;

        const actionsDiv = listItem.querySelector('.clipboard-actions');
        const copyBtn = document.createElement('button');
        copyBtn.className = 'btn btn-secondary btn-sm'; copyBtn.title = 'Copy';
        copyBtn.innerHTML = `<i data-feather="copy"></i>`; copyBtn.onclick = () => copyText(msg.content);

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-danger btn-sm'; deleteBtn.title = 'Delete';
        deleteBtn.innerHTML = `<i data-feather="trash-2"></i>`; deleteBtn.onclick = () => deleteMessage(msg.id);

        actionsDiv.appendChild(copyBtn); actionsDiv.appendChild(deleteBtn);
        clipboardList.appendChild(listItem);
    });
    feather.replace();
    filterMessages();
}

async function shareMessage() {
    const content = clipboardInput.value;
    const title = clipboardTitleInput.value.trim();
    if (content) {
        clipboardInput.disabled = true; clipboardTitleInput.disabled = true; shareBtn.disabled = true;
        const messageData = { content };
        if (title) messageData.title = title;
        const { error } = await supabase.from('messages').insert(messageData);
        if (error) { showToast('Failed to share message.', true); console.error('Share error:', error); }
        else { clipboardInput.value = ''; clipboardTitleInput.value = ''; }
        clipboardInput.disabled = false; clipboardTitleInput.disabled = false; shareBtn.disabled = false;
        clipboardInput.focus();
    }
}

async function deleteMessage(id) {
    const { error } = await supabase.from('messages').delete().eq('id', id);
    if (error) showToast('Failed to delete message.', true); else showToast('Message deleted.');
}

async function resetClipboard() {
    const { error } = await supabase.from('messages').delete().neq('id', 0);
    if (error) showToast('Failed to reset clipboard.', true); else showToast('Clipboard cleared.');
}

function selectNextMessage() {
    const messages = clipboardList.querySelectorAll('.list-item');
    if (messages.length === 0) return;
    if (currentMessageIndex > -1) messages[currentMessageIndex].classList.remove('highlighted');
    currentMessageIndex = (currentMessageIndex + 1) % messages.length;
    const currentMessage = messages[currentMessageIndex];
    currentMessage.classList.add('highlighted');
    currentMessage.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// --- FILE HUB FEATURE ---
async function fetchFiles() {
    const { data, error } = await supabase.storage.from('files').list('', { sortBy: { column: 'created_at', order: 'desc' } });
    if (error) { console.error('Error listing files:', error); return; }
    fileList.innerHTML = '';
    data.forEach(file => {
        const listItem = document.createElement('li');
        listItem.className = 'list-item';
        const fileUrl = supabase.storage.from('files').getPublicUrl(file.name).data.publicUrl;
        listItem.innerHTML = `<div class="file-info"><i data-feather="file-text"></i><span></span></div><div class="file-actions"><a class="btn btn-primary btn-sm" href="${fileUrl}" title="Download"><i data-feather="download"></i></a></div>`;
        listItem.querySelector('.file-info span').textContent = file.name;

        const previewBtn = document.createElement('button');
        previewBtn.className = 'btn btn-secondary btn-sm';
        previewBtn.title = 'Preview';
        previewBtn.innerHTML = `<i data-feather="eye"></i>`;
        previewBtn.onclick = () => showPreview(fileUrl, file.name);
        listItem.querySelector('.file-actions').appendChild(previewBtn);

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn btn-danger btn-sm'; deleteBtn.title = 'Delete';
        deleteBtn.innerHTML = `<i data-feather="trash-2"></i>`; deleteBtn.onclick = () => deleteFile(file.name);
        listItem.querySelector('.file-actions').appendChild(deleteBtn);
        fileList.appendChild(listItem);
    });
    feather.replace();
}

function processFileQueue() {
    if (filesToUploadQueue.length === 0) {
        renameContainer.style.display = 'none';
        return;
    }
    const file = filesToUploadQueue[0];
    renameTitle.innerHTML = `Rename File (${filesToUploadQueue.length} remaining): <br><strong>${escapeHTML(file.name)}</strong>`;
    renameInput.value = file.name;
    renameContainer.style.display = 'block';
    renameInput.focus();
}

async function confirmUpload() {
    const newName = renameInput.value.trim();
    if (!newName) { showToast("File name cannot be empty.", true); return; }

    const fileToUpload = filesToUploadQueue.shift();
    if (fileToUpload) {
        setUploadStatus(`Uploading ${newName}...`);
        const { error } = await supabase.storage.from('files').upload(newName, fileToUpload, {
            upsert: true,
            onUploadProgress: (progress) => {
                const percent = Math.round((progress.loaded / progress.total) * 100);
                setUploadStatus(`Uploading ${newName}... ${percent}%`);
            }
        });
        if (error) { setUploadStatus(`Failed to upload ${newName}.`, true); console.error('Upload error:', error); }
        else { setUploadStatus(`Uploaded ${newName} successfully!`); }
    }
    processFileQueue();
}

async function uploadFileFromUrl() {
    let url = urlInput.value.trim();
    if (!url) return;
    if (url.startsWith('data:')) {
        try {
            const file = dataURLtoFile(url, `pasted-file-${Date.now()}`);
            filesToUploadQueue.push(file);
            processFileQueue();
            urlInput.value = '';
        } catch (error) { setUploadStatus('Failed to upload from data URL.', true); console.error('Data URL Error:', error); }
        return;
    }

    let fetchUrl;
    const isGoogleDrive = url.includes("drive.google.com") || url.includes("docs.google.com");

    if (isGoogleDrive) {
        const match = url.match(/(?:\/d\/|id=)([\w-]+)/);
        if (match && match[1]) {
            const fileId = match[1];
            const directDownloadUrl = `https://drive.google.com/uc?export=download&id=${fileId}`;
            fetchUrl = `/api/fetch-proxy?url=${encodeURIComponent(directDownloadUrl)}`;
        } else { setUploadStatus('Invalid Google Drive link format.', true); return; }
    } else {
        fetchUrl = `/api/fetch-proxy?url=${encodeURIComponent(url)}`;
    }

    setUploadStatus('Fetching file from URL...');
    try {
        const response = await fetch(fetchUrl);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}`);

        const blob = await response.blob();
        const mimeType = blob.type;

        if (mimeType === 'text/html' && !isGoogleDrive) {
             const text = await blob.text();
             const doc = new DOMParser().parseFromString(text, 'text/html');
             const img = doc.querySelector('meta[property="og:image"]');
             if (img && img.content) { urlInput.value = img.content; uploadFileFromUrl(); return; }
             else { throw new Error('No direct image found on the page.'); }
        }

        let fileName = response.headers.get('X-Filename');
        if (!fileName || fileName === 'downloaded-file') {
             fileName = url.substring(url.lastIndexOf('/') + 1).split('?')[0] || `file-${Date.now()}`;
        }

        const file = new File([blob], fileName, { type: mimeType });
        filesToUploadQueue.push(file);
        processFileQueue();
        urlInput.value = '';

    } catch (error) {
        setUploadStatus(`Failed to fetch from URL. ${error.message}`, true);
        console.error('URL Fetch Error:', error);
    }
}

async function deleteFile(fileName) {
    const { error } = await supabase.storage.from('files').remove([fileName]);
    if (error) showToast(`Failed to delete ${fileName}.`, true);
    else showToast(`Deleted ${fileName}.`);
}

async function resetFiles() {
    const { data: files, error } = await supabase.storage.from('files').list();
    if (error) { showToast('Could not list files to delete.', true); return; }
    if (files.length === 0) { showToast('No files to delete.'); return; }
    const fileNames = files.map(f => f.name);
    const { error: deleteError } = await supabase.storage.from('files').remove(fileNames);
    if (deleteError) showToast('Failed to delete all files.', true);
    else showToast('All files have been deleted.');
}

// --- REWRITTEN: Preview Logic ---
async function showPreview(fileUrl, fileName) {
    const extension = fileName.split('.').pop().toLowerCase();
    const openPreviewTab = (content) => {
        const previewTab = window.open('about:blank', '_blank');
        previewTab.document.write(content);
        previewTab.document.close();
    };

    showToast(`Opening preview for ${escapeHTML(fileName)}...`);

    try {
        if (OFFICE_EXTENSIONS.includes(extension)) {
            const officeUrl = `https://view.officeapps.live.com/op/view.aspx?src=${encodeURIComponent(fileUrl)}`;
            window.open(officeUrl, '_blank');
        } else if (IMAGE_EXTENSIONS.includes(extension) || extension === 'pdf') {
            openPreviewTab(`<body style="margin:0; background-color: #282c34;"><iframe src="${fileUrl}" frameborder="0" style="width:100%; height:100vh;"></iframe></body>`);
        } else if (CODE_EXTENSIONS.includes(extension) || TEXT_EXTENSIONS.includes(extension)) {
            const response = await fetch(fileUrl);
            const text = await response.text();
            let content;

            if (extension === 'csv') {
                const rows = text.trim().split('\n').map(row => `<tr><td>${row.split(',').join('</td><td>')}</td></tr>`).join('');
                content = `<html><head><title>Preview: ${escapeHTML(fileName)}</title><style>html,body{margin:0;padding:0;height:100%;} body{font-family:monospace;background-color:#282c34;color:#abb2bf;padding:1em;} table{width:100%;border-collapse:collapse;} td,th{border:1px solid #555;padding:8px;text-align:left;} th{background-color:#444;}</style></head><body><table>${rows}</table></body></html>`;
            } else if (extension === 'md') {
                const html = marked.parse(text);
                content = `<html><head><title>Preview: ${escapeHTML(fileName)}</title><style>html,body{margin:0;padding:0;height:100%;} body{font-family:sans-serif;background-color:#282c34;color:#abb2bf;padding:2em;} h1,h2,h3{color:#61afef;} a{color:#98c379;} code{background:#3a3f4b;padding:2px 4px;border-radius:4px;}</style></head><body>${html}</body></html>`;
            } else {
                content = `<html><head><title>Preview: ${escapeHTML(fileName)}</title><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/atom-one-dark.min.css"><style>html, body { margin:0; padding:0; height:100%; font-family: monospace; background-color: #282c34; } pre { margin: 1em; }</style></head><body><pre><code class="${extension}">${escapeHTML(text)}</code></pre><script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js"><\/script><script>hljs.highlightAll();<\/script></body></html>`;
            }
            openPreviewTab(content);
        } else {
             showToast("Preview not available for this file type.", true);
        }
    } catch (error) {
        console.error('Preview error:', error);
        showToast(`Could not load preview for ${escapeHTML(fileName)}.`, true);
    }
}

// --- UPDATED: Clipboard Sync Logic ---
async function initClipboardSync() {
    try {
        const permissionStatus = await navigator.permissions.query({ name: 'clipboard-read' });
        if (permissionStatus.state === 'granted') {
            showToast("Clipboard sync enabled.");
            setInterval(async () => {
                const text = await navigator.clipboard.readText();
                if (text && text !== lastClipboardText) {
                    clipboardInput.value = text;
                    lastClipboardText = text;
                }
            }, 1000);
        }
    } catch (error) {
        console.log("Clipboard permission not yet granted. Will ask on first focus.");
    }
}

async function requestClipboardSync() {
    try {
        const text = await navigator.clipboard.readText();
        clipboardInput.value = text;
        lastClipboardText = text;
        initClipboardSync(); // Start polling now that permission is granted
    } catch (error) {
        if (error.name === 'NotAllowedError') {
            showToast("Clipboard permission denied.", true);
        } else {
            console.error('Clipboard error:', error);
            showToast("Could not access clipboard.", true);
        }
    }
}

// --- INITIALIZATION ---
async function initializeApp() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) throw new Error('Network response was not ok');
        const config = await response.json();
        if (!config.url || !config.key) throw new Error('Supabase URL or Key is missing from config.');
        supabase = window.supabase.createClient(config.url, config.key);
        await fetchMessages();
        await fetchFiles();
        feather.replace();

        initClipboardSync();

        shareBtn.addEventListener('click', shareMessage);
        clipboardInput.addEventListener('keypress', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); shareMessage(); } });
        clipboardInput.addEventListener('focus', requestClipboardSync, { once: true });
        resetClipboardBtn.addEventListener('click', resetClipboard);
        nextMessageBtn.addEventListener('click', selectNextMessage);
        dropZone.addEventListener('click', () => fileInput.click());
        clipboardSearchInput.addEventListener('keyup', filterMessages);

        fileInput.addEventListener('change', (e) => { if (e.target.files.length > 0) { filesToUploadQueue.push(...e.target.files); processFileQueue(); fileInput.value = ''; } });
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
        dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('dragover'); });
        dropZone.addEventListener('drop', (e) => { e.preventDefault(); dropZone.classList.remove('dragover'); if (e.dataTransfer.files.length > 0) { filesToUploadQueue.push(...e.dataTransfer.files); processFileQueue(); } });

        document.addEventListener('paste', (e) => {
            const activeElement = document.activeElement;
            const isTyping = activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA');
            if (isTyping) return;
            e.preventDefault();
            if (e.clipboardData.files.length > 0) { filesToUploadQueue.push(...e.clipboardData.files); processFileQueue(); }
            else {
                const pastedText = (e.clipboardData || window.clipboardData).getData('text');
                if (pastedText) {
                    urlInput.value = pastedText;
                    showToast('URL pasted. Click Upload to proceed.');
                    urlUploadBtn.classList.add('highlighted');
                    setTimeout(() => urlUploadBtn.classList.remove('highlighted'), 2000);
                }
            }
        });

        urlUploadBtn.addEventListener('click', uploadFileFromUrl);
        resetFilesBtn.addEventListener('click', resetFiles);

        confirmUploadBtn.addEventListener('click', confirmUpload);
        cancelUploadBtn.addEventListener('click', () => {
            filesToUploadQueue.shift();
            processFileQueue();
        });

        supabase.channel('public:messages')
            .on('postgres_changes', { event: '*', schema: 'public', table: 'messages' }, (payload) => { console.log('Message change received!', payload); fetchMessages(); })
            .subscribe((status) => { if (status === 'SUBSCRIBED') console.log('Connected to realtime message channel!'); });

        // Listen for any new row in the 'notifications' table
        supabase.channel('public:notifications')
            .on('postgres_changes', { 
                event: 'INSERT', 
                schema: 'public', 
                table: 'notifications' 
            }, (payload) => {
                console.log('File change detected via notification table!', payload);
                // When a notification is received, refresh the file list
                fetchFiles();
            })
            .subscribe((status) => {
                if (status === 'SUBSCRIBED') {
                    console.log('Connected to notifications channel for file updates!');
                }
            });

    } catch (error) {
        console.error('Failed to initialize the application:', error);
        document.body.innerHTML = '<h1 style="color:red; text-align:center; margin-top: 50px;">Application failed to load. Check console for errors.</h1>';
    }
}
document.addEventListener('DOMContentLoaded', initializeApp);
