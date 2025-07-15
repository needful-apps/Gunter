# Testing Guide for Gunter

This document outlines the testing approach for the Gunter project.

## Testing Structure

The tests are organized into the following directories:

- `tests/unit/`: Unit tests for individual components
- `tests/integration/`: Tests for API endpoints and component integrations
- `tests/fixtures/`: Test data files

## Running Tests

### Local Development

To run tests locally:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=term

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Watch mode (automatically re-run tests when files change)
pytest-watch
```

### Using Docker

Using Docker Compose:

```bash
# Run all tests
docker-compose run --rm test

# Run tests in watch mode
docker-compose run --rm test-watch
```

## Test Coverage

We aim for at least 80% code coverage. The coverage report is generated after running tests with the `--cov` option.

## Continuous Integration

Tests are automatically run in the GitHub Actions CI pipeline on every push and pull request to the main branch.

## Mocking Strategy

- External dependencies like the GeoLite2 database are mocked
- API calls to GitHub or other services are mocked using `requests-mock` or `responses`
- Time-dependent tests use `freezegun` to control the datetime

## Best Practices

1. Write tests before implementing new features (TDD)
2. Mock external dependencies
3. Use meaningful test names that describe the behavior being tested
4. Keep tests small and focused
5. Use fixtures for reusable test data
6. Use parameterized tests for testing similar cases with different inputs
