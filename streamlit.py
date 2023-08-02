import openai, os, pdfplumber, toml
import streamlit as st

openai.api_key = st.secrets["OPENAI_API_KEY"]


RECRUITER_HEAD_MAX_TOKENS = 1500
RECRUITER_MAX_TOKENS = 500

def user_said(content, history):
    history.append({"role":"user", "content":content})

def assistant_said(content, history):
    history.append({"role":"assistant", "content":content})

def ask_chatgpt(user_content, messages, system=None, new_chat=False, max_tokens=256, only_response=False):

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


def ninja_chat(question, resume_texts):
    recruiters_guide = create_recruiters_guide(len(resume_texts))
    recruiters_response = {}

    for recruiter in recruiters_guide:
        response = ask_recruiter(question, resume_texts, recruiters_guide[recruiter])
        response = f'Recruiter {recruiter}, Analyzing Candidates {", ".join(recruiters_guide[recruiter])}:\n\n' + response

        with st.chat_message("assistant"):
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})
        recruiters_response[recruiter] = response


    response, messages = ask_head_recruiter(question, recruiters_guide, recruiters_response)
    response = f'Head Recruiter, Analyzing All Recruiters:\n\n' + response

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
    system = f'Act as a the head of a committee of professional recruiters trying to answer question.' \
             f'Candidates resumes where split into groups of three and each recruiter has only analyzed three resumes.' \
             f'Summarize relevant information from each recruiter with honesty and act as a professional recruiter' \
             f'to answer question. Refer to each candidate by their number and name.'

    prompt = f'' \
             f'\nquestion: {question}'
    for i in range(len(recruiters_guide)):
        candidates = ', '.join(recruiters_guide[i])
        prompt += f'\nrecruiter{i} analyzing candidates {candidates}: {recruiters_response[i]}'
    prompt += f'\ncommittee head:'

    response, messages = ask_chatgpt(prompt, messages=[], system=system, new_chat=True, max_tokens=RECRUITER_HEAD_MAX_TOKENS)
    return response, messages

def ask_recruiter(question, resume_texts, candidates):
    system = f'Act as a recruiter of a committee of professional recruiters. The committee has to answer the question' \
             f'based on several resumes, yet you can analyze only 3 of them. Analyze resumes word by word, answer question' \
             f'and explain your reason with honesty very briefly to the committee. If you cannot answer the question,' \
             f'return the very short part of resume that corresponds to that question. Refer to each candidate' \
             f'by their number and name. End sentences with dot.'
    prompt = f'' \
             f'\nquestion: {question}'
    for candidate in candidates:
        prompt += f'\ncandidate{candidate}: {resume_texts[int(candidate)]}'
    prompt += f'\ncommittee head:'

    return ask_chatgpt(prompt, messages=[], system=system, new_chat=True, max_tokens=RECRUITER_MAX_TOKENS, only_response=True)


def get_candidate_name_email(resume):
    prompt = f'Only fill in the blanks using information. Stop after the last blank is filled. Candidate Name: [BLANK], Email: [BLANK], information: {resume}'
    return ask_chatgpt(prompt, messages=[], system=None, new_chat=True, max_tokens=100, only_response=True).strip()


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
            st.write(f"Resume {i} from Candidate:")
            st.write(get_candidate_name_email(resume_text[:200]))
            st.write('\n')

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

        ninja_chat(prompt, resume_texts)

        ending_message = 'Is there any other question I can help you with?'

        with st.chat_message("assistant"):
            st.markdown(ending_message)

        st.session_state.messages.append({"role": "assistant", "content": ending_message})


if __name__ == '__main__':
    main()
