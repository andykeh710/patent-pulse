"""Validate BigQuery patent dataset freshness."""

from google.cloud import bigquery

client = bigquery.Client(project="patent-signals")

# 1. Max publication_date for all US rows
q1 = """
    SELECT MAX(publication_date) as max_pub,
           COUNT(*) as total
    FROM patents-public-data.patents.publications
    WHERE country_code = 'US'
"""
rows = list(client.query(q1))
print(f"1. Max pub date US: {dict(rows[0]) if rows else 'EMPTY'}")

# 2. Counts by publication_date since May 28
q2 = """
    SELECT publication_date, COUNT(*) as cnt
    FROM patents-public-data.patents.publications
    WHERE country_code = 'US'
      AND publication_date >= 20260528
    GROUP BY publication_date
    ORDER BY publication_date DESC
    LIMIT 10
"""
rows = list(client.query(q2))
print("2. Counts by date since May 28:")
for r in rows:
    print(f"   {r['publication_date']}: {r['cnt']}")

# 3. Kind codes in window
q3 = """
    SELECT SUBSTR(publication_number, LENGTH(publication_number)-1) as kind,
           COUNT(*) as cnt
    FROM patents-public-data.patents.publications
    WHERE country_code = 'US'
      AND publication_date >= 20260528
    GROUP BY kind
    ORDER BY cnt DESC
    LIMIT 10
"""
rows = list(client.query(q3))
print("3. Kind codes:")
for r in rows:
    print(f"   {r['kind']}: {r['cnt']}")

# 4. ALL rows in window regardless of filters
q4 = """
    SELECT COUNT(*) as total,
           MAX(publication_date) as max_pub,
           MIN(publication_date) as min_pub
    FROM patents-public-data.patents.publications
    WHERE country_code = 'US'
      AND publication_date >= 20260528
      AND publication_date <= 20260619
"""
rows = list(client.query(q4))
print(f"4. All rows May28-Jun19: {dict(rows[0]) if rows else 'EMPTY'}")

# 5. Total US
q5 = """
    SELECT COUNT(*) as total_us
    FROM patents-public-data.patents.publications
    WHERE country_code = 'US'
"""
rows = list(client.query(q5))
print(f"5. Total US patents: {dict(rows[0]) if rows else 'EMPTY'}")

# 6. Check row count in last 7 days regardless of country
q6 = """
    SELECT publication_date, country_code, COUNT(*) as cnt
    FROM patents-public-data.patents.publications
    WHERE publication_date >= 20260612
    GROUP BY publication_date, country_code
    ORDER BY publication_date DESC
    LIMIT 10
"""
rows = list(client.query(q6))
print("6. Any rows globally since Jun 12:")
for r in rows:
    print(f"   {r['publication_date']} ({r['country_code']}): {r['cnt']}")

# 7. Dry run bytes estimate
job_config = bigquery.QueryJobConfig(dry_run=True)
job = client.query(q4, job_config=job_config)
print(f"7. Dry run bytes: {job.total_bytes_processed:,}")
