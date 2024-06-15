{{
    config(materialized='incremental',database='Spotify',schema='dbo', alias='SPOTIFY_SONGS')
}}

with cte as (
    select  Song_ID::VARCHAR(255) COLLATE 'en-ci' as Song_ID,
            Song_Name::VARCHAR(255) COLLATE 'en-ci' as Song_Name,
            Song_Duration::NUMBER(38,0) as Song_Duration,
            Song_URL::VARCHAR(255) COLLATE 'en-ci' as Song_URL,
            Song_Popularity::NUMBER(38,0) as Song_Popularity,
            Song_Added::TIMESTAMP_NTZ(9) as Song_Added,
            Album_ID::VARCHAR(255) COLLATE 'en-ci' as Album_ID,
            Artist_ID::VARCHAR(255) COLLATE 'en-ci' as Artist_ID,
            'Transformed_Songs'::VARCHAR(255) COLLATE 'en-ci' as SourceFilename,
            SourceFiledate::date as SourceFiledate  
    from {{ ref('stg_song') }}
),

{% if is_incremental() %}

new_data as (
    select * from cte
    where SourceFiledate  > (select max(SourceFiledate) from {{ this }})
)

{% else %}

new_data as (
    select * from source
)

{% endif %}

select * from new_data