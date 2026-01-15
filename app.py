import streamlit as st
import pandas as pd
import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from workflow import create_appointment_bot_graph
from dotenv import load_dotenv
from database import init_database, load_chat_history, load_appointments_from_db, save_appointments_to_db, save_chat_message
from datetime import datetime

load_dotenv()

# Initialize database
init_database()

# Generate or retrieve session ID
if 'session_id' not in st.session_state:
    st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}"

if 'chat_history' not in st.session_state:
    # Try to load from database
    loaded_history = load_chat_history(st.session_state.session_id)
    st.session_state.chat_history = loaded_history if loaded_history else []

if 'df' not in st.session_state:
    # Try to load from database first
    df_from_db = load_appointments_from_db()
    
    if df_from_db is not None:
        st.session_state.df = df_from_db
    else:
        # Fallback to CSV if database fails
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        CSV_PATH = os.path.join(BASE_DIR, "data", "doctor_availability.csv")
        st.session_state.df = pd.read_csv(CSV_PATH)
        st.session_state.df['doctor_name'] = st.session_state.df['doctor_name'].str.lower().str.strip()
        st.session_state.df['specialization'] = st.session_state.df['specialization'].str.lower().str.strip()

        # Save initial data to database
        save_appointments_to_db(st.session_state.df)


if 'graph_thread_id' not in st.session_state:
    st.session_state.graph_thread_id = f"thread_{datetime.now().strftime('%Y%m%d%H%M%S')}"

if 'pending_booking_data' not in st.session_state:
    st.session_state.pending_booking_data = None

if "available_slots" not in st.session_state:
    st.session_state.available_slots = []

if 'last_available_slot' not in st.session_state:
    st.session_state.last_available_slot = None

if 'awaiting_patient_info' not in st.session_state:
    st.session_state.awaiting_patient_info = False

if 'awaiting_slot_selection' not in st.session_state:
    st.session_state.awaiting_slot_selection = False

if 'current_doctor' not in st.session_state:
    st.session_state.current_doctor = None

if "awaiting_booking_confirmation" not in st.session_state:
    st.session_state.awaiting_booking_confirmation = False


# Initialize LLM from environment variable
if 'llm' not in st.session_state:
    api_key = os.getenv('GROQ_API_KEY')
    if api_key:
        try:
            st.session_state.llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=0,
                max_retries=2,
                api_key=api_key
            )
            st.session_state.api_configured = True
        except Exception as e:
            st.session_state.llm = None
            st.session_state.api_configured = False
            st.session_state.api_error = str(e)
    else:
        st.session_state.llm = None
        st.session_state.api_configured = False
        st.session_state.api_error = "GROQ_API_KEY not found in .env file"

