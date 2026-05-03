import requests
import time
import json
import re
from typing import Dict, Any, Optional

class APIClient:
    def __init__(self):
        self.session = requests.Session()
        self.default_params = {}
        self.custom_headers = {}

    def set_custom_headers(self, headers: Dict):
        self.custom_headers.update(headers)

    def substitute_variables(self, text: str, context: Dict) -> str:
        if not text:
            return text
        def replacer(match):
            var_path = match.group(1).strip()
            keys = var_path.split('.')
            value = context
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    return match.group(0)
            return str(value) if value is not None else ''
        return re.sub(r'\{\{\s*([^}]+?)\s*\}\}', replacer, text)

    def execute_integration(self, integration: Dict, context: Optional[Dict] = None) -> Dict:
        context = context or {}
        endpoint = self.substitute_variables(integration['endpoint'], context)
        method = integration['method']

        headers = json.loads(integration.get('headers') or '{}')
        for k, v in headers.items():
            self.session.headers[k] = self.substitute_variables(str(v), context)

        auth_type = integration.get('auth_type', 'none')
        auth_config = json.loads(integration.get('auth_config') or '{}')
        if auth_type == 'bearer':
            token = self.substitute_variables(auth_config.get('token', ''), context)
            self.session.headers['Authorization'] = f'Bearer {token}'
        elif auth_type == 'basic':
            username = self.substitute_variables(auth_config.get('username', ''), context)
            password = self.substitute_variables(auth_config.get('password', ''), context)
            self.session.auth = (username, password)
        elif auth_type == 'api_key':
            key_name = auth_config.get('key_name', '')
            key_value = self.substitute_variables(auth_config.get('key_value', ''), context)
            location = auth_config.get('location', 'header')
            if location == 'header':
                self.session.headers[key_name] = key_value
            else:
                self.default_params[key_name] = key_value
                self.session.params = self.default_params

        body = None
        body_template = integration.get('body_template')
        if body_template:
            body_str = self.substitute_variables(body_template, context)
            try:
                body = json.loads(body_str)
            except:
                body = body_str

        start = time.time()
        try:
            resp = self.session.request(method, endpoint, json=body if isinstance(body, dict) else None,
                                        data=body if isinstance(body, str) else None, timeout=30)
            elapsed_ms = (time.time() - start) * 1000
            try:
                resp_body = resp.json()
            except:
                resp_body = resp.text
            return {
                'success': resp.status_code < 400,
                'status_code': resp.status_code,
                'response_time_ms': round(elapsed_ms, 2),
                'response_body': resp_body,
                'error': None
            }
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            return {
                'success': False,
                'status_code': None,
                'response_time_ms': round(elapsed_ms, 2),
                'response_body': None,
                'error': str(e)
            }