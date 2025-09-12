-- Create movies table
CREATE TABLE movies (
    id SERIAL PRIMARY KEY,
    imdb_id TEXT NOT NULL,
    message_id BIGINT NOT NULL,
    user_rating FLOAT,
    channel_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create settings table
CREATE TABLE settings (
    id SERIAL PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX idx_movies_imdb_id ON movies(imdb_id);
CREATE INDEX idx_movies_channel_id ON movies(channel_id);
CREATE INDEX idx_movies_guild_id ON movies(guild_id);
CREATE INDEX idx_settings_guild_id ON settings(guild_id);