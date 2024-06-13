create or replace stage spotify.stages.spotify_song
    url ='s3://spotifyetlproject/transformed_data/song_data/'
    STORAGE_INTEGRATION = spotify_stage;   