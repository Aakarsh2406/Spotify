CREATE OR REPLACE TABLE Songs(
    "Song_ID" INT ,
    "Song_Name" VARCHAR(255) collate 'en-ci' ,
    "Song_Duration" INT ,
    "Song_URL" VARCHAR(255) collate 'en-ci' ,
    "Song_Popularity" INT ,
    "Song_Added" DATETIME ,
    "Album_ID" INT ,
    "Artist_ID" INT 
);