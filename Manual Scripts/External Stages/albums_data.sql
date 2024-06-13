create or replace external table spotify.external_table.albums_data
    with location = @spotify_album
    file_format = (Type = CSV);