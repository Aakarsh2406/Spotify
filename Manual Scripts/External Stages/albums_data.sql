create or replace external table SPOTIFY.EXTERNAL_TABLE.ALBUMS_DATA
location=@SPOTIFY.STAGES.SPOTIFY_ALBUM/
FILE_FORMAT = (FORMAT_NAME = 'my_csv_format');