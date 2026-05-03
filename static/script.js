// Global variables
let currentPage = 1;
let statusChartObj = null, trendChartObj = null;

// Helper escape HTML
function escapeHtml(str) {
    return String(str).replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// DOM Elements
const authTypeSelect = document.getElementById('authType');
const authDynamic = document.getElementById('authDynamicFields');
const bodyTypeSelect = document.getElementById('bodyType');
const bodyDynamic = document.getElementById('bodyDynamicField');
const sendBtn = document.getElementById('sendRequestBtn');
const exportCsv = document.getElementById('exportCsvBtn');
const exportJson = document.getElementById('exportJsonBtn');
const newEnvBtn = document.getElementById('newEnvBtn');

// Update auth fields
function updateAuthFields() {
    const val = authTypeSelect.value;
    if (val === 'bearer') {
        authDynamic.innerHTML = `<label>Bearer Token</label><input type="text" id="bearerToken" placeholder="eyJhbGciOiJIUzI1NiIs...">`;
    } else if (val === 'basic') {
        authDynamic.innerHTML = `<label>Username</label><input id="basicUser"><label>Password</label><input type="password" id="basicPass">`;
    } else if (val === 'api_key') {
        authDynamic.innerHTML = `<label>Key Name</label><input id="apiKeyName"><label>Key Value</label><input id="apiKeyValue"><label>Location</label><select id="apiKeyLoc"><option>header</option><option>query</option></select>`;
    } else {
        authDynamic.innerHTML = '';
    }
}

function updateBodyFields() {
    const val = bodyTypeSelect.value;
    if (val === 'json') {
        bodyDynamic.innerHTML = `<label>JSON Body</label><textarea id="jsonBody" rows="6" placeholder='{\n  "key": "value"\n}'></textarea>`;
    } else if (val === 'form') {
        bodyDynamic.innerHTML = `<label>Form Data (key=value&...)</label><textarea id="formBody" rows="3" placeholder="name=John&age=30"></textarea>`;
    } else {
        bodyDynamic.innerHTML = '';
    }
}

// Send Request
async function sendRequest() {
    const method = document.getElementById('reqMethod').value;
    const url = document.getElementById('reqUrl').value;
    const headersRaw = document.getElementById('reqHeaders').value;
    const authType = authTypeSelect.value;
    let authData = {};
    if (authType === 'bearer') authData = { token: document.getElementById('bearerToken')?.value };
    else if (authType === 'basic') authData = { username: document.getElementById('basicUser')?.value, password: document.getElementById('basicPass')?.value };
    else if (authType === 'api_key') authData = { key_name: document.getElementById('apiKeyName')?.value, key_value: document.getElementById('apiKeyValue')?.value, location: document.getElementById('apiKeyLoc')?.value };
    const bodyType = bodyTypeSelect.value;
    let bodyContent = '';
    if (bodyType === 'json') bodyContent = document.getElementById('jsonBody')?.value;
    if (bodyType === 'form') bodyContent = document.getElementById('formBody')?.value;

    const payload = { method, url, headers: headersRaw, auth_type: authType, auth_data: authData, body_type: bodyType, body_content: bodyContent };
    try {
        const res = await fetch('/api/send', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const data = await res.json();
        document.getElementById('respStatus').innerHTML = `Status: ${data.status_code || '?'} ${data.success ? '✅' : '❌'}`;
        document.getElementById('respTime').innerHTML = `<i class="far fa-clock"></i> ${data.response_time_ms} ms`;
        let bodyHtml = data.body;
        if (typeof data.body === 'object') bodyHtml = JSON.stringify(data.body, null, 2);
        document.getElementById('respBody').innerHTML = escapeHtml(bodyHtml);
        document.getElementById('respHeaders').innerHTML = escapeHtml(JSON.stringify(data.headers, null, 2));
        if (typeof hljs !== 'undefined') hljs.highlightAll();
    } catch(e) { alert('Request failed: '+e); }
}

// History
async function loadHistory(page) {
    try {
        const resp = await fetch(`/api/history?page=${page}`);
        const data = await resp.json();
        const tbody = document.getElementById('historyBody');
        tbody.innerHTML = '';
        data.items.forEach(item => {
            const row = `<tr>
                <td><span class="badge-status" style="background:#e2e8f0;">${item.method}</span></td>
                <td style="max-width:300px; overflow:hidden; text-overflow:ellipsis;">${item.url}</td>
                <td>${item.status}</td>
                <td>${item.time_ms}</td>
                <td>${new Date(item.created_at).toLocaleString()}</td>
                <td><button class="secondary" onclick="viewDetail(${item.id})">Detail</button></td>
            </tr>`;
            tbody.innerHTML += row;
        });
        const paginationDiv = document.getElementById('paginationControls');
        if (paginationDiv) {
            paginationDiv.innerHTML = '';
            for (let i = 1; i <= data.pages; i++) {
                const btn = document.createElement('button');
                btn.innerText = i;
                btn.className = 'secondary';
                btn.style.margin = '0 4px';
                if (i === page) { btn.style.background = '#3b82f6'; btn.style.color = 'white'; }
                btn.onclick = () => loadHistory(i);
                paginationDiv.appendChild(btn);
            }
        }
    } catch(e) { console.error(e); }
}

window.viewDetail = async (id) => {
    const res = await fetch(`/api/history/${id}`);
    const data = await res.json();
    alert(`Request ${id}\nMethod: ${data.method}\nURL: ${data.url}\nStatus: ${data.response_status}\nBody preview: ${data.response_body_preview}`);
};

// Analytics
async function loadAnalytics() {
    try {
        const res = await fetch('/api/analytics/stats');
        const data = await res.json();
        document.getElementById('totalReqs').innerText = data.total_requests;
        document.getElementById('avgRespTime').innerText = data.avg_response_time_ms + ' ms';
        document.getElementById('successRate').innerText = data.success_rate_percent + '%';

        const ctx = document.getElementById('statusChart').getContext('2d');
        if (statusChartObj) statusChartObj.destroy();
        statusChartObj = new Chart(ctx, {
            type: 'doughnut',
            data: { labels: Object.keys(data.status_distribution), datasets: [{ data: Object.values(data.status_distribution), backgroundColor: ['#3b82f6','#ef4444','#10b981','#f59e0b'] }] },
            options: { responsive: true, maintainAspectRatio: true }
        });

        const trendCtx = document.getElementById('trendChart').getContext('2d');
        if (trendChartObj) trendChartObj.destroy();
        trendChartObj = new Chart(trendCtx, {
            type: 'line',
            data: { labels: data.response_time_trend.map(t=>t.date), datasets: [{ label: 'Avg Response Time (ms)', data: data.response_time_trend.map(t=>t.avg_time), borderColor: '#3b82f6', tension: 0.2 }] }
        });

        const topList = document.getElementById('topEndpointsList');
        if (topList) topList.innerHTML = data.popular_endpoints.map(ep => `<li><i class="fas fa-link"></i> ${ep.url} <span style="float:right;">${ep.count} req</span></li>`).join('');
    } catch(e) { console.error(e); }
}

// Environments
async function loadEnvironments() {
    try {
        const res = await fetch('/api/environments');
        const envs = await res.json();
        const container = document.getElementById('envList');
        if (!container) return;
        if (envs.length === 0) container.innerHTML = '<div class="card" style="background:#f8fafc;">No environments yet. Click + New to create.</div>';
        else {
            container.innerHTML = envs.map(env => `
                <div class="card" style="margin-bottom:16px;">
                    <div style="display:flex; justify-content:space-between;"><strong>${env.name}</strong> 
                        <div><button class="secondary" onclick="editEnv(${env.id}, '${env.name}', ${JSON.stringify(env.variables).replace(/"/g, '&quot;')})">Edit</button>
                        <button class="secondary" style="background:#fee2e2;" onclick="deleteEnv(${env.id})">Delete</button></div>
                    </div>
                    <pre style="background:#f1f5f9; padding:8px; border-radius:12px;">${JSON.stringify(env.variables, null, 2)}</pre>
                </div>
            `).join('');
        }
    } catch(e) { console.error(e); }
}

window.editEnv = (id, name, vars) => {
    const newName = prompt('Environment name:', name);
    if (newName) {
        const newVars = prompt('Variables as JSON:', JSON.stringify(vars));
        if (newVars) {
            fetch(`/api/environments/${id}`, { method: 'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ name: newName, variables: JSON.parse(newVars) }) }).then(()=>loadEnvironments());
        }
    }
};

window.deleteEnv = async (id) => {
    if (confirm('Delete environment?')) await fetch(`/api/environments/${id}`, { method: 'DELETE' });
    loadEnvironments();
};

// Tab switching (for index.html with tab panels)
function initTabs() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            // Jika link biasa (a href) biarkan berjalan normal, hanya untuk tab fake
            if (item.getAttribute('href') && item.getAttribute('href') !== '#') return;
            e.preventDefault();
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
            const tabId = item.getAttribute('data-tab');
            if (tabId) {
                document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active-panel'));
                const targetPanel = document.getElementById(`${tabId}Panel`);
                if (targetPanel) targetPanel.classList.add('active-panel');
                if (tabId === 'history') loadHistory(1);
                if (tabId === 'analytics') loadAnalytics();
                if (tabId === 'environments') loadEnvironments();
            }
        });
    });
}

