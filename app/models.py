# models.py

from typing import List, Optional
from pydantic import BaseModel, Field
import enum


class RequestType(enum.Enum):
    feature_request = "feature_request"
    bug_report = "bug_report"
    general_request = "general_request"
    ai_conversation = "ai_conversation"
    conversation = "conversation"


class AIResponse(BaseModel):
    content: str = Field(
        description="The assistant's response to the user's message.",
    )


class IssueType(enum.Enum):
    new_feature = "new_feature"
    bug = "bug"
    improvement = "improvement"


class IssueTicket(BaseModel):
    type: IssueType = Field(description="The type of the issue ticket.")
    summary: str = Field(description="The summary of the issue ticket.")
    description: str = Field(description="A detailed description of the issue ticket.")
    action_items: List[str] = Field(
        description="The action items for the issue ticket."
    )


class Node(BaseModel):
    id: str = Field(description="The unique identifier of the node.")
    label: str = Field(description="The label or name of the node.")
    description: str = Field(description="A detailed description of the node.")


class Edge(BaseModel):
    source: str = Field(description="The ID of the source node.")
    target: str = Field(description="The ID of the target node.")
    predicate: str = Field(
        description="The label or description of the relationship between the nodes."
    )


class EntityGraph(BaseModel):
    nodes: List[Node] = Field(description="The list of nodes in the entity graph.")
    edges: List[Edge] = Field(
        description="The list of edges connecting the nodes in the entity graph."
    )

    def add_node(self, node_id: str, node_label: str):
        self.nodes.append(Node(id=node_id, label=node_label))

    def add_edge(self, source_id: str, target_id: str, edge_label: str):
        self.edges.append(Edge(source=source_id, target=target_id, label=edge_label))
