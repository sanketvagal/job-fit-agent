"""
Job Fit Analyzer Agent
Autonomously reads your resume, decides what jobs to search for,
analyzes fit, and ranks results.

Two modes:
    pipeline  — Fixed 4-step pipeline (works within free tier limits)
    agentic   — LLM decides which tools to call via Gemini function calling

Usage:
    1. Copy .env.example to .env and add your API keys
    2. Place your resume PDF in the data/ folder
    3. Run: python job_fit_agent.py
"""

import json
import os
import time
import requests
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from google import genai
from google.genai import types

# ─── Configuration ───────────────────────────────────────────────
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
RESUME_PATH = os.getenv("RESUME_PATH", "data/resume.pdf")
MODEL = "gemini-3-flash-preview"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# ─── Shared State ────────────────────────────────────────────────
RESUME_TEXT = ""
analyzed_results = []


# ─── PDF Text Extraction ────────────────────────────────────────
def extract_text_from_pdf(pdf_path):
    """Extracts text from all pages of a PDF file."""
    all_text = ""
    with open(pdf_path, 'rb') as file:
        reader = PdfReader(file)
        for page in reader.pages:
            page_content = page.extract_text()
            if page_content:
                all_text += page_content + "\n"
    return all_text


# ═════════════════════════════════════════════════════════════════
# TOOL-USE FUNCTIONS (for agentic mode)
# Gemini reads the type hints and docstrings to understand these
# ═════════════════════════════════════════════════════════════════

def search_jobs(query: str, location: str = "canada", num_results: int = 3) -> list:
    """Searches for real job listings on Adzuna.
    Use this when you need to find jobs matching a keyword.

    Args:
        query: Job search keywords, e.g. 'Data Analyst' or 'Python Developer'
        location: Location to search in, e.g. 'canada', 'toronto'
        num_results: Number of job listings to return (1-10)

    Returns:
        List of job listings with title and description
    """
    response = requests.get("https://api.adzuna.com/v1/api/jobs/ca/search/1", params={
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": query,
        "where": location,
        "results_per_page": num_results
    })
    data = response.json()
    listings = [
        {"title": job["title"], "description": job["description"]}
        for job in data["results"]
    ]
    print(f"  Found {len(listings)} jobs for '{query}'")
    return listings


def analyze_single_job(job_title: str, job_description: str) -> dict:
    """Analyzes how well the candidate's resume matches a single job listing.
    Use this after searching for jobs to evaluate fit.

    Args:
        job_title: The title of the job posting
        job_description: The full job description text

    Returns:
        Dict with skill matching scores and likelihood rating out of 5
    """
    json_template = """
    {
    "title": "job_title",
  "top_technical_skills": [
    {
      "skill": "",
      "importance": "High | Medium | Low",
      "reasoning": ""
    }
  ],
  "candidate_skill_matching": [
    {
      "skill": "",
      "score_out_of_5": 0,
      "brutal_honesty": ""
    }
  ],
  "final_verdict": {
    "likelihood_of_hire_out_of_5": 0,
    "summary": ""
  }
}"""

    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""
    I have a job description below. Extract the top 5 most important 
    technical skills they're looking for, and for each one, rate how 
    important it seems (high/medium/low) based on the posting.
    Similarly, I have attached my resume. Give me a rating out of 5 for each 
    of those 5 skills on how I match it, and then a final out of 5 score 
    how likely I am to get that job.
    Be brutally honest. If my skills don't match, say so clearly. Don't sugarcoat.
    Give the output in the following JSON format.
    {json_template}
    Strip the markdown fences and return clean, parseable JSON without the backtick wrapper.
    Job title:
    {job_title}
    Job Description:
    {job_description}
    Resume:
    {RESUME_TEXT}
    """

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt
            )
            json_response = json.loads(response.text)
            analyzed_results.append(json_response)
            print(f"    ✓ Analyzed: {job_title}")
            return json_response
        except Exception as e:
            print(f"    Attempt {attempt + 1} failed: {e}")
            time.sleep(RETRY_DELAY)

    error = {"error": f"{job_title} - all attempts failed"}
    analyzed_results.append(error)
    return error


def get_results_so_far() -> list:
    """Returns all job analyses completed so far, sorted by fit score.
    Use this to check progress and decide if more searching is needed.

    Returns:
        List of analyzed jobs sorted by likelihood score, highest first
    """
    sorted_results = sorted(
        analyzed_results,
        key=lambda x: x.get("final_verdict", {}).get("likelihood_of_hire_out_of_5", 0) if isinstance(x, dict) else 0,
        reverse=True
    )
    return sorted_results


# ═════════════════════════════════════════════════════════════════
# MODE 1: AGENTIC (LLM decides which tools to call)
# ═════════════════════════════════════════════════════════════════

def run_agentic(resume_path):
    """
    Full agentic mode: Gemini decides which tools to call and in what order.
    Uses function calling to let the LLM control the workflow.
    Note: Requires sufficient API quota (uses many calls per run).
    """
    global RESUME_TEXT, analyzed_results
    RESUME_TEXT = extract_text_from_pdf(resume_path)
    analyzed_results = []

    print("=" * 60)
    print("JOB FIT AGENT (Agentic Mode) - Starting...")
    print("=" * 60)

    client = genai.Client(api_key=GEMINI_API_KEY)

    response = client.models.generate_content(
        model=MODEL,
        contents="""Find me jobs in Canada that I'm a strong fit for (3/5 or higher). 
        Try different job titles based on my resume. If the first search doesn't 
        find good matches, try different search terms. Stop when you find at least 
        3 jobs I score 3/5 or above on.""",
        config=types.GenerateContentConfig(
            tools=[search_jobs, analyze_single_job, get_results_so_far],
            system_instruction=f"""You are a job search agent. You have access to the candidate's resume below. 
