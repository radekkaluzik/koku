DELETE FROM {{schema_name | sqlsafe}}.reporting_ocpazure_network_summary_p
WHERE usage_start >= {{start_date}}::date
    AND usage_start <= {{end_date}}::date
    AND cluster_id = {{cluster_id}}
    AND source_uuid = {{source_uuid}}
;

INSERT INTO {{schema_name | sqlsafe}}.reporting_ocpazure_network_summary_p (
    id,
    usage_start,
    usage_end,
    cluster_id,
    cluster_alias,
    subscription_guid,
    service_name,
    usage_quantity,
    unit_of_measure,
    pretax_cost,
    markup_cost,
    currency,
    source_uuid
)
    SELECT uuid_generate_v4() as id,
        usage_start as usage_start,
        usage_start as usage_end,
        {{cluster_id}},
        {{cluster_alias}},
        subscription_guid,
        service_name,
        sum(usage_quantity) as usage_quantity,
        max(unit_of_measure) as unit_of_measure,
        sum(pretax_cost) as pretax_cost,
        sum(markup_cost) as markup_cost,
        max(currency) as currency,
        {{source_uuid}}::uuid as source_uuid
    FROM reporting_ocpazurecostlineitem_daily_summary_p
    WHERE service_name IN ('Virtual Network','VPN','DNS','Traffic Manager','ExpressRoute','Load Balancer','Application Gateway')
        AND usage_start >= {{start_date}}::date
        AND usage_start <= {{end_date}}::date
        AND cluster_id = {{cluster_id}}
        AND source_uuid = {{source_uuid}}
    GROUP BY usage_start, subscription_guid, service_name
;
