CREATE OR REPLACE TABLE `doit-ticket-review.sampled_data.sampled_tickets`
CLUSTER BY custom_platform
AS (
    WITH _base AS (
        SELECT
            tc.* EXCEPT (id),
            t.*,
            CASE
                WHEN
                    REGEXP_CONTAINS(u.email, '(?i)doit.com')
                    THEN 'internal'
                ELSE 'external'
            END AS user_type
        FROM `doit-zendesk-analysis.zendesk.ticket` AS t
        INNER JOIN doit-zendesk-analysis.zendesk.ticket_comment AS tc
            ON t.id = tc.ticket_id
        INNER JOIN doit-zendesk-analysis.zendesk.user AS u
            ON tc.user_id = u.id
        WHERE
            1 = 1
            AND tc.user_id != 12741275940764 # exclude ZR comments
            AND tc.user_id != 10480587018012 # exclude Zippy comments
            AND tc.user_id != 1824442126 # exclude urgent ticket warnings
            AND custom_platform IS NOT NULL # exclude finance tickets
            AND subject NOT LIKE ('%[gCRE]%')
            # exlude all other GetDoer requests such as Onboarding / ..
            AND system_client != 'GetDoer/ZendeskClient'
            AND custom_platform IN (
                'amazon_web_services', 'google_g_suite', 'google_cloud_platform'
            )
            AND CAST(t.created_at AS DATE) >= DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY)
            AND t.status IN ('solved', 'closed')
    ),

    time_to_reply AS (
        SELECT
            *,
            TIMESTAMP_DIFF(
                created,
                LEAD(created) OVER (PARTITION BY id ORDER BY created DESC),
                MINUTE
            ) AS time_to_reply
        FROM _base
        ORDER BY created_at DESC
    ),

    tags AS (
        SELECT
            ticket_id AS t,
            ARRAY_AGG(tag) AS taggs
        FROM doit-zendesk-analysis.zendesk.ticket_tag
        GROUP BY t
    ),

    escalated_tickets AS (
        SELECT
            t,
            taggs AS escalation
        FROM tags AS t0, t0.taggs
        WHERE taggs = 'ticket_escalated'
    ),

    badcsat_tickets AS (
        SELECT
            t,
            taggs AS csat
        FROM tags AS t0, t0.taggs
        WHERE taggs = 'bad_satisfaction_notice'
    ),

    final_tags AS (
        SELECT
            t.t AS ticket_id,
            COALESCE(te.escalation, 'false') AS escalation,
            COALESCE(tb.csat, 'none') AS csat
        FROM tags AS t
        FULL OUTER JOIN escalated_tickets AS te
            ON t.t = te.t
        FULL OUTER JOIN badcsat_tickets AS tb
            ON t.t = tb.t
    ),

    _calc AS (
        SELECT
            t.*,
            id,
            created_at AS ticket_creation_ts,
            assignee_id,
            subject,
            priority,
            status,
            custom_product,
            NULL AS frt,
            CASE custom_platform
                WHEN 'amazon_web_services' THEN 'AWS' WHEN
                    'google_cloud_platform'
                    THEN 'GCP'
                ELSE 'OTHER'
            END AS custom_platform,
            ARRAY_AGG(
                STRUCT(created, user_id, body, user_type) ORDER BY created ASC
            ) AS comment,
            MAX(updated_at) AS lastupdate_at #FIXME
        FROM time_to_reply AS ttr
        INNER JOIN final_tags AS t
            ON ttr.id = t.ticket_id
        GROUP BY ALL
    )

    SELECT *
    FROM _calc
)
