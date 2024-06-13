CREATE OR REPLACE STORAGE INTEGRATION spotify.stages.spotify_stage 
TYPE = EXTERNAL_STAGE STORAGE_PROVIDER = 'S3' 
ENABLED = TRUE 
STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::986390869802:role/Spotify_Role' 
STORAGE_ALLOWED_LOCATIONS = (
    's3://spotifyetlproject/transformed_data/album_data/',
    's3://spotifyetlproject/transformed_data/artist_data/',
    's3://spotifyetlproject/transformed_data/song_data/'
) 
COMMENT = 'Integration S3 to Stage in Snowflake'
