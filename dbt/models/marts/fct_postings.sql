-- fct_postings.sql
-- Fact table: one row per posting, with aggregated skill list.

with base as (

    select
        posting_id,
        source,
        title,
        company_name,
        location,
        contract_type,
        posted_date,
        scraped_at,
        list(skill order by skill)  as skills

    from {{ ref('int_skills_extracted') }}
    group by 1, 2, 3, 4, 5, 6, 7, 8

)

select * from base
