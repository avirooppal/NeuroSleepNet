# Contributing to NeuroSleepNet

We love your input! We want to make contributing to NeuroSleepNet as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, and to accept pull requests.

### Prerequisites

- Python 3.9 or higher
- Git
- Familiarity with the codebase

### Setting Up Development Environment

1. **Fork the repository**
   ```bash
   git clone https://github.com/your-username/NeuroSleepNet.git
   cd NeuroSleepNet
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

### Code Style and Quality

We use several tools to maintain code quality:

- **Black** for code formatting
- **Ruff** for linting and import sorting
- **mypy** for type checking
- **pytest** for testing

Run the full quality check:
```bash
make lint
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=neurosleepnet --cov-report=html

# Run specific test file
pytest tests/test_memory.py
```

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, concise commit messages
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new memory consolidation algorithm"
   ```

We follow [Conventional Commits](https://www.conventionalcommits.org/) specification:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `style:` for formatting changes
- `refactor:` for code refactoring
- `test:` for adding tests
- `chore:` for maintenance tasks

### Submitting Changes

1. **Push your branch**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request**
   - Use a clear title and description
   - Link to relevant issues
   - Include screenshots if applicable
   - Ensure CI passes

### Code Review Process

- All PRs require at least one approval
- Automated tests must pass
- Code coverage should not decrease
- Documentation must be updated for API changes

## Project Structure

```
NeuroSleepNet/
├── sdk/
│   ├── python/
│   │   ├── neurosleepnet/
│   │   │   ├── __init__.py
│   │   │   ├── local_store.py
│   │   │   ├── embeddings.py
│   │   │   └── ...
│   │   └── tests/
│   └── nodejs/
├── distributed/
│   ├── backend/
│   └── frontend/
├── docs/
├── benchmarks/
└── tests/
```

## Testing Strategy

### Unit Tests
- Test individual functions and classes
- Mock external dependencies
- Fast execution, isolated scope

### Integration Tests
- Test component interactions
- Use real databases/services
- Slower, but more realistic

### End-to-End Tests
- Test complete user workflows
- Use real API endpoints
- Slowest, but most comprehensive

### Performance Tests
- Benchmark critical paths
- Monitor memory usage
- Track regression over time

## Documentation

### API Documentation
- Auto-generated from docstrings
- Located in `docs/api/`
- Built with Sphinx

### User Guides
- Step-by-step tutorials
- Common use cases
- Troubleshooting guides

### Architecture Documentation
- High-level design decisions
- Component interactions
- Performance considerations

## Release Process

1. **Version bump** in `pyproject.toml`
2. **Update CHANGELOG.md**
3. **Create release tag**
   ```bash
   git tag -a v2.1.0 -m "Release version 2.1.0"
   git push origin v2.1.0
   ```
4. **Build and publish**
   ```bash
   python -m build
   twine upload dist/*
   ```

## Community Guidelines

### Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

### Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **Discord**: For general discussion and questions
- **Documentation**: For detailed guides and API reference

### Security Issues

If you discover a security vulnerability, please do not open a public issue. Instead, send an email to security@neurosleepnet.dev with:

- Description of the vulnerability
- Steps to reproduce
- Potential impact

We will respond within 48 hours and provide a timeline for the fix.

## Recognition

Contributors are recognized in several ways:

- **Contributors list** in README
- **Release notes** mentioning significant contributions
- **Contributor badge** on GitHub profile
- **Swag** for significant contributions

Thank you for contributing to NeuroSleepNet! 🎉
