import openai, os, pdfplumber
import streamlit as st

RECRUITER_HEAD_MAX_TOKENS = 1200
RECRUITER_MAX_TOKENS = 400

def user_said(content, history):
    history.append({"role":"user", "content":content})

def assistant_said(content, history):
    history.append({"role":"assistant", "content":content})

def ask_chatgpt(user_content, messages, system=None, new_chat=False, max_tokens=256, only_response=False):

    return 'HEllo'

    messages = [] if new_chat else messages
    if system and new_chat:
        messages.append({"role":"system", "content":system})

    user_said(user_content, messages)

    response = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=messages,
      temperature=0,
      max_tokens=max_tokens,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0
    )
    response = response['choices'][0]['message']['content']

    if only_response:
        return response

    assistant_said(response, messages)

    return response, messages


def foo(question, resume_texts):
    recruiters_guide = create_recruiters_guide(len(resume_texts))
    recruiters_response = {}

    for recruiter in recruiters_guide:
        response = ask_recruiter(question, resume_texts, recruiters_guide[recruiter])
        response += f'Recruiter {recruiter} analyzing resumes {", ".join(recruiters_guide[recruiter])}:\n\n'

        with st.chat_message("assistant"):
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        recruiters_response[recruiter] = response


    response, messages = ask_head_recruiter(question, recruiters_guide, recruiters_response)
    response += f'Head Recruiter:\n\n'

    with st.chat_message("assistant"):
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})


def create_recruiters_guide(num_resumes):
    count = 0
    recruiter = 0
    recruiters_guide = {}

    for i_resume in range(num_resumes):

        if count == 3:
            count = 0
            recruiter += 1

        else:
            if recruiter in recruiters_guide:
                recruiters_guide[recruiter].append(str(i_resume))
            else:
                recruiters_guide[recruiter] = [str(i_resume)]
            count += 1

    return recruiters_guide

def ask_head_recruiter(question, recruiters_guide, recruiters_response):
    # recruiters_guide = {0: ['0', '1', '2'], 1: ['3', '4']}
    # recruiters_response = {0: 'Hello', 1: 'Welcome'}

    system = f'Act as a the head of a committee of professional recruiters trying to answer question. Candidates resumes where split into groups of three and each recruiter has only analyzed three resumes. Summarize relevant information from each recruiter and act as a professional recruiter to answer question. Refer to each candidate by their number and name.'

    prompt = f'' \
             f'\nquestion: {question}'
    for i in range(len(recruiters_guide)):
        candidates = ', '.join(recruiters_guide[i])
        prompt += f'\nrecruiter{i} analyzing candidates {candidates}: {recruiters_response[i]}'
    prompt += f'\ncommittee head:'

    response, messages = ask_chatgpt(prompt, messages=[], system=system, new_chat=True, max_tokens=RECRUITER_HEAD_MAX_TOKENS)
    return response, messages

def ask_recruiter(question, resume_texts, candidates):
    system = f'Act as a member of a committee of professional recruiters. The committee has to answer the question based on several resumes, yet you can analyze only 3 resumes. Analyze resumes of all 3 candidates line by line, answer question and explain your reason with honesty very briefly to the committee. If you cannot answer the question, return the short summarized part of resume that corresponds to that question. Refer to each candidate by their number and name. End sentences with dot'

    prompt = f'' \
             f'\nquestion: {question}'
    for candidate in candidates:
        prompt += f'\ncandidate{candidate}: {resume_texts[int(candidate)]}'
    prompt += f'\ncommittee head:'

    response, _ = ask_chatgpt(prompt, messages=[], system=system, new_chat=True, max_tokens=RECRUITER_MAX_TOKENS, only_response=True)
    return response


def preprocess_resume(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        pdf_text = ""
        for page_number in range(len(pdf.pages)):
            page = pdf.pages[page_number]
            pdf_text += page.extract_text(x_tolerance=2, y_tolerance=5, layout=False).strip()
    return pdf_text.replace("|", ",")


def resume_to_text(resume_list):
    return [preprocess_resume(resume_path) for resume_path in resume_list]


def main():
    uploaded_files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)

    if uploaded_files:
        st.subheader("Uploaded PDFs:")
        pdf_names = [file.name for file in uploaded_files]
        for i, pdf_file in enumerate(uploaded_files):
            new_name = f"resume{i}.pdf"
            with open(os.path.join(".", new_name), "wb") as f:
                f.write(pdf_file.getbuffer())
            st.write(f"Renamed to: {new_name}")
        pdf_names = [f'resume{i}.pdf' for i in range(len(uploaded_files))]

        st.subheader("Processed Resumes:")
        resume_texts = resume_to_text(pdf_names)
        for i, resume_text in enumerate(resume_texts):
            st.write(f"Resume {i} Header:")
            st.write(resume_text[:resume_text.find('\n')])

    # Chat Interface
    st.subheader("Chat!")
    intro_message = "Hello! I am Chat-Ninja and will assist you with analyzing resumes. Resumes will be presented to AI recruiters in chunks of 3, and each recruiter will express their analysis. Then, head of the recruiters will present you a final answer!"

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": intro_message}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Type your question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        assistant_response = foo(prompt, resume_texts)

        with st.chat_message("assistant"):
            st.markdown(assistant_response)

        st.session_state.messages.append({"role": "assistant", "content": assistant_response})


if __name__ == '__main__':
    main()
