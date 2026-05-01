SELECT
  estimated_expiry_date AS expires,
  COALESCE(assignees->>0, 'unknown') AS assignee,
  LEFT(title, 70) AS title
FROM patent_publications
WHERE legal_status='GRANTED'
  AND estimated_expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '6 months'
ORDER BY estimated_expiry_date ASC
LIMIT 15;
