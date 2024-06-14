create or replace external table SPOTIFY.EXTERNAL_TABLE.ARTIST_DATA
location=@SPOTIFY.STAGES.SPOTIFY_ARTIST/
FILE_FORMAT = (FORMAT_NAME = 'my_csv_format');