def main():
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/doctor-male.png", width=80)
        st.title("⚙️ System Status")
        
        # API Configuration Status
        if st.session_state.api_configured:
            st.markdown('<div class="success-box">✅ API Configured</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="error-box">❌ API Not Configured</div>', unsafe_allow_html=True)
            st.error(f"Error: {st.session_state.get('api_error', 'Unknown error')}")
            st.info("💡 Please add GROQ_API_KEY to your .env file")
        
        st.divider()
        
        st.subheader("📊 System Stats")
        df = st.session_state.df
        total_slots = len(df)
        available = df['is_available'].sum()
        booked = total_slots - available
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Slots", total_slots)
            st.metric("Available", available)
        with col2:
            st.metric("Booked", booked)
            st.metric("Doctors", df['doctor_name'].nunique())
        
        st.divider()
        
        st.subheader("👨‍⚕️ Available Doctors")
        doctors = df.groupby(['doctor_name', 'specialization']).size().reset_index()
        for _, row in doctors.iterrows():
            st.write(f"**Dr. {row['doctor_name'].title()}**")
            st.write(f"_{row['specialization'].replace('_', ' ').title()}_")
            st.write("---")
        
        st.divider()

         # Show pending human decision
        if st.session_state.pending_booking_data:
            st.markdown('<div class="pending-box">⏳ Awaiting Human Decision</div>', unsafe_allow_html=True)
        
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            # Also clear from database
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (st.session_state.session_id,))
            conn.commit()
            conn.close()
            st.rerun()
        
        if st.button("🔄 Reset Appointments"):
            # Reset the DataFrame to original state
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            CSV_PATH = os.path.join(BASE_DIR, "data", "doctor_availability.csv")
            
            st.session_state.df = pd.read_csv(CSV_PATH)
            st.session_state.df['doctor_name'] = st.session_state.df['doctor_name'].str.lower().str.strip()
            st.session_state.df['specialization'] = st.session_state.df['specialization'].str.lower().str.strip()

            # Save to database
            save_appointments_to_db(st.session_state.df)
            
            # Clear HITL state
            st.session_state.pending_booking_data = None
            st.session_state.last_available_slot = None
            st.session_state.awaiting_patient_info = False
            st.session_state.awaiting_slot_selection = False
            st.session_state.available_slots = None

            st.success("✅ Appointments reset!")
            st.rerun()
    
    # Main content
    st.markdown('<div class="main-header">🏥 AI Appointment Bot</div>', unsafe_allow_html=True)
    st.markdown("**Your intelligent assistant for booking medical appointments**")
    
    # Show error if API not configured
    if not st.session_state.api_configured:
        st.error("⚠️ System not ready. Please configure GROQ_API_KEY in your .env file and restart the application.")
        st.stop()

    # Show HITL interruption if awaiting decision
    if st.session_state.pending_booking_data:
        pending_data = st.session_state.pending_booking_data
        
        st.markdown(f"""
        <div class="interruption-box">
            <h3>⚠️ Human Approval Required</h3>
            <p><strong>Patient:</strong> {pending_data['patient_name']} (Age: {pending_data['patient_age']})</p>
            <p><strong>Phone:</strong> {pending_data['patient_phone']}</p>
            <p><strong>Doctor:</strong> Dr. {pending_data['doctor_name'].title()}</p>
            <p><strong>Date & Time:</strong> {pending_data['date']} at {pending_data['time']}</p>
            <p><strong>Approve this booking?</strong></p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Approve Booking", type="primary", use_container_width=True):
                result = handle_human_decision("yes")
                st.session_state.chat_history.append({"role": "bot", "content": result["message"]})
                save_chat_message(st.session_state.session_id, "bot", result["message"])
                st.rerun()
        
        with col2:
            if st.button("❌ Reject Booking", type="secondary", use_container_width=True):
                result = handle_human_decision("no")
                st.session_state.chat_history.append({"role": "bot", "content": result["message"]})
                save_chat_message(st.session_state.session_id, "bot", result["message"])
                st.rerun()
        
        st.divider()
    
    # Quick action buttons
    st.subheader("🚀 Quick Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📅 Check Availability"):
            example = "Is Dr. Jane Doe available on 08-08-2024 at 20:00?"
            st.session_state.chat_history.append({"role": "user", "content": example})
            st.rerun()
    
    with col2:
        if st.button("🔍 Search by Specialization"):
            example = "Show me available slots for general dentist"
            st.session_state.chat_history.append({"role": "user", "content": example})
            st.rerun()
    
    with col3:
        if st.button("✅ Book Appointment"):
            example = "Please check and book an appointment with general dentist on 05-08-2024 at 08:00 for patient John Smith"
            st.session_state.chat_history.append({"role": "user", "content": example})
            st.rerun()
    
    st.divider()
    
    # Chat container
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message user-message">👤 <strong>You:</strong><br>{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message bot-message">🤖 <strong>Bot:</strong><br>{message["content"]}</div>', unsafe_allow_html=True)
    
    # Chat input
    user_input = st.chat_input("Type your message here... (e.g., 'Is Dr. Jane Doe available on 08-08-2024 at 20:00?')")
    
    if user_input:

        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        # Save to database
        save_chat_message(st.session_state.session_id, "user", user_input)
        
        # Process with bot
        with st.spinner("🤔 Processing..."):
            try:
                graph = create_appointment_bot_graph()
                
                # Get thread ID from session state
                thread_id = st.session_state.graph_thread_id
                
                # Create initial state
                initial_state = {
                    "messages": [HumanMessage(content=user_input)],
                    "current_intent": "",
                    "query_results": {},
                    "booking_status": "",
                    "next_action": ""
                }
                
                # Invoke graph with checkpointer
                config = {"configurable": {"thread_id": thread_id}}
                result = graph.invoke(initial_state, config)
                
                # Extract bot response
                bot_response = ""
                for message in result["messages"]:
                    if isinstance(message, AIMessage) and not message.content.startswith("[Supervisor]"):
                        bot_response = message.content
                
                if bot_response:
                    st.session_state.chat_history.append({"role": "bot", "content": bot_response})
                    save_chat_message(st.session_state.session_id, "bot", bot_response)
                else:
                    fallback = "I'm processing your request. How can I help you further?"
                    st.session_state.chat_history.append({"role": "bot", "content": fallback})
                    save_chat_message(st.session_state.session_id, "bot", fallback)
                
            except Exception as e:
                error_msg = f"⚠️ Error: {str(e)}"
                st.session_state.chat_history.append({"role": "bot", "content": error_msg})
                save_chat_message(st.session_state.session_id, "bot", error_msg)
        
        st.rerun()
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: gray; font-size: 0.9rem;'>
        💡 <strong>Tip:</strong> Try asking "Is Dr. John Doe available?" or "Book an appointment with a general dentist"
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()