import os
import secrets
import json
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, abort, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, desc
import requests as http_requests

# ================= FLASK APP INIT =================
app = Flask(__name__)

# ================= DATABASE CONFIGURATION =================
# Vercel: must provide DATABASE_URL (PostgreSQL)
database_url = os.environ.get('DATABASE_URL')
if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is not set!")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-me')

db = SQLAlchemy(app)

# ================= MODELS =================
class Integration(db.Model):
    __tablename__ = 'integrations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    endpoint = db.Column(db.String(500), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    headers = db.Column(db.Text)          # JSON string
    auth_type = db.Column(db.String(20), default='none')
    auth_config = db.Column(db.Text)      # JSON string
    body_template = db.Column(db.Text)
    response_mapping = db.Column(db.Text) # JSON mapping
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

class ExecutionLog(db.Model):
    __tablename__ = 'execution_logs'
    id = db.Column(db.Integer, primary_key=True)
    integration_id = db.Column(db.Integer, db.ForeignKey('integrations.id'), nullable=True)
    status_code = db.Column(db.Integer)
    response_time_ms = db.Column(db.Float)
    request_payload = db.Column(db.Text)
    response_body = db.Column(db.Text)
    error_message = db.Column(db.Text)
    success = db.Column(db.Boolean, default=False)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    integration = db.relationship('Integration', backref='logs')

class ApiKey(db.Model):
    __tablename__ = 'api_keys'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    key = db.Column(db.String(64), unique=True, nullable=False)
    permissions = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Webhook(db.Model):
    __tablename__ = 'webhooks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    source_url = db.Column(db.String(200), unique=True)
    target_integration_id = db.Column(db.Integer, db.ForeignKey('integrations.id'))
    secret = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)

class Schedule(db.Model):
    __tablename__ = 'schedules'
    id = db.Column(db.Integer, primary_key=True)
    integration_id = db.Column(db.Integer, db.ForeignKey('integrations.id'))
    cron_expression = db.Column(db.String(100))
    next_run = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

# ================= INIT DATABASE & DEFAULT API KEY =================
def init_db():
    with app.app_context():
        db.create_all()
        if not ApiKey.query.first():
            default_key = secrets.token_urlsafe(32)
            api_key = ApiKey(name='default_admin', key=default_key, permissions='admin', is_active=True)
            db.session.add(api_key)
            db.session.commit()
            print(f"Default API Key: {default_key}")

# We'll call init_db at startup, but inside app context
init_db()

# ================= API CLIENT =================
# Minimal APIClient class (assumes 'execute_integration' method)
class APIClient:
    def __init__(self):
        self.session = http_requests.Session()
        self.default_params = {}

    def set_custom_headers(self, headers):
        for k, v in headers.items():
            self.session.headers[k] = v

    def substitute_variables(self, text, context):
        # Simple variable substitution {{variable}}
        if not text:
            return text
        import re
        def replacer(m):
            key = m.group(1).strip()
            return str(context.get(key, ''))
        return re.sub(r'\{\{\s*([^}]+?)\s*\}\}', replacer, text)

    def execute_integration(self, integration, context=None):
        context = context or {}
        endpoint = self.substitute_variables(integration['endpoint'], context)
        method = integration['method']
        headers = json.loads(integration.get('headers') or '{}')
        self.set_custom_headers(headers)
        auth_type = integration.get('auth_type', 'none')
        auth_config = json.loads(integration.get('auth_config') or '{}')
        if auth_type == 'bearer':
            token = auth_config.get('token', '')
            self.session.headers['Authorization'] = f'Bearer {token}'
        elif auth_type == 'basic':
            self.session.auth = (auth_config.get('username', ''), auth_config.get('password', ''))
        elif auth_type == 'api_key':
            key_name = auth_config.get('key_name', '')
            key_value = auth_config.get('key_value', '')
            location = auth_config.get('location', 'header')
            if location == 'header':
                self.session.headers[key_name] = key_value
            else:
                self.default_params[key_name] = key_value
                self.session.params = self.default_params
        body = integration.get('body_template')
        json_body = None
        data_body = None
        if body:
            body_str = self.substitute_variables(body, context)
            try:
                json_body = json.loads(body_str)
            except:
                data_body = body_str
        start = time.time()
        try:
            resp = self.session.request(method, endpoint, json=json_body, data=data_body, timeout=30)
            elapsed = (time.time() - start) * 1000
            try:
                resp_body = resp.json()
            except:
                resp_body = resp.text
            return {
                'success': resp.status_code < 400,
                'status_code': resp.status_code,
                'response_time_ms': round(elapsed, 2),
                'response_body': resp_body,
                'error': None
            }
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return {
                'success': False,
                'status_code': None,
                'response_time_ms': round(elapsed, 2),
                'response_body': None,
                'error': str(e)
            }

