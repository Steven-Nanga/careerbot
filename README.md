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
$env:EMAIL_PROVIDER = "smtp"
$env:SMTP_PASSWORD = "your_app_password_here"
$env:BREVO_API_KEY = ""
$env:ALERT_EMAIL = "stephennanga97@gmail.com"
```

Alternatively, create a local `.env` file in the project directory with the same variable names. The scraper loads `.env` automatically when `python-dotenv` is installed. Keep `.env` out of Git; this project includes `.gitignore` rules for that.

For Gmail, use an app password rather than your normal account password. In Google Account settings, enable 2-Step Verification, create an app password for mail, and use that value as `SMTP_PASSWORD`.

Current sender setup:

```text
From: CareerBot <careerbot71@gmail.com>
To: stephennanga97@gmail.com
```

If your server blocks outbound SMTP, use the Brevo API over HTTPS instead:

```text
EMAIL_PROVIDER=brevo
BREVO_API_KEY=your_brevo_api_key
SMTP_USER=careerbot71@gmail.com
```

In Brevo, the `SMTP_USER` email address must be a verified sender.

For an open-source push notification option, use ntfy over HTTPS:

```text
EMAIL_PROVIDER=ntfy
NTFY_URL=https://ntfy.sh
NTFY_TOPIC=careerbot-your-random-private-topic
NTFY_PRIORITY=4
```

Subscribe to the same topic in the ntfy phone app or at `https://ntfy.sh/careerbot-your-random-private-topic`. Pick a long random topic name because anyone who knows the topic can read/publish to it on the public ntfy server.

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
- `EMAIL_PROVIDER`
- `SMTP_PASSWORD`
- `BREVO_API_KEY`
- `ALERT_EMAIL`

Then push the project to GitHub. The action will install dependencies and run:

```bash
python scraper.py
```

## DigitalOcean Docker Deployment

This is the recommended deployment method for a DigitalOcean droplet. The Docker container runs CareerBot immediately when it starts, then runs it again every hour. The SQLite database is stored in a Docker volume so seen jobs are preserved across container restarts and image updates.

Do not run both GitHub Actions and the droplet container at the same time unless you intentionally want two separate deployments checking jobs. They would have separate databases and can send duplicate alerts.

SSH into the droplet, update packages, and install Docker:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Clone the app:

```bash
sudo git clone https://github.com/Steven-Nanga/careerbot.git /opt/careerbot
cd /opt/careerbot
```

Create the production environment file:

```bash
sudo cp .env.example .env
sudo nano .env
sudo chmod 600 .env
sudo mkdir -p Resumes
```

Set these values in `/opt/careerbot/.env`:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=careerbot71@gmail.com
EMAIL_FROM_NAME=CareerBot
EMAIL_PROVIDER=smtp
SMTP_PASSWORD=your_gmail_app_password_here
SMTP_TIMEOUT=60
BREVO_API_KEY=
NTFY_URL=https://ntfy.sh
NTFY_TOPIC=
NTFY_PRIORITY=4
ALERT_EMAIL=stephennanga97@gmail.com
SSL_VERIFY=true
REQUEST_TIMEOUT=30
RESUME_SCORE_ALERT_THRESHOLD=45
```

Build and start CareerBot:

```bash
sudo docker compose up -d --build
```

If you want resume-aware matching on the droplet, upload your resume files into `/opt/careerbot/Resumes`. The Docker container mounts that folder read-only at `/data/Resumes`.

Check logs:

```bash
sudo docker compose logs -f careerbot
```

Run a manual dry run without sending email:

```bash
sudo docker compose run --rm careerbot python /app/scraper.py --dry-run
```

Send a test email:

```bash
sudo docker compose run --rm careerbot python /app/scraper.py --test-email
```

Run the scraper once immediately:

```bash
sudo docker compose run --rm careerbot python /app/scraper.py
```

Update the app later:

```bash
cd /opt/careerbot
sudo git pull
sudo docker compose up -d --build
```

Stop CareerBot:

```bash
sudo docker compose down
```

The database lives in the `careerbot_data` Docker volume. Do not delete that volume unless you want CareerBot to forget all previously seen jobs.

## DigitalOcean Systemd Deployment

Use this only if you prefer running Python directly on the droplet without Docker.

SSH into the droplet, update packages, and install system dependencies:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip curl ca-certificates
```

Create a dedicated Linux user and install the app under `/opt/careerbot`:

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin careerbot
sudo git clone https://github.com/Steven-Nanga/careerbot.git /opt/careerbot
sudo chown -R careerbot:careerbot /opt/careerbot
cd /opt/careerbot
```

Create the virtual environment and install Python dependencies:

```bash
sudo -u careerbot python3 -m venv /opt/careerbot/.venv
sudo -u careerbot /opt/careerbot/.venv/bin/pip install --upgrade pip
sudo -u careerbot /opt/careerbot/.venv/bin/pip install -r /opt/careerbot/requirements.txt
```

Create the production environment file:

```bash
sudo cp /opt/careerbot/.env.example /opt/careerbot/.env
sudo nano /opt/careerbot/.env
sudo chown careerbot:careerbot /opt/careerbot/.env
sudo chmod 600 /opt/careerbot/.env
```

Set these values in `/opt/careerbot/.env`:

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=careerbot71@gmail.com
EMAIL_FROM_NAME=CareerBot
EMAIL_PROVIDER=smtp
SMTP_PASSWORD=your_gmail_app_password_here
SMTP_TIMEOUT=60
BREVO_API_KEY=
NTFY_URL=https://ntfy.sh
NTFY_TOPIC=
NTFY_PRIORITY=4
ALERT_EMAIL=stephennanga97@gmail.com
SSL_VERIFY=true
REQUEST_TIMEOUT=30
RESUME_SCORE_ALERT_THRESHOLD=45
```

Test the app manually from the droplet:

```bash
sudo -u careerbot /opt/careerbot/.venv/bin/python /opt/careerbot/scraper.py --dry-run
sudo -u careerbot /opt/careerbot/.venv/bin/python /opt/careerbot/scraper.py --test-email
```

Install the hourly `systemd` timer:

```bash
sudo cp /opt/careerbot/deploy/systemd/careerbot.service /etc/systemd/system/careerbot.service
sudo cp /opt/careerbot/deploy/systemd/careerbot.timer /etc/systemd/system/careerbot.timer
sudo systemctl daemon-reload
sudo systemctl enable --now careerbot.timer
```

Check that the timer is active:

```bash
systemctl list-timers careerbot.timer
systemctl status careerbot.timer
```

Run it immediately:

```bash
sudo systemctl start careerbot.service
```

View logs:

```bash
journalctl -u careerbot.service -n 100 --no-pager
journalctl -u careerbot.service -f
```

Update the app later:

```bash
cd /opt/careerbot
sudo git pull
sudo chown -R careerbot:careerbot /opt/careerbot
sudo -u careerbot /opt/careerbot/.venv/bin/pip install -r /opt/careerbot/requirements.txt
sudo systemctl restart careerbot.timer
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
