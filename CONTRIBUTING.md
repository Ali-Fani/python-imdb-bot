# Contributing to Python IMDB Bot

Thank you for your interest in contributing to the Python IMDB Bot! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Documentation](#documentation)
- [Issue Reporting](#issue-reporting)

## Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. By participating, you agree to:

- Be respectful and inclusive
- Focus on constructive feedback
- Accept responsibility for mistakes
- Show empathy towards other contributors
- Help create a positive community

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- Supabase account (for database development)
- Discord Bot Token (for testing)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/python-imdb-bot.git
   cd python-imdb-bot
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/original-repo/python-imdb-bot.git
   ```

## Development Setup

### 1. Install Dependencies

Using uv (recommended):
```bash
# Install uv if not already installed
pip install uv

# Install dependencies
uv sync
```

Using pip:
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file for development:
```bash
cp .env.example .env
# Edit .env with your development credentials
```

Required environment variables:
- `DISCORD_TOKEN`: Your Discord bot token
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase anon key
- `OMDB_API_KEY`: OMDB API key (optional for basic functionality)

### 3. Database Setup

1. Create a Supabase project for development
2. Apply migrations:
   ```bash
   npx supabase db push
   ```
3. Verify schema:
   ```bash
   npx supabase db diff
   ```

### 4. Run the Bot

```bash
# Using uv
uv run python main.py

# Or using Python directly
python main.py
```

## Development Workflow

### Branching Strategy

- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: Feature branches
- `bugfix/*`: Bug fix branches
- `hotfix/*`: Critical fixes for production

### Commit Messages

Follow conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Testing related changes
- `chore`: Maintenance tasks

Examples:
```
feat(rating): add emoji-based rating system
fix(api): handle OMDB API rate limits
docs(readme): update installation instructions
```

### Pull Request Process

1. Create a feature branch from `develop`
2. Make your changes
3. Write tests for new functionality
4. Update documentation if needed
5. Ensure all tests pass
6. Submit a pull request to `develop`

## Code Style

This project follows PEP 8 with some additional guidelines:

### Python Style

- Use `black` for code formatting
- Use `isort` for import sorting
- Maximum line length: 88 characters
- Use type hints for function parameters and return values
- Use docstrings for all public functions and classes

### Formatting

```bash
# Format code with black
uv run black .

# Sort imports with isort
uv run isort .

# Check style with flake8
uv run flake8 .
```

### Linting

```bash
# Run pylint for additional checks
uv run pylint src/
```

### Pre-commit Hooks

Install pre-commit hooks to automatically format and lint code:
```bash
pip install pre-commit
pre-commit install
```

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src

# Run specific test file
uv run pytest tests/test_bot.py
```

### Writing Tests

- Place tests in the `tests/` directory
- Use descriptive test names
- Test both success and failure cases
- Mock external API calls
- Use fixtures for common test data

Example test structure:
```python
import pytest
from src.python_imdb_bot.utils import parse_message

class TestMessageParsing:
    def test_valid_imdb_url(self):
        """Test parsing of valid IMDB URLs"""
        message = "Check out tt0111161"
        result = parse_message(message)
        assert result is not None
        assert result.IMDB_ID == "tt0111161"

    def test_invalid_url(self):
        """Test handling of invalid URLs"""
        message = "This is just text"
        result = parse_message(message)
        assert result is None
```

## Submitting Changes

### Pull Request Checklist

Before submitting a pull request, ensure:

- [ ] Code follows the established style guidelines
- [ ] All tests pass locally
- [ ] New functionality is covered by tests
- [ ] Documentation is updated if needed
- [ ] Commit messages follow conventional format
- [ ] Branch is up to date with `develop`

### Pull Request Template

Use the following template for pull requests:

```markdown
## Description
Brief description of the changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Performance improvement

## Testing
Describe how the changes were tested.

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Code style checks pass
- [ ] Ready for review
```

## Documentation

### Code Documentation

- Use docstrings for all public functions, classes, and methods
- Follow Google docstring format
- Include type hints
- Document parameters, return values, and exceptions

### Project Documentation

- Update README.md for user-facing changes
- Update API.md for endpoint changes
- Update this CONTRIBUTING.md for process changes
- Keep changelog up to date

## Issue Reporting

### Bug Reports

When reporting bugs, please include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Step-by-step instructions
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**: Python version, OS, bot version
6. **Logs**: Relevant log output (with sensitive info removed)

### Feature Requests

For feature requests, include:

1. **Description**: What feature you'd like to see
2. **Use Case**: Why this feature would be useful
3. **Implementation Ideas**: Any thoughts on how to implement it
4. **Alternatives**: Other solutions you've considered

## Getting Help

- **Documentation**: Check the README and other docs first
- **Issues**: Search existing issues before creating new ones
- **Discussions**: Use GitHub Discussions for questions
- **Discord**: Join our Discord server for real-time help

## Recognition

Contributors will be recognized in the project:
- Contributors list in README.md
- Changelog entries
- GitHub contributor statistics

Thank you for contributing to the Python IMDB Bot! 🎬