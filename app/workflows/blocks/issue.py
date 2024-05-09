import json
from blockkit import Section, MarkdownText, PlainText, Divider


def generate_jira_issue_section(
    key, summary, description, status, issue_type, assignee, priority, url
):
    """
    Generate a Slack UI section block for a Jira issue with clickable summary and other details.

    :param summary: The summary of the issue.
    :param description: The description of the issue.
    :param status: The current status of the issue.
    :param issue_type: The type of the issue.
    :param assignee: The assignee of the issue.
    :param priority: The priority of the issue.
    :param url: The URL to the issue.
    :return: A list of block elements representing the issue in Slack's BlockKit format.
    """

    # Construct the fields for the section
    issue_details_fields = [
        MarkdownText(text="*Priority:*"),
        MarkdownText(text="*Assignee:*"),
        PlainText(text=priority),
        PlainText(text=assignee),
        MarkdownText(text="*Status:*"),
        MarkdownText(text="*Type:*"),
        PlainText(text=status),
        PlainText(text=issue_type),
    ]
    # Construct the section with the issue summary as a clickable link
    return Section(
        text=MarkdownText(text=f"<{url}|{key} - {summary}>\n{description}"),
        fields=issue_details_fields,
    )


def generate_jira_issues_section(issues):
    blocks = []
    for issue in issues:
        blocks.append(generate_jira_issue_section(**issue))
        if issue != issues[-1]:
            blocks.append(Divider())
    return blocks


if __name__ == "__main__":
    # Example usage:
    section = generate_jira_issue_section(
        key="ISSUE-123",
        summary="Implement new login feature",
        description="Implement OAuth login feature for the application.",
        status="In Progress",
        issue_type="Feature",
        assignee="John Doe",
        priority="High",
        url="https://jira.example.com/browse/ISSUE-123",
    )

    with open("issue.json", "w") as f:
        json.dump(section.build(), f)
