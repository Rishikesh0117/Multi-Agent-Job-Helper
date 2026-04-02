import requests
import re 

# LLM CALL (Ollama - Phi3)

def call_llm(prompt):
    url = "http://localhost:11434/api/generate"

    data = {
        "model": "phi3",
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 120
        }
    }

    response = requests.post(url, json=data)
    return response.json()["response"]


# TOOL 1: Question Generator

def generate_question(role, level="medium"):
    prompt = f"""
You are an interviewer.

Task: Generate exactly ONE interview question.

Role: {role}
Difficulty: {level}

STRICT RULES:
- Output ONLY the question
- No numbering
- No explanation
- Max 15 words
"""

    response = call_llm(prompt)
    return response.strip().split("\n")[0].replace("Question:", "").strip()


# TOOL 2: Answer Evaluator

def evaluate_answer(question, answer):
    prompt = f"""
You are a strict interview evaluator.

Evaluate the answer based ONLY on correctness.

Question: {question}
Answer: {answer}

Return EXACTLY in this format:

Score: <number>/10
Strength: <short phrase>
Weakness: <short phrase>
Improvement: <short phrase>

Rules:
- Score must be between 0 and 10
- Do NOT add extra text
"""

    response = call_llm(prompt)

    lines = response.strip().split("\n")

    # Default structure (fallback)
    result = {
        "Score": "Score: 5/10",
        "Strength": "Strength: Basic attempt",
        "Weakness": "Weakness: Missing details",
        "Improvement": "Improvement: Add more explanation"
    }

    for line in lines:
        if "Score:" in line:
            result["Score"] = line.strip()
        elif "Strength:" in line:
            result["Strength"] = line.strip()
        elif "Weakness:" in line:
            result["Weakness"] = line.strip()
        elif "Improvement:" in line:
            result["Improvement"] = line.strip()

    final = "\n".join([
        result["Score"],
        result["Strength"],
        result["Weakness"],
        result["Improvement"]
    ])

    return "\n".join(fix_score(final).split("\n")[:4])

def fix_score(text):
    match = re.search(r"Score:\s*(\d+)", text)
    if match:
        score = int(match.group(1))
        if score > 10:
            score = 10
        return re.sub(r"Score:.*", f"Score: {score}/10", text)
    return text


def summarize_performance(history):
    import re

    scores = []
    strengths = []
    weaknesses = []

    for item in history:
        eval_text = item["evaluation"]

        # Extract score
        match = re.search(r"Score:\s*(\d+)", eval_text)
        if match:
            scores.append(int(match.group(1)))

        # Extract strengths & weaknesses
        for line in eval_text.split("\n"):
            if "Strength:" in line:
                strengths.append(line.replace("Strength:", "").strip())
            elif "Weakness:" in line:
                weaknesses.append(line.replace("Weakness:", "").strip())

    avg_score = sum(scores) / len(scores) if scores else 0

    # Simple summary logic
    if avg_score >= 7:
        level = "Good"
    elif avg_score >= 4:
        level = "Average"
    else:
        level = "Needs Improvement"

    return avg_score, level, strengths[:2], weaknesses[:2]

# =========================
# AGENT (ReAct Style)
# =========================
def interview_agent():
    print("=== AI Interview Agent ===\n")

    role = input("Enter role (e.g., Python Developer): ")
    level = input("Enter difficulty (easy/medium/hard): ")

    history = []

    for i in range(3):
        print(f"\n--- Question {i+1} ---")

        # Thought
        print("\n[Agent Thought] Generating question based on role...")

        # Action
        question = generate_question(role, level)

        print("\n[Agent Action] Asking question:")
        print("Q:", question)

        # User input
        answer = input("\nYour Answer: ")

        # Thought
        print("\n[Agent Thought] Evaluating answer...")

        # Action
        evaluation = evaluate_answer(question, answer)

        # Observation (PRINT ONLY ONCE)
        print("\n[Agent Observation]")
        print(evaluation)

        # Store memory
        history.append({
            "question": question,
            "evaluation": evaluation
        })

    # ===== FINAL SUMMARY =====
    print("\n=== FINAL PERFORMANCE SUMMARY ===")

    avg_score, level, strengths, weaknesses = summarize_performance(history)

    print(f"Average Score: {avg_score:.1f}/10")
    print(f"Performance Level: {level}")

    print("\nKey Strengths:")
    for s in strengths:
        print("-", s)

    print("\nKey Weaknesses:")
    for w in weaknesses:
        print("-", w)

# =========================
# RUN
# =========================
if __name__ == "__main__":
    interview_agent()