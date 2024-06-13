create or replace stage spotify.stages.spotify_artist
    url ='s3://spotifyetlproject/transformed_data/artist_data/'
    STORAGE_INTEGRATION = spotify_stage;  