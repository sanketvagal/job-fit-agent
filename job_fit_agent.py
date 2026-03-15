"""
Job Fit Analyzer Agent
Autonomously reads your resume, decides what jobs to search for,
analyzes fit, and ranks results.

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

# ─── Configuration ───────────────────────────────────────────────
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")
RESUME_PATH = os.getenv("RESUME_PATH", "data/resume.pdf")
MODEL = "gemini-3-flash-preview"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


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


# ─── Step 1: Agent decides what to search ────────────────────────
def generate_search_queries(resume_path, num_queries=2):
    """
    Reads resume and asks Gemini to suggest the most relevant job titles.
    Args:
        resume_path (str): Path to resume PDF.
        num_queries (int): Number of job titles to return.
    Returns:
        list: List of job title strings.
    """
    client = genai.Client(api_key=GEMINI_API_KEY)
    resume = extract_text_from_pdf(resume_path)
    prompt = f"""
    Based on the resume below, give me exactly {num_queries} job titles 
    that this candidate should search and apply for. Pick the titles 
    where the candidate has the strongest fit. Return the output as a 
    JSON array of strings. No markdown, no backticks, just the raw JSON array.
    Resume:
    {resume}
    """

    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt
            )
            queries = json.loads(response.text)
            print(f"✓ Agent decided to search for: {queries}")
            return queries
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            time.sleep(RETRY_DELAY)

    print("✗ Failed to generate search queries")
    return []


# ─── Step 2: Search for jobs ────────────────────────────────────
def search_jobs(query, location="canada", num_results=3):
    """Searches for jobs using the Adzuna API."""
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


# ─── Step 3: Analyze fit ────────────────────────────────────────
def analyze_job_fit(resume_path, listings):
    """Analyzes resume fit against a list of job listings."""
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
    resume = extract_text_from_pdf(resume_path)
    responses = []

    for i, listing in enumerate(listings):
        job_title = listing["title"]
        job_description = listing["description"]
        print(f"\n  Analyzing ({i + 1}/{len(listings)}): {job_title}...")

        prompt = f"""
        I have a job description below. Extract the top 5 most important 
        technical skills they're looking for, and for each one, rate how 
        important it seems (high/medium/low) based on the posting.
        Similarly, I have attached my resume. Give me a rating out of 5 for each of those 5 skills on how I match it, and then a finalout of 5 score how likely I am to get that job.
        Be brutally honest. If my skills don't match, say so clearly. Don't sugarcoat.
        Give the output in the following JSON format. 
        {json_template}
        Strip the markdown fences and return clean, parseable JSON without the backtick wrapper. 
        Job title:
        {job_title}
        Job Description:
        {job_description}
        Resume:
        {resume}
        """

        for attempt in range(MAX_RETRIES):
            try:
                response = client.models.generate_content(
                    model=MODEL,
                    contents=prompt
                )
                json_response = json.loads(response.text)
                responses.append(json_response)
                print(f"    ✓ Success")
                break
            except Exception as e:
                print(f"    Attempt {attempt + 1} failed: {e}")
                time.sleep(RETRY_DELAY)
        else:
            print(f"    ✗ All {MAX_RETRIES} attempts failed")
            responses.append(f"{job_title} prompt failed")

    return responses


# ─── Step 4: Sort by fit ────────────────────────────────────────
def sort_by_fit(responses):
    """Sorts results by likelihood score, highest first."""
    return sorted(
        responses,
        key=lambda x: x["final_verdict"]["likelihood_of_hire_out_of_5"] if isinstance(x, dict) else 0,
        reverse=True
    )


# ─── Display Results ─────────────────────────────────────────────
def display_results(sorted_responses):
    """Prints a ranked summary of job fit results."""
    print("\n" + "=" * 60)
    print("JOB FIT RESULTS (ranked by likelihood)")
    print("=" * 60)

    for i, r in enumerate(sorted_responses):
        if isinstance(r, dict):
            title = r["title"]
            score = r["final_verdict"]["likelihood_of_hire_out_of_5"]
            summary = r["final_verdict"]["summary"]
            print(f"\n#{i + 1} | {title}: {score}/5")
            print(f"    {summary}")
        else:
            print(f"\n#{i + 1} | {r}")

    print("\n" + "=" * 60)


# ─── The Agent ───────────────────────────────────────────────────
def run_agent(resume_path):
    """
    Full agentic pipeline:
    1. Reads resume and decides what jobs to search for
    2. Searches Adzuna for each query
    3. Analyzes each job against resume
    4. Ranks and displays results
    """
    print("=" * 60)
    print("JOB FIT AGENT - Starting...")
    print("=" * 60)

    # Step 1: Agent decides what to search
    print("\n[Step 1] Reading resume and deciding what to search for...")
    queries = generate_search_queries(resume_path, num_queries=2)
    if not queries:
        print("Agent could not generate search queries. Exiting.")
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
    responses = analyze_job_fit(resume_path, all_listings)

    # Step 4: Rank and display
    print("\n[Step 4] Ranking results...")
    sorted_responses = sort_by_fit(responses)
    display_results(sorted_responses)

    return sorted_responses


# ─── Main ────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_agent(RESUME_PATH)
