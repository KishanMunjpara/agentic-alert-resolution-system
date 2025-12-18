# Contributing to Agentic Alert Resolution System

Thank you for your interest in contributing to the Agentic Alert Resolution System (AARS)!

## Development Workflow

### 1. Setup Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd Agentic

# Setup backend
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup frontend
cd ../frontend
npm install
```

### 2. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 3. Make Your Changes

- Follow the existing code style
- Write clear, descriptive commit messages
- Add tests for new features
- Update documentation as needed

### 4. Code Style Guidelines

#### Python
- Follow PEP 8 style guide
- Use `black` for code formatting
- Maximum line length: 100 characters
- Use type hints where appropriate
- Write docstrings for all functions and classes

#### TypeScript/React
- Follow ESLint rules
- Use Prettier for formatting
- Use functional components with hooks
- Follow React best practices

### 5. Testing Requirements

- **All new features must have tests**
- Use parametrized tests for multiple scenarios (default requirement)
- Maintain >80% code coverage
- Run tests before committing:
  ```bash
  cd backend
  pytest -v
  ```

### 6. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
# or
git commit -m "fix: resolve bug description"
```

**Commit Message Format:**
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test additions/changes
- `refactor:` for code refactoring
- `chore:` for maintenance tasks

### 7. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear description of changes
- Reference to related issues (if any)
- Screenshots (for UI changes)
- Test results

## Code Review Process

1. All PRs require at least one approval
2. All tests must pass
3. Code must follow style guidelines
4. Documentation must be updated

## Reporting Issues

When reporting issues, please include:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Relevant logs or error messages

## Questions?

Feel free to open an issue for questions or discussions about the project.

Thank you for contributing! 🎉

