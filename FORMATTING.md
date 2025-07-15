# Code Formatting and Linting

This document describes how to set up and use code formatting and quality checking for the Gunter project.

## Required Tools

- **Black**: Python code formatter
- **isort**: Import sorter for Python
- **Flake8**: Python linter

## Installing the Tools

### Option 1: Using a Virtual Environment (recommended)

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the development dependencies
pip install -r requirements-dev.txt
```

### Option 2: Global Installation

```bash
pip install black isort flake8
```

## Using the Formatting Tools

### Method 1: Format Script

```bash
# Run the formatting script (automatically detects virtual environment)
./scripts/format_code.sh
```

If the script doesn't work, try the alternative version:

```bash
./scripts/format_code_alt.sh
```

### Method 2: Manual Execution

```bash
# Run Black and isort directly
black .
isort .

# Or as Python modules
python -m black .
python -m isort .
```

### Method 3: Pre-commit Hooks (recommended for developers)

1. Install pre-commit:
```bash
pip install pre-commit
```

2. Install the Git hooks:
```bash
pre-commit install
```

Now Black, isort, and Flake8 will run automatically before each commit!

## Configuration

- **Black**: Configuration is in `pyproject.toml` (if present)
- **isort**: Uses the Black profile for compatibility
- **Flake8**: Configuration is in `setup.cfg` or `.flake8`

## Troubleshooting

If you encounter error messages like `command not found`:

1. Make sure the virtual environment is activated: `source venv/bin/activate`
2. Check if the tools are installed: `pip list | grep -E "black|isort|flake8"`
3. Install missing tools: `pip install black isort flake8`
