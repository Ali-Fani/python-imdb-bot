# Python IMDb Bot

A Discord bot that fetches and displays IMDb movie/TV show information.

## Features

- Automatically detects IMDb links in Discord messages
- Fetches movie data from OMDB API
- Stores data in Supabase for persistence
- **Enhanced Community Rating System:**
  - Multi-user ratings via emoji reactions (1️⃣-9️⃣, 🔟)
  - 1-10 rating scale (industry standard)
  - Real-time average calculations
  - Duplicate prevention per user
  - Cache-independent reaction handling
- Guild-specific channel configuration
- Comprehensive error handling and logging

## Database Migrations

This project uses Supabase for data storage and includes database migrations for schema management.

### Prerequisites

- Node.js and npm (for Supabase CLI)
- Supabase account and project

### Setup Migrations

1. **Install Supabase CLI** (if not already installed):
   ```bash
   npm install supabase --save-dev
   ```

2. **Link to your Supabase project**:
   ```bash
   npx supabase link --project-ref YOUR_PROJECT_REF
   ```
   Get your project ref from your Supabase dashboard URL (the part before `.supabase.co`).

3. **Apply migrations to remote database**:
   ```bash
   npx supabase db push
   ```
   This applies all migration files in `supabase/migrations/` to your remote Supabase database.

### Creating New Migrations

When you need to modify the database schema:

1. Create a new migration file:
   ```bash
   npx supabase migration new migration_name
   ```

2. Edit the generated SQL file in `supabase/migrations/`

3. Apply locally (optional):
   ```bash
   npx supabase db reset
   ```

4. Push to remote:
   ```bash
   npx supabase db push
   ```

### Migration Validation

The bot automatically validates database schema on startup. If required tables are missing, it will log an error and exit gracefully, preventing runtime failures.

## Installation

### Local Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pdm install
   ```

3. Copy `.env` from `example.env` and fill in your API keys

4. Apply database migrations (see above)

5. Run the bot:
   ```bash
   pdm run dev
   ```

### Docker Deployment

```bash
# Build the image
docker build -t python-imdb-bot .

# Run with environment variables
docker run -e DISCORD_TOKEN=your_token \
           -e SUPABASE_URL=your_url \
           -e SUPABASE_KEY=your_key \
           -e OMDB_API_KEY=your_omdb_key \
           -e TMDB_API_KEY=your_tmdb_key \
           python-imdb-bot
```

### Coolify Deployment

If deploying with Coolify, you may encounter `.env` file conflicts. Here's how to fix it:

**Option 1: Remove .env from repository**
```bash
# Remove .env from git tracking
git rm --cached .env

# Add .env to .gitignore (if not already there)
echo ".env" >> .gitignore
```

**Option 2: Use .env.example as template**
```bash
# Copy example file
cp example.env .env

# Fill in your values
# DISCORD_TOKEN=your_token
# SUPABASE_URL=your_url
# etc.
```

**Option 3: Configure environment variables in Coolify dashboard**
- Go to your Coolify application settings
- Set environment variables directly in the UI instead of using .env file
- Remove the .env file from your repository

**Coolify Environment Variables to Set:**
- `DISCORD_TOKEN`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `OMDB_API_KEY`
- `TMDB_API_KEY` (optional, for trailers)
- `CHANNEL_ID`

## Environment Variables

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon/public key
- `DISCORD_TOKEN`: Discord bot token
- `OMDB_API_KEY`: OMDB API key
- `CHANNEL_ID`: Default Discord channel ID (can be overridden per guild)



# Discord Bot Configuration
DISCORD_TOKEN=your_discord_bot_token_here

# Supabase Database Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here

# Movie Database APIs
OMDB_API_KEY=your_omdb_api_key_here
TMDB_API_KEY=your_tmdb_api_key_here

# Bot Configuration
CHANNEL_ID=your_default_channel_id_here
LOG_LEVEL=INFO