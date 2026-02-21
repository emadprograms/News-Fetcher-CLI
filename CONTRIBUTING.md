# Contributing to News-Fetcher 🦅

First off, thank you for considering contributing to News-Fetcher! It's people like you that make this tool such a great resource for the financial community.

## 🤝 How to Contribute

We welcome contributions of all kinds, whether it's:
- 🐛 **Reporting Bugs**: Find a broken link or a crash? Let us know!
- 💡 **Suggesting Features**: Have an idea for a new data source or dashboard widget?
- 📝 **Improving Documentation**: Typos, unclear instructions, or missing guides.
- 💻 **Writing Code**: Fixing bugs, adding features, or optimizing performance.

### 🐛 Reporting Bugs

This section guides you through submitting a bug report for News-Fetcher. Following these guidelines helps maintainers and the community understand your report 📝, reproduce the behavior 💻, and find related reports 🔎.

- **Use a clear and descriptive title** for the issue to identify the problem.
- **Describe the exact steps to reproduce the problem** in as many details as possible.
- **Provide specific examples** to demonstrate the steps.
- **Describe the behavior you observed after following the steps** and point out what exactly is the problem with that behavior.
- **Explain which behavior you expected to see instead and why.**

### 💡 Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for News-Fetcher, including completely new features and minor improvements to existing functionality.

- **Use a clear and descriptive title** for the issue to identify the suggestion.
- **Provide a step-by-step description of the suggested enhancement** in as many details as possible.
- **Explain why this enhancement would be useful** to most News-Fetcher users.

### 💻 Pull Requests

The process is straightforward:

1.  **Fork** the repo on GitHub.
2.  **Clone** the project to your own machine.
3.  **Create a branch** for your feature or fix (`git checkout -b feature/amazing-feature`).
4.  **Commit** your changes to your own branch.
5.  **Push** your work back up to your fork.
6.  Submit a **Pull Request** so that we can review your changes.

## 🛠️ Development Setup

To get your development environment running:

1.  **Prerequisites**: Ensure you have Python 3.9+ installed.
2.  **Environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```
3.  **Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Secrets**:
    You will need to set up your `.env` file with Infisical credentials. See the `README.md` for details.

## 🎨 Style Guide

- **Code Style**: We follow PEP 8. Please run a linter before submitting.
- **Commit Messages**: Use clear, descriptive commit messages. Start with a verb (e.g., "Add feature", "Fix bug").

Thank you for your contributions! 🚀
