-- Add trailer_url column to movies table for storing trailer URLs
ALTER TABLE movies ADD COLUMN trailer_url TEXT;

-- Add index for potential future queries
CREATE INDEX idx_movies_trailer_url ON movies(trailer_url) WHERE trailer_url IS NOT NULL;