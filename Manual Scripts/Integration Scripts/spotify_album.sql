create or replace stage spotify.stages.spotify_album
    url ='s3://spotifyetlproject/transformed_data/album_data/'
    STORAGE_INTEGRATION = spotify_stage;