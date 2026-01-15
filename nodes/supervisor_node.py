from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from state import AgentState
import streamlit as st
import re

def supervisor_node(state: AgentState) -> AgentState:
    """Supervisor Node: Orchestrates workflow and routes to appropriate nodes."""
    messages = state["messages"]
    last_message = messages[-1].content.lower() if messages else ""
    query_results = state.get("query_results", {})
    
    llm = st.session_state.llm
    if not llm:
        return {
            "messages" :[AIMessage(content="⚠️ Please configure your Groq API key in the sidebar.")],
            "current_intent" :"error",
            "next_action" :"end",
            "query_results" :{},
            "booking_status" :""
        }

    # Awaiting booking confirmation
    if st.session_state.get("awaiting_booking_confirmation", False):
        return {
            "messages": [],
            "current_intent": "awaiting_confirmation",
            "next_action": "booking_confirmation",
            "query_results": query_results,
            "booking_status": state.get("booking_status", "")
        }


    # Check if we're awaiting slot selection
    if st.session_state.get('awaiting_slot_selection', False):
        # Check if user message looks like a date/time slot
        if re.search(r'\d{2}-\d{2}-\d{4} \d{2}:\d{2}', last_message):
            return {
                "messages": [],
                "current_intent": "select_slot",
                "next_action": "select_slot",
                "query_results": query_results,
                "booking_status": state.get("booking_status", "")
            }
    
    # Check if we're awaiting patient info
    if st.session_state.get('awaiting_patient_info', False):
        # Check if user is providing patient info
        info_keywords = ['name', 'age', 'phone', 'patient', 'years old', 'contact', 'book for']
        has_patient_info = any(keyword in last_message.lower() for keyword in info_keywords)
        
        if has_patient_info or any(char.isdigit() for char in last_message):
            return {
                "messages": [],
                "current_intent": "provide_patient_info",
                "next_action": "process_booking",
                "query_results": query_results,
                "booking_status": state.get("booking_status", "")
            }

    system_prompt = """You are a supervisor agent for an appointment booking system.

Analyze user requests and determine their intent. Respond with ONLY the intent name.

User intents:
- "check_availability": User wants to know if a doctor/slot is available
- "book_appointment": User wants to book an appointment (mentions booking, scheduling, making appointment)
- "provide_patient_info": User is providing patient information for booking
- "select_slot": User is selecting a specific time slot
- "end": Task is complete

Examples:
- "Is Dr. John available?" -> check_availability
- "Book appointment" -> book_appointment
- "John Smith, 35, 555-1234" -> provide_patient_info
- "05-08-2024 08:00" -> select_slot
- "Thanks, bye" -> end

Now analyze: "{user_message}"
Respond with ONLY the intent name.""".replace("{user_message}", last_message)

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=last_message)
    ])
    
    intent = response.content.strip().lower()
    
    # Check for patient info in message
    info_keywords = ['name', 'age', 'phone', 'patient', 'years old', 'contact']
    has_patient_info = any(keyword in last_message.lower() for keyword in info_keywords) and any(char.isdigit() for char in last_message)
    
    if "select" in intent or re.search(r'\d{2}-\d{2}-\d{4} \d{2}:\d{2}', last_message):
        current_intent = "select_slot"
        next_action = "select_slot"
    elif has_patient_info:
        current_intent = "provide_patient_info"
        next_action = "process_booking"
    elif "book" in intent or "appointment" in intent or "schedule" in intent:
        current_intent = "book_appointment"
        next_action = "check_first"
    elif "end" in intent or "thank" in intent or "bye" in intent:
        current_intent = "end"
        next_action = "end"
    else:
        current_intent = "check_availability"
        next_action = "information"
    
    return {
        "messages": [],
        "current_intent": current_intent,
        "next_action": next_action,
        "query_results": query_results,
        "booking_status": state.get("booking_status", "")
    }

    
    