create or replace external table SPOTIFY.EXTERNAL_TABLE.SONG_DATA
location=@SPOTIFY.STAGES.SPOTIFY_SONG/
FILE_FORMAT = (FORMAT_NAME = 'my_csv_format');