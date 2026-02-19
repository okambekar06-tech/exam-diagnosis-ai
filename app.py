import streamlit as st
from google.cloud import vision
from PIL import Image
import plotly.graph_objects as go

# ---------------- PAGE SETUP ----------------
st.set_page_config(page_title="Exam Diagnosis AI", layout="wide")

st.title("📘 Exam Diagnosis AI System")

# ---------------- SECURITY SYSTEM ----------------
if "teacher_locked" not in st.session_state:
    st.session_state.teacher_locked = False

if "teacher_key" not in st.session_state:
    st.session_state.teacher_key = "Omkar@12"   # change if you want

# ---------------- MODE SELECT ----------------
mode = st.sidebar.radio(
    "Select Mode",
    ["Student Mode", "Teacher Mode (Locked)"]
)

# ---------------- GOOGLE OCR ----------------
def read_handwriting_google(uploaded_file):
    client = vision.ImageAnnotatorClient()
    content = uploaded_file.read()
    image = vision.Image(content=content)

    response = client.document_text_detection(image=image)
    texts = response.text_annotations

    if texts:
        return texts[0].description
    return ""


# =====================================================
# 👨‍🏫 TEACHER MODE
# =====================================================
if mode == "Teacher Mode (Locked)":

    entered_key = st.sidebar.text_input(
        "Enter Teacher Key",
        type="password"
    )

    if entered_key != st.session_state.teacher_key:
        st.warning("Teacher access locked 🔒")
        st.stop()

    st.header("👨‍🏫 Teacher Blueprint Setup")

    if st.session_state.teacher_locked:
        st.success("Blueprint already locked ✅")
        st.stop()

    question = st.text_input("Enter Question")

    keywords = st.text_area(
        "Enter Keywords (comma separated)",
        "queue, enqueue, dequeue, front, rear"
    )

    total_marks = st.slider("Total Marks", 5, 20, 10)

    if st.button("Save & Lock Blueprint 🔒"):
        st.session_state["question"] = question
        st.session_state["keywords"] = keywords.split(",")
        st.session_state["marks"] = total_marks
        st.session_state.teacher_locked = True
        st.success("Blueprint Saved & Locked ✅")


# =====================================================
# 👨‍🎓 STUDENT MODE
# =====================================================
else:

    st.header("👨‍🎓 Student Analysis")

    if "keywords" not in st.session_state:
        st.warning("Teacher has not created blueprint yet.")
        st.stop()

    has_kt = st.radio(
        "Did you get KT in this subject?",
        ["Yes", "No"]
    )

    uploaded_file = st.file_uploader(
        "Upload Answer Sheet",
        type=["jpg", "png", "jpeg"]
    )

    if uploaded_file:

        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        st.image(image, use_column_width=True)

        with st.spinner("Reading handwriting using AI..."):
            uploaded_file.seek(0)
            text = read_handwriting_google(uploaded_file)

        st.subheader("Extracted Text")
        text = st.text_area("Edit if needed:", text, height=200)

        # -------- ANALYSIS --------
        keywords = [k.strip().lower() for k in st.session_state["keywords"]]

        found = [k for k in keywords if k in text.lower()]
        missing = list(set(keywords) - set(found))

        concept_score = int((len(found) / len(keywords)) * 100)

        writing_score = min(len(text.split()) + text.count(".") * 10, 100)

        predicted_marks = int(
            (concept_score / 100) * st.session_state["marks"]
        )

        # -------- GRAPH --------
        fig = go.Figure(data=[
            go.Bar(
                x=["Concept Understanding", "Writing Quality"],
                y=[concept_score, writing_score]
            )
        ])

        fig.update_layout(
            template="plotly_dark",
            title="Performance Overview"
        )

        st.plotly_chart(fig, use_container_width=True)

        # -------- RESULTS --------
        st.subheader("📊 Evaluation Result")

        st.write(
            f"### Predicted Marks: {predicted_marks}/{st.session_state['marks']}"
        )

        if has_kt == "Yes":
            st.error("Priority: Concept Improvement Required")
        else:
            st.success("Priority: Writing Enhancement")

        # -------- MISSING CONCEPTS --------
        st.subheader("🚨 Missing Concepts")

        if missing:
            for m in missing:
                st.write("❌", m)
        else:
            st.write("✅ All important concepts covered")

        # -------- SUGGESTIONS --------
        st.subheader("✅ Suggestions")

        if has_kt == "Yes":
            st.write("• Revise fundamental concepts carefully.")
            st.write("• Practice university past papers.")
            st.write("• Include keywords and definitions.")
        else:
            st.write("• Improve answer structure.")
            st.write("• Write in points and headings.")
            st.write("• Add examples & diagrams.")