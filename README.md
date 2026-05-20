# Job Scraper and Alert System

Python scraper for monitoring job boards and organisation career pages for roles matching Steven Nanga's data, analytics, BI, monitoring and evaluation, research, and data governance profile.

## Sources

- ReliefWeb API, filtered for Malawi
- MyJobMalawi
- Job Search Malawi
- CareersMW
- Nyasa Jobs
- Mlenje
- Ntchito
- CareerNova
- MyJobo
- Jobs.mw
- JobIsland Malawi
- Mvungi Job Master
- LinkedIn public jobs search
- FHI 360 careers
- Jhpiego careers
- Palladium Group careers
- UN Jobs Malawi

Each source lives in `sources/` and exposes a `scrape()` function that returns normalized job dictionaries. To add another source, create a new module with the same interface and register it in `scraper.py`.

LinkedIn is handled through public guest job search pages only. The scraper does not use login credentials, private APIs, browser automation, or access-control bypasses. LinkedIn may return no results if it rate-limits, blocks public scraping, or changes its HTML.

## Requirements

- Python 3.10 or higher
- Gmail app password, or SMTP credentials for another provider
- `curl` available on the system path. Windows 10/11 and GitHub Actions runners include it by default. It is used as a fallback for Job Search Malawi because that site can reset Python `requests` connections.

## Setup

Clone the repository and enter the project directory:

```powershell
git clone <your-repo-url>
cd job-scraper
```

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Playwright is included for future JavaScript-rendered sources. The current scrapers use `requests` and `BeautifulSoup`, so browser binaries are not required unless you add a Playwright-based source later.

## Environment Variables

Set these locally before running:

```powershell
$env:SMTP_HOST = "smtp.gmail.com"
$env:SMTP_PORT = "587"
$env:SMTP_USER = "careerbot71@gmail.com"
$env:EMAIL_FROM_NAME = "CareerBot"
$env:SMTP_PASSWORD = "your_app_password_here"
$env:ALERT_EMAIL = "stephennanga97@gmail.com"
```

Alternatively, create a local `.env` file in the project directory with the same variable names. The scraper loads `.env` automatically when `python-dotenv` is installed. Keep `.env` out of Git; this project includes `.gitignore` rules for that.

For Gmail, use an app password rather than your normal account password. In Google Account settings, enable 2-Step Verification, create an app password for mail, and use that value as `SMTP_PASSWORD`.

Current sender setup:

```text
From: CareerBot <careerbot71@gmail.com>
To: stephennanga97@gmail.com
```

## Running Manually

```powershell
python scraper.py
```

The scraper logs each source as it runs. If one source fails, the error is logged and the remaining sources continue. If no new matching jobs are found, no email is sent.

The local SQLite database is created automatically as `jobs.db`. It stores seen job IDs or URLs so the same job is not emailed twice across runs.

To test scraping and matching without sending email or writing newly matched jobs to the database:

```powershell
python scraper.py --dry-run
```

If your local Windows Python install rejects website certificates during testing, you can temporarily disable SSL verification for that run:

```powershell
$env:SSL_VERIFY = "false"
python scraper.py --dry-run
```

Use that only for local testing. Leave SSL verification enabled for normal runs and GitHub Actions.

To test that Gmail SMTP and the CareerBot sender name work:

```powershell
python scraper.py --test-email
```

## GitHub Actions Deployment

The workflow file is already included at `.github/workflows/scraper.yml`. It runs every hour and can also be started manually from the GitHub Actions tab.

Each GitHub Actions run restores the previous `jobs.db` file from the Actions cache before scraping. After the run, GitHub saves the updated database again. This is what lets CareerBot keep checking every source every hour while only emailing roles that have not been seen before.

Add these repository secrets in GitHub:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `EMAIL_FROM_NAME`
- `SMTP_PASSWORD`
- `ALERT_EMAIL`

Then push the project to GitHub. The action will install dependencies and run:

```bash
python scraper.py
```

## Matching Rules

A job must match at least one primary keyword in its title, organisation, location, or description to trigger an alert. Secondary keywords are included in the email's match reason but do not trigger an alert by themselves.

Primary keyword examples include `Data Analyst`, `Database Analyst`, `Business Intelligence`, `Monitoring and Evaluation`, `Data Governance`, `Research Analyst`, `Statistical Analyst`, `Biostatistician`, `Data Consultant`, and `Research Consultant`.

LinkedIn search terms are configured in `config.py` under `LINKEDIN_SEARCH_TERMS`.

## Resume-Aware Scoring

The scraper reads resume files from the local `Resumes/` folder and uses them to improve matching. Supported formats are `.docx`, `.pdf`, and `.txt`.

For each job, the matcher now produces a score from 0 to 100 using:

- Primary keyword matches
- Supporting keyword matches
- Terms found in your resume and also found in the job advert
- Extra weight when strong terms appear in the job title

Jobs still alert when they match a primary keyword. They can also alert when the resume-aware score reaches `RESUME_SCORE_ALERT_THRESHOLD`, which defaults to `45`.

You can change the threshold locally:

```powershell
$env:RESUME_SCORE_ALERT_THRESHOLD = "55"
```

The `Resumes/` folder is ignored by Git because it contains personal documents. On GitHub Actions, resume-aware matching will only use resume files if you intentionally add them to the deployment environment.

## Email Behavior

Matching jobs are marked as seen only after the email digest sends successfully. This prevents an SMTP outage from causing missed alerts. Non-matching jobs are marked as seen immediately to reduce repeat processing.

Emails are sent as both plain text and HTML. The HTML version includes source, location, closing date, score, match reason, and an open-link action for each role.

Each run logs a source health summary showing how many jobs each source returned, plus any failed sources.
