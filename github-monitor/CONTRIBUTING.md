# Contributing to GitHub Activity Monitor

Welcome! We are excited that you want to contribute to the GitHub Activity Monitor. This document outlines the process for setting up your local environment, making changes, and submitting them for review.

## Architecture Overview

This project is a stateless Python script (`monitor.py`) that runs automatically via GitHub Actions (`.github/workflows/daily-digest.yml`). 
*   It uses `PyGithub` to fetch data from the GitHub API.
*   It uses `slack_sdk` to post threaded messages to a Slack channel.
*   It does not currently maintain state or save files to the repository between runs.

## Local Development Setup

To work on this project locally, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-org/github-slack-agent.git
    cd github-slack-agent
    ```

2.  **Set up a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    Create a `.env` file in the root directory and add your development tokens. The script uses `python-dotenv` to load these automatically during local runs.
    ```env
    GH_TOKEN=ghp_your_personal_access_token
    SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
    SLACK_CHANNEL=C12345678
    TARGET_ORG=your-test-organization # Optional
    DAYS_BACK=1 # Optional, defaults to 1
    ```

5.  **Run the script locally:**
    ```bash
    python monitor.py
    ```

## Adding Features

If you want to add new integrations (like Microsoft Teams or Discord) or add statefulness (like saving daily reports to a `reports/` folder), please consider the following:

1.  **Modularity:** Keep the data-fetching logic (`get_recent_activity`) separate from the formatting/posting logic.
2.  **Dependencies:** If you add a new library, make sure to add it to `requirements.txt`.
3.  **Statelessness:** If you propose adding state (saving files to the repo), please open an Issue to discuss the design first.

## Submitting Changes

1.  **Create a branch:** Create a new branch for your feature or bugfix (e.g., `feature/add-llm-summary` or `fix/slack-formatting`).
2.  **Test your changes:** Run the script locally using your `.env` file to ensure the Slack messages look correct and the GitHub API is queried properly.
3.  **Open a Pull Request:** Push your branch and open a Pull Request against the `main` branch. 
4.  **Review:** Provide a clear description of your changes in the PR. Include screenshots of the Slack output if you modified the formatting!

Thank you for contributing!