# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoFlow is an AI-powered RPA (Robotic Process Automation) platform. Users describe automation tasks in natural language or via video, and the system generates executable workflows using a visual block-based builder with 120+ pre-built automation blocks.

## Tech Stack

- **Frontend**: Next.js 16.2 / React 19 / TypeScript 5.7 / Tailwind CSS 4.2 / shadcn/ui (Radix)
- **Backend**: FastAPI 0.109 / Python 3.9+ / SQLAlchemy 2.0 (async) / SQLite (dev) or PostgreSQL (prod)
- **AI**: Claude API (workflow generation, video analysis) / OpenAI (embeddings, Whisper)
- **Vector DB**: ChromaDB for knowledge base semantic search

## Development Commands

### Frontend (root directory)
```bash
npm install          # Install dependencies
npm run dev          # Dev server on http://localhost:3000
npm run build        # Production build
npm run lint         # ESLint
```

### Backend (backend/ directory)
```bash
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
python run.py        # Dev server on http://localhost:8000 (auto-reload)
```

API documentation available at http://localhost:8000/docs (Swagger UI)

## Environment Variables

Backend requires `.env` file (copy from `.env.example`):
- `ANTHROPIC_API_KEY` - Required for AI features
- `OPENAI_API_KEY` - Optional, for embeddings and Whisper

Frontend connects to `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000/api`)

## Architecture

### Frontend Structure
- `app/` - Next.js App Router pages
- `components/blocks/` - Workflow canvas, block palette, AI dialogs
- `components/ui/` - shadcn/ui base components
- `lib/api.ts` - Comprehensive API client (40+ methods, all backend communication)
- `types/blocks.ts` - Block definitions and types (120+ blocks across 10 categories)

### Backend Structure
- `backend/app/api/` - FastAPI routers (auth, ai, workspaces, videos, knowledge, execution, etc.)
- `backend/app/models/` - SQLAlchemy ORM models
- `backend/app/schemas/` - Pydantic validation schemas
- `backend/app/services/` - Business logic:
  - `code_generator.py` - Converts blocks → executable Python code
  - `video_processor.py` - Video analysis with FFmpeg + Claude Vision
  - `knowledge_base/` - Hybrid search (keyword + semantic via ChromaDB)

### API Routes
All routes prefixed with `/api`:
- `/auth` - Authentication (JWT-based)
- `/ai` - AI analysis and workflow generation
- `/workspaces` - Workflow CRUD (blocks stored as JSON in `blocks_data`)
- `/videos` - Video upload and analysis
- `/knowledge` - Knowledge base search (458 indexed projects)
- `/execution` - Code generation and workflow execution

### Data Flow
1. User enters prompt → `/api/ai/analyze` → Claude generates WorkflowGroup[]
2. Frontend converts to WorkspaceBlock[] and displays in canvas
3. User edits blocks → Save to workspace → `/api/workspaces`
4. Execute → `/api/execution/generate-code` → Python code generated from blocks

### Block System
Blocks are defined in `types/blocks.ts` with categories: start, browser, tab, action, keyboard, data, control, api, desktop, advanced. Each block has fields, a type, and maps to Python code generation logic in `code_generator.py`.

## Demo Accounts

Auto-created on first run:
- `seller@demo.com` / `demo1234`
- `buyer@demo.com` / `demo1234`

## Documentation

Korean documentation in `docs/`:
- `01-아키텍처.md` - Architecture
- `02-API-명세서.md` - API specs
- `docs/KNOWLEDGE_BASE_GUIDE.md` - Knowledge base setup
