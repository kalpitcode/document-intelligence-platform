# Contributing Guidelines

Thank you for your interest in contributing to the **Enterprise AI Document Intelligence Platform**!

## How to Contribute
1. **Fork the Repository**: Create your feature branch (`git checkout -b feature/amazing-feature`).
2. **Setup Local Environment**: Follow the setup steps in [README.md](README.md).
3. **Run Code Quality Checks**:
   ```bash
   poetry run ruff check .
   poetry run black --check .
   poetry run python scripts/security_scan.py
   poetry run pytest
   ```
4. **Submit a Pull Request**: Provide a clear description using our Pull Request template.

## Code Standards
- Adhere to Clean Architecture and SOLID principles.
- Use type hints for all public functions.
- Write unit tests for new services or repository methods.
