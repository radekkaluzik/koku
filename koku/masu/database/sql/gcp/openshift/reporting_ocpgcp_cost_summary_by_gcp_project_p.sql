-- Clear out old entries first
DELETE FROM {{schema_name | sqlsafe}}.reporting_ocpgcp_cost_summary_by_gcp_project_p
WHERE usage_start >= {{start_date}}::date
    AND usage_start <= {{end_date}}::date
    AND invoice_month = {{invoice_month}}
    AND cluster_id = {{cluster_id}}
    AND source_uuid = {{source_uuid}}::uuid
;

-- Populate the daily aggregate line item data
INSERT INTO {{schema_name | sqlsafe}}.reporting_ocpgcp_cost_summary_by_gcp_project_p (
    id,
    cluster_id,
    cluster_alias,
    usage_start,
    usage_end,
    project_id,
    project_name,
    unblended_cost,
    markup_cost,
    currency,
    source_uuid,
    credit_amount,
    invoice_month
)
    SELECT uuid_generate_v4() as id,
        cluster_id,
        cluster_alias,
        usage_start,
        usage_end,
        project_id,
        project_name,
        sum(unblended_cost) as unblended_cost,
        sum(markup_cost) as markup_cost,
        max(currency) as currency,
        source_uuid,
        sum(credit_amount) as credit_amount,
        invoice_month
    FROM {{schema_name | sqlsafe}}.reporting_ocpgcpcostlineitem_daily_summary_p
    WHERE usage_start >= {{start_date}}::date
        AND usage_start <= {{end_date}}::date
        AND invoice_month = {{invoice_month}}
        AND cluster_id = {{cluster_id}}
        AND source_uuid = {{source_uuid}}::uuid
    GROUP BY cluster_id,
        cluster_alias,
        usage_start,
        usage_end,
        project_id,
        project_name,
        source_uuid,
        invoice_month
;