def execute_integration_job(integration_id, context=None):
    integration = Integration.query.get(integration_id)
    if not integration or not integration.is_active:
        return {'error': 'Integration not active'}
    client = APIClient()
    integration_dict = {
        'endpoint': integration.endpoint,
        'method': integration.method,
        'headers': integration.headers,
        'auth_type': integration.auth_type,
        'auth_config': integration.auth_config,
        'body_template': integration.body_template
    }
    result = client.execute_integration(integration_dict, context or {})
    log = ExecutionLog(
        integration_id=integration.id,
        status_code=result.get('status_code'),
        response_time_ms=result.get('response_time_ms'),
        request_payload=json.dumps(context or {}),
        response_body=json.dumps(result.get('response_body'))[:5000],
        error_message=result.get('error'),
        success=result.get('success', False)
    )
    db.session.add(log)
    db.session.commit()
    return result

# ================= ROUTES =================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/integrations')
def integrations_page():
    return render_template('integrations.html')

@app.route('/logs')
def logs_page():
    return render_template('logs.html')

@app.route('/settings')
def settings_page():
    return render_template('settings.html')

# --- Integrations CRUD ---
@app.route('/api/integrations', methods=['GET'])
def get_integrations():
    integrations = Integration.query.order_by(Integration.created_at.desc()).all()
    return jsonify([{
        'id': i.id, 'name': i.name, 'description': i.description,
        'endpoint': i.endpoint, 'method': i.method,
        'headers': i.headers, 'auth_type': i.auth_type,
        'auth_config': i.auth_config, 'body_template': i.body_template,
        'response_mapping': i.response_mapping, 'is_active': i.is_active,
        'created_at': i.created_at.isoformat()
    } for i in integrations])

@app.route('/api/integrations', methods=['POST'])
def create_integration():
    data = request.json
    integ = Integration(
        name=data['name'],
        description=data.get('description'),
        endpoint=data['endpoint'],
        method=data['method'],
        headers=json.dumps(data.get('headers', {})),
        auth_type=data.get('auth_type', 'none'),
        auth_config=json.dumps(data.get('auth_config', {})),
        body_template=data.get('body_template'),
        response_mapping=json.dumps(data.get('response_mapping', {})),
        is_active=data.get('is_active', True)
    )
    db.session.add(integ)
    db.session.commit()
    return jsonify({'id': integ.id}), 201

@app.route('/api/integrations/<int:integ_id>', methods=['PUT'])
def update_integration(integ_id):
    integ = Integration.query.get_or_404(integ_id)
    data = request.json
    for key in ['name', 'description', 'endpoint', 'method', 'auth_type', 'body_template', 'is_active']:
        if key in data:
            setattr(integ, key, data[key])
    if 'headers' in data:
        integ.headers = json.dumps(data['headers'])
    if 'auth_config' in data:
        integ.auth_config = json.dumps(data['auth_config'])
    if 'response_mapping' in data:
        integ.response_mapping = json.dumps(data['response_mapping'])
    db.session.commit()
    return jsonify({'message': 'updated'})

@app.route('/api/integrations/<int:integ_id>', methods=['DELETE'])
def delete_integration(integ_id):
    integ = Integration.query.get_or_404(integ_id)
    db.session.delete(integ)
    db.session.commit()
    return jsonify({'message': 'deleted'})

@app.route('/api/integrations/<int:integ_id>/execute', methods=['POST'])
def execute_integration(integ_id):
    context = request.json or {}
    result = execute_integration_job(integ_id, context)
    return jsonify(result)

