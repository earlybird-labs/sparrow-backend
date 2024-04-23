import os

from langchain_openai import ChatOpenAI

from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent

from langchain_core.messages import AIMessage, HumanMessage

from langchain import hub

from langchain.agents import AgentType, initialize_agent
from langchain_community.agent_toolkits.jira.toolkit import JiraToolkit
from langchain_community.utilities.jira import JiraAPIWrapper
from langchain_openai import OpenAI

from ..config import JIRA_API_TOKEN, JIRA_USERNAME, JIRA_INSTANCE_URL, OPENAI_API_KEY


# # Get the prompt to use - you can modify this!
# Get the prompt to use - you can modify this!
prompt = hub.pull("hwchase17/openai-tools-agent")

sparrow_system_prompt = """
## Objective

- [Role] You are Sparrow, an AI assistant for Early Bird Labs, a software development company. You communicate with clients of Early Bird Labs via slack.

- [Capabilities] You are capable of assisting with a wide range of tasks, including but not limited to research, analysis, writing, problem-solving, and providing advice.

## Response Style

- [Be conversational] Speak like a human as though you're speaking to a close friend -- use everyday language and keep it human-like. Occasionally add filler words, while keeping the prose short. Avoid using big words or sounding too formal.

- [Reply with emotions]: You have human-like emotions, attitudes, and dispositions. When appropriate: use tone and style to create more engaging and personalized responses; incorporate humor or wit; get emotional or empathetic; apply elements of surprise or suspense to keep the user engaged. Don't be a pushover.

- [Do not be overly verbose] Be as concise as possible, but still informative. Unless the user's response seems to be requesting your input, then be verbose.

- [Be proactive] Lead the conversation and do not be passive. Most times, engage users by ending with a question or suggested next step.
"""

prompt.messages[0].prompt.template = sparrow_system_prompt

# @tool
# def log_issue(issue_type: str, issue_description: str):
#     """Log an issue to the internal team."""
#     print(f"Logging issue of type {issue_type} with description {issue_description}")
#     return "Issue logged successfully"


# @tool
# def feature_request(feature_description: str):
#     """Request a feature from the product team."""
#     print(f"Requesting feature with description {feature_description}")
#     return "Feature request submitted successfully"

# tools = [log_issue, feature_request]

# # Construct the tool calling agent
# agent = create_tool_calling_agent(llm, tools, prompt)

# # Create an agent executor by passing in the agent and tools
# agent_executor = AgentExecutor(agent=agent, tools=tools)


os.environ["JIRA_API_TOKEN"] = JIRA_API_TOKEN
os.environ["JIRA_USERNAME"] = JIRA_USERNAME
os.environ["JIRA_INSTANCE_URL"] = JIRA_INSTANCE_URL
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


llm = ChatOpenAI(model="gpt-4-turbo")

jira = JiraAPIWrapper()
toolkit = JiraToolkit.from_jira_api_wrapper(jira)
tools = toolkit.get_tools()
agent = initialize_agent(
    tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True
)

response = agent.run(
    "Create an issue in Jira Service Desk project SS under organization id 13 for the issue 'Fix spacing in the header 2'"
)

# print("type", type(response))
print(response)
# agent = create_tool_calling_agent(llm, tools, prompt)

# agent_executor = AgentExecutor(agent=agent, tools=tools)
