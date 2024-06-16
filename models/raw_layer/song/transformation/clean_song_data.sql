--depends on {{ref('stg_song')}}
{{
    config(materialized='incremental',database='Spotify',schema='dbo', alias='SPOTIFY_SONGS', merge_exclude_columns = ['created_date'])
}}

with cte as (
    select  Song_ID::VARCHAR(255) COLLATE 'en-ci' as Song_ID,
            Song_Name::VARCHAR(255) COLLATE 'en-ci' as Song_Name,
            (TO_CHAR( FLOOR(song_duration / 60000), 'FM9990') || ' min ' || TO_CHAR(FLOOR((song_duration % 60000) / 1000), 'FM990') || ' sec')::VARCHAR(255) COLLATE 'en-ci' as Song_Duration,
            Song_URL::VARCHAR(255) COLLATE 'en-ci' as Song_URL,
            Song_Popularity::NUMBER(38,0) as Song_Popularity,
            Song_Added::TIMESTAMP_NTZ(9) as Song_Added,
            Album_ID::VARCHAR(255) COLLATE 'en-ci' as Album_ID,
            Artist_ID::VARCHAR(255) COLLATE 'en-ci' as Artist_ID,
            'Transformed_Songs'::VARCHAR(255) COLLATE 'en-ci' as SourceFilename,
            SourceFiledate::date as SourceFiledate ,
            getdate()::timestamp_ntz(9) as created_date
    from {{ ref('stg_song') }}
),

{% if is_incremental() %}

new_data as (
    select src.* from cte as src
    left join {{ this }} as main
    on src.SourceFilename = main.SourceFilename
    AND src.SourceFiledate = main.SourceFiledate
    where main.SourceFilename is null and main.SourceFiledate is null

)

{% else %}

new_data as (
    select * from source
)

{% endif %}

select * from new_data