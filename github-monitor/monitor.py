import os
import logging
from datetime import datetime, timedelta
from github import Github
from github.GithubException import RateLimitExceededException
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Try to load .env for local testing (fails silently in CI)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Read configuration from environment variables
GITHUB_TOKEN = os.environ.get("GH_TOKEN")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL")
TARGET_ORG = os.environ.get("TARGET_ORG", "")
DAYS_BACK = int(os.environ.get("DAYS_BACK", 1))

if not GITHUB_TOKEN:
    logger.error("No GH_TOKEN provided. Cannot authenticate with GitHub.")
    exit(1)

if not SLACK_BOT_TOKEN or not SLACK_CHANNEL:
    logger.error("SLACK_BOT_TOKEN and SLACK_CHANNEL must be provided to post threaded messages.")
    exit(1)

def get_recent_activity(g: Github, target: str, since: datetime) -> dict:
    """Fetches activity for the specified target and returns it grouped by repository."""
    
    logger.info(f"Fetching activity for {'organization ' + target if target else 'authenticated user'} since {since.isoformat()}...")
    
    repos_activity = {}
    
    if target:
        try:
            entity = g.get_organization(target)
            repos = entity.get_repos()
        except Exception as e:
            logger.error(f"Failed to fetch organization '{target}': {e}")
            return repos_activity
    else:
        entity = g.get_user()
        repos = entity.get_repos()
        
    for repo in repos:
        try:
            repo_data = {
                "url": repo.html_url,
                "prs_merged": [],
                "prs_opened": [],
                "issues_closed": [],
                "issues_opened": [],
                "releases": []
            }
            has_activity = False
            
            # --- PULL REQUESTS ---
            prs = repo.get_pulls(state='all', sort='updated', direction='desc')
            for pr in prs:
                if pr.updated_at < since:
                    break
                    
                if pr.merged and pr.merged_at and pr.merged_at >= since:
                    repo_data["prs_merged"].append(pr)
                    has_activity = True
                elif pr.created_at >= since and not pr.merged:
                    repo_data["prs_opened"].append(pr)
                    has_activity = True

            # --- ISSUES ---
            issues = repo.get_issues(state='all', since=since)
            for issue in issues:
                if issue.pull_request: # Skip PRs
                    continue
                    
                if issue.closed_at and issue.closed_at >= since:
                    repo_data["issues_closed"].append(issue)
                    has_activity = True
                elif issue.created_at >= since:
                    repo_data["issues_opened"].append(issue)
                    has_activity = True
                    
            # --- RELEASES ---
            releases = repo.get_releases()
            for release in releases:
                if release.created_at < since:
                    break
                
                if release.created_at >= since:
                    repo_data["releases"].append(release)
                    has_activity = True
                    
            if has_activity:
                repos_activity[repo.full_name] = repo_data

        except RateLimitExceededException:
            logger.warning("GitHub API rate limit exceeded. Sleeping or aborting...")
            raise
        except Exception as e:
            logger.warning(f"Error processing repository {repo.full_name}: {e}")
            continue

    logger.info(f"Finished fetching activity. Found activity in {len(repos_activity)} repositories.")
    return repos_activity

def build_repo_blocks(repo_name: str, repo_data: dict) -> list:
    """Builds the Slack Block Kit message for a single repository's activity."""
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Repository: {repo_name}",
                "emoji": True
            }
        }
    ]
    
    def add_items(title: str, emoji: str, items: list, formatter: callable):
        if not items:
            return
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *{title}*"
            }
        })
        
        lines = [formatter(item) for item in items]
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(lines)[:2900]
            }
        })
    
    add_items("New Releases / Tags", "🚀", repo_data["releases"], 
              lambda r: f"  • <{r.html_url}|{r.title or r.tag_name}> by @{r.author.login if r.author else 'System'}")
    
    add_items("Merged Pull Requests", "🔀", repo_data["prs_merged"], 
              lambda pr: f"  • <{pr.html_url}|#{pr.number} {pr.title}> by @{pr.user.login}")
              
    add_items("Opened Pull Requests", "📝", repo_data["prs_opened"], 
              lambda pr: f"  • <{pr.html_url}|#{pr.number} {pr.title}> by @{pr.user.login}")
              
    add_items("Closed Issues", "✅", repo_data["issues_closed"], 
              lambda i: f"  • <{i.html_url}|#{i.number} {i.title}> by @{i.user.login}")
              
    add_items("New Issues", "🐛", repo_data["issues_opened"], 
              lambda i: f"  • <{i.html_url}|#{i.number} {i.title}> by @{i.user.login}")
              
    # Add link to repo pulse
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"📈 <{repo_data['url']}/pulse|View full '{repo_name}' activity report on GitHub>"
            }
        ]
    })
    
    return blocks

def post_threaded_summary(repos_activity: dict, target: str, days_back: int):
    """Posts a parent message and then replies in a thread for each active repository."""
    client = WebClient(token=SLACK_BOT_TOKEN)
    
    target_display = f"organization *{target}*" if target else "your repositories"
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    if not repos_activity:
        logger.info("No activity to report. Sending single quiet message.")
        try:
            client.chat_postMessage(
                channel=SLACK_CHANNEL,
                text=f"📊 *GitHub Daily Digest ({date_str})*\n\n📭 _No significant activity found across {target_display} in the last {days_back} day(s)._"
            )
        except SlackApiError as e:
            logger.error(f"Error posting to Slack: {e.response['error']}")
        return

    # 1. Post Parent Message
    parent_text = f"📊 *GitHub Daily Digest ({date_str})*\nFound recent activity in *{len(repos_activity)} repositories* across {target_display}.\n\n👇 See the thread below for repository-specific details!"
    
    try:
        logger.info("Posting parent message...")
        response = client.chat_postMessage(
            channel=SLACK_CHANNEL,
            text=parent_text
        )
        thread_ts = response["ts"]
        logger.info(f"Parent message posted. Thread TS: {thread_ts}")
        
        # 2. Post thread replies for each repository
        for repo_name, repo_data in repos_activity.items():
            logger.info(f"Posting thread reply for {repo_name}...")
            blocks = build_repo_blocks(repo_name, repo_data)
            
            # Use text as a fallback string for notifications
            client.chat_postMessage(
                channel=SLACK_CHANNEL,
                thread_ts=thread_ts,
                text=f"Activity report for {repo_name}",
                blocks=blocks
            )
            
        logger.info("Successfully posted all thread replies!")
        
    except SlackApiError as e:
        logger.error(f"Error posting to Slack API: {e.response['error']}")

def main():
    g = Github(GITHUB_TOKEN)
    now = datetime.utcnow()
    since = now - timedelta(days=DAYS_BACK)
    
    repos_activity = get_recent_activity(g, TARGET_ORG, since)
    post_threaded_summary(repos_activity, TARGET_ORG, DAYS_BACK)

if __name__ == "__main__":
    main()
