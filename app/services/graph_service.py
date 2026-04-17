import os
from typing import Annotated, List, TypedDict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages

from app.utils.prompts import CHAT_ANALYSIS_SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# State Definition
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    # add_messages is a reducer that appends new messages to the existing list
    messages: Annotated[List[BaseMessage], add_messages]
    user_info: str
    memory_summary: str

# ---------------------------------------------------------------------------
# Graph Logic
# ---------------------------------------------------------------------------

def create_agent():
    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.4,
    )

    # Define the core node that calls the LLM
    async def call_model(state: AgentState):
        prompt = ChatPromptTemplate.from_messages([
            ("system", CHAT_ANALYSIS_SYSTEM_PROMPT + "\n\nUser Demographics:\n{user_info}\n\nUser Background:\n{memory_summary}"),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        chain = prompt | llm
        
        # We pass the full state context
        response = await chain.ainvoke({
            "messages": state["messages"],
            "user_info": state["user_info"],
            "memory_summary": state["memory_summary"]
        })
        
        return {"messages": [response]}

    # Build the graph
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", END)

    # Add memory persistence
    checkpointer = MemorySaver()
    
    return workflow.compile(checkpointer=checkpointer)

# Singleton instance
agent_app = create_agent()
