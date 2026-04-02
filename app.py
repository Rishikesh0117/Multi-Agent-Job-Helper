import streamlit as st
import requests
import re
import ast
from pypdf import PdfReader
import google.generativeai as genai
import os
from dotenv import load_dotenv
from main import generate_question, evaluate_answer

# =========================
# SETUP
# =========================
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("❌ GEMINI_API_KEY not found in .env file")
    st.stop()

genai.configure(api_key=api_key)
gemini_model = genai.GenerativeModel("gemini-3-flash-preview")

# =========================
# MODE SELECTOR (FIXED)
# =========================
st.title("🤖 Multi-Agent Career Assistant")

mode = st.sidebar.selectbox(
    "Choose Mode",
    ["Interview Agent", "Resume Analyzer"]
)

# =========================
# RESUME AGENT FUNCTIONS
# =========================
def read_pdf(file):
    text = ""
    pdf = PdfReader(file)
    for page in pdf.pages:
        text += page.extract_text() or ""
    return text


def extract_skills(text):
    prompt = f"""
Extract ONLY skills as a Python list.

Example:
["python", "sql", "machine learning"]

Text:
{text}
"""
    try:
        response = gemini_model.generate_content(prompt)
        return ast.literal_eval(response.text.strip())
    except:
        return []


def normalize(skill):
    return skill.lower().replace("-", "").replace(" ", "")


def compare_skills(resume, jd):
    resume_norm = [normalize(s) for s in resume]

    matched = []
    missing = []

    for skill in jd:
        norm_skill = normalize(skill)

        if any(norm_skill in r or r in norm_skill for r in resume_norm):
            matched.append(skill)
        else:
            missing.append(skill)

    return matched, missing

def calculate_score(matched, jd):
    if len(jd) == 0:
        return 0

    return round((len(matched) / len(jd)) * 100, 2)

def get_suggestions(resume_skills, jd_skills, missing, score):
    prompt = f"""
You are an expert career coach.

Analyze the resume against the job description.

Resume Skills: {resume_skills}
Job Skills: {jd_skills}
Missing Skills: {missing}
Match Score: {score}%

Give structured suggestions:

1. Missing Skills to Learn:
- Key missing skills

2. Resume Improvements:
- Improve wording, bullet points, clarity

3. Project Suggestions:
- Projects based on missing skills

4. ATS Optimization Tips:
- Keywords, formatting, resume optimization

Keep it clear and practical.
"""
    response = gemini_model.generate_content(prompt)
    return response.text


# =========================
# INTERVIEW AGENT UI
# =========================
if mode == "Interview Agent":

    st.header("🎤 Interview Preparation")

    if "step" not in st.session_state:
        st.session_state.step = 0
        st.session_state.history = []
        st.session_state.question = ""

    if st.session_state.step == 0:
        role = st.text_input("Role")
        level = st.selectbox("Difficulty", ["easy", "medium", "hard"])

        if st.button("Start Interview"):
            st.session_state.role = role
            st.session_state.level = level
            st.session_state.step = 1

    elif st.session_state.step <= 3:

        if st.session_state.question == "":
            st.session_state.question = generate_question(
                st.session_state.role,
                st.session_state.level
            )

        st.subheader(f"Question {st.session_state.step}")
        st.write(st.session_state.question)

        answer = st.text_area("Your Answer")

        if st.button("Submit Answer"):
            eval_result = evaluate_answer(st.session_state.question, answer)

            st.markdown("### 📊 Evaluation")
            st.text(eval_result)

            st.session_state.history.append(eval_result)
            st.session_state.question = ""
            st.session_state.step += 1

    else:
        st.success("✅ Interview Completed!")


# =========================
# RESUME ANALYZER UI
# =========================
else:

    st.header("📄 Resume Analyzer")

    file = st.file_uploader("Upload Resume", type=["pdf"])
    jd = st.text_area("Paste Job Description")

    if st.button("Analyze Resume"):

        if file and jd:

            with st.spinner("Analyzing resume..."):

                resume_text = read_pdf(file)

                resume_skills = extract_skills(resume_text)
                jd_skills = extract_skills(jd)

                if not jd_skills:
                    st.warning("⚠️ Could not extract skills from JD. Try clearer description.")
                    score = 0
                else:
                    matched, missing = compare_skills(resume_skills, jd_skills)
                    score = calculate_score(matched, jd_skills)

                suggestions = get_suggestions(
                    resume_skills, jd_skills, missing if jd_skills else [], score
                )

            # 📊 RESULTS
            st.subheader("📊 Analysis Results")

            st.write("**Match Score:**", score, "%")

            if score >= 75:
                st.success("✅ Strong match!")
            elif score >= 50:
                st.warning("⚠️Decent Match — needs improvement.")
            else:
                st.error("❌ Low match — major improvements needed.")

            st.write("**Matched Skills:**", matched if jd_skills else [])
            st.write("**Missing Skills:**", missing if jd_skills else [])

            # 💡 IMPROVED SUGGESTIONS UI
            st.markdown("### 💡 Improvement Suggestions")
            st.markdown(suggestions)

        else:
            st.warning("⚠️ Upload resume and enter job description.")