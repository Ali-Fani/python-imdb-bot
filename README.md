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

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/python-imdb-bot.git
   cd python-imdb-bot
   ```

2. **Install dependencies using uv**
   ```bash
   # Install uv (if not already installed)
   pip install uv

   # Install project dependencies
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Apply database migrations**
   ```bash
   npx supabase db push
   ```

5. **Run the bot**
   ```bash
   uv run python main.py
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

The bot requires the following environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | ✅ | Discord bot token from Developer Portal |
| `SUPABASE_URL` | ✅ | Supabase project URL |
| `SUPABASE_KEY` | ✅ | Supabase anon/public key |
| `OMDB_API_KEY` | ❌ | OMDB API key for movie data |
| `TMDB_API_KEY` | ❌ | TMDB API key for trailers |
| `CHANNEL_ID` | ❌ | Default Discord channel ID |
| `LOG_LEVEL` | ❌ | Logging level (INFO, DEBUG, etc.) |
| `SENTRY_DSN` | ❌ | Sentry DSN for error monitoring |

### Example .env file

```bash
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

# Optional: Error monitoring
SENTRY_DSN=your_sentry_dsn_here
```

## Usage

1. **Invite the bot** to your Discord server with the required permissions
2. **Set a channel** for movie discussions using `/setchannel`
3. **Post IMDB links** and the bot will automatically respond with movie details
4. **Rate movies** using emoji reactions (1️⃣-9️⃣, 🔟 for 10)

### Bot Commands

- `/setchannel` - Configure the channel for movie detection
- `/ping` - Check bot latency
- `/echo` - Echo a message (for testing)

### Rating System

Users can rate movies by reacting with number emojis:
- 1️⃣ = 1 star
- 2️⃣ = 2 stars
- ...
- 9️⃣ = 9 stars
- 🔟 = 10 stars

Each user can only rate each movie once, and ratings update the community average in real-time.

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for detailed information on:

- Setting up a development environment
- Code style and standards
- Testing guidelines
- Submitting pull requests
- Issue reporting

## Documentation

- [API Reference](API.md) - Health check endpoints documentation
- [Deployment Guide](DEPLOYMENT.md) - Production deployment instructions
- [Coolify Optimization](COOLIFY_OPTIMIZATION_GUIDE.md) - Coolify-specific deployment guide
- [Rating System Integration](RATING_SYSTEM_INTEGRATION.md) - Technical details of the rating system
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions
- [Changelog](CHANGELOG.md) - Version history and changes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 [Documentation](README.md)
- 🐛 [Issue Tracker](https://github.com/your-repo/python-imdb-bot/issues)
- 💬 [Discussions](https://github.com/your-repo/python-imdb-bot/discussions)

---

Built with ❤️ using Discord.py, Supabase, and modern Python practices.