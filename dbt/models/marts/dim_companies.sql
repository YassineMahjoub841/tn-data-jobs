-- dim_companies.sql
-- Dimension table: company-level aggregates.

with company_stats as (

    select
        company_name,
        count(distinct posting_id)                              as total_postings,
        count(distinct case when source = 'tanitjobs'
                            then posting_id end)                as tanitjobs_postings,
        count(distinct case when source = 'france_travail'
                            then posting_id end)                as france_travail_postings,
        list(distinct skill order by skill)                     as skills_demanded,
        max(posted_date)                                        as latest_posting_date

    from {{ ref('int_skills_extracted') }}
    group by 1

)

select * from company_stats
order by total_postings desc
