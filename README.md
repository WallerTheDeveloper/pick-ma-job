# Pick Ma Job
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=flat&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
> **AI-powered job discovery and evaluation platform** — Automatically scrape job postings from Upwork and LinkedIn, evaluate them against your profile using Claude AI, and discover the best opportunities.
![Version](https://img.shields.io/badge/version-1.4.0-blue)
## Features
### Core Capabilities
- **Multi-platform scraping** — Automatically fetch jobs from Upwork and LinkedIn via Apify actors
- **AI-powered evaluation** — Two-pass Claude AI evaluation system that scores jobs 1-10 and provides detailed analysis
- **Smart filtering** — Keyword-based pre-filters and company blacklists to eliminate noise
- **Custom CV generation** — Generate tailored CV content for specific job applications
- **Auto-listing** — Automatically organize matching jobs into custom lists
- **Real-time pipeline** — Background job processing with live status tracking
### User Experience
- **Magic link authentication** — Passwordless login via email
- **Modern React UI** — Clean, responsive interface with dark mode support
- **Drag-and-drop organization** — Easily manage job lists with intuitive sorting
- **Dashboard insights** — Visual overview of job matches and pipeline status
### Developer Features
- **Comprehensive test suite** — 80%+ coverage with pytest
- **Database migrations** — Version-controlled schema with asyncpg
- **Rate limiting** — Built-in API protection with SlowAPI
- **CSRF protection** — HMAC-based token validation
- **Type safety** — Full Pydantic models and TypeScript support
## Tech Stack
### Backend
- **Framework:** FastAPI + Uvicorn
- **Database:** PostgreSQL 14+ with asyncpg
- **AI/ML:** Anthropic Claude API
- **Scraping:** Apify actors
- **Email:** Resend
- **Authentication:** Session-based with magic links
### Frontend
- **Framework:** React 19 + TypeScript
- **Build Tool:** Vite
- **Styling:** Tailwind CSS 4
- **UI Components:** shadcn/ui + Base UI
- **State Management:** TanStack Query
- **Testing:** Vitest + React Testing Library
## Quick Start
### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Node.js 20+
- Apify account
- Resend account
- Anthropic API key
### Installation
1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/pick-ma-job.git
   cd pick-ma-job
   ```
2. **Set up the backend**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Copy environment file
   cp .env.example .env
   # Edit .env with your credentials
   ```
3. **Set up the database**
   ```bash
   # Create PostgreSQL database
   createdb pickmajob
   
   # Run migrations
   python db/migrate.py
   ```
4. **Set up the frontend**
   ```bash
   cd frontend
   npm install
   cd ..
   ```
### Configuration
Create a `.env` file with the following variables:
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/pickmajob
# Auth
MAGIC_LINK_SECRET=your-random-secret-here
# Email (Resend)
EMAIL_FROM=noreply@yourdomain.com
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
# URLs
BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173  # For local dev
# AI & Scraping
ANTHROPIC_API_KEY=sk-ant-api03-...
APIFY_API_TOKEN=apify_api_...
# Admin (optional)
ADMIN_EMAIL=admin@yourdomain.com
```
### Running Locally
**Start the backend:**
```bash
python main.py
```
Server runs on http://localhost:8000
**Start the frontend (in a new terminal):**
```bash
cd frontend
npm run dev
```
Frontend runs on http://localhost:5173
## Architecture
### Request Lifecycle
```
HTTP Request
    ↓
api/routes/<route>.py       # FastAPI router — validates input
    ↓
services/<service>.py       # Business logic
    ↓
repositories/<repo>.py      # asyncpg queries
    ↓
PostgreSQL
```
### Pipeline Flow
```
POST /api/run → run_id
    ↓ (background task)
scrapers/<platform>.py      # Fetch from Upwork/LinkedIn
    ↓
services/pipeline.py        # Deduplicate → Filter → Evaluate
    ↓
core/evaluator.py           # Two-pass Claude evaluation
    ↓
repositories/job_result.py  # Store results
```
### Two-Pass AI Evaluation
1. **Pass 1** — Lightweight score (1-10) using `max_tokens=16`
2. **Pass 2** — Full evaluation with `scratchpad`, `evaluation`, `recommendation`, `flags`, `summary` (only for jobs scoring ≥ threshold)
This approach minimizes API costs by avoiding detailed analysis of low-relevance jobs.
## API Endpoints
### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/magic-link` | Request magic link |
| GET | `/auth/verify` | Verify token and login |
| POST | `/auth/logout` | Logout |
### Jobs & Pipeline
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/run` | Start a new pipeline run |
| GET | `/api/run/{run_id}` | Get run status |
| GET | `/api/results` | List job results |
| GET | `/api/results/{id}` | Get specific job result |
### Profile & CV
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/profile` | Get user profile |
| PUT | `/api/profile` | Update profile |
| POST | `/api/cv/generate` | Generate CV for job |
### Lists
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/lists` | Get all lists |
| POST | `/api/lists` | Create list |
| PUT | `/api/lists/{id}` | Update list |
| DELETE | `/api/lists/{id}` | Delete list |
| POST | `/api/lists/{id}/jobs` | Add job to list |
### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/users` | List all users |
| GET | `/api/admin/usage` | Get usage stats |
## Development
### Running Tests
**Backend:**
```bash
# Run all tests
pytest
# Run with coverage
pytest --cov=. --cov-report=term-missing
# Run specific test file
pytest tests/test_evaluator.py
# Run specific test
pytest -k "test_name"
```
**Frontend:**
```bash
cd frontend
npm test
```
### Database Migrations
Migrations are stored in `db/migrations/` as numbered `.sql` files:
```bash
# Apply pending migrations
python db/migrate.py
# Create new migration
# Add a new numbered .sql file to db/migrations/
```
### Adding a New Platform
1. Create `scrapers/<platform>.py` extending `BaseScraper`
2. Add `configs/platforms/<platform>.json` with actor config
3. Add `configs/prompts/<platform>_context.json` with evaluation prompts
4. The platform is auto-discovered by `scrapers/registry.py`
### Project Structure
```
pick-ma-job/
├── api/                    # FastAPI routes and dependencies
│   ├── routes/            # API endpoint handlers
│   ├── deps.py            # Dependency injection
│   └── schemas.py         # Pydantic models
├── core/                  # Core business logic
│   ├── evaluator.py       # Claude AI evaluation
│   ├── prompt_adapter.py  # Prompt construction
│   └── settings.py        # Configuration
├── db/                    # Database
│   ├── migrations/        # SQL migrations
│   └── pool.py           # Connection pool
├── frontend/              # React SPA
│   ├── src/              # Source code
│   └── package.json
├── repositories/          # Data access layer
├── scrapers/             # Platform scrapers
├── services/             # Business services
├── tests/                # Test suite
└── configs/              # JSON configurations
```
## Deployment
### Production Setup
1. **Build the frontend:**
   ```bash
   cd frontend
   npm run build
   ```
2. **Set production environment variables:**
   - Set `FRONTEND_URL=` (empty for same-domain)
   - Use a strong `MAGIC_LINK_SECRET`
   - Configure `ADMIN_EMAIL`
3. **Run migrations:**
   ```bash
   python db/migrate.py
   ```
4. **Start with systemd (example):**
   ```bash
   # Using the provided deploy.sh script
   bash deploy.sh
   ```
### Docker (Optional)
```dockerfile
# Dockerfile.example
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN cd frontend && npm install && npm run build
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```
## Contributing
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `pytest`
5. Commit with clear messages
6. Push and create a pull request
### Code Style
- **Python:** Follow PEP 8, use type hints on all functions
- **TypeScript:** Enable strict mode, prefer interfaces over types
- **Commits:** Use conventional commits format
## License
MIT License — see [LICENSE](LICENSE) for details.
## Acknowledgments
- [Anthropic](https://anthropic.com/) for Claude AI
- [Apify](https://apify.com/) for scraping infrastructure
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [shadcn/ui](https://ui.shadcn.com/) for beautiful React components
---
<p align="center">
  Built with ❤️ to make job hunting smarter, not harder.
</p>
