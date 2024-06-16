--depends on {{ref('raw_album')}}
{{
    config(materialized='incremental',database='Spotify',schema='dbo', alias='SPOTIFY_ALBUM')
}}

with cte as (

select
    {{ dbt_utils.star(from=ref('raw_album')) }}
from {{ ref('raw_album') }}

),

{% if is_incremental() %}

new_data as (
    select 
        src.album_id::VARCHAR(255) COLLATE 'en-ci' AS Album_ID,
        src.album_name::VARCHAR(255) COLLATE 'en-ci' AS ALBUM_NAME,
        src.release_date::TIMESTAMP_NTZ(9) AS RELEASE_DATE,
        src.total_tracks::NUMBER(38,0) AS TOTAL_TRACKS,
        src.urls::VARCHAR(255) AS URLS,
        'Transformed_Album_Details'::varchar(255) COLLATE 'en-ci' as sourcefilename,
        src.sourcefiledate::TIMESTAMP_NTZ(9) as sourcefiledate from cte as src
    left join {{ this }} as main
    on src.SourceFilename = main.SourceFilename
    AND src.SourceFiledate = main.SourceFiledate
    where main.SourceFilename is null and main.SourceFiledate is null

)
{% endif %}

select * from new_data
