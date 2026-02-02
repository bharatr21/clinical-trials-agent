# CLAUDE.md

## Project Overview

Clinical Trials Text to SQL Agent - converts natural language queries into SQL for the AACT (Aggregate Analysis of ClinicalTrials.gov) database.

## Database

The agent connects to the public AACT PostgreSQL database hosted at `aact-db.ctti-clinicaltrials.org`. Database credentials should be stored in `.env`. See https://aact.ctti-clinicaltrials.org/ for schema documentation.

## Development Commands

### Backend (Python)
- `uv sync` - Install dependencies
- `uv run pytest` - Run tests
- `uv run ruff check .` - Lint code
- `uv run ruff format .` - Format code

### Database Migrations (Alembic)
Run from `src/clinical_trials_agent/`:
- `uv run alembic upgrade head` - Apply all migrations
- `uv run alembic downgrade -1` - Rollback one migration
- `uv run alembic revision --autogenerate -m "description"` - Generate new migration

### Frontend (ui/)
Prefer `bun` over `npm` for the frontend.
- `bun install` - Install dependencies
- `bun run dev` - Start development server
- `bun run lint` - Lint code
- `bun run build` - Build for production