// Event Listeners & Initialization
document.addEventListener('DOMContentLoaded', () => {
    // Tab switching only for in-page tabs (if they exist)
    if (document.querySelector('.nav-item[data-tab]')) {
        initTabs();
    }

    // Auth & Body dynamic fields
    if (authTypeSelect) authTypeSelect.addEventListener('change', updateAuthFields);
    if (bodyTypeSelect) bodyTypeSelect.addEventListener('change', updateBodyFields);
    if (sendBtn) sendBtn.addEventListener('click', sendRequest);
    if (exportCsv) exportCsv.addEventListener('click', () => window.open('/api/history/export/csv', '_blank'));
    if (exportJson) exportJson.addEventListener('click', () => window.open('/api/history/export/json', '_blank'));
    if (newEnvBtn) newEnvBtn.addEventListener('click', async () => {
        const name = prompt('Environment name:');
        if (name) {
            const vars = prompt('Variables (JSON format):', '{}');
            if (vars) {
                await fetch('/api/environments', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ name, variables: JSON.parse(vars) }) });
                loadEnvironments();
            }
        }
    });

    if (authTypeSelect) updateAuthFields();
    if (bodyTypeSelect) updateBodyFields();

    // Load data jika panel aktif
    if (document.getElementById('historyPanel') && document.getElementById('historyPanel').classList.contains('active-panel')) {
        loadHistory(1);
    }
    if (document.getElementById('analyticsPanel') && document.getElementById('analyticsPanel').classList.contains('active-panel')) {
        loadAnalytics();
    }
    if (document.getElementById('environmentsPanel') && document.getElementById('environmentsPanel').classList.contains('active-panel')) {
        loadEnvironments();
    }
});