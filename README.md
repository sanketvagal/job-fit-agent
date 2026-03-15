# Job Fit Agent

An AI-powered agent that autonomously analyzes your resume, searches for relevant jobs, and ranks them by how well you match — with brutally honest feedback.

## What It Does

Give it your resume PDF. The agent handles the rest:

```
Resume → AI reads your skills → Decides what jobs to search for
       → Searches real job listings → Analyzes each one against your resume
       → Ranks by fit score with honest feedback
```

### Sample Output

```
============================================================
JOB FIT AGENT - Starting...
============================================================

[Step 1] Reading resume and deciding what to search for...
✓ Agent decided to search for: ['Data Analyst', 'Software Developer']

[Step 2] Searching for jobs...
  Found 3 jobs for 'Data Analyst'
  Found 3 jobs for 'Software Developer'

[Step 3] Analyzing job fit...
  Analyzing (1/6): Data Analyst... ✓ Success
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

The agent runs a 4-step pipeline:

1. **Generate Search Queries** — Sends your resume to Google Gemini, which analyzes your skills and decides which job titles to search for
2. **Search Jobs** — Queries the Adzuna API for real, current job listings in Canada matching those titles
3. **Analyze Fit** — For each job, extracts the top 5 required skills, scores your resume against each one (out of 5), and gives a brutally honest assessment
4. **Rank Results** — Sorts all analyzed jobs by overall likelihood score so you see your best matches first

All output is structured JSON, making it easy to extend with filtering, storage, or a web UI.

## Tech Stack

- **Python** — Core language
- **Google Gemini API** — LLM for resume analysis, query generation, and job fit scoring
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
python job_fit_agent.py
```

## Project Structure

```
job-fit-agent/
├── job_fit_agent.py     # Main agent script
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
- **Agentic Behavior** — The AI autonomously decides what actions to take based on input data
- **Error Handling** — Retry logic with backoff for API failures and malformed responses
- **Multi-API Orchestration** — Chaining Gemini (AI) + Adzuna (job search) into a single pipeline

## Configuration

You can tune the agent's behavior by modifying these variables in `job_fit_agent.py`:

| Variable | Default | Description |
|---|---|---|
| `num_queries` | 2 | Number of job titles the agent searches for |
| `num_results` | 3 | Jobs fetched per search query |
| `MAX_RETRIES` | 3 | Retry attempts per API call |
| `RETRY_DELAY` | 2 | Seconds between retries |

## License

MIT
