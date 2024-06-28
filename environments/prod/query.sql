
#DROP TABLE doit-ticket-review.sample_data.v3

CREATE OR REPLACE TABLE doit-ticket-review.sample_data.v3 CLUSTER BY custom_product, id AS (

WITH _base AS (
SELECT tc.* EXCEPT(id), t.*, CASE  WHEN REGEXP_CONTAINS(u.email, '(?i)doit.com') THEN "internal" ELSE "external" END as user_type

FROM `doit-zendesk-analysis.zendesk.ticket` t 
JOIN doit-zendesk-analysis.zendesk.ticket_comment tc 
ON t.id = tc.ticket_id 
JOIN doit-zendesk-analysis.zendesk.user u
ON tc.user_id = u.id
where 1=1 
and tc.user_id != 12741275940764 # exclude ZR comments
and tc.user_id != 10480587018012 # exclude Zippy comments
and tc.user_id != 1824442126 # exclude urgent ticket warnings
and custom_platform is not null # exclude finance tickets
and subject not like ("[gCRE] %")
and system_client != "GetDoer/ZendeskClient" # exlude all other GetDoer requests such as Onboarding / ..
and custom_platform in ("amazon_web_services", "google_g_suite", "google_cloud_platform" )
and CAST(t.created_at as DATE) = DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY)
and t.status in ("solved", "closed")
)
, tags AS (
  SELECT ticket_id as t, ARRAY_AGG(tag) as taggs
  FROM doit-zendesk-analysis.zendesk.ticket_tag ta
  GROUP BY 1
)
, escalated_tickets AS (
    SELECT t, taggs as escalation from tags t0, t0.taggs where taggs="ticket_escalated"
)
, badcsat_tickets AS (
    SELECT t, taggs as csat from tags t0, t0.taggs where taggs="bad_satisfaction_notice"
)

, final_tags AS ( 
SELECT t.t as ticket_id , IFNULL(te.escalation, "false") escalation, IFNULL(tb.csat , "none") csat
FROM tags t
FULL OUTER JOIN escalated_tickets te
ON t.t = te.t
FULL OUTER JOIN badcsat_tickets tb
ON t.t =tb.t
)

, _calc AS (

SELECT 
id
, created_at as ticket_creation_ts
, assignee_id
, subject
, priority
, status
, CASE custom_platform WHEN "amazon_web_services" THEN "AWS" WHEN "google_cloud_platform" THEN "GCP" ELSE "OTHER" END as custom_platform
, custom_product
, created as comment_create_ts
, t.*
, ARRAY_AGG(STRUCT(created, user_id, body, user_type) ORDER BY created ASC) as comment 
, MAX(updated_at) lastupdate_at
, NULL as frt #FIXME
FROM _base b
JOIN final_tags t
ON b.id =t.ticket_id

GROUP BY ALL)

, t1 AS (

SELECT *
  , TIMESTAMP_DIFF(comment_create_ts, LEAD(comment_create_ts) OVER(PARTITION BY id ORDER BY comment_create_ts DESC ) , MINUTE) AS time_to_reply
FROM _calc
ORDER BY ticket_creation_ts DESC

)

SELECT *, 

FROM t1)