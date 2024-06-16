{{
    config(
        materialized="table",
        database="Spotify",
        schema="raw",
        alias="raw_album_data",
        pre_hook="alter external table {{ source('raw_stg_album','ALBUMS_DATA') }} refresh;",
    )
}}

with
    raw_data as (
        select
            value:c1::varchar collate 'en-ci' as album_id,
            value:c2::varchar collate 'en-ci' as album_name,
            value:c3::varchar collate 'en-ci' as release_date,
            value:c4::varchar collate 'en-ci' as total_tracks,
            value:c5::varchar collate 'en-ci' as urls,
           split_part(split(split_part(metadata$filename,'/',3),'_')[3],' ',1) as sourcefiledate
        from {{ source("raw_stg_album", "ALBUMS_DATA") }}
        where metadata$filename like '%album%'
    ),
    clean_data as (
        select
            album_id,
            album_name,
            release_date,
            total_tracks,
            urls,
            'Transformed_Album_Details' as sourcefilename,
            sourcefiledate,
        from raw_data
    )
select *
from clean_data
