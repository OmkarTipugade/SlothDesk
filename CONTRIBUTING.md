# Contributing to SlothDesk 🦥

Thank you for your interest in contributing to **SlothDesk**!  
Whether you are an experienced developer or contributing to open source for the very first time, we welcome your contributions with open arms.

SlothDesk was created with the **"Slow and Steady"** spirit of Hacktoberfest 2026: we prioritize thoughtful code, user privacy, non-destructive safety, and clear documentation over rushing features.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How You Can Contribute](#how-you-can-contribute)
3. [Getting Started](#getting-started)
   - [Forking and Cloning](#forking-and-cloning)
   - [Branch Naming Convention](#branch-naming-convention)
4. [Development Environment Setup](#development-environment-setup)
   - [Backend Setup (Python & FastAPI)](#backend-setup-python--fastapi)
   - [Frontend Setup (React & Vite)](#frontend-setup-react--vite)
5. [Submitting a Pull Request (PR)](#submitting-a-pull-request-pr)
6. [Coding Standards & Guidelines](#coding-standards--guidelines)
   - [Backend Guidelines](#backend-guidelines)
   - [Frontend Guidelines](#frontend-guidelines)
   - [Git Commit Messages](#git-commit-messages)
7. [Running Tests](#running-tests)
8. [Great First Issues & Ideas](#great-first-issues--ideas)

---

## Code of Conduct

We are committed to providing a friendly, safe, and welcoming environment for everyone, regardless of background, identity, or experience level.

- **Be respectful and kind**: Treat all contributors and users with empathy and patience.
- **Focus on constructive feedback**: Offer helpful explanations and welcome beginners asking questions.
- **Privacy & Safety First**: Never introduce code that uploads local user data to external cloud services or deletes files without permission.

---

## How You Can Contribute

There are many ways to contribute to SlothDesk:

1. **Adding File Extensions**: Help expand the file-type mappings in `scanner.py` and `App.tsx` for languages, data formats, or media files.
2. **Improving AI Prompt Heuristics**: Refine prompt guidelines in `ai.py` so the model categorizes subtle files (e.g. tax returns, invoices, spreadsheets) even more accurately.
3. **UI / UX Enhancements**: Improve accessibility, add keyboard navigation shortcuts, polish animations, or enhance responsive layouts.
4. **Fixing Bugs**: Look through open issues or report bugs you encounter.
5. **Documentation**: Clarify tutorials, write guides, or translate documentation.

---

## Getting Started

### Forking and Cloning

1. Fork the repository on GitHub by clicking the **Fork** button in the top right.
2. Clone your fork to your local machine:
   ```bash
   git clone https://github.com/<your-username>/slothdesk.git
   cd slothdesk
   ```
3. Set the upstream remote to stay synced with main:
   ```bash
   git remote add upstream https://github.com/omkartipugade/slothdesk.git
   ```

### Branch Naming Convention

Create a new branch from `main` with a descriptive name:

```bash
git checkout -b feat/add-audio-formats
# or
git checkout -b fix/timeout-issue
# or
git checkout -b docs/improve-readme
```

---

## Development Environment Setup

SlothDesk consists of two parts: a **Python FastAPI backend** and a **React TypeScript frontend**.

### Backend Setup (Python & FastAPI)

1. Ensure you have **Python 3.9+** and **Ollama** installed.
2. Navigate to the backend directory:
   ```bash
   cd backend
   ```
3. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
4. Install all dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Set up your `.env` configuration:
   ```bash
   cp .env.example .env
   ```
6. Start the backend server with live reload:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

### Frontend Setup (React & Vite)

1. Ensure you have **Node.js 18+** installed.
2. In a separate terminal, navigate to the frontend directory:
   ```bash
   cd frontend
   ```
3. Install frontend dependencies:
   ```bash
   npm install
   ```
4. Copy the environment file:
   ```bash
   cp .env.example .env
   ```
5. Start the frontend development server:
   ```bash
   npm run dev
   ```
6. Open `http://localhost:5173` in your browser.

---

## Submitting a Pull Request (PR)

Before submitting your Pull Request, follow this quick checklist:

1. **Keep PRs focused**: Each PR should address one specific issue or feature.
2. **Sync with latest main**:
   ```bash
   git fetch upstream
   git merge upstream/main
   ```
3. **Run all tests**: Ensure all backend and frontend tests pass (see [Running Tests](#running-tests)).
4. **Push your branch to your fork**:
   ```bash
   git push origin <your-branch-name>
   ```
5. **Open the PR on GitHub**:
   - Provide a clear title and description of what you changed.
   - Reference any related issue (e.g., `Fixes #12`).
   - Include screenshots or terminal outputs if you made visual changes.

---

## Coding Standards & Guidelines

### Backend Guidelines

- **Python Style**: Follow PEP 8 guidelines.
- **Type Annotations**: Use Python typing (e.g. `List[str]`, `Optional[int]`, `Pydantic` models).
- **Security Rule #1**: Never introduce code that deletes files (`os.remove`, `shutil.rmtree`, etc.). All moves must pass through `security/paths.py` checks.
- **Security Rule #2**: Do not make outgoing HTTP requests to external cloud services. All AI inference must remain local via Ollama.

### Frontend Guidelines

- **TypeScript**: Always define strict types in `src/types.ts` matching backend models. Avoid using `any`.
- **Component Design**: Keep components modular, accessible (with proper ARIA labels), and responsive.
- **Icons**: Use [Lucide React](https://lucide.dev/) for consistency with existing UI icons.

### Git Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) convention:

- `feat: add support for markdown and latex in notes category`
- `fix: prevent timeout when generating plan for large directories`
- `docs: update troubleshooting guide in README`
- `test: add unit tests for code and data file extensions`
- `refactor: optimize scanner type map lookup`

---

## Running Tests

Both the backend and frontend have automated test suites. **All tests must pass** before a PR can be merged.

### Backend Tests (pytest)

Run all 67+ backend unit tests:

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

*All backend tests run in temporary test directories with mocked Ollama responses and take under 1 second.*

### Frontend Tests (Vitest)

Run the frontend test suite:

```bash
cd frontend
npm test -- --run
```

Check TypeScript compilation and build:

```bash
npm run build
```

---

## 💡 Great First Issues & Ideas

Looking for inspiration on what to contribute? Here are some great ideas:

- [ ] **Add new file extension mappings**: Support more programming languages (e.g. `.zig`, `.nim`, `.elm`, `.f90`) or 3D formats (e.g. `.obj`, `.stl`, `.fbx`).
- [ ] **Custom Category Rules**: Allow users to define custom category folders in `.env` or settings.
- [ ] **Keyboard Shortcuts**: Add quick keyboard shortcuts (e.g., `Cmd/Ctrl + Enter` to approve plan, `Space` to toggle item).
- [ ] **Visual Progress Bar**: Display a progress bar during large multi-file batch moves.
- [ ] **Export Plan Report**: Add an option to export the proposed plan as a JSON or Markdown file before moving.

---

Thank you for contributing to SlothDesk and helping make file management calmer, smarter, and private! 🦥💚
