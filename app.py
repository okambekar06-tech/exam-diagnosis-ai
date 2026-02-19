import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import random

# ---------------- PAGE ----------------
st.set_page_config(page_title="Exam Diagnosis AI", layout="wide")

# ---------------- LOAD USERS ----------------
@st.cache_data
def load_users():
    return pd.read_csv("users.csv")

# ---------------- LOGIN ----------------
def authenticate(username, password):
    users = load_users()
    user = users[(users.username==username) & (users.password==password)]
    if not user.empty:
        return user.iloc[0].to_dict()
    return None

if "user" not in st.session_state:
    st.session_state.user=None

# ---------------- LOGIN SCREEN ----------------
if st.session_state.user is None:

    st.title("📘 Exam Diagnosis AI Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        user = authenticate(u,p)
        if user:
            st.session_state.user=user
            st.rerun()
        else:
            st.error("Invalid credentials")

    st.stop()

user = st.session_state.user

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.write(f"👋 {user['fullname']}")
    st.write(f"Role: {user['role']}")
    if st.button("Logout"):
        st.session_state.user=None
        st.rerun()

# ---------------- PDF FUNCTION ----------------
def generate_pdf(student, questions, scores, max_marks, suggestions):

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    y = 800

    pdf.setFont("Helvetica",12)
    pdf.drawString(50,y,"Exam Diagnosis AI Report")
    y-=40
    pdf.drawString(50,y,f"Student: {student}")
    y-=30

    total=0
    total_max=0

    for q,s,m,sug in zip(questions,scores,max_marks,suggestions):
        pdf.drawString(50,y,f"{q}")
        y-=15
        pdf.drawString(70,y,f"Marks: {s}/{m}")
        y-=15
        pdf.drawString(70,y,f"Suggestion: {sug}")
        y-=25

        total+=s
        total_max+=m

    pdf.drawString(50,y,f"Final Score: {total}/{total_max}")
    pdf.save()
    buffer.seek(0)
    return buffer

# =====================================================
# 👨‍🏫 TEACHER PANEL
# =====================================================
if user["role"]=="teacher":

    st.title("👨‍🏫 Teacher Control Panel")

    tab1,tab2=st.tabs(["Blueprint Editor","Teacher Advice"])

    # ----- ADD QUESTIONS -----
    with tab1:

        df=pd.read_csv("blueprint.csv")

        q=st.text_input("Question")
        k=st.text_input("Keywords (comma separated)")
        m=st.number_input("Marks",1,20)
        s=st.text_area("Suggestion")

        if st.button("Add Question"):
            new=pd.DataFrame([[q,k,m,s]],
            columns=["question","keywords","marks","suggestion"])

            df=pd.concat([df,new],ignore_index=True)
            df.to_csv("blueprint.csv",index=False)
            st.success("Added ✅")

        st.dataframe(df)

    # ----- GLOBAL ADVICE -----
    with tab2:
        note=st.text_area("Advice for students")

        if st.button("Save Advice"):
            with open("teacher_note.txt","w") as f:
                f.write(note)
            st.success("Saved ✅")

# =====================================================
# 🎓 STUDENT PANEL
# =====================================================
else:

    st.title("🎓 Student Analysis")

    df=pd.read_csv("blueprint.csv")

    if df.empty:
        st.warning("Teacher has not added questions yet.")
        st.stop()

    uploaded=st.file_uploader("Upload Answer Sheet")

    if uploaded:

        st.image(uploaded,use_container_width=True)

        st.subheader("📊 Evaluation")

        scores=[]
        suggestions=[]

        for _,row in df.iterrows():

            score=random.randint(1,row["marks"])
            scores.append(score)
            suggestions.append(row["suggestion"])

            if score < row["marks"]*0.5:
                st.warning(f"{row['question']} → {row['suggestion']}")
            else:
                st.success(f"{row['question']} → Good")

        # ----- GRAPH -----
        fig=go.Figure()
        fig.add_bar(x=df["question"],y=scores,name="Student")
        fig.add_bar(x=df["question"],y=df["marks"],name="Max")

        st.plotly_chart(fig,use_container_width=True)

        # ----- TEACHER NOTE -----
        try:
            with open("teacher_note.txt") as f:
                st.info("Teacher Advice:\n"+f.read())
        except:
            pass

        # ----- PDF DOWNLOAD -----
        pdf=generate_pdf(
            user["fullname"],
            list(df["question"]),
            scores,
            list(df["marks"]),
            suggestions
        )

        st.download_button(
            "⬇ Download PDF Report",
            data=pdf,
            file_name="evaluation_report.pdf",
            mime="application/pdf"
        )