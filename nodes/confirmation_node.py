from langchain_core.messages import HumanMessage, AIMessage
from state import AgentState
import streamlit as st
from nodes.booking_node import execute_booking

def booking_confirmation_node(state: AgentState) -> AgentState:
    messages = state["messages"]
    user_message = ""

    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_message = msg.content.strip().lower()
            break

    pending_data = st.session_state.get("pending_booking_data")

    if not pending_data:
        return {
            "messages": [AIMessage(content="⚠️ No pending booking found.")],
            "current_intent": "error",
            "query_results": {},
            "next_action": "end",
            "booking_status": "failed"
        }

    if user_message in ["yes", "y", "confirm", "book"]:
        # Now actually book
        result = execute_booking(pending_data)

        st.session_state.pending_booking_data = None
        st.session_state.awaiting_booking_confirmation = False

        return {
            "messages": [AIMessage(content=result["message"])],
            "current_intent": "booking_done",
            "query_results": result,
            "next_action": "end",
            "booking_status": "confirmed"
        }

    elif user_message in ["no", "n", "cancel"]:
        st.session_state.pending_booking_data = None
        st.session_state.awaiting_booking_confirmation = False

        return {
            "messages": [AIMessage(content="❌ Booking cancelled.")],
            "current_intent": "booking_cancelled",
            "query_results": {},
            "next_action": "await_user",
            "booking_status": "cancelled"
        }

    else:
        return {
            "messages": [AIMessage(content="Please reply with YES to confirm or NO to cancel.")],
            "current_intent": "awaiting_confirmation",
            "query_results": {},
            "next_action": "await_user",
            "booking_status": "pending"
        }
