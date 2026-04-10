# ReviewInsight — AI-Powered Product Review Analysis 🔍✨

ReviewInsight is a premium, full-stack web application designed to automatically extract, process, and analyze product reviews from e-commerce platforms. It leverages LLMs (like OpenAI GPT-3.5/4) to provide instant sentiment analysis, extract key themes, and summarize insights in a stunning, Apple-inspired interface.

## 🚀 Features

- **Smart Scraping System**: Extracts reviews from Amazon, Flipkart, and generic e-commerce sites, handling pagination and robust HTML parsing.
- **AI-Powered Sentiment Analysis**: Evaluates each review for positive, negative, neutral, or mixed sentiments with granular scores.
- **Theme Extraction & Summarization**: Automatically clusters reviews into key themes (e.g., "Battery Life", "Build Quality") and generates a concise executive summary.
- **Premium Apple-Inspired UI**: Built with Next.js and pure CSS. Features a clean, minimal design, smooth micro-animations, glassmorphism effects, and highly responsive layouts.
- **Robust Backend Architecture**: FastAPI python backend with rate limiting, retry logic (Tenacity), and graceful fallbacks when LLM quotas are exceeded.
- **Structured Outputs**: Analyzed data can be exported to JSON or CSV via API endpoints.

## 🏗️ Architecture

### Frontend (Next.js / React)
- **Framework**: Next.js App Router for optimal performance.
- **Styling**: Vanilla CSS Modules with a comprehensive design token system (`globals.css`) for strict adherence to Apple's design guidelines (Inter font, subtle shadows, specific neutral palettes).
- **State Management**: Custom React hook (`useAnalysis.js`) manages the entire lifecycle (Idle, Loading, Success, Error) with detailed loading stages for better UX.

### Backend (Python / FastAPI)
- **Framework**: FastAPI for blazing fast, async API endpoints.
- **Scraping (`scraper.py`)**: Uses `httpx` and `BeautifulSoup4` with rotating user agents to scrape effectively. Uses platform-specific parsing heuristics.
- **Preprocessing (`preprocessor.py`)**: Cleans HTML entities, normalizes unicode, removes noise patterns, and chunks text for efficient LLM consumption.
- **LLM Integration (`analyzer.py`)**: Uses the OpenAI API with structured JSON prompts to guarantee stable data formats. Implements exponential backoff for API limits and heuristic fallbacks if the API fails.

## 🛠️ Tech Stack
**Frontend**: Next.js (React), CSS Modules
**Backend**: Python, FastAPI, BeautifulSoup4, LXML, Pandas
**AI/LLM**: OpenAI API

## 📋 Installation & Setup

### Prerequisites
- Node.js (v18+)
- Python (3.9+)
- OpenAI API Key

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend` directory based on `.env.example`:
```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo
HOST=0.0.0.0
PORT=8000
DEBUG=true
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Start the backend server:
```bash
uvicorn app.main:app --reload
```
The API will run at `http://localhost:8000`. API docs available at `http://localhost:8000/docs`.

### 2. Frontend Setup
```bash
cd frontend
npm install
```

Create a `.env.local` file in the `frontend` directory:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Start the development server:
```bash
npm run dev
```

Visit `http://localhost:3000` to use the application.

## 🗂️ Project Structure

```
review-insight/
├── backend/                  # Python FastAPI Backend
│   ├── app/
│   │   ├── api/routes.py     # Endpoints
│   │   ├── core/config.py    # Env settings
│   │   ├── models/schemas.py # Pydantic types
│   │   ├── services/         # Scraping & LLM logic
│   │   ├── utils/export.py   # CSV/JSON export
│   │   └── main.py
│   ├── .env.example
│   └── requirements.txt
└── frontend/                 # Next.js Frontend
    ├── src/
    │   ├── app/              # Next.js App router & global CSS
    │   ├── components/       # UI, Layout, and Analysis views
    │   ├── hooks/            # State management
    │   └── lib/              # API Client & Utils
    └── package.json
```

## ⚖️ Tradeoffs & Decisions
1. **Vanilla CSS over Tailwind**: Chosen to demonstrate high-level design capability and strict adherence to a custom Apple-inspired design system without relying on predefined utility classes.
2. **BeautifulSoup over Playwright/Selenium**: To keep the scraping lightweight and fast, traditional HTTP requests + BS4 were used. For highly dynamic JS-rendered single-page apps, a headless browser might be needed in a future iteration.
3. **Graceful Degradation**: If the LLM API fails or rate limits, the system seamlessly falls back to keyword-heuristic sentiment analysis to ensure the user still receives actionable data.
## 🔗 Example Product Link

You can test the application using the following sample product URL:

👉 https://amzn.in/d/01uUU0gn
