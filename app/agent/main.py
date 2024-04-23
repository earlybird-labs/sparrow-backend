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

# Only get the first 3 tools (JQL Query, Get Projects, Create Issue)
tools = toolkit.get_tools()


agent = initialize_agent(
    tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True
)

agent_input = """
Here's a detailed Jira ticket in markdown for the Rescue Ring feature: \\ Title: Implement Rescue Ring Feature \\ Description: \\ **Objective:** To develop a discreet activation feature within the app that allows users to simulate an incoming phone call. The feature, named Rescue Ring, will enable users to exit uncomfortable or unsafe situations by providing a plausible excuse without attracting undue attention. These are the requirements and suggested functionalities: \\ - **Discreet Activation Mechanism:** Users should be able to trigger the Rescue Ring discreetly. Possible activation methods include a specific button sequence, a gesture, or a voice command. \\ - **Fake Call Simulation:** Upon activation, the app will simulate an incoming call. This includes customization options such as caller name, ringtone, and vibration pattern to ensure the call seems genuine. \\ - **Emergency Contact Notification:** Optionally send a notification to a predetermined emergency contact with the user's location and a brief alert message. \\ - **Background Audio Recording:** Start recording audio in the background once the Rescue Ring is activated to document the environment, which could be helpful if later review is necessary. \\ Acceptance Criteria: \\ - The feature must be easily accessible and must operate reliably under different conditions. \\ - The activation method must be intuitive yet secure to prevent accidental triggers. \\ - The user interface for feature setup must be user-friendly and integrate seamlessly with the rest of the app's design. \\ - Ensure privacy compliance with audio recording and sharing of user data. \\ Priority: High \\ Labels: safety_features, user_privacy, emergency_response \\ This structure provides a clear and comprehensive overview to guide the development team in implementing the Rescue Ring feature effectively.
"""

response = agent.run(
    f"Create an issue in project THRD with the following details: {agent_input}"
)

# print("type", type(response))
print(response)
# agent = create_tool_calling_agent(llm, tools, prompt)

# agent_executor = AgentExecutor(agent=agent, tools=tools)
