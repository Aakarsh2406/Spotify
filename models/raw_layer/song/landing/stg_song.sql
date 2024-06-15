{{
    config (
        materialized="table",
        database = "Spotify",
        schema="raw",
        alias= "raw_songs",
        pre_hook= "alter external table {{ source('raw_stg_song','SONG_DATA') }} refresh;",
    )
}}

With raw_data as (
Select
value:c1::varchar  collate 'en-ci' as Song_ID,
value:c2::varchar  collate 'en-ci' as Song_Name,
value:c3::varchar  collate 'en-ci' as Song_Duration,
value:c4::varchar  collate 'en-ci' as Song_URL,
value:c5::varchar  collate 'en-ci' as Song_Popularity,
value:c6::varchar  collate 'en-ci' as Song_Added,
value:c7::varchar  collate 'en-ci' as Album_ID,
value:c8::varchar  collate 'en-ci' as Artist_ID,
split_part(split(split_part(metadata$filename,'/',3),'_')[2],' ',1) as SourceFiledate
FROM  {{ source('raw_stg_song','SONG_DATA') }}
Where metadata$filename like '%song%' ),
Clean_Data as (
Select
Song_ID,
Song_Name,
Song_Duration,
Song_URL,
Song_Popularity,
Song_Added,
Album_ID,
Artist_ID,
'Raw_Top_50_Songs' as SourceFilename,
SourceFiledate,
From raw_data )
Select * from Clean_Data