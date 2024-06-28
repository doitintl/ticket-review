WITH
    _base AS (
        SELECT
            tc.* EXCEPT (id),
            t.*
        FROM
            `doit-zendesk-analysis.zendesk.ticket` t
            JOIN doit-zendesk-analysis.zendesk.ticket_comment tc ON t.id = tc.ticket_id
        where
            1 = 1
            and tc.user_id != 12741275940764 # exclude ZR comments 
            and tc.user_id != 10480587018012 # exclude Zippy comments 
            and tc.user_id != 1824442126 # exclude urgent ticket warnings 
            and custom_platform is not null # exclude finance tickets 
            and subject not like ("[gCRE] %")
            and custom_platform in (
                "amazon_web_services",
                "google_g_suite",
                "google_cloud_platform"
            )
            and CAST(t.created_at as DATE) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
            and t.status in ("solved", "closed")
            --and t.id = 191936 # test case 
            --and t.id = 199461 --and t.id = 199457 
    ),
    _calc AS (
        SELECT
            id,
            created_at as ticket_creation_ts,
            assignee_id,
            subject,
            priority,
            status,
            custom_platform,
            custom_product,
            created as comment_create_ts,
            ARRAY_AGG(
                STRUCT (created, user_id, body)
                ORDER BY
                    created ASC
            ) as comment,
            MAX(updated_at) lastupdate_at,
            MAX(has_incidents) escalated
        FROM
            _base
        GROUP BY
            ALL
    )
SELECT
    *,
    comment_create_ts - LEAD(comment_create_ts) OVER (
        PARTITION BY
            id
        ORDER BY
            comment_create_ts DESC
    ) time_to_reply
FROM
    _calc
ORDER BY
    ticket_creation_ts DESC