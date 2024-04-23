from blockkit import Section, Button, MarkdownText


def generate_issue_prompt_blocks():
    blocks = [
        Section(
            text=MarkdownText(text="Do you want help creating a Jira issue?")
        ).build(),
        {
            "type": "actions",
            "elements": [
                Button(
                    text="Yes",
                    style="primary",
                    value="yes",
                    action_id="create_jira_yes",
                ).build(),
                Button(
                    text="No", style="danger", value="no", action_id="create_jira_no"
                ).build(),
            ],
        },
    ]
    return blocks
