# 🌐 API Integration Platform

[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)
[![Flask](https://img.shields.io/badge/flask-3.0-green)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/mysql-8.0-orange)](https://www.mysql.com/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

**A full‑featured API gateway, integration engine, and analytics dashboard**  
Build, test, monitor, and orchestrate any REST API – including AI services – from a single platform.

![Dashboard Preview](https://via.placeholder.com/800x400?text=API+Integration+Platform+Dashboard)  

## ✨ Key Features

- 🚀 **Universal API Client** – Send HTTP requests (GET, POST, PUT, DELETE, PATCH) with support for **Bearer Token**, **Basic Auth**, and **API Key** (header/query).
- 🗂️ **Integration Management** – Store reusable API configurations (endpoint, method, headers, auth, body template) in MySQL.
- ⏱️ **Execution Logs** – Every request is logged with status, response time, payload preview, and error details.
- 📊 **Advanced Analytics** – Response time trends, status code distribution, success rate, and top‑used endpoints (Chart.js).
- 🔌 **Webhook Receiver** – Create unique webhook URLs that forward incoming payloads to any integration.
- ⏰ **Cron Scheduler** – Run integrations automatically using cron expressions (powered by APScheduler).
- 🤖 **AI Proxy** – Seamless integration with OpenAI (extendable to Claude, Gemini, etc.).
- 🔑 **API Key Management** – Generate and revoke API keys for secure external access.
- 🐳 **Docker Ready** – Run the entire stack with `docker compose up`.
- 🎨 **Modern UI** – Responsive sidebar, dark gradient theme, real‑time charts, and syntax‑highlighted responses.

## 🧱 Tech Stack

| Layer       | Technology                                                                 |
|-------------|----------------------------------------------------------------------------|
| Backend     | Python 3.11, Flask, SQLAlchemy                                            |
| Database    | MySQL 8.0 (with PyMySQL driver)                                           |
| Scheduler   | APScheduler                                                               |
| Frontend    | HTML5, Bootstrap 5, Chart.js, Highlight.js, Font Awesome                  |
| Container   | Docker, Docker Compose                                                     |
| HTTP Client | `requests` with retry strategy and variable substitution (`{{variable}}`) |

## 📦 Getting Started

### Prerequisites
- Docker & Docker Compose installed on your machine.
- Git (optional).

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/api-integration-platform.git
cd api-integration-platform
2. Configure environment variables
Copy the example file and edit it:

bash
cp .env.example .env
Adjust passwords and secrets if needed – but the defaults work out of the box.

3. Build and run with Docker Compose
bash
docker compose up --build
The containers will start:

MySQL on port 3306

Flask app on port 5000

Wait for the logs to show:

text
api_platform  | Default API Key: <your_admin_key>
api_platform  | * Running on http://0.0.0.0:5000
4. Access the UI
Open your browser at http://localhost:5000

You will see the Dashboard with statistics. The default API key is printed in the logs – save it for later.

🧪 Usage
Web Interface Tabs
Request – Manually call any external API with custom authentication and body.

History – Browse past executions, view details, export as CSV/JSON.

Analytics – Visual charts of system performance and usage.

Settings – Manage API keys (other settings like webhooks & schedules are available via API calls).

Creating an Integration (via API)
bash
curl -X POST http://localhost:5000/api/integrations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "GitHub User",
    "endpoint": "https://api.github.com/users/{{username}}",
    "method": "GET",
    "auth_type": "none"
  }'
Executing an Integration
bash
curl -X POST http://localhost:5000/api/integrations/1/execute \
  -H "Content-Type: application/json" \
  -d '{"username": "octocat"}'
Using the AI Proxy (OpenAI example)
bash
curl -X POST http://localhost:5000/api/ai/proxy \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "api_key": "sk-...",
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
Webhook (receive and forward)
Create a webhook that points to an integration ID, then send POST requests to:

text
POST http://localhost:5000/webhook/your-unique-path
The payload will be injected as {{payload}} into the target integration.

Schedules (cron)
Create a schedule via API:

bash
curl -X POST http://localhost:5000/api/schedules \
  -H "Content-Type: application/json" \
  -d '{
    "integration_id": 1,
    "cron_expression": "0 */6 * * *"
  }'
🗄️ API Endpoints Overview
Method	Endpoint	Description
GET	/api/integrations	List all integrations
POST	/api/integrations	Create a new integration
PUT	/api/integrations/<id>	Update integration
DELETE	/api/integrations/<id>	Delete integration
POST	/api/integrations/<id>/execute	Execute an integration
GET	/api/logs	Paginated execution logs
GET	/api/dashboard/stats	Dashboard statistics
GET	/api/api_keys	List API keys
POST	/api/api_keys	Generate a new API key
GET	/api/schedules	List scheduled jobs
POST	/api/schedules	Create a cron schedule
POST	/api/ai/proxy	Proxy calls to OpenAI
Full API documentation is available via browsing the routes in app.py.

🔧 Environment Variables (.env)
Variable	Description	Default
MYSQL_ROOT_PASSWORD	MySQL root password	rootpass123
MYSQL_DATABASE	Database name	api_platform
MYSQL_USER	Application database user	api_user
MYSQL_PASSWORD	Password for application user	api_pass123
SECRET_KEY	Flask secret key	(auto‑generated)
FLASK_DEBUG	Flask debug mode (True/False)	False
🚢 Docker Commands
Command	Description
docker compose up -d	Start in background
docker compose logs -f app	Follow application logs
docker compose down	Stop containers
docker compose down -v	Stop and delete volumes (reset DB)
docker exec -it api_platform bash	Open shell inside app container
🧪 Testing the Platform
You can quickly test the API with built‑in manual request tool (UI → Request tab) or with curl:

bash
# Send a GET request to a public API
curl -X POST http://localhost:5000/api/send \
  -H "Content-Type: application/json" \
  -d '{"method":"GET","url":"https://jsonplaceholder.typicode.com/posts/1"}'
📁 Project Structure
text
api-integration-platform/
├── app.py                 # Flask application (all routes)
├── models.py              # SQLAlchemy models
├── api_client.py          # Robust HTTP client with variable substitution
├── scheduler.py           # APScheduler cron runner
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── templates/             # Jinja2 HTML files
│   ├── base.html
│   ├── index.html
│   ├── integrations.html
│   ├── logs.html
│   └── settings.html
└── static/                # CSS & JS
    ├── style.css
    └── script.js
🤝 Contributing
Contributions, issues, and feature requests are welcome!
Feel free to open a pull request or an issue on GitHub.

📄 License
Distributed under the MIT License. See LICENSE for more information.

🙏 Acknowledgements
Flask

SQLAlchemy

Chart.js

Highlight.js

