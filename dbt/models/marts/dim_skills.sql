-- dim_skills.sql
-- Dimension table: skill demand statistics.

with skill_counts as (

    select
        skill                                                   as skill_name,
        count(distinct posting_id)                              as posting_count,
        count(distinct case when source = 'tanitjobs'
                            then posting_id end)                as tanitjobs_count,
        count(distinct case when source = 'france_travail'
                            then posting_id end)                as france_travail_count,
        min(posted_date)                                        as first_seen,
        max(posted_date)                                        as last_seen

    from {{ ref('int_skills_extracted') }}
    group by 1

)

select * from skill_counts
order by posting_count desc
