create or replace external table spotify.external_table.song_data
    with location = @spotify_song
    file_format = (Type = CSV);