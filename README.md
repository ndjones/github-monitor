# GitHub Activity Monitor to Slack

This repository contains a GitHub Actions workflow and a Python script that runs daily to monitor activity across your GitHub repositories. It summarizes the activity (Pull Requests, Issues, Commits, Releases) into a formatted Slack message, with direct links back to the detailed reports/items on GitHub.

## Deployment

This tool is designed to run automatically via GitHub Actions. You just need to configure a few secrets.

### Prerequisites

1.  **GitHub Personal Access Token (PAT):** 
    *   Go to GitHub Settings -> Developer settings -> Personal access tokens -> Tokens (classic).
    *   Generate a new token with `repo` (for private repositories) and `read:org` (if monitoring an organization) scopes.
2.  **Slack Bot Token & Channel:**
    *   To create threaded messages, you need a full Slack App instead of a simple webhook.
    *   Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new App from scratch.
    *   Under **OAuth & Permissions**, add the `chat:write` scope to Bot Token Scopes.
    *   Install the App to your workspace. This will generate a **Bot User OAuth Token** (starts with `xoxb-`).
    *   Find the ID of the channel you want to post in (e.g., right-click the channel name in Slack -> View channel details -> copy the Channel ID at the bottom, looks like `C12345678`).

### Setup

1.  Clone or create this repository as a **private** repository in your GitHub account.
2.  Go to your new repository's **Settings** -> **Secrets and variables** -> **Actions**.
3.  Add the following **Repository secrets**:
    *   `GH_TOKEN`: Your Personal Access Token.
    *   `SLACK_BOT_TOKEN`: Your Slack Bot User OAuth Token (`xoxb-...`).
    *   `SLACK_CHANNEL`: The Channel ID where the bot should post (e.g., `C12345678`).
4.  (Optional) Add **Repository variables** (under the "Variables" tab next to "Secrets"):
    *   `TARGET_ORG`: If you want to monitor a specific organization (e.g., `my-company-org`). If omitted, it will default to the user account of the `GH_TOKEN` owner.
    *   `DAYS_BACK`: The number of days to look back for activity (defaults to 1).

### How it works

The GitHub Action (`.github/workflows/daily-digest.yml`) runs on a schedule (e.g., every weekday morning) and executes `monitor.py`. 

The script uses the GitHub API to fetch:
*   Merged Pull Requests
*   Open Pull Requests
*   Closed Issues
*   New Issues
*   Releases

It then formats this data into a Slack message, including Markdown links back to the specific PRs, issues, and repositories on GitHub, so your team can easily click through for the full details.
