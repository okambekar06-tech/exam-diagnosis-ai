import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from google.cloud import vision
from google.oauth2 import service_account

st.set_page_config(page_title="Exam Diagnosis AI", layout="wide")

# ---------------- GOOGLE VISION ----------------
cred_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
credentials = service_account.Credentials.from_service_account_info(cred_dict)
vision_client = vision.ImageAnnotatorClient(credentials=credentials)

# ---------------- USERS ----------------
@st.cache_data
def load_users():
    return pd.read_csv("users.csv")

def authenticate(u,p):
    users=load_users()
    user=users[(users.username==u)&(users.password==p)]
    if not user.empty:
        return user.iloc[0].to_dict()
    return None

if "user" not in st.session_state:
    st.session_state.user=None

# ---------------- LOGIN ----------------
if st.session_state.user is None:

    st.title("📘 Exam Diagnosis AI Login")

    u=st.text_input("Username")
    p=st.text_input("Password",type="password")

    if st.button("Login"):
        user=authenticate(u,p)
        if user:
            st.session_state.user=user
            st.rerun()
        else:
            st.error("Invalid login")

    st.stop()

user=st.session_state.user

with st.sidebar:
    st.write(f"👋 {user['fullname']}")
    st.write(f"Role: {user['role']}")
    if st.button("Logout"):
        st.session_state.user=None
        st.rerun()

# ---------------- OCR ----------------
def read_handwriting(file):
    content=file.read()
    image=vision.Image(content=content)
    response=vision_client.document_text_detection(image=image)
    return response.full_text_annotation.text

# ---------------- ANALYSIS ----------------
def analyze_answer(text, keywords, marks, kt_mode):

    kw=[k.strip().lower() for k in keywords.split(",")]
    matched=[k for k in kw if k in text.lower()]
    gaps=list(set(kw)-set(matched))

    concept_score=(len(matched)/len(kw))*100 if kw else 0
    writing_score=min(len(text.split())/80*10,10)
    obtained=round((concept_score/100)*marks,2)

    # PRIORITY ORDER
    priority=[]

    if kt_mode:
        priority.append("Revise entire syllabus starting from core definitions")
        priority.append("Practice previous university papers daily")

    if concept_score < 60:
        priority.append("Strengthen conceptual understanding")

    if gaps:
        priority.append("Focus on missing keywords and diagrams")

    if writing_score < 5:
        priority.append("Improve answer structure and explanation")

    if not priority:
        priority.append("Maintain consistency and revise weekly")

    return obtained, concept_score, writing_score, gaps, priority

# ---------------- PDF ----------------
def generate_pdf(student, questions, scores, max_marks):

    buffer=io.BytesIO()
    pdf=canvas.Canvas(buffer,pagesize=A4)

    y=800
    pdf.drawString(50,y,"Exam Diagnosis AI Report")
    y-=40
    pdf.drawString(50,y,f"Student: {student}")
    y-=30

    total=sum(scores)
    total_max=sum(max_marks)

    for q,s,m in zip(questions,scores,max_marks):
        pdf.drawString(50,y,q)
        y-=15
        pdf.drawString(70,y,f"Marks: {s}/{m}")
        y-=25

    pdf.drawString(50,y,f"Final Score: {total}/{total_max}")
    pdf.save()
    buffer.seek(0)
    return buffer

# =====================================================
# TEACHER PANEL
# =====================================================
if user["role"]=="teacher":

    st.title("👨‍🏫 Teacher Control Panel")

    df=pd.read_csv("blueprint.csv")

    q=st.text_input("Question")
    k=st.text_input("Keywords")
    m=st.number_input("Marks",1,20)
    s=st.text_area("Suggestion")

    if st.button("Add Question"):
        new=pd.DataFrame([[q,k,m,s]],
        columns=["question","keywords","marks","suggestion"])
        df=pd.concat([df,new],ignore_index=True)
        df.to_csv("blueprint.csv",index=False)
        st.success("Added")

    st.dataframe(df)

# =====================================================
# STUDENT PANEL
# =====================================================
else:

    st.title("🎓 Student Analysis")

    # ⭐ KT QUESTION AFTER LOGIN
    kt_choice = st.radio(
        "Did you get KT / Fail in this subject?",
        ["No, I want improvement", "Yes, I have KT / Failed"]
    )

    kt_mode = True if kt_choice.startswith("Yes") else False

    df=pd.read_csv("blueprint.csv")

    uploaded=st.file_uploader("Upload Answer Sheet")

    if uploaded:

        st.image(uploaded,use_container_width=True)

        with st.spinner("Reading handwriting..."):
            text=read_handwriting(uploaded)

        st.subheader("Extracted Text")
        st.write(text)

        scores=[]
        questions=list(df["question"])

        for _,row in df.iterrows():

            marks,concept,writing,gaps,priority=analyze_answer(
                text,row["keywords"],row["marks"],kt_mode
            )

            scores.append(marks)

            st.markdown(f"### {row['question']}")
            st.metric("Concept Score",f"{concept:.1f}%")
            st.metric("Writing Score",f"{writing:.1f}/10")

            if gaps:
                for g in gaps:
                    st.warning(f"Missing Concept: {g}")

            st.subheader("📌 Priority Improvement Order")
            for i,p in enumerate(priority,1):
                st.write(f"{i}. {p}")

        fig=go.Figure()
        fig.add_bar(x=questions,y=scores,name="Student")
        fig.add_bar(x=questions,y=df["marks"],name="Max")
        st.plotly_chart(fig,use_container_width=True)

        pdf=generate_pdf(
            user["fullname"],
            questions,
            scores,
            list(df["marks"])
        )

        st.download_button(
            "⬇ Download PDF Report",
            pdf,
            "evaluation_report.pdf",
            "application/pdf"
        )