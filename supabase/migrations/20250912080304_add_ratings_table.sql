-- Create ratings table for storing individual user ratings
CREATE TABLE ratings (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    imdb_id TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating >= 0 AND rating <= 10),
    channel_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure one rating per user per movie per channel
    UNIQUE(user_id, imdb_id, channel_id, guild_id)
);

-- Add indexes for performance
CREATE INDEX idx_ratings_user_id ON ratings(user_id);
CREATE INDEX idx_ratings_imdb_id ON ratings(imdb_id);
CREATE INDEX idx_ratings_channel_id ON ratings(channel_id);
CREATE INDEX idx_ratings_guild_id ON ratings(guild_id);

-- Add index for common query pattern (imdb_id + channel_id + guild_id)
CREATE INDEX idx_ratings_movie_channel ON ratings(imdb_id, channel_id, guild_id);

-- Remove the old user_rating column from movies table as it's no longer needed
ALTER TABLE movies DROP COLUMN IF EXISTS user_rating;