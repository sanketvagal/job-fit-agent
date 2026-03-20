# Job Fit Agent

An AI-powered agent that autonomously analyzes your resume, searches for relevant jobs, and ranks them by how well you match — with brutally honest feedback.

## What It Does

Give it your resume PDF. The agent handles the rest:

```
Resume → AI reads your skills → Decides what jobs to search for
       → Searches real job listings → Analyzes each one against your resume
       → Ranks by fit score with honest feedback
```

### Two Modes

**Pipeline Mode** (default) — Fixed 4-step flow. Predictable, lower API usage. Great for daily use.

**Agentic Mode** — The LLM decides which tools to call and in what order using Gemini's function calling. It can adapt its strategy based on results (e.g., try different search terms if initial matches are poor). Uses more API quota.

### Sample Output

```
============================================================
JOB FIT AGENT (Pipeline Mode) - Starting...
============================================================

[Step 1] Reading resume and deciding what to search for...
✓ Agent decided to search for: ['Data Analyst', 'Software Developer']

[Step 2] Searching for jobs...
  Found 3 jobs for 'Data Analyst'
  Found 3 jobs for 'Software Developer'

[Step 3] Analyzing job fit...
  Analyzing (1/6): Data Analyst... ✓ Analyzed: Data Analyst
  ...

[Step 4] Ranking results...

============================================================
JOB FIT RESULTS (ranked by likelihood)
============================================================

#1 | Data Analyst: 4/5
    Strong technical match. Excel/VBA automation experience
    aligns directly with requirements...

#2 | Software Developer: 3.5/5
    Solid Python and AWS skills, but resume trends toward
    data analysis rather than software engineering...

#3 | Senior Data Analyst: 2/5
    Under-qualified for senior level. Less than a year of
    professional data analyst experience...
```

## How It Works

### Pipeline Mode
A fixed 4-step pipeline:
1. **Generate Search Queries** — Sends your resume to Google Gemini, which decides which job titles to search for
2. **Search Jobs** — Queries the Adzuna API for real, current job listings in Canada
3. **Analyze Fit** — For each job, scores your resume against the top 5 required skills with brutally honest feedback
4. **Rank Results** — Sorts all jobs by overall likelihood score

### Agentic Mode
Uses Gemini's **function calling** — the LLM receives tool descriptions and autonomously decides:
- Which tools to call and with what arguments
- What order to call them in
- When to try different search terms based on results
- When it has found enough good matches to stop

The three tools available to the agent:
- `search_jobs` — Search Adzuna for job listings by keyword and location
- `analyze_single_job` — Analyze a single job against the candidate's resume
- `get_results_so_far` — Review all analyses completed so far

## Tech Stack

- **Python** — Core language
- **Google Gemini API** — LLM for resume analysis, query generation, job fit scoring, and autonomous tool calling
- **Adzuna API** — Real-time job search across Canada
- **PyPDF2** — PDF text extraction

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/sanketvagal/job-fit-agent.git
cd job-fit-agent
```

### 2. Create a virtual environment

```bash
python3 -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up API keys

```bash
cp .env.example .env
```

Edit `.env` and add your keys:
- **Gemini API Key** — Free from [aistudio.google.com](https://aistudio.google.com)
- **Adzuna API Key** — Free from [developer.adzuna.com](https://developer.adzuna.com)

### 5. Add your resume

Place your resume PDF in the `data/` folder and update `RESUME_PATH` in `.env`.

### 6. Run

```bash
# Pipeline mode (default — lower API usage)
python job_fit_agent.py

# Agentic mode (LLM controls the workflow)
python job_fit_agent.py agentic
```

## Project Structure

```
job-fit-agent/
├── job_fit_agent.py     # Main agent script (both modes)
├── requirements.txt     # Python dependencies
├── .env.example         # API key template
├── .gitignore
├── data/                # Place your resume PDF here
│   └── resume.pdf
└── README.md
```

## Key Concepts Demonstrated

- **AI API Integration** — Calling LLMs programmatically with structured JSON output
- **Prompt Engineering** — Designing prompts that produce reliable, honest, parseable results
- **LLM Function Calling** — Defining tools that the LLM autonomously selects and invokes
- **Agentic Behavior** — The AI decides what actions to take, adapts strategy based on results
- **Error Handling** — Retry logic with backoff for API failures and malformed responses
- **Multi-API Orchestration** — Chaining Gemini (AI) + Adzuna (job search) into a single pipeline

## Configuration

You can tune the agent's behavior by modifying these variables in `job_fit_agent.py`:

| Variable | Default | Description |
|---|---|---|
| `MODEL` | gemini-3-flash-preview | Gemini model to use |
| `MAX_RETRIES` | 3 | Retry attempts per API call |
| `RETRY_DELAY` | 2 | Seconds between retries |

In pipeline mode, search queries and results per query are set in the `run_pipeline()` function.

## License

MIT