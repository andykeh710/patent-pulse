-- 6-month window assessment
SELECT 'total_expiring_6mo' AS metric, COUNT(*) AS count
FROM patent_publications
WHERE legal_status='GRANTED'
  AND estimated_expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '6 months'
UNION ALL
SELECT 'with_real_abstract', COUNT(*)
FROM patent_publications
WHERE legal_status='GRANTED'
  AND estimated_expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '6 months'
  AND abstract IS NOT NULL AND LENGTH(abstract) > 100
UNION ALL
SELECT 'with_real_claims', COUNT(*)
FROM patent_publications
WHERE legal_status='GRANTED'
  AND estimated_expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '6 months'
  AND claims_text IS NOT NULL AND LENGTH(claims_text) > 100
UNION ALL
SELECT 'fresh_quality_summary', COUNT(*)
FROM patent_publications
WHERE legal_status='GRANTED'
  AND estimated_expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '6 months'
  AND abstract IS NOT NULL AND LENGTH(abstract) > 100
  AND summary IS NOT NULL
  AND summarized_at >= updated_at - INTERVAL '1 minute'
UNION ALL
SELECT 'stale_title_only_summary', COUNT(*)
FROM patent_publications
WHERE legal_status='GRANTED'
  AND estimated_expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '6 months'
  AND abstract IS NOT NULL AND LENGTH(abstract) > 100
  AND summary IS NOT NULL
  AND summarized_at < updated_at - INTERVAL '1 minute'
UNION ALL
SELECT 'no_summary_yet', COUNT(*)
FROM patent_publications
WHERE legal_status='GRANTED'
  AND estimated_expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '6 months'
  AND abstract IS NOT NULL AND LENGTH(abstract) > 100
  AND summary IS NULL
UNION ALL
SELECT 'no_abstract_yet', COUNT(*)
FROM patent_publications
WHERE legal_status='GRANTED'
  AND estimated_expiry_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '6 months'
  AND (abstract IS NULL OR LENGTH(abstract) <= 100);