# --- Logs ---
@app.route('/api/logs', methods=['GET'])
def get_logs():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    integration_id = request.args.get('integration_id', type=int)
    query = ExecutionLog.query
    if integration_id:
        query = query.filter_by(integration_id=integration_id)
    pagination = query.order_by(desc(ExecutionLog.executed_at)).paginate(page=page, per_page=per_page)
    items = [{
        'id': l.id,
        'integration_id': l.integration_id,
        'integration_name': l.integration.name if l.integration else None,
        'status_code': l.status_code,
        'response_time_ms': l.response_time_ms,
        'success': l.success,
        'error_message': l.error_message,
        'executed_at': l.executed_at.isoformat()
    } for l in pagination.items]
    return jsonify({
        'items': items,
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })

# --- Dashboard Stats ---
@app.route('/api/dashboard/stats')
def dashboard_stats():
    total_integrations = Integration.query.count()
    active_integrations = Integration.query.filter_by(is_active=True).count()
    total_executions = ExecutionLog.query.count()
    success_rate = db.session.query(func.avg(ExecutionLog.success.cast(db.Float))).scalar() or 0
    avg_response_time = db.session.query(func.avg(ExecutionLog.response_time_ms)).scalar() or 0
    recent_errors = ExecutionLog.query.filter_by(success=False).order_by(ExecutionLog.executed_at.desc()).limit(5).all()
    error_items = [{
        'id': e.id,
        'integration_name': e.integration.name if e.integration else 'Deleted',
        'error': e.error_message,
        'executed_at': e.executed_at.isoformat()
    } for e in recent_errors]
    return jsonify({
        'total_integrations': total_integrations,
        'active_integrations': active_integrations,
        'total_executions': total_executions,
        'success_rate_percent': round(success_rate * 100, 2),
        'avg_response_time_ms': round(avg_response_time, 2),
        'recent_errors': error_items
    })

# --- API Keys ---
@app.route('/api/api_keys', methods=['GET'])
def get_api_keys():
    keys = ApiKey.query.all()
    return jsonify([{'id': k.id, 'name': k.name, 'key': k.key, 'permissions': k.permissions, 'is_active': k.is_active} for k in keys])

@app.route('/api/api_keys', methods=['POST'])
def create_api_key():
    data = request.json
    key = secrets.token_urlsafe(32)
    api_key = ApiKey(name=data['name'], key=key, permissions=data.get('permissions', 'execute'), is_active=True)
    db.session.add(api_key)
    db.session.commit()
    return jsonify({'id': api_key.id, 'key': key})

@app.route('/api/api_keys/<int:key_id>', methods=['DELETE'])
def delete_api_key(key_id):
    key = ApiKey.query.get_or_404(key_id)
    db.session.delete(key)
    db.session.commit()
    return jsonify({'message': 'deleted'})

# --- Webhooks ---
@app.route('/api/webhooks', methods=['GET'])
def get_webhooks():
    webhooks = Webhook.query.all()
    return jsonify([{
        'id': w.id, 'name': w.name, 'source_url': w.source_url,
        'target_integration_id': w.target_integration_id,
        'secret': w.secret, 'is_active': w.is_active
    } for w in webhooks])

@app.route('/api/webhooks', methods=['POST'])
def create_webhook():
    data = request.json
    wh = Webhook(
        name=data['name'],
        source_url=data['source_url'],
        target_integration_id=data['target_integration_id'],
        secret=data.get('secret'),
        is_active=True
    )
    db.session.add(wh)
    db.session.commit()
    return jsonify({'id': wh.id}), 201

@app.route('/api/webhooks/<int:wh_id>', methods=['DELETE'])
def delete_webhook(wh_id):
    wh = Webhook.query.get_or_404(wh_id)
    db.session.delete(wh)
    db.session.commit()
    return jsonify({'message': 'deleted'})

