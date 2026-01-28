# Wenko 🤖

**[English](./README.md)** | **[中文](./README_CN.md)**

> **Your Intelligent Desktop Companion with Heart & Memory.**

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/daijinru/wenko)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Electron](https://img.shields.io/badge/Electron-Desktop-blueviolet)](https://www.electronjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-Frontend-61DAFB)](https://reactjs.org/)

![HITL](./docs/Snipaste_2026-01-21.png)
![Memory Management](./docs/Snipaste_2026-01-20.png)
![Plan Reminder](./docs/plan-reminder.png)

## 📖 Introduction

**Wenko** is an open-source Desktop AI Assistant designed to be more than just a chatbot. It integrates **Live2D** avatars with a powerful **Memory & Emotion System**, creating a personalized and interactive experience.

Unlike standard AI tools, Wenko:
- **Remembers** your preferences and past conversations (Long-term Memory).
- **Understands** the context of your current work (Working Memory).
- **Reacts** with emotions, changing its expression based on the conversation.
- **Collaborates** with you through Human-in-the-Loop (HITL) workflows.

## ✨ Key Features

- **🧠 Advanced Memory System**
  - **Long-term Memory**: Stores facts, user preferences, and historical data persistently using SQLite.
  - **Working Memory**: Maintains context for the current session, ensuring smooth multi-turn conversations.

- **❤️ Emotion Engine**
  - Detects emotions from text (Joy, Sadness, Anger, Neutral, etc.).
  - Updates the Live2D avatar's expression in real-time to match the conversation mood.

- **🎨 Live2D Avatar**
  - Fully interactive desktop widget.
  - Supports custom Live2D models (Cubism 2/5).
  - Touch and gaze interactions.

- **🤝 Human-in-the-Loop (HITL)**
  - Collaborative workflows where the AI proposes actions and you approve/edit them.
  - Perfect for complex tasks requiring human oversight.
  - Supports readonly replay mode for reviewing past decisions.

- **🖼️ Image Analysis**
  - Paste images directly into the app for instant preview.
  - OCR-powered text extraction from screenshots and images.
  - Save extracted content to Long-term Memory for future reference.

- **📊 Memory Dashboard**
  - Visual management of Chat History, Working Memory, and Long-term Memory.
  - Browse, search, and organize your AI's memory data.
  - Transfer important context from Working Memory to Long-term Memory.

- **⏰ Plan Reminder**
  - Create reminders using natural language (e.g., "Remind me to take a break at 3:30 PM").
  - Supports popup window alerts and OS-level notifications (macOS/Windows).
  - Snooze, dismiss, or mark plans as complete directly from the reminder.
  - Recurring reminders for daily, weekly, or custom schedules.

- **🔒 Privacy First**
  - All chat history and memory data are stored locally (`workflow/data/`).
  - You control your data.

## 🛠️ Tech Stack

- **Frontend (Desktop)**: Electron, React, TypeScript, TailwindCSS, Vite
- **Avatar Engine**: Live2D Cubism SDK (Web)
- **Backend (Brain)**: Python, FastAPI, Uvicorn
- **Data Store**: SQLite (Chat History & Memory)
- **AI**: OpenAI API / Compatible LLMs

## 📂 Project Structure

```bash
.
├── electron/                    # Electron Desktop App
│   ├── main.cjs                 # Main Process
│   ├── src/                     # Renderer Process (React)
│   │   └── renderer/
│   │       ├── workflow/        # Memory Management UI
│   │       ├── hitl/            # Human-in-the-Loop UI
│   │       └── image-preview/   # Image Preview & Analysis UI
│   └── live2d/live2d-widget/    # Live2D Widget Implementation
├── workflow/                    # Python Backend Service
│   ├── main.py                  # FastAPI Entry Point
│   ├── chat_db.py               # Chat History Database
│   ├── memory_manager.py        # Memory Logic
│   └── data/                    # Local Database (SQLite)
└── openspec/                    # Project Specifications
```

### Renderer Modules

| Module | Description |
|--------|-------------|
| **workflow/** | Memory management system UI. Contains three tabs: Chat History, Working Memory, Long-term Memory. Used to view and manage AI's conversation records and memory data. |
| **hitl/** | Human-in-the-Loop collaboration UI. Pops up when AI needs human review, allowing users to approve or reject AI operation requests. Supports readonly replay mode. |
| **image-preview/** | Image preview and analysis UI. Supports pasting images for OCR text extraction, and saving results to Long-term Memory. |

## 🚀 Getting Started

### Prerequisites

- Node.js (v18+)
- Python (v3.10+)
- OpenAI API Key (or compatible)

### Installation

1.  **Setup Backend (Python)**
    ```bash
    cd workflow
    uv sync
    ```

2.  **Setup Frontend (Electron)**
    ```bash
    cd electron
    npm install
    ```

3.  **Setup Live2D Widget**
    ```bash
    cd electron/live2d/live2d-widget
    npm install
    ```

### Running the App

```bash
# Start Backend
cd workflow && ./start.sh

# Start Electron (in another terminal)
cd electron && ./start.sh
```

After starting the app, first fill in the LLM configuration:
![LLM Config](./docs/llm-config-open.png)

### Building

#### 1. Build Live2D Widget

Live2D Widget needs to be built first as the Electron app depends on it:

```bash
cd electron/live2d/live2d-widget
npm run build
```

#### 2. Build Electron App

Build the desktop client executable:

```bash
cd electron
npm run dist
```

After building, executables are located in `electron/dist/`:
- **macOS**: `dist/Wenko-x.x.x.dmg` or `dist/mac/Wenko.app`
- **Windows**: `dist/Wenko Setup x.x.x.exe`
- **Linux**: `dist/Wenko-x.x.x.AppImage`

#### 3. Deploy Backend Service

The backend service runs independently, providing AI capabilities to the Electron client:

```bash
cd workflow

# Install dependencies
uv sync

# Start service
./start.sh
# Or manually: uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

The backend service runs on `http://localhost:8000` by default.

#### Production Deployment

For production environments:

1. **Backend Service**: Use systemd or Docker to manage backend processes
2. **Client Configuration**: Ensure client points to the correct backend service address
3. **Data Backup**: Regularly backup SQLite database in `workflow/data/`

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

## 🔗 Related

- [DeepWiki Article](https://deepwiki.com/daijinru/wenko)
