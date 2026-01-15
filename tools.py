from typing import Optional
from langchain_core.tools import tool
import streamlit as st
from datetime import datetime


@tool
def check_availability(doctor_name: Optional[str] = None, specialization: Optional[str] = None, 
                       date: Optional[str] = None, time: Optional[str] = None) -> dict:
    """Check doctor availability based on name, specialization, date, and time."""
    try:
        df = st.session_state.df
        
        if doctor_name:
            doctor_name = doctor_name.lower().strip()
        if specialization:
            specialization = specialization.lower().strip().replace(" ", "_")
        
        query_df = df.copy()
        
        if doctor_name:
            query_df = query_df[query_df['doctor_name'] == doctor_name]
        
        if specialization:
            query_df = query_df[query_df['specialization'] == specialization]
        
        if date and time:
            date_slot = f"{date} {time}"
            specific_slot = query_df[query_df['date_slot'] == date_slot]
            
            if not specific_slot.empty:
                result = specific_slot.iloc[0]
                if result['is_available']:
                    return {
                        "status": "available",
                        "doctor": result['doctor_name'],
                        "specialization": result['specialization'],
                        "date_slot": result['date_slot'],
                        "message": f"Dr. {result['doctor_name'].title()} is available on {date_slot}"
                    }
                else:
                    alternatives = query_df[query_df['is_available'] == True].head(3)
                    alt_slots = alternatives['date_slot'].tolist() if not alternatives.empty else []
                    
                    return {
                        "status": "unavailable",
                        "doctor": result['doctor_name'],
                        "specialization": result['specialization'],
                        "date_slot": result['date_slot'],
                        "message": f"Dr. {result['doctor_name'].title()} is not available on {date_slot}. Already booked for: {result['patient_to_attend']}",
                        "alternatives": alt_slots
                    }
            else:
                alternatives = query_df[query_df['is_available'] == True].head(3)
                alt_slots = alternatives['date_slot'].tolist() if not alternatives.empty else []
                
                return {
                    "status": "not_found",
                    "message": f"No slot found for the specified criteria",
                    "alternatives": alt_slots
                }
        
        available_slots = query_df[query_df['is_available'] == True]
        
        if not available_slots.empty:
            slots_list = available_slots['date_slot'].tolist()
            return {
                "status": "multiple_available",
                "slots": slots_list,
                "count": len(slots_list),
                "message": f"Found {len(slots_list)} available slots"
            }
        else:
            return {
                "status": "no_availability",
                "message": "No available slots found for the specified criteria"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error checking availability: {str(e)}"
        }


@tool
def book_appointment(
    doctor_name: str,
    date: str,
    time: str,
    patient_name: str,
    patient_age: int,
    patient_phone: str
) -> dict:
    """
    Book an appointment after user confirmation.
    No human-in-the-loop interrupt.
    """

    # Perform the booking directly
    df = st.session_state.df
    date_slot = f"{date} {time}"
    doctor_name = doctor_name.lower().strip()

    slot_mask = (df["doctor_name"] == doctor_name) & (df["date_slot"] == date_slot)

    if df[slot_mask].empty:
        return {
            "status": "unavailable",
            "message": "❌ Slot no longer available."
        }

    slot_info = df[slot_mask].iloc[0]

    if not slot_info["is_available"]:
        return {
            "status": "unavailable",
            "message": "❌ Slot already booked."
        }

    confirmation_number = f"APPT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    df.loc[slot_mask, "is_available"] = False
    df.loc[slot_mask, "patient_to_attend"] = patient_name
    df.loc[slot_mask, "patient_age"] = patient_age
    df.loc[slot_mask, "patient_phone"] = patient_phone
    df.loc[slot_mask, "confirmation_number"] = confirmation_number

    st.session_state.df = df

    return {
        "status": "booked",
        "confirmation_number": confirmation_number,
        "doctor": doctor_name.title(),
        "date_slot": date_slot,
        "patient": patient_name,
        "message": f"✅ Appointment booked successfully for {patient_name} with Dr. {doctor_name.title()} on {date_slot}"
    }

