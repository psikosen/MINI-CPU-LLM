# Contributing to MINI-CPU-LLM

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/MINI-CPU-LLM.git
   cd MINI-CPU-LLM
   ```
3. **Set up development environment**:
   ```bash
   ./scripts/dev_setup.sh
   ```

## Development Workflow

### Building Components

**C++ voice_core**:
```bash
cd core
mkdir build && cd build
cmake ..
make -j4
```

**Python orchestrator**:
```bash
cd orchestrator
source venv/bin/activate
python src/main.py --dev
```

### Testing Changes

Before submitting, ensure:
- Code compiles without warnings
- No memory leaks in C++ code (use valgrind)
- Python code follows PEP 8
- All components integrate properly

### Code Style

**C++**:
- Follow Google C++ Style Guide
- Use meaningful variable names
- Add comments for complex logic
- Keep functions focused and small

**Python**:
- Follow PEP 8
- Use type hints where beneficial
- Write docstrings for functions
- Keep functions under 50 lines when possible

## Areas for Contribution

### High Priority

1. **Porcupine Integration** - Replace placeholder wake word detector
2. **Silero VAD Integration** - Replace simple energy-based VAD
3. **Kokoro TTS Implementation** - Add native Kokoro support
4. **KittenTTS Implementation** - Add KittenTTS support
5. **Tool System** - Implement safe tool execution framework

### Medium Priority

1. **Performance Optimization** - Reduce latency and resource usage
2. **Better Error Handling** - Improve recovery from failures
3. **Unit Tests** - Add comprehensive test coverage
4. **Metrics Dashboard** - Web UI for monitoring
5. **Multi-language Support** - Support languages beyond English

### Documentation

1. **Tutorial Videos** - Setup and usage guides
2. **API Documentation** - Detailed component documentation
3. **Example Configurations** - Common use cases
4. **Performance Tuning Guide** - Optimization tips

## Submitting Changes

1. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** with clear, focused commits:
   ```bash
   git add .
   git commit -m "Add feature: description"
   ```

3. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create a Pull Request** on GitHub

### Pull Request Guidelines

- **Title**: Clear, descriptive summary
- **Description**: Explain what changes and why
- **Testing**: Describe how you tested the changes
- **Documentation**: Update docs if needed
- **Breaking Changes**: Clearly mark any breaking changes

### Commit Message Format

```
type: Short summary (50 chars or less)

Detailed explanation of the change, if needed.
- Bullet points for multiple changes
- Reference issues: Fixes #123

Type can be:
- feat: New feature
- fix: Bug fix
- docs: Documentation changes
- style: Code style changes (formatting)
- refactor: Code restructuring
- perf: Performance improvements
- test: Adding tests
- chore: Maintenance tasks
```

## Code Review Process

1. Maintainers will review your PR
2. Address any feedback or requested changes
3. Once approved, your PR will be merged

## Reporting Issues

### Bug Reports

Include:
- Clear title and description
- Steps to reproduce
- Expected vs actual behavior
- System information (OS, Pi model, etc.)
- Relevant log output
- Screenshots if applicable

### Feature Requests

Include:
- Clear use case
- Proposed solution (if you have one)
- Alternative approaches considered
- Willingness to implement it yourself

## Community Guidelines

- Be respectful and inclusive
- Help others learn and grow
- Focus on constructive feedback
- Assume good intentions

## Questions?

- Open an issue for questions
- Check existing issues and docs first
- Be specific and provide context

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be acknowledged in:
- README.md contributors section
- Release notes for significant contributions

Thank you for contributing!
