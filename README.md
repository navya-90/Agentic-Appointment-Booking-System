# 🧠 Agentic Appointment Booking Assistant

A multi-agent, stateful conversational system that allows users to check doctor availability, select time slots, provide patient details, confirm bookings, and store appointments persistently using SQLite.

Built using **LangGraph**, **Streamlit**, and **LLM APIs**, this project demonstrates workflow orchestration, agent-based routing, and reliable state management for real-world conversational applications.

---

## 🚀 Features

- 🤖 Multi-agent architecture with a **Supervisor node** for workflow orchestration  
- 🗓️ Doctor availability checking with alternative slot suggestions  
- ⏰ Dynamic slot selection  
- 🧾 Patient information extraction using structured JSON output from LLMs  
- ✅ User-driven booking confirmation (YES / NO flow)  
- 💾 Persistent storage using SQLite database  
- 🔁 Robust state recovery across Streamlit reruns  

---

## 🏗️ Architecture Overview

User → Streamlit UI
↓
Supervisor Node (LangGraph)
↓
┌─────────────────────────────┐
| Information Node |
| Select Slot Node |
| Process Booking Node |
| Booking Confirmation Node |
└─────────────────────────────┘
↓
SQLite Database


Each node is a specialized agent responsible for a specific task, and the Supervisor node dynamically routes user messages to the correct agent based on conversation state and intent.

---

## 🧩 Tech Stack

- **Python**
- **LangGraph** – Multi-agent workflow orchestration
- **Streamlit** – Interactive UI
- **SQLite** – Persistent database
- **LLM APIs** – Intent detection and structured data extraction

---

## 📁 Project Structure

.
├── app.py
├── workflow.py
├── state.py
├── tools.py
├── database.py
├── extractJson.py
├── appointments.db # (ignored by git)
├── nodes/
│ ├── supervisor_node.py
│ ├── information_node.py
│ ├── booking_node.py
│ └── confirmation_node.py
├── data/
├── requirements.txt
├── .env # (ignored by git)
├── .gitignore
└── README.md

---

## ⚙️ Setup Instructions

1. Clone the repository:
git clone <your-repo-url>
cd <your-repo> 

2. Create and activate virtual environment:
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows

3. Install dependencies:
pip install -r requirements.txt

4. Add your API keys in .env:
GROQ_API_KEY=your_key_here

5. Run the app:
streamlit run app.py
