"""Central configuration for the job scraper."""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parent
if load_dotenv:
    load_dotenv(BASE_DIR / ".env")

DATABASE_PATH = os.getenv("JOB_SCRAPER_DB", str(BASE_DIR / "jobs.db"))
RESUME_DIR = os.getenv("RESUME_DIR", str(BASE_DIR / "Resumes"))

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
SSL_VERIFY = os.getenv("SSL_VERIFY", "true").lower() not in {"0", "false", "no"}
USER_AGENT = os.getenv(
    "USER_AGENT",
    "StevenNangaJobScraper/1.0 (+https://github.com/Steven-Nanga)",
)

ALERT_EMAIL = os.getenv("ALERT_EMAIL", "stephennanga97@gmail.com")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "CareerBot")
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "smtp").lower()
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "careerbot71@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", "60"))
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")

PRIMARY_KEYWORDS = [
    "Data Analyst",
    "Database Analyst",
    "BI Analyst",
    "Business Intelligence",
    "M&E Analyst",
    "Monitoring and Evaluation",
    "Monitoring & Evaluation",
    "MEL",
    "MEAL",
    "MERL",
    "Data Protection Officer",
    "Data Governance",
    "Research Analyst",
    "Statistical Analyst",
    "Biostatistician",
    "Data Consultant",
    "Research Consultant",
]

SECONDARY_KEYWORDS = [
    "Power BI",
    "SQL",
    "Python",
    "R",
    "ETL",
    "Credit Risk",
    "IFRS9",
    "Regulatory Reporting",
    "Malawi",
    "Remote",
    "Southern Africa",
]

RESUME_PROFILE_TERMS = [
    "Data Analysis",
    "Database Management",
    "Database Administration",
    "Data Quality",
    "Data Cleaning",
    "Data Visualization",
    "Dashboard",
    "Dashboards",
    "Power Query",
    "DAX",
    "Excel",
    "Advanced Excel",
    "SPSS",
    "Stata",
    "KoboToolbox",
    "ODK",
    "SurveyCTO",
    "ETL Pipelines",
    "Reporting",
    "Analytics",
    "Credit Bureau",
    "Credit Data",
    "Data Protection",
    "Privacy",
    "Compliance",
    "Risk",
    "Financial Data",
    "Financial Inclusion",
    "Research",
    "Quantitative",
    "Qualitative",
    "Statistics",
    "Regression",
    "Logistic Regression",
    "Mixed Effects",
    "Impact Evaluation",
    "Monitoring",
    "Evaluation",
    "M&E",
    "MEL",
]

RESUME_SCORE_ALERT_THRESHOLD = int(os.getenv("RESUME_SCORE_ALERT_THRESHOLD", "45"))

LINKEDIN_SEARCH_TERMS = [
    "Data Analyst Malawi",
    "Database Analyst Malawi",
    "Business Intelligence Malawi",
    "Monitoring and Evaluation Malawi",
    "Data Governance Malawi",
    "Research Analyst Malawi",
    "Data Consultant Malawi",
    "Power BI Malawi",
]

RELIEFWEB_ENDPOINT = "https://api.reliefweb.int/v2/jobs"
RELIEFWEB_PROFILE = "job-scraper-steven-nanga"
