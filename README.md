# Schedulr 🗓️

An AI-powered planning assistant that turns your goals into actionable day-by-day schedules and deploys them directly to Google Tasks.

## Architecture

**Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind CSS  
**Backend:** FastAPI + Python 3.12  
**AI:** Google Gemini 2.5 Flash  
**Storage:** In-memory (`will be migrated to Snowflake`)  
**Authentication:** Google OAuth 2.0  
**Deployment:** Google Tasks API

## Features

- 🤖 **AI-Powered Planning**: Generate comprehensive day-by-day plans using Gemini AI
- 💬 **Conversational Updates**: Refine your plans through natural language chat
- 📜 **Plan History**: Track and revisit all your plan iterations
- 🚀 **One-Click Deployment**: Push your plans directly to Google Tasks
- 🔒 **Secure Authentication**: Google OAuth with encrypted token storage
- 💾 **Chat Persistence**: Your conversations are saved in browser storage

## Project Structure

```
Schedulr/
├── frontend/           # Next.js application
│   ├── app/           # App Router pages
│   │   ├── page.tsx              # Landing page with animated text
│   │   └── app/page.tsx          # Main app (3-panel layout)
│   ├── components/    # React components
│   │   ├── ChatInterface.tsx     # Chat UI
│   │   ├── PlanViewer.tsx        # Plan display & deploy
│   │   └── PlanHistory.tsx       # Sidebar history
│   └── lib/           # Utilities
│       ├── api.ts                # API client
│       ├── types.ts              # TypeScript types
│       └── storage.ts            # LocalStorage utils
│
├── backend/           # FastAPI application
│   └── app/
│       ├── main.py               # FastAPI app with CORS
│       ├── config.py             # Settings from .env
│       ├── routers/
│       │   ├── auth.py           # OAuth routes
│       │   └── plans.py          # Plan CRUD + AI
│       ├── services/
│       │   ├── google_auth.py    # authlib OAuth
│       │   ├── gemini.py         # Gemini AI integration
│       │   └── google_tasks.py   # Tasks API client
│       ├── models/
│       │   └── schemas.py        # Pydantic models
│       └── utils/
│           ├── session.py        # Cookie sessions
│           ├── encryption.py     # Token encryption
│           └── storage.py        # In-memory store
│
├── .env.example       # Environment template
├── .gitignore
└── package.json       # Root scripts (concurrently)
```

## Setup Instructions

### 1. Prerequisites

- **Node.js** 18+ (for frontend)
- **Python** 3.12+ (for backend)
- **Google Cloud Project** with OAuth credentials
- **Gemini API Key**

### 2. Google Cloud Configuration

#### A. Create OAuth 2.0 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Navigate to **APIs & Services** → **Credentials**
4. Click **"Create Credentials"** → **"OAuth client ID"**
5. Application type: **"Web application"**
6. **Authorized JavaScript origins**: `http://127.0.0.1:3000`
7. **Authorized redirect URIs**: `http://127.0.0.1:8000/api/auth/callback`
8. Save your **Client ID** and **Client Secret**

#### B. Enable Required APIs

1. Go to **APIs & Services** → **Library**
2. Search and enable:
   - **Google Tasks API**
   - People API (included by default)

#### C. Configure OAuth Consent Screen

1. Go to **OAuth consent screen**
2. Choose **External** (for personal Gmail) or **Internal** (Google Workspace)
3. Fill in app name: **"Schedulr"**
4. Add scopes:
   - `openid`
   - `email`
   - `profile`
   - `https://www.googleapis.com/auth/tasks`
5. Add test users (your Gmail) if External

#### D. Get Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **"Get API Key"**
3. Select your Google Cloud project
4. Copy the API key (starts with `AIza...`)

### 3. Install Dependencies

```bash
# Install root dependencies (concurrently)
npm install

# Install frontend dependencies
cd frontend && npm install

# Install backend dependencies (using conda environment)
conda activate ds_mode
cd backend
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example file and fill in your credentials:

```bash
cp .env.example backend/.env
```

Edit `backend/.env`:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/api/auth/callback

# Core Settings
APP_ENV=dev
FRONTEND_BASE_URL=http://127.0.0.1:3000
BACKEND_BASE_URL=http://127.0.0.1:8000
COOKIE_SECURE=false
# Optional additional frontend origins (comma-separated)
# CORS_ALLOWED_ORIGINS=http://127.0.0.1:3000,http://localhost:3000

# Generate SECRET_KEY
SECRET_KEY=your-generated-secret-key

# Generate ENCRYPTION_KEY
ENCRYPTION_KEY=your-generated-encryption-key

# Gemini API
GEMINI_API_KEY=AIzaSy...your-key
GEMINI_MODEL=gemini-2.0-flash-exp
```

#### Generate Security Keys

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

### 5. Run the Application

#### Option 1: Run Both Servers (Recommended)

```bash
# From project root
npm run dev
```

This runs both frontend (port 3000) and backend (port 8000) concurrently.

#### Option 2: Run Separately

