# SlothDesk Frontend

The frontend for **SlothDesk** — a modern, local-first web application designed to help users organize their local files using on-device AI. Built with React, TypeScript, and Vite, it emphasizes privacy, safety, and a calm, transparent user experience.

---

## Features

- **Overview Dashboard**: Instant visibility into local AI connectivity, files scanned, suggested organization plans, and recent activity.
- **Interactive Plan Review (`Organize Files`)**: 
  - Review proposed file moves before any action is taken on disk.
  - Category filters (`Documents`, `Images`, `Audio`, `Video`, `Code`, `Data`, `Invoices`, `Resumes`, `Notes`, `Other`).
  - Multi-select controls with approval confirmation modal.
- **File Explorer**:
  - Fast file search and inventory browser.
  - Dynamic file-type icons tailored for Code (`<FileCode />`), Data & Spreadsheets (`<Database />`), Audio (`<FileAudio />`), Video (`<FileVideo />`), Images (`<FileImage />`), and Documents (`<FileText />`).
- **Activity History**: Transparent audit log of successful moves and skipped files from the current session.
- **Settings & Privacy**:
  - Verification of backend API health and local Ollama model connection.
  - Display of the active target directory on your machine.
- **Theme Support**: Seamless dark and light modes, automatically persisted via `localStorage`.

---

## Tech Stack

- **Framework**: [React 19](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
- **Build Tool**: [Vite 6](https://vite.dev/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **Styling**: Vanilla CSS design system with CSS custom properties and dark mode tokens
- **Testing**: [Vitest](https://vitest.dev/) + [Testing Library](https://testing-library.com/)

---

## Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) v18 or later
- npm v9 or later
- Running SlothDesk Backend (defaults to `http://localhost:8000`)

### Installation

```bash
cd frontend
npm install
```

### Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Configure your backend URL in `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

### Development Server

Start the Vite development server with Hot Module Replacement (HMR):

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Available Scripts

| Command | Description |
|---|---|
| `npm run dev` | Starts the local development server at `http://localhost:5173` |
| `npm run build` | Typechecks with `tsc` and generates production bundle in `dist/` |
| `npm run preview` | Locally previews the production build |
| `npm test` | Runs the test suite in watch mode using Vitest |
| `npm run test:run` | Runs the Vitest test suite once and exits |
| `npm run lint` | Runs Oxlint linter across source files |

---

## Project Structure

```
frontend/
├── src/
│   ├── App.tsx             # Main application layout, state, routing, and views
│   ├── index.css           # Global CSS variables, design tokens, and components
│   ├── main.tsx            # React application entry point
│   ├── types.ts            # TypeScript definitions matching backend API schemas
│   ├── setupTests.ts       # Vitest setup and testing-library configurations
│   └── lib/
│       ├── api.ts          # Typed REST API client with timeout and abort handling
│       └── api.test.ts     # API client unit tests
├── index.html              # HTML shell
├── vite.config.ts          # Vite & Vitest configuration
├── tsconfig.json           # Root TypeScript configuration
└── package.json            # Scripts and dependencies
```

---

## Safety & Privacy Design

- **Explicit User Confirmation**: The UI never moves or modifies files automatically. All actions require reviewing suggestions and confirming via the approval dialog.
- **No Third-Party Cloud Requests**: All network calls remain strictly local to `127.0.0.1:8000`. No external analytics or tracking scripts are loaded.
- **Fail-Safe UI**: Displays honest connection and error states when the backend or local AI model is unreachable.
