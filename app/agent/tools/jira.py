import os

from atlassian import Jira, ServiceDesk

# Set the `jira_token`, `jira_email`, `jira_url` environment variables.

jira_token = os.getenv("JIRA_TOKEN")
jira_email = os.getenv("JIRA_EMAIL")
jira_url = os.getenv("JIRA_URL")

# Create a ServiceDesk instance
sd = ServiceDesk(jira_url, username=jira_email, password=jira_token, cloud=True)

SERVICE_DESK_ID = "11"


def create_attachment(
    issue_id_or_key: str, filename: str, public: bool = True, comment: str = None
):
    sd.create_attachment(
        SERVICE_DESK_ID, issue_id_or_key, filename, public=public, comment=comment
    )


def create_customer_request(text: str):
    pass
