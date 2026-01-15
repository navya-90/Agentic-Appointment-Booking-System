from langchain_core.messages import HumanMessage, AIMessage
from state import AgentState
from tools import check_availability
from extractJson import extract_json_from_text
import streamlit as st
from tools import check_availability
from datetime import datetime, timedelta

def information_node(state: AgentState) -> AgentState:
    """Information Node: Queries doctor availability."""
    messages = state["messages"]
    user_message = ""
    
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) and not msg.content.startswith("["):
            user_message = msg.content
            break
    
    llm = st.session_state.llm
    
    extraction_prompt = f"""Extract booking parameters from this user message: "{user_message}"

IMPORTANT: Return ONLY a valid JSON object, nothing else. No explanations, no additional text.

JSON format:
{{
    "doctor_name": "string or null",
    "specialization": "string or null", 
    "date": "string in DD-MM-YYYY format or null",
    "time": "string in HH:MM format or null"
}}

Examples:
User: "Is Dr. Jane Doe available on 8 August 2024 at 8 PM?"
Response: {{"doctor_name": "jane doe", "specialization": null, "date": "08-08-2024", "time": "20:00"}}

User: "Book with general dentist on 5 Aug 2024 8 AM"
Response: {{"doctor_name": null, "specialization": "general_dentist", "date": "05-08-2024", "time": "08:00"}}

User: "Check availability for John Doe tomorrow at 10 AM"
Response: {{"doctor_name": "john doe", "specialization": null, "date": "06-08-2024", "time": "10:00"}}

Now extract from: "{user_message}"
Response:"""

    extraction_response = llm.invoke([HumanMessage(content=extraction_prompt)])
    
    try:
        params = extract_json_from_text(extraction_response.content)
        print("🔍 Extracted params:", params)

        if params.get("date") is None and "tomorrow" in user_message.lower():
            tomorrow = datetime.now() + timedelta(days=1)
            params["date"] = tomorrow.strftime("%d-%m-%Y")

        
        result = check_availability.invoke(params)
        print("🧪 Availability result:", result)


        # Store doctor info for context
        if params.get("doctor_name"):
            st.session_state.current_doctor = params["doctor_name"]
        
         # Store in session for potential booking
        if result["status"] == "available":
            st.session_state.last_available_slot = result
            
            # Check if user wants to book
            booking_check_prompt = f"""Does this user want to BOOK an appointment or just CHECK availability?
User message: "{user_message}"

If they mention booking, scheduling, making appointment, or similar, respond with "BOOK".
If they're just asking if available, checking, or similar, respond with "CHECK".

Respond with ONLY "BOOK" or "CHECK"."""
            
            booking_response = llm.invoke([HumanMessage(content=booking_check_prompt)])
            wants_to_book = "BOOK" in booking_response.content.upper()
            
            if wants_to_book:
                response_text = f"""✅ **Available!**

**Doctor:** Dr. {result['doctor'].title()}
**Specialization:** {result['specialization'].replace('_', ' ').title()}
**Date & Time:** {result['date_slot']}

💡 **Please provide patient information to book:**
1. Patient Name
2. Patient Age
3. Patient Phone Number

Example: "John Smith, age 35, phone 555-1234" """
                
                st.session_state.awaiting_patient_info = True
                st.session_state.awaiting_slot_selection = False
            else:
                response_text = f"""✅ **Available!**

**Doctor:** Dr. {result['doctor'].title()}
**Specialization:** {result['specialization'].replace('_', ' ').title()}
**Date & Time:** {result['date_slot']}

💡 **Would you like to book this appointment?** If yes, please provide patient information:
1. Patient Name
2. Patient Age  
3. Patient Phone Number

Example: "Yes, book for John Smith, age 35, phone 555-1234" """
                
                st.session_state.awaiting_patient_info = False
                st.session_state.awaiting_slot_selection = False
            
        elif result["status"] == "multiple_available":
            response_text = f"📋 **{result['message']}:**\n\n"
            for i, slot in enumerate(result["slots"][:8], 1):
                response_text += f"  • {slot}\n"
            
            # Store slots for selection
            st.session_state.available_slots = result["slots"][:8]
            st.session_state.awaiting_slot_selection = True
            st.session_state.awaiting_patient_info = False
            
            response_text += "\n💡 **Please specify which slot you'd like (e.g., '05-08-2024 08:00').**"
            
        elif result["status"] == "not_found":
            response_text = f"❌ **Unavailable**\n\n{result['message']}"

            if result.get("alternatives"):
                # 🔴 THIS IS THE MISSING PART
                st.session_state.available_slots = result["alternatives"]
                st.session_state.awaiting_slot_selection = True
                st.session_state.awaiting_patient_info = False

                response_text += f"\n\n**Alternative available slots:**\n"
                for slot in result["alternatives"]:
                    response_text += f"  • {slot}\n"
            st.session_state.awaiting_patient_info = False
            st.session_state.awaiting_slot_selection = False
            
        else:
            response_text = f"ℹ️ {result['message']}"
            st.session_state.awaiting_patient_info = False
            st.session_state.awaiting_slot_selection = False
        
        return {
            "messages": [AIMessage(content=response_text)],
            "current_intent": state["current_intent"],
            "query_results": result,
            "next_action": "await_user",
            "booking_status": state.get("booking_status", "")
        }
        
    except Exception as e:
        error_msg = f"⚠️ Error: {str(e)[:100]}\n\n"
        error_msg += "Please try being more specific. Example: 'Is Dr. John Doe available on 08-08-2024 at 10:00?'"
        
        return {
            "messages": [AIMessage(content=error_msg)],
            "current_intent": state["current_intent"],
            "query_results": {},
            "next_action": "await_user",
            "booking_status": state.get("booking_status", "")
        }