EXPLAIN SELECT o.run_id::text AS run_id, o.option_type,
       CASE WHEN o.gamma IS NULL THEN 'NULL'
            WHEN o.gamma = 0 THEN 'zero'
            ELSE 'dp=' || length(split_part(o.gamma::text, '.', 2))::text END AS bucket,
       count(*) AS legs
  FROM option_chain_snapshots o
 WHERE o.run_id IN ('612692d1-0ddf-45af-934d-0a8e0fd35501',
                    'e7793aef-4ed8-4bff-8a3c-ef21af5e2c03')
 GROUP BY 1,2,3
 ORDER BY 1,2,3;
