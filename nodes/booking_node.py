from langchain_core.messages import HumanMessage, AIMessage
from state import AgentState
from extractJson import extract_json_from_text
import streamlit as st
import re
from tools import check_availability
from datetime import datetime
from database import save_appointments_to_db

print(
    "Before slot select, session slots:",
    st.session_state.get("available_slots", [])
)


def select_slot_node(state: AgentState) -> AgentState:
    """Handle slot selection from multiple available options."""
    messages = state["messages"]
    user_message = ""
    
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) and not msg.content.startswith("["):
            user_message = msg.content
            break
    
    # Extract date and time from user message
    slot_match = re.search(r'(\d{2}-\d{2}-\d{4} \d{2}:\d{2})', user_message)
    
    if slot_match:
        selected_slot = slot_match.group(1)
        
        # Check if this slot is in our available slots
        available_slots = st.session_state.get('available_slots', [])

        print("User selected:", repr(selected_slot))
        print("Available slots:", [repr(s) for s in available_slots])

        
        if selected_slot in available_slots:
            # Parse the selected slot
            date, time = selected_slot.split(" ", 1)
            
            # Get doctor name from context
            doctor_name = st.session_state.get('current_doctor', 'john doe')
            
            # Check availability for this specific slot
            result = check_availability.invoke({
                "doctor_name": doctor_name,
                "date": date,
                "time": time
            })
            
            if result["status"] == "available":
                st.session_state.last_available_slot = result
                st.session_state.awaiting_slot_selection = False
                st.session_state.awaiting_patient_info = True
                
                response_text = f"""✅ **Slot Selected!**

**Doctor:** Dr. {result['doctor'].title()}
**Specialization:** {result['specialization'].replace('_', ' ').title()}
**Date & Time:** {result['date_slot']}

💡 **Please provide patient information to book:**
1. Patient Name
2. Patient Age
3. Patient Phone Number

Example: "John Smith, age 35, phone 555-1234" """
                
                return {
                    "messages": [AIMessage(content=response_text)],
                    "current_intent": "slot_selected",
                    "query_results": result,
                    "next_action": "await_user",
                    "booking_status": "slot_selected"
                }
            else:
                response_text = f"❌ **Slot {selected_slot} is no longer available.**\n\n"
                response_text += "Please select another slot from the available options."
                
                return {
                    "messages": [AIMessage(content=response_text)],
                    "current_intent": "select_slot",
                    "query_results": {},
                    "next_action": "await_user",
                    "booking_status": "retry"
                }
        else:
            response_text = f"❌ **Slot {selected_slot} not found in available options.**\n\n"
            response_text += "Please select a slot from the list shown above."
            
            return {
                "messages": [AIMessage(content=response_text)],
                "current_intent": "select_slot",
                "query_results": {},
                "next_action": "await_user",
                "booking_status": "retry"
            }
    
    else:
        response_text = "❌ **Please specify a slot in the format: DD-MM-YYYY HH:MM**\n\n"
        response_text += "Example: '05-08-2024 08:00'"
        
        return {
            "messages": [AIMessage(content=response_text)],
            "current_intent": "select_slot",
            "query_results": {},
            "next_action": "await_user",
            "booking_status": "retry"
        }



