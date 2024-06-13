create or replace external table spotify.external_table.artist_data
    with location = @spotify_artist
    file_format = (Type = CSV);