
from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    current_intent: str
    query_results: dict
    booking_status: str
    next_action: str