def process_booking_node(state: AgentState) -> AgentState:
    """Booking Node: Handles appointment booking."""
    messages = state["messages"]
    
    user_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage) and not msg.content.startswith("["):
            user_message = msg.content
            break
    
    
    llm = st.session_state.llm

    # Check if this is just saying "yes" to booking
    if user_message.lower().strip() in ['yes', 'y', 'sure', 'ok', 'okay', 'confirm']:
        response_text = "💡 **Please provide patient information:**\n\n"
        response_text += "1. Patient Name\n2. Patient Age\n3. Patient Phone Number\n\n"
        response_text += "Example: 'John Smith, age 35, phone 555-1234'"
        
        return {
            "messages": [AIMessage(content=response_text)],
            "current_intent": "provide_patient_info",
            "query_results": {},
            "next_action": "process_booking",
            "booking_status": "info_required"
        }

    # Extract patient info from message
    extraction_prompt = f"""Extract patient information from this message: "{user_message}"

IMPORTANT: Return ONLY a valid JSON object, nothing else. No explanations, no additional text.

JSON format:
{{
    "patient_name": "string or null",
    "patient_age": "integer or null",
    "patient_phone": "string or null"
}}

Examples:
User: "John Smith, 35, 555-1234"
Response: {{"patient_name": "John Smith", "patient_age": 35, "patient_phone": "555-1234"}}

User: "Book for Alice, age 28, phone 555-9876"
Response: {{"patient_name": "Alice", "patient_age": 28, "patient_phone": "555-9876"}}

User: "Patient name is Robert Brown, he is 45 years old, contact 555-1111"
Response: {{"patient_name": "Robert Brown", "patient_age": 45, "patient_phone": "555-1111"}}

Now extract from: "{user_message}"
Response:"""
    
    extraction_response = llm.invoke([HumanMessage(content=extraction_prompt)])
    
    try:
        patient_info = extract_json_from_text(extraction_response.content)
        
        # Get the last available slot
        available_slot = st.session_state.get('last_available_slot', {})
        
        if not available_slot or available_slot.get("status") != "available":
            return {
                "messages": [AIMessage(content="⚠️ No available slot found. Please check availability first.")],
                "current_intent": "error",
                "query_results": {},
                "next_action": "end",
                "booking_status": "failed"
            }
        
        # Validate patient info
        missing_fields = []
        if not patient_info.get("patient_name"):
            missing_fields.append("patient name")
        if not patient_info.get("patient_age"):
            missing_fields.append("patient age")
        if not patient_info.get("patient_phone"):
            missing_fields.append("patient phone number")
        
        if missing_fields:
            response_text = f"❌ **Missing information:** {', '.join(missing_fields)}\n\n"
            response_text += "Please provide all required information:\n"
            response_text += "1. Patient Name\n2. Patient Age\n3. Patient Phone Number\n\n"
            response_text += "Example: 'John Smith, age 35, phone 555-1234'"
            
            return {
                "messages": [AIMessage(content=response_text)],
                "current_intent": "provide_patient_info",
                "query_results": {},
                "next_action": "process_booking",
                "booking_status": "info_required"
            }
        
        # Extract date and time from date_slot
        date_slot = available_slot.get("date_slot", "")
        if " " in date_slot:
            date, time = date_slot.split(" ", 1)
        else:
            date, time = date_slot, ""
        
        
        # Save patient info temporarily
        st.session_state.pending_booking_data = {
            "doctor_name": available_slot.get("doctor", ""),
            "date": date,
            "time": time,
            "patient_name": patient_info["patient_name"],
            "patient_age": patient_info["patient_age"],
            "patient_phone": patient_info["patient_phone"]
        }

        st.session_state.awaiting_booking_confirmation = True
        st.session_state.awaiting_patient_info = False
        st.session_state.awaiting_slot_selection = False

        response_text = f"""📝 **Please confirm your booking**

        Doctor: Dr. {available_slot.get("doctor").title()}
        Date & Time: {date} {time}

        Patient: {patient_info["patient_name"]}  
        Age: {patient_info["patient_age"]}  
        Phone: {patient_info["patient_phone"]}

        Are you sure you want to book this appointment?

        Type **YES** to confirm  
        Type **NO** to cancel
        """

        return {
            "messages": [AIMessage(content=response_text)],
            "current_intent": "awaiting_confirmation",
            "query_results": {},
            "next_action": "await_user",
            "booking_status": "pending"
        }

    except Exception as e:
        return {
            "messages": [AIMessage(content=f"⚠️ Error processing booking: {str(e)}")],
            "current_intent": "error",
            "query_results": {},
            "next_action": "end",
            "booking_status": "failed"
        }

def execute_booking(pending_data):
    """Execute the actual booking after human approval"""
    try:
        df = st.session_state.df
        doctor_name = pending_data["doctor_name"].lower().strip()
        date_slot = f"{pending_data['date']} {pending_data['time']}"
        
        slot_mask = (df['doctor_name'] == doctor_name) & (df['date_slot'] == date_slot)
        
        if not df[slot_mask].empty:
            slot_info = df[slot_mask].iloc[0]
            
            if slot_info['is_available']:
                confirmation_number = f"APPT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                df.loc[slot_mask, 'is_available'] = False
                df.loc[slot_mask, 'patient_to_attend'] = pending_data["patient_name"]
                df.loc[slot_mask, 'patient_age'] = pending_data["patient_age"]
                df.loc[slot_mask, 'patient_phone'] = pending_data["patient_phone"]
                df.loc[slot_mask, 'confirmation_number'] = confirmation_number
                st.session_state.df = df
                
                # Persist to database
                save_appointments_to_db(df)

                # Clear state
                st.session_state.last_available_slot = None
                st.session_state.awaiting_patient_info = False
                st.session_state.awaiting_slot_selection = False
                st.session_state.available_slots = None
                
                return {
                    "status": "booked",
                    "confirmation_number": confirmation_number,
                    "doctor": doctor_name.title(),
                    "specialization": slot_info['specialization'],
                    "date_slot": date_slot,
                    "patient": pending_data["patient_name"],
                    "patient_age": pending_data["patient_age"],
                    "patient_phone": pending_data["patient_phone"],
                    "message": f"✅ Appointment successfully booked for {pending_data['patient_name']} with Dr. {doctor_name.title()} on {date_slot}"
                }
        
        return {
            "status": "unavailable",
            "message": "❌ Slot no longer available"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Error: {str(e)}"
        }
