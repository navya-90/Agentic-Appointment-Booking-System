from typing import Literal
from langgraph.graph import StateGraph, END
from state import AgentState
from langgraph.checkpoint.memory import MemorySaver
from nodes.booking_node import process_booking_node, select_slot_node
from nodes.supervisor_node import supervisor_node
from nodes.information_node import information_node
from nodes.confirmation_node import booking_confirmation_node
import streamlit as st

def create_appointment_bot_graph():
    """Create and configure the LangGraph workflow"""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("information", information_node)
    workflow.add_node("select_slot", select_slot_node)
    workflow.add_node("process_booking", process_booking_node)
    workflow.add_node("booking_confirmation", booking_confirmation_node)
    
    def route_after_supervisor(state: AgentState) -> Literal["information", "select_slot", "process_booking", "booking_confirmation", "end"]:
        current_intent = state.get("current_intent", "")
        # We pull the next_action decided by the supervisor_node
        next_action = state.get("next_action")

        if st.session_state.get("awaiting_booking_confirmation", False):
            return "booking_confirmation"
        
        if next_action == "end" or current_intent == "end":
            return "end"
        elif current_intent == "select_slot":
            return "select_slot"
        elif next_action == "check_first" or current_intent == "check_availability":
            return "information"
        elif current_intent == "provide_patient_info" or next_action == "process_booking":
            return "process_booking"
        elif current_intent == "awaiting_confirmation":
            return "booking_confirmation"
        else:
            return "information"
    
    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "information": "information",
            "select_slot": "select_slot",
            "process_booking": "process_booking",
            "booking_confirmation": "booking_confirmation",
            "end": END
        }
    )
    
    workflow.add_edge("information", END)
    workflow.add_edge("select_slot", END)
    workflow.add_edge("process_booking", END)
    workflow.add_edge("booking_confirmation", END)
    workflow.set_entry_point("supervisor")

    # Create checkpointer for state persistence
    memory = MemorySaver()
    
    return workflow.compile(checkpointer=memory)