Use it to decide what jobs to search for and to evaluate fit.

Resume:
{RESUME_TEXT}"""
        )
    )

    # Show tool usage history
    print("\n--- Tool Usage History ---")
    for entry in response.automatic_function_calling_history:
        for part in entry.parts:
            if hasattr(part, 'function_call') and part.function_call:
                print(f"  [TOOL CALL] {part.function_call.name}({part.function_call.args})")
            if hasattr(part, 'function_response') and part.function_response:
                print(f"  [TOOL RESULT] {part.function_response.name} returned")

    print("\n--- Agent Summary ---")
    print(response.text)

    return analyzed_results


# ═════════════════════════════════════════════════════════════════
# MODE 2: PIPELINE (fixed 4-step flow, lower API usage)
# ═════════════════════════════════════════════════════════════════

def run_pipeline(resume_path):
    """
    Fixed pipeline mode:
    1. Reads resume and decides what jobs to search for
    2. Searches Adzuna for each query
    3. Analyzes each job against resume
    4. Ranks and displays results
    """
    global RESUME_TEXT
    RESUME_TEXT = extract_text_from_pdf(resume_path)

    print("=" * 60)
    print("JOB FIT AGENT (Pipeline Mode) - Starting...")
    print("=" * 60)

    client = genai.Client(api_key=GEMINI_API_KEY)

    # Step 1: Agent decides what to search
    print("\n[Step 1] Reading resume and deciding what to search for...")
    prompt = f"""
    Based on the resume below, give me exactly 2 job titles 
    that this candidate should search and apply for. Pick the titles 
    where the candidate has the strongest fit. Return the output as a 
    JSON array of strings. No markdown, no backticks, just the raw JSON array.
    Resume:
    {RESUME_TEXT}
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(model=MODEL, contents=prompt)
            queries = json.loads(response.text)
            print(f"✓ Agent decided to search for: {queries}")
            break
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            time.sleep(RETRY_DELAY)
    else:
        print("✗ Failed to generate search queries. Exiting.")
        return

    # Step 2: Search for jobs
    print("\n[Step 2] Searching for jobs...")
    all_listings = []
    for query in queries:
        listings = search_jobs(query, location="canada", num_results=3)
        all_listings.extend(listings)

    if not all_listings:
        print("No jobs found. Exiting.")
        return

    print(f"\nTotal jobs to analyze: {len(all_listings)}")

    # Step 3: Analyze fit
    print("\n[Step 3] Analyzing job fit...")
    responses = []
    for i, listing in enumerate(all_listings):
        print(f"\n  Analyzing ({i + 1}/{len(all_listings)}): {listing['title']}...")
        result = analyze_single_job(listing["title"], listing["description"])
        responses.append(result)

    # Step 4: Rank and display
    print("\n[Step 4] Ranking results...")
    sorted_responses = sorted(
        responses,
        key=lambda x: x["final_verdict"]["likelihood_of_hire_out_of_5"] if isinstance(x, dict) and "final_verdict" in x else 0,
        reverse=True
    )

    print("\n" + "=" * 60)
    print("JOB FIT RESULTS (ranked by likelihood)")
    print("=" * 60)
    for i, r in enumerate(sorted_responses):
        if isinstance(r, dict) and "final_verdict" in r:
            title = r["title"]
            score = r["final_verdict"]["likelihood_of_hire_out_of_5"]
            summary = r["final_verdict"]["summary"]
            print(f"\n#{i + 1} | {title}: {score}/5")
            print(f"    {summary}")
        else:
            print(f"\n#{i + 1} | {r}")
    print("\n" + "=" * 60)

    return sorted_responses


# ─── Main ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "pipeline"

    if mode == "agentic":
        run_agentic(RESUME_PATH)
    else:
        run_pipeline(RESUME_PATH)