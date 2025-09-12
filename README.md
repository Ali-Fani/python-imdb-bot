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

## Environment Variables

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon/public key
- `DISCORD_TOKEN`: Discord bot token
- `OMDB_API_KEY`: OMDB API key
- `CHANNEL_ID`: Default Discord channel ID (can be overridden per guild)
