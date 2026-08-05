# Contributing to Spicetify Bridge

Thank you for considering contributing to **ha-spicetify-bridge**! We welcome bug reports, feature requests, documentation improvements, and pull requests.

---

## 🚀 Getting Started

### 1. Fork & Setup Development Environment

1. **Fork** this repository on GitHub.
2. Clone your fork locally and set up a virtual environment (Python 3.12+ recommended):
   ```bash
   git clone https://github.com/tobfd/ha-spicetify-bridge.git
   cd ha-spicetify-bridge
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. **Install development dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   pre-commit install
   ```

---

## 🛠️ Code Style & Linting

We strictly enforce Home Assistant's code quality standards. Before submitting a pull request, run `pre-commit` to ensure code style compliance:

```bash
pre-commit run -a
```

We use:
- **Ruff** for Python formatting and linting.
- **Strict type annotations** on all functions.
- **Conventional Commits** (e.g., `feat: add volume mute support`, `fix: handle reconnection edge case`).

---

## 🧪 Testing

Always test your changes before submitting a pull request on a local Home Assistant instance.
Run the test suite locally using `pytest` (only available on Linux in other case use the GitHub Actions CI in the PR):

```bash
pytest
```

---

## 📥 Submitting a Pull Request

1. Create a new branch for your feature or bug fix:
   ```bash
   git checkout -b feat/my-amazing-feature
   ```
2. Commit your changes and push them to your fork.
3. Open a **Pull Request** against the `master` branch of this repository.
4. Ensure all GitHub Actions checks pass.

Thank you for helping make Home Assistant and Spicetify better together!
