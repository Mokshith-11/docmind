-- Phase 6 — dashboard metrics aggregated in one call.
-- PostgREST can't do percentiles/group-by across the messages↔conversations join,
-- so this rolls everything into a single jsonb result the API returns as-is.

create or replace function public.workspace_metrics(ws uuid)
returns jsonb
language sql
stable
as $$
  with m as (
    select msg.*
    from public.messages msg
    join public.conversations c on c.id = msg.conversation_id
    where c.workspace_id = ws and msg.role = 'assistant'
  )
  select jsonb_build_object(
    'queries', (select count(*) from m),
    'avg_latency_ms', (select coalesce(round(avg(latency_ms))::int, 0) from m),
    'p50_latency_ms', (select coalesce(percentile_cont(0.5)
        within group (order by latency_ms), 0)::int from m where latency_ms is not null),
    'p95_latency_ms', (select coalesce(percentile_cont(0.95)
        within group (order by latency_ms), 0)::int from m where latency_ms is not null),
    'cache_hits', (select count(*) from m where cache_hit),
    'cache_hit_rate', (select case when count(*) = 0 then 0
        else round(count(*) filter (where cache_hit)::numeric / count(*), 3) end from m),
    'est_cost_usd', (select coalesce(round(sum(cost_usd), 4), 0) from m),
    'tokens_in', (select coalesce(sum(tokens_in), 0)::int from m),
    'tokens_out', (select coalesce(sum(tokens_out), 0)::int from m),
    'routes', (select coalesce(jsonb_agg(jsonb_build_object('route', route, 'count', cnt)), '[]')
        from (select route, count(*) cnt from m where route is not null group by route order by cnt desc) r),
    'per_day', (select coalesce(jsonb_agg(jsonb_build_object(
          'day', dt, 'queries', cnt, 'cost', cost) order by dt), '[]')
        from (select date_trunc('day', created_at)::date as dt, count(*) cnt,
                     coalesce(round(sum(cost_usd), 5), 0) cost
              from m group by 1) d),
    'evals', (select coalesce(jsonb_agg(jsonb_build_object(
          'ran_at', ran_at, 'faithfulness', faithfulness,
          'answer_relevance', answer_relevance) order by ran_at desc), '[]')
        from (select * from public.eval_runs order by ran_at desc limit 10) e)
  );
$$;
