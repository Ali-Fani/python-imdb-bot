#!/bin/bash
set -e

# Docker entrypoint script for Python IMDB Bot
# Handles database migrations and startup

echo "🚀 Starting Python IMDB Bot..."

# Function to check if Supabase is accessible
check_supabase() {
    echo "🔍 Checking Supabase connection..."

    # Try to run a simple query to check if migrations have been applied
    python -c "
import sys
import os
sys.path.insert(0, '/app/src')
from python_imdb_bot.utils import supabase

try:
    # Try a simple query to check if database is accessible
    result = supabase.table('settings').select('*').limit(1).execute()
    print('✅ Supabase connection successful')
    return 0
except Exception as e:
    print('❌ Supabase connection failed:', str(e))
    print('⚠️  Please ensure:')
    print('   1. Database migrations are applied')
    print('   2. SUPABASE_URL and SUPABASE_KEY are set correctly')
    print('   3. Database is accessible from this container')
    return 1
"

    return $?
}

# Function to run database migrations
run_migrations() {
    echo "🗄️  Checking database migrations..."

    # Check if we have npx available (for Supabase CLI)
    if command -v npx &> /dev/null; then
        echo "📦 Running Supabase migrations..."

        # Change to the supabase directory if it exists
        if [ -d "/app/supabase" ]; then
            cd /app/supabase

            # Run migrations
            if npx supabase db push; then
                echo "✅ Database migrations completed successfully"
                return 0
            else
                echo "❌ Database migration failed"
                return 1
            fi
        else
            echo "⚠️  No supabase directory found, skipping migrations"
            return 0
        fi
    else
        echo "⚠️  npx not found, skipping automatic migrations"
        echo "   Run migrations manually: npx supabase db push"
        return 0
    fi
}

# Function to validate environment variables
validate_env() {
    echo "🔧 Validating environment variables..."

    required_vars=("DISCORD_TOKEN" "SUPABASE_URL" "SUPABASE_KEY")

    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo "❌ Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "   - $var"
        done
        echo ""
        echo "   Please set these in your .env file or Docker environment"
        return 1
    fi

    echo "✅ Environment variables validated"
    return 0
}

# Main execution flow
main() {
    echo "🐳 Docker container started"
    echo "📍 Working directory: $(pwd)"
    echo "👤 Running as user: $(whoami)"

    # Validate environment
    if ! validate_env; then
        exit 1
    fi

    # Check Supabase connection
    if ! check_supabase; then
        echo "⚠️  Supabase connection issues detected"
        echo "   The bot will continue but may have limited functionality"
    fi

    # Run migrations if possible
    if ! run_migrations; then
        echo "⚠️  Migration issues detected"
        echo "   The bot will continue but may have database issues"
    fi

    # Start the bot
    echo "🤖 Starting Discord bot..."
    echo "📊 Environment:"
    echo "   - Python: $(python --version)"
    echo "   - Working directory: $(pwd)"
    echo "   - Log level: ${LOG_LEVEL:-INFO}"

    # Execute the bot
    exec python -m src.python_imdb_bot.rewrite
}

# Handle graceful shutdown
trap 'echo "🛑 Received shutdown signal, exiting gracefully..."; exit 0' SIGTERM SIGINT

# Run main function
main "$@"