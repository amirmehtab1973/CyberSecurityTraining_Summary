import streamlit as st
import pandas as pd
import os

from transformers import pipeline
import docx
import PyPDF2

# --- Configuration ---
MATERIALS_DIR = "materials"
LOG_FILE = "access_log.xlsx"

# --- Initialize summarization pipeline (using a free model) ---
@st.cache_resource
def get_summarizer():
    return pipeline("summarization", model="facebook/bart-large-cnn")

summarizer = get_summarizer()

# Create materials folder
import zipfile

with zipfile.ZipFile("materials.zip", 'r') as zip_ref:
    zip_ref.extractall()

# --- Utilities ---
def list_materials():
    if not os.path.exists(MATERIALS_DIR):
        os.makedirs(MATERIALS_DIR, exist_ok=True)
    return sorted([
        f for f in os.listdir(MATERIALS_DIR)
        if os.path.isfile(os.path.join(MATERIALS_DIR, f))
    ])

def read_text(file_path):
    """Extract text from supported files for summarization."""
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    elif ext == ".docx":
        doc = docx.Document(file_path)
        text = "\n".join(p.text for p in doc.paragraphs)
    elif ext == ".pdf":
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    return text.strip()

def summarize_text(text, max_chars=3000):
    """Summarize long text using the summarizer."""
    if not text:
        return "No preview or summary available for this file format."
    # Limit text length to avoid memory issues
    text = text[:max_chars]
    summary = summarizer(text, max_length=150, min_length=50, do_sample=False)
    return summary[0]['summary_text']

def record_access(name, email, material):
    if not name or not email:
        return False, "❌ Please enter both Name and Email."
    new_entry = pd.DataFrame([[name, email, material]],
                             columns=["Name", "Email", "Material"])
    if os.path.exists(LOG_FILE):
        existing = pd.read_excel(LOG_FILE)
        updated = pd.concat([existing, new_entry], ignore_index=True)
    else:
        updated = new_entry
    updated.to_excel(LOG_FILE, index=False)
    return True, f"✅ Access recorded for {name}."

# --- Streamlit App ---
st.set_page_config(page_title="Employee Training Portal", layout="wide")
st.title("📂 Employee Training Material Portal")
st.write("Enter your details, choose a training file, and view its summary before downloading.")

materials = list_materials()

# --- Form to collect user details ---
with st.form("access_form"):
    name = st.text_input("Full Name")
    email = st.text_input("Email Address")
    if not materials:
        st.info("No materials available. Contact the admin to upload files.")
        selected = None
    else:
        selected = st.selectbox("Select Training Material", materials)
    submit = st.form_submit_button("Record Access")

# --- After form submission ---
if submit and selected:
    success, msg = record_access(name, email, selected)
    if success:
        st.success(msg)

        # Display summary if possible
        file_path = os.path.join(MATERIALS_DIR, selected)
        ext = os.path.splitext(selected)[1].lower()
        if ext in [".txt", ".docx", ".pdf"]:
            with st.spinner("Generating summary..."):
                text = read_text(file_path)
                summary = summarize_text(text)
            st.subheader("📑 Training Material Summary")
            st.write(summary)
        else:
            st.info("Summary not available for this file format. You can still download it below.")

        # Download button
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                st.download_button(
                    label=f"⬇ Download '{selected}'",
                    data=f,
                    file_name=selected,
                    mime="application/octet-stream"
                )
        else:
            st.error("❌ File not found on the server.")
    else:
        st.error(msg)

# --- Admin Section ---
st.markdown("---")
st.subheader("📊 Admin: View and Download Access Log")
if os.path.exists(LOG_FILE):
    df = pd.read_excel(LOG_FILE)
    st.dataframe(df, use_container_width=True)
    with open(LOG_FILE, "rb") as f:
        st.download_button(
            label="⬇ Download Access Log",
            data=f,
            file_name=LOG_FILE,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("No access log available yet.")
