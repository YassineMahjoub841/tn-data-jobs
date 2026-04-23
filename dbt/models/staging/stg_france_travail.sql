-- stg_france_travail.sql
-- Staging model: clean and normalise raw France Travail postings.

with source as (

    select *
    from {{ source('raw', 'france_travail') }}

),

renamed as (

    select
        source_id                                       as posting_id,
        'france_travail'                                as source,
        url,
        trim(title)                                     as title,
        trim(company_name)                              as company_name,
        trim(location)                                  as location,
        contract_type,
        description,
        try_cast(posted_date as date)                   as posted_date,
        try_cast(scraped_at  as date)                   as scraped_at

    from source

),

deduped as (

    select *
    from renamed
    qualify row_number() over (partition by url order by scraped_at desc) = 1

)

select * from deduped