@app.route('/webhook/<path:webhook_path>', methods=['POST', 'GET', 'PUT', 'DELETE'])
def webhook_receiver(webhook_path):
    webhook = Webhook.query.filter_by(source_url=webhook_path, is_active=True).first()
    if not webhook:
        abort(404)
    if webhook.secret:
        token = request.headers.get('X-Webhook-Secret')
        if token != webhook.secret:
            abort(401)
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    result = execute_integration_job(webhook.target_integration_id, {'payload': payload})
    return jsonify({'forwarded': result['success']})

# --- Schedules (CRUD only - no background execution) ---
@app.route('/api/schedules', methods=['GET'])
def get_schedules():
    scheds = Schedule.query.all()
    return jsonify([{
        'id': s.id, 'integration_id': s.integration_id,
        'cron_expression': s.cron_expression,
        'next_run': s.next_run.isoformat() if s.next_run else None,
        'is_active': s.is_active
    } for s in scheds])

@app.route('/api/schedules', methods=['POST'])
def create_schedule():
    data = request.json
    # No trigger evaluation in serverless; just store
    sched = Schedule(
        integration_id=data['integration_id'],
        cron_expression=data['cron_expression'],
        is_active=True
    )
    db.session.add(sched)
    db.session.commit()
    return jsonify({'id': sched.id})

@app.route('/api/schedules/<int:sched_id>', methods=['DELETE'])
def delete_schedule(sched_id):
    sched = Schedule.query.get_or_404(sched_id)
    db.session.delete(sched)
    db.session.commit()
    return jsonify({'message': 'deleted'})

# --- AI Proxy ---
@app.route('/api/ai/proxy', methods=['POST'])
def ai_proxy():
    data = request.json
    provider = data.get('provider', 'openai')
    api_key = data.get('api_key')
    model = data.get('model', 'gpt-3.5-turbo')
    messages = data.get('messages', [])
    if not api_key:
        return jsonify({'error': 'API key required'}), 400
    if provider == 'openai':
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
        payload = {'model': model, 'messages': messages}
        try:
            resp = http_requests.post(url, json=payload, headers=headers, timeout=60)
            return jsonify(resp.json()), resp.status_code
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'error': 'Provider not supported'}), 400

# --- History (for UI Request tab) ---
@app.route('/api/history', methods=['GET'])
def get_history():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    pagination = ExecutionLog.query.order_by(ExecutionLog.executed_at.desc()).paginate(page=page, per_page=per_page)
    items = [{
        'id': l.id,
        'method': 'GET',   # default because manual requests are stored without method
        'url': l.integration.endpoint if l.integration else '-',
        'status': l.status_code,
        'time_ms': l.response_time_ms,
        'success': l.success,
        'created_at': l.executed_at.isoformat()
    } for l in pagination.items]
    return jsonify({
        'items': items,
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    })

@app.route('/api/history/export/csv')
def export_history_csv():
    import csv, io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Integration', 'Status', 'Time (ms)', 'Success', 'Executed At'])
    logs = ExecutionLog.query.order_by(ExecutionLog.executed_at.desc()).all()
    for log in logs:
        writer.writerow([log.id, log.integration.name if log.integration else '-', log.status_code, log.response_time_ms, log.success, log.executed_at])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8')), mimetype='text/csv', as_attachment=True, download_name='history.csv')

@app.route('/api/history/export/json')
def export_history_json():
    logs = ExecutionLog.query.order_by(ExecutionLog.executed_at.desc()).all()
    data = [{
        'id': l.id,
        'integration': l.integration.name if l.integration else None,
        'status': l.status_code,
        'response_time_ms': l.response_time_ms,
        'success': l.success,
        'executed_at': l.executed_at.isoformat()
    } for l in logs]
    return jsonify(data)

