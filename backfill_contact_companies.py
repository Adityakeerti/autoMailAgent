"""
Backfill migration: Extract human-readable company names from email domains
for all contacts where company = 'Target Company'.

Logic:
  careers@mitremedia.com  -> domain=mitremedia  -> "Mitremedia"
  jobs@akamaitechnologies.com -> "Akamaitechnologies" -> "Akamai Technologies"
  etc.

We also try to look up the actual company name from the scrape_queue
found_leads metadata if available.
"""
import sqlite3
import json
import re

conn = sqlite3.connect('automail.db')
conn.row_factory = sqlite3.Row

# Build a lookup: email -> {company, job_title, job_url} from found_leads in scrape_queue
email_to_meta = {}

queue_rows = conn.execute(
    "SELECT raw_data FROM scrape_queue WHERE user_id=3"
).fetchall()

for row in queue_rows:
    try:
        raw = json.loads(row['raw_data']) if isinstance(row['raw_data'], str) else row['raw_data']
    except Exception:
        continue
    if not isinstance(raw, dict):
        continue
    for lead in raw.get('found_leads', []):
        if isinstance(lead, dict) and lead.get('email'):
            email_to_meta[lead['email'].lower()] = {
                'company': lead.get('company'),
                'job_title': lead.get('job_title'),
                'job_url': lead.get('job_url'),
            }
    # Also check results_by_platform for companies_found
    for result in raw.get('results_by_platform', []):
        if isinstance(result, dict):
            companies = result.get('companies_found', [])
            emails = result.get('found_emails', [])
            # Map emails back to their discovered company if possible
            for i, email in enumerate(emails):
                if email.lower() not in email_to_meta and i < len(companies):
                    email_to_meta[email.lower()] = {
                        'company': companies[i],
                        'job_title': result.get('role', ''),
                        'job_url': result.get('url'),
                    }

def domain_to_company_name(domain: str) -> str:
    """Convert a domain like 'mitremedia.com' to a human-readable company name."""
    # Strip TLD
    base = domain.split('.')[0] if '.' in domain else domain
    # Known mappings for common tech companies
    known = {
        'mitremedia': 'Mitre Media',
        'mantech': 'ManTech',
        'everai': 'EverAI',
        'binance': 'Binance',
        'lawnstarter': 'LawnStarter',
        'kubikware': 'Kubikware',
        'lemonio': 'Lemonio',
        'akamaitechnologies': 'Akamai Technologies',
        'akamai': 'Akamai Technologies',
        'clipster': 'Clipster',
        'mountsinaihealthsystem': 'Mount Sinai Health System',
        'clickhouse': 'ClickHouse',
        'certik': 'CertiK',
        'datacatalystllc': 'Data Catalyst LLC',
        'headspace': 'Headspace',
        'twilio': 'Twilio',
        '6sense': '6sense',
        'ateam': 'A-Team',
        'turnitin': 'Turnitin',
    }
    if base.lower() in known:
        return known[base.lower()]
    # Generic: split on camelCase or known separators, title-case
    # Insert space before uppercase letters that follow lowercase
    spaced = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', base)
    return spaced.strip().title()

def email_to_company(email: str) -> str:
    """Extract company name from an email address."""
    try:
        _, domain = email.lower().split('@', 1)
    except ValueError:
        return 'Target Company'
    return domain_to_company_name(domain)

# Fetch all contacts with 'Target Company'
contacts = conn.execute(
    "SELECT id, email, company, role, job_posting_url FROM contacts WHERE user_id=3 AND company='Target Company'"
).fetchall()

print(f"Found {len(contacts)} contacts to backfill\n")

updates = 0
for c in contacts:
    email = c['email']
    meta = email_to_meta.get(email.lower(), {})

    new_company = meta.get('company') or email_to_company(email)
    new_role = meta.get('job_title') or c['role']
    new_job_url = meta.get('job_url') or c['job_posting_url']

    # Clean up generic role placeholder
    if new_role == 'Recruiter / Engineering Lead':
        new_role = 'Recruiter'

    print(f"  [{c['id']}] {email}")
    print(f"       company: 'Target Company' -> '{new_company}'")
    print(f"       role:    '{c['role']}' -> '{new_role}'")
    if new_job_url:
        print(f"       job_url: {new_job_url}")
    print()

    conn.execute(
        "UPDATE contacts SET company=?, role=?, job_posting_url=? WHERE id=?",
        (new_company, new_role, new_job_url, c['id'])
    )
    updates += 1

conn.commit()
print(f"\n✅ Backfilled {updates} contacts successfully.")
conn.close()
