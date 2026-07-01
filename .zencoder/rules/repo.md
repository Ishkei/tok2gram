---
description: Repository Information Overview
alwaysApply: true
---

# Repository Information Overview

## Repository Summary
This repository contains the **Tok2gram** project, a TikTok to Telegram local monitor and reposter, currently in its planning and design phase. It also includes the **BMAD (Business Model Agentic Design)** framework, which provides agent-based workflows for project management, architecture, and implementation.

## Repository Structure
- **_bmad/**: Contains the BMAD framework configuration, agents, and workflows.
- **docs/**: Extensive documentation for Tok2gram, including PRD, architecture, and user stories.
- **cookies/**: Placeholder for TikTok session cookies (e.g., `sid_tt`).
- **downloads/**: Placeholder for temporary storage of downloaded media.
- **logs/**: Placeholder for application execution logs.
- **team-fullstack.txt**: A bundled set of agent instructions and configurations for the BMAD framework.

### Main Repository Components
- **Tok2gram**: A Python-based automation tool to monitor TikTok creators and repost content to Telegram.
- **BMAD Framework**: An agentic orchestration system that manages the development lifecycle through specialized AI personas.

## Projects

### Tok2gram (TikTok → Telegram Reposter)
**Status**: Planning / Ready for Development  
**Configuration Files**: `config.yaml`, `creators.yaml` (Planned)

#### Language & Runtime
**Language**: Python  
**Version**: 3.11  
**Build System**: Sequential execution (Short-lived stateless scripts)  
**Package Manager**: `pip` (Virtualenv)

#### Dependencies
**Main Dependencies**:
- `yt-dlp`: TikTok media downloading and metadata extraction
- `python-telegram-bot v20.x`: Telegram Bot API integration
- `SQLite`: Persistent state storage for duplicate prevention
- `PyYAML`: Configuration parsing
- `tenacity`: Retry and backoff logic

#### Build & Installation
```bash
# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install yt-dlp python-telegram-bot==20.* PyYAML tenacity
```

#### Main Files & Entry Points
- `main.py`: Orchestrator (Planned)
- `tiktok.py`: Intake and metadata extraction (Planned)
- `downloader.py`: Media download handling (Planned)
- `telegram_uploader.py`: Telegram upload logic (Planned)
- `state.py`: SQLite state management (Planned)

#### Testing
**Framework**: Not yet implemented.
**Strategy**: Quality strategy focuses on preserving media quality (best available video/audio, no re-encoding) and ensuring idempotent operations via SQLite state checks.

### BMAD Framework (Agentic Design)
**Type**: Agentic Framework / Workflow Configuration

#### Specification & Tools
**Type**: YAML/CSV-based Agent and Workflow definitions.
**Required Tools**: BMAD-compatible AI orchestrator.

#### Key Resources
**Main Files**:
- `_bmad/_config/manifest.yaml`: Central manifest for agents and workflows.
- `_bmad/bmm/module.yaml`: Module definition for BMAD-Method.
- `team-fullstack.txt`: Bundled agent instructions for various roles (Orchestrator, Analyst, Architect, PM, Dev).

#### Usage & Operations
**Key Commands**:
- `*help`: Show available agents and workflows.
- `*agent [name]`: Transform into a specialized agent.
- `*workflow [name]`: Start a specific workflow (e.g., `sprint-planning`).
- `*task [name]`: Execute a specific agent task.

#### Validation
**Quality Checks**: Sprint status tracking via `docs/sprint-status.yaml` and checklist-driven development as outlined in `docs/Checklist.md`.
