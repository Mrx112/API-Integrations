from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

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
    integration_id = db.Column(db.Integer, db.ForeignKey('integrations.id'), nullable=False)
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