# --- Analytics Stats (for UI) ---
@app.route('/api/analytics/stats')
def analytics_stats():
    total_requests = ExecutionLog.query.count()
    avg_response_time = db.session.query(func.avg(ExecutionLog.response_time_ms)).scalar() or 0
    success_rate = db.session.query(func.avg(ExecutionLog.success.cast(db.Float))).scalar() or 0
    status_counts = db.session.query(ExecutionLog.status_code, func.count(ExecutionLog.id)).filter(ExecutionLog.status_code != None).group_by(ExecutionLog.status_code).all()
    status_dist = {str(s): count for s, count in status_counts}
    popular = db.session.query(Integration.endpoint, func.count(ExecutionLog.id)).join(ExecutionLog, Integration.id == ExecutionLog.integration_id).group_by(Integration.endpoint).order_by(func.count().desc()).limit(10).all()
    popular_endpoints = [{'url': url, 'count': count} for url, count in popular]
    # Last 7 days trend
    last_7_days = []
    for i in range(6, -1, -1):
        date = datetime.utcnow().date() - timedelta(days=i)
        day_logs = ExecutionLog.query.filter(func.date(ExecutionLog.executed_at) == date).all()
        avg_time = sum([l.response_time_ms for l in day_logs if l.response_time_ms]) / len(day_logs) if day_logs else 0
        last_7_days.append({'date': date.isoformat(), 'avg_time': round(avg_time, 2)})
    return jsonify({
        'total_requests': total_requests,
        'avg_response_time_ms': round(avg_response_time, 2),
        'success_rate_percent': round(success_rate * 100, 2),
        'status_distribution': status_dist,
        'popular_endpoints': popular_endpoints,
        'response_time_trend': last_7_days
    })

# --- Send Manual Request ---
@app.route('/api/send', methods=['POST'])
def send_manual_request():
    data = request.json
    method = data.get('method', 'GET')
    url = data.get('url')
    headers_raw = data.get('headers', '')
    auth_type = data.get('auth_type', 'none')
    auth_data = data.get('auth_data', {})
    body_type = data.get('body_type', 'none')
    body_content = data.get('body_content', '')
    if not url:
        return jsonify({'error': 'URL required'}), 400

    client = APIClient()
    # parse headers
    for line in headers_raw.split('\n'):
        if ':' in line:
            k, v = line.split(':', 1)
            client.session.headers[k.strip()] = v.strip()
    # authentication
    if auth_type == 'bearer':
        client.session.headers['Authorization'] = f"Bearer {auth_data.get('token', '')}"
    elif auth_type == 'basic':
        client.session.auth = (auth_data.get('username', ''), auth_data.get('password', ''))
    elif auth_type == 'api_key':
        key_name = auth_data.get('key_name', '')
        key_value = auth_data.get('key_value', '')
        location = auth_data.get('location', 'header')
        if location == 'header':
            client.session.headers[key_name] = key_value
        else:
            client.default_params[key_name] = key_value
            client.session.params = client.default_params
    # body
    body = None
    if body_type == 'json' and body_content:
        try:
            body = json.loads(body_content)
        except:
            return jsonify({'error': 'Invalid JSON'}), 400
    elif body_type == 'form' and body_content:
        body = body_content

    start = time.time()
    try:
        resp = client.session.request(method, url, json=body if isinstance(body, dict) else None,
                                      data=body if isinstance(body, str) else None, timeout=30)
        elapsed = (time.time() - start) * 1000
        try:
            resp_body = resp.json()
        except:
            resp_body = resp.text
        # store log (integration_id = None for manual)
        log = ExecutionLog(
            integration_id=None,
            status_code=resp.status_code,
            response_time_ms=round(elapsed, 2),
            request_payload=json.dumps({'method': method, 'url': url, 'body': body_content}),
            response_body=json.dumps(resp_body)[:5000],
            success=resp.status_code < 400
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({
            'success': resp.status_code < 400,
            'status_code': resp.status_code,
            'response_time_ms': round(elapsed, 2),
            'headers': dict(resp.headers),
            'body': resp_body
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# --- Environments (dummy for UI compatibility) ---
@app.route('/api/environments', methods=['GET'])
def get_environments():
    return jsonify([])

@app.route('/api/environments', methods=['POST'])
def create_environment():
    return jsonify({'message': 'Not implemented, use API Keys instead'}), 501

@app.route('/api/environments/<int:env_id>', methods=['PUT'])
def update_environment(env_id):
    return jsonify({'message': 'Not implemented'}), 501

@app.route('/api/environments/<int:env_id>', methods=['DELETE'])
def delete_environment(env_id):
    return jsonify({'message': 'Not implemented'}), 501

# ================= This is not used on Vercel (serverless) =================
# Vercel uses the 'app' object directly.