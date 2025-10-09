# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Health check API endpoints (`/health`, `/ready`, `/metrics`)
- Comprehensive API documentation
- Contributing guidelines for developers
- Enhanced code documentation with docstrings

### Changed
- Improved error handling in reaction processing
- Enhanced logging configuration for production use
- Updated Docker configuration for Coolify deployment

### Fixed
- Reaction event handling for cached vs uncached messages
- Database connection validation on startup
- Memory usage optimization in rating calculations

## [0.1.0] - 2025-01-12

### Added
- Initial release of Python IMDB Bot
- Discord bot with IMDB URL detection
- Movie information fetching from OMDB API
- Community rating system with emoji reactions (1-10 scale)
- Supabase database integration for persistence
- Docker containerization
- Production deployment guides
- Comprehensive logging and error handling
- Health check endpoints for monitoring
- Trailer URL fetching from TMDB API
- Guild-specific channel configuration
- Caching system for performance optimization

### Features
- Automatic IMDB link detection in Discord messages
- Rich movie embeds with posters, ratings, and details
- Emoji-based rating system (1️⃣-9️⃣, 🔟)
- Real-time rating averages and vote counts
- Duplicate rating prevention per user
- Database migrations for schema management
- Sentry integration for error monitoring
- Structured logging with JSON output

### Technical
- Built with Discord.py 2.4.0+
- Python 3.11+ support
- Supabase PostgreSQL backend
- TinyDB for local caching
- aiohttp for API calls
- Pydantic for data validation
- Docker multi-stage builds
- Coolify deployment optimized

---

## Types of Changes

- `Added` for new features
- `Changed` for changes in existing functionality
- `Deprecated` for soon-to-be removed features
- `Removed` for now removed features
- `Fixed` for any bug fixes
- `Security` in case of vulnerabilities

## Version Format

This project uses [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
  - MAJOR: Breaking changes
  - MINOR: New features, backward compatible
  - PATCH: Bug fixes, backward compatible

## Release Process

1. Update version in `pyproject.toml`
2. Update this changelog
3. Create git tag
4. Deploy to production
5. Update documentation if needed

---

For older changes, see the [Git history](https://github.com/your-repo/python-imdb-bot/commits/main).