Terminal 1 (Backend):
```bash
conda activate ds_mode
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

### 6. Access the Application

- **Frontend**: http://127.0.0.1:3000
- **Backend API**: http://127.0.0.1:8000
- **API Docs**: http://127.0.0.1:8000/docs (Swagger UI)

## Usage Guide

### 1. Sign In

1. Visit http://127.0.0.1:3000
2. Click **"Sign in with Google"**
3. Complete OAuth consent
4. You'll be redirected to `/app`

### 2. Generate a Plan

In the chat interface, describe your goal:

**Example prompts:**
- "Train for a marathon in 14 days, 60 minutes per day"
- "Learn Python in 21 days, 2 hours daily"
- "Plan a trip to Japan over 10 days"

The AI will generate a day-by-day plan with specific tasks.

### 3. Refine Your Plan

Continue the conversation to adjust your plan:

**Example updates:**
- "Make weekends lighter"
- "Add more rest days"
- "Focus more on cardio in week 2"
- "Max 3 tasks per day"

Each update creates a new version (visible in Plan History).

### 4. Deploy to Google Tasks

1. Review your plan in the right panel
2. Click **"🚀 Deploy to Google Tasks"**
3. Tasks are created with:
   - Titles and descriptions
   - Due dates
   - Duration and priority info
   - Plan ID for tracking

### 5. View Plan History

- Left sidebar shows all your plan iterations
- Click any plan to view it
- Current plan is highlighted

## API Endpoints

### Authentication

- `GET /api/auth/login` - Initiate OAuth flow
- `GET /api/auth/callback` - Handle OAuth callback
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout user

### Plans

- `POST /api/plan/generate` - Generate new plan
- `POST /api/plan/update` - Update existing plan
- `POST /api/plan/deploy` - Deploy plan to Google Tasks
- `GET /api/plan/history` - Get user's plan history
- `GET /api/plan/{plan_id}` - Get specific plan

## Technology Decisions

### Why These Choices?

- **Cookie-based sessions** (vs JWT): Simpler for MVP, more secure (httponly cookies)
- **LocalStorage for chat** (vs DB): Faster MVP, easy to migrate later
- **In-memory storage** (vs Snowflake): Zero setup, state resets are acceptable for demo
- **gemini-2.5-flash** (vs pro): 2x faster, sufficient for plan generation
- **Pure CSS animations** (vs Framer Motion): No dependencies, smooth performance
- **Monorepo structure**: Easier local development, shared types stay in sync

### Security Features

- ✅ HTTPOnly cookies (prevents XSS)
- ✅ Token encryption with Fernet
- ✅ Signed sessions with itsdangerous
- ✅ CORS properly configured
- ✅ OAuth refresh tokens encrypted at rest

## Troubleshooting

### Issue: "Not authenticated" error

**Solution:** Clear cookies and sign in again. Session may have expired (7-day limit).

### Issue: "Failed to generate plan"

**Possible causes:**
1. **Gemini API quota exceeded** - Check [Google AI Studio](https://aistudio.google.com/)
2. **Invalid API key** - Verify `GEMINI_API_KEY` in `.env`
3. **Network issues** - Check backend logs for details

### Issue: OAuth redirect fails

**Check:**
1. Redirect URI in Google Cloud Console matches: `http://127.0.0.1:8000/api/auth/callback`
2. Frontend URL in backend `.env` is: `http://127.0.0.1:3000`
3. You added your Gmail as a test user (if using External consent screen)

### Issue: Deploy to tasks fails with 401

**Solution:** Sign out and sign in again. Access token may have expired, and refresh might have failed.

### Issue: Frontend can't connect to backend

**Check:**
1. Backend is running on port 8000
2. `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` in `frontend/.env.local`
3. CORS is configured for `http://127.0.0.1:3000`
4. If you open frontend on `localhost` or a different dev port, set `CORS_ALLOWED_ORIGINS`

## Development Commands

```bash
# Root commands
npm run dev              # Run both servers
npm run dev:fe           # Frontend only
npm run dev:be           # Backend only
npm run install:all      # Install all dependencies

# Frontend commands
cd frontend
npm run dev              # Dev server (port 3000)
npm run build            # Production build
npm run start            # Start production server

# Backend commands
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000     # Dev server
pytest                                         # Run tests (when added)
```

## Future Enhancements

- [ ] **Snowflake Integration**: Persist plans and traces to database
- [ ] **Agent Traces**: Log LLM prompts/responses for analysis
- [ ] **Plan Templates**: Pre-built plan structures for common goals
- [ ] **Collaborative Planning**: Share plans with others
- [ ] **Calendar Integration**: Sync with Google Calendar
- [ ] **Mobile App**: React Native version
- [ ] **Analytics Dashboard**: Track goal completion rates

## Contributing

This is an MVP project. Contributions welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
- Check [Troubleshooting](#troubleshooting) section
- Review backend logs: `cd backend && uvicorn app.main:app --log-level debug`
- Check browser console for frontend errors

---

**Built with ❤️ using Next.js, FastAPI, and Gemini AI**