-- int_skills_extracted.sql
-- Intermediate model: cross-source union + skill tagging against the taxonomy.
--
-- The skills taxonomy seed exposes two columns:
--   canonical_name  — the normalised skill name we store
--   variants        — pipe-separated list of aliases (e.g. "python|py|python3")

with postings as (

    select * from {{ ref('stg_tanitjobs') }}
    union all
    select * from {{ ref('stg_france_travail') }}

),

taxonomy as (

    select
        canonical_name,
        trim(variant.value)      as variant
    from {{ ref('skills') }}
    -- Unnest the pipe-separated variants column into individual rows
    cross join lateral unnest(string_split(variants, '|')) as variant(value)

),

-- Tag each posting with every skill whose variant appears in the description
posting_skills as (

    select
        p.posting_id,
        p.source,
        p.title,
        p.company_name,
        p.location,
        p.contract_type,
        p.posted_date,
        p.scraped_at,
        t.canonical_name         as skill

    from postings p
    join taxonomy t
        on lower(p.description) like '%' || lower(t.variant) || '%'

)

select * from posting_skills
