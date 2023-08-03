import openai, os, pdfplumber, toml, tiktoken
import streamlit as st

openai.api_key = st.secrets["OPENAI_API_KEY"]


RECRUITER_HEAD_MAX_TOKENS = 1500
RECRUITER_MAX_TOKENS = 450
ASSISTANT_SUMMARY_MAX_TOKENS = 350
USER_SUMMARY_MAX_TOKENS = 150

def user_said(content, history, summarize=True):
    if summarize:
        prompt = f'question: {content}. Your task is to summarize the user asked question without answering it so the summary can be saved in chat history. brief question of user, followed by summary of any relevant information: '
        content = ask_chatgpt(prompt, messages=[], system=None, new_chat=True, max_tokens=USER_SUMMARY_MAX_TOKENS,
                              only_response=True, temp=0)
    history.append({"role": "user", "content": content})

def assistant_said(content, history, summarize=False):
    if summarize:
        prompt = f'{content}. In very brief summary: '
        content = ask_chatgpt(prompt, messages=[], system=None, new_chat=True, max_tokens=ASSISTANT_SUMMARY_MAX_TOKENS,
                    only_response=True, temp=0.1)
    history.append({"role":"assistant", "content":content})

def ask_chatgpt(user_content, messages, system=None, new_chat=False, max_tokens=256, only_response=False, temp=0.0):

    messages = [] if new_chat else messages
    if system and new_chat:
        messages.append({"role":"system", "content":system})

    user_said(user_content, messages, summarize=False)

    response = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=messages,
      temperature=temp,
      max_tokens=max_tokens,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0
    )
    response = response['choices'][0]['message']['content']

    if only_response:
        return response

    # assistant_said(response, messages)

    return response, messages


def ninja_chat(session_state, user_input, resume_texts):

    with st.chat_message("assistant"):
        st.markdown(f'prev_input = {session_state.prev_input}')
    st.session_state.messages.append({"role": "assistant", "content": f'prev_input = {session_state.prev_input}'})

    if user_input.strip().upper() == 'Q':
        session_state.prev_input = 'Q'
        return "Sure! I will try my best to answer your question."

    if user_input.strip().upper() == 'J':
        session_state.prev_input = 'J'
        return "Sure! Send me the job posting."

    if session_state.prev_input.strip().upper() == 'Q':
        answer_resume_question(user_input, resume_texts, session_state)
        return ''

    if session_state.prev_input.strip().upper() == 'J':
        job = get_job_posting(user_input)
        session_state.job_posting = job
        return f'Job Posting Analyzed! Summary:\n{job}'

    if session_state.prev_input == 'N':
        return 'N'

    return 'ERRROROROR'




def answer_resume_question(question, resume_texts, session_state):
    recruiters_guide = create_recruiters_guide(len(resume_texts))
    recruiters_response = {}

    for recruiter in recruiters_guide:
        response = ask_recruiter(question, resume_texts, recruiters_guide[recruiter], session_state)
        response = f'Recruiter {recruiter}, Analyzing Candidates {", ".join(recruiters_guide[recruiter])}:\n\n' + response

        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
        recruiters_response[recruiter] = response


    response = ask_head_recruiter(question, recruiters_guide, recruiters_response, session_state)
    response = f'Head Recruiter, Analyzing All Recruiters:\n\n' + response

    with st.chat_message("assistant"):
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})

    user_said(question, session_state.gpt_messages, summarize=True)
    assistant_said(response, session_state.gpt_messages, summarize=True)


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



def token_counter(messages):
    encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = 0
    for message in messages:
        num_tokens += 4
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += -1
    num_tokens += 2
    return num_tokens

def polish_messages(messages):

    conv_history_tokens = token_counter(messages)

    while conv_history_tokens >= 4096:
        del messages[1]
        conv_history_tokens = token_counter(messages)

    return messages


def ask_head_recruiter(question, recruiters_guide, recruiters_response, session_state):
    system = f'Act as a the head of a committee of professional recruiters trying to answer question.' \
             f'Candidates resumes where split into groups of three and each recruiter has only analyzed three resumes.' \
             f'Summarize relevant information from each recruiter with honesty and act as a professional recruiter' \
             f'to answer question. Refer to each candidate by their number and name.'

    prompt = f'' \
             f'\nquestion: {question}'

    if session_state.job_posting:
        prompt = prompt + f'\njob posting: {session_state.job_posting}'


    for i in range(len(recruiters_guide)):
        candidates = ', '.join(recruiters_guide[i])
        prompt += f'\nrecruiter{i} analyzing candidates {candidates}: {recruiters_response[i]}'
    prompt += f'\ncommittee head:'

    session_state.gpt_messages = polish_messages(session_state.gpt_messages)

    response, session_state.gpt_messages = ask_chatgpt(prompt, messages=session_state.gpt_messages, system=system, new_chat=False, max_tokens=RECRUITER_HEAD_MAX_TOKENS, only_response=False)
    del session_state.gpt_messages[-1]
    return response

def ask_recruiter(question, resume_texts, candidates, session_state):
    system = f'Act as a recruiter of a committee of professional recruiters. The committee has to answer the question' \
             f'based on several resumes, yet you can analyze only 3 of them. Analyze resumes word by word, answer question' \
             f'and explain your reason with honesty very briefly to the committee. If you cannot answer the question,' \
             f'return the very short part of resume that corresponds to that question. Refer to each candidate' \
             f'by their number and name. End sentences with dot.'
    prompt = f'' \
             f'\nquestion: {question}'

    if session_state.job_posting:
        prompt = prompt + f'\njob posting: {session_state.job_posting}'

    for candidate in candidates:
        prompt += f'\ncandidate{candidate}: {resume_texts[int(candidate)]}'
    prompt += f'\ncommittee head:'

    return ask_chatgpt(prompt, messages=[], system=system, new_chat=True, max_tokens=RECRUITER_MAX_TOKENS, only_response=True, temp=0.2)


def get_candidate_name_email(resume):
    prompt = f'resume: {resume}. Only fill in the blanks using the scrapped beginning of resume. Stop after the last blank is filled. Candidate Name: [BLANK], Email: [BLANK]'
    response = ask_chatgpt(prompt, messages=[], system=None, new_chat=True, max_tokens=60, only_response=True).strip()
    return [elem.split(':')[-1].strip() for elem in response.split(',')]


def get_job_posting(raw_posting):
    prompt = f'Act as a professional recruiter. Summarize the most important information of the job posting: {raw_posting}'
    return ask_chatgpt(prompt, messages=[], system=None, new_chat=True, max_tokens=500, only_response=True, temp=0)


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
        for i, pdf_file in enumerate(uploaded_files):
            new_name = f"resume{i}.pdf"
            with open(os.path.join(".", new_name), "wb") as f:
                f.write(pdf_file.getbuffer())
            st.write(f"Renamed To: {new_name}")
        pdf_names = [f'resume{i}.pdf' for i in range(len(uploaded_files))]

        st.subheader("Processed Resumes:")
        st.session_state.resume_texts = resume_to_text(pdf_names)

        st.session_state.candidates_info = {}
        for i, resume_text in enumerate(st.session_state.resume_texts):
            st.write(f"Resume {i} From:")
            name, email = get_candidate_name_email(resume_text[:150])
            st.session_state.candidates_info[i] = [name, email]
            st.write(f'Name: {name}; Email: {email}\n')


    st.subheader("Let's Chat!")
    intro_message = "Hello! My name is Chat-Ninja and I'll assist you with analyzing resumes. Your uploaded resumes will be presented to AI recruiter teams in groups of 3, and each recruiter will express their analysis. Then, the head of recruiters will present you a final answer!"
    intro_message_2 = """Please choose one of the following options:\n1. To ask a question, type 'Q'\n2. To send interview invite to chosen candidates, type 'I'\n3. To send calendar invitation, type 'C'\n4. To enter a job posting, type 'J'"""

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": intro_message + '\n\n' + intro_message_2}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if "prev_input" not in st.session_state and "gpt_messages" not in st.session_state and "job_posting" not in st.session_state:
        st.session_state.prev_input = 'N'; st.session_state.gpt_messages = []; st.session_state.job_posting = ''

    if prompt := st.chat_input("Your Message..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        ninja = ninja_chat(st.session_state, prompt, st.session_state.resume_texts)


        if len(ninja) > 0:
            with st.chat_message("assistant"):
                st.markdown(ninja)
            st.session_state.messages.append({"role": "assistant", "content": ninja})

        # ending_message = 'Is there any other question I can help you with?'
        # with st.chat_message("assistant"):
        #     st.markdown(ending_message)
        # st.session_state.messages.append({"role": "assistant", "content": ending_message})


if __name__ == '__main__':
    main()
    #
    #
    #
    #
    #
    #
    # messages = []
    # job_posting = ''
    #
    # if prompt := st.chat_input("Type Q, I, C, or J"):
    #     st.session_state.messages.append({"role": "user", "content": prompt})
    #
    #     with st.chat_message("user"):
    #         st.markdown(prompt)
    #
    #     prompt = prompt.strip().upper()
    #     if prompt in ('Q', 'I', 'C', 'J'):
    #
    #         if prompt == 'J':
    #             with st.chat_message("assistant"):
    #                 st.markdown("Sure! Send me the job posting.")
    #             st.session_state.messages.append({"role": "assistant", "content": "Sure! Send me the job posting."})
    #
    #             job_posting_input = st.text_area("Job Posting...")
    #
    #             # Custom button to submit the job posting
    #             if st.button("Analyze Job Posting"):
    #                 st.session_state.messages.append({"role": "user", "content": job_posting_input})
    #                 with st.chat_message("user"):
    #                     st.markdown(job_posting_input)
    #
    #                 job_posting_summary = get_job_posting(job_posting_input)
    #
    #                 with st.chat_message("assistant"):
    #                     st.markdown(f"Job Posting Analyzed! Here is the summary: {job_posting_summary}")
    #                 st.session_state.messages.append({"role": "assistant",
    #                                                   "content": f"Job Posting Analyzed! Here is the summary: {job_posting_summary}"})
    #

                # if prompt := st.chat_input("Job Posting...", key=hash("J")):
                #     st.session_state.messages.append({"role": "user", "content": prompt})
                #     with st.chat_message("user"):
                #         st.markdown(prompt)
                #
                #     if st.button("Analyze Job Posting"):
                #         job_posting_summary = get_job_posting(prompt)
                #
                #         with st.chat_message("assistant"):
                #             st.markdown(f"Job Posting Analyzed! Here is the summary: {job_posting_summary}")
                #         st.session_state.messages.append({"role": "assistant",
                #                                           "content": f"Job Posting Analyzed! Here is the summary: {job_posting_summary}"})

#
#
#             elif prompt == 'Q':
#
#                 with st.chat_message("assistant"):
#                     st.markdown("Sure! I will try my best to answer your question.")
#                 st.session_state.messages.append(
#                     {"role": "assistant", "content": "Sure! I will try my best to answer your question."})
#
#                 while True:
#                     user_input = st.chat_input()
#
#                     if user_input:
#                         st.session_state.messages.append({"role": "user", "content": user_input})
#                         with st.chat_message("user"):
#                             st.markdown(user_input)
#
#                         messages = ninja_chat(user_input, resume_texts, messages, job_posting)
#                         break
#
#             ending_message = intro_message_2
#
#             with st.chat_message("assistant"):
#                 st.markdown(ending_message)
#             st.session_state.messages.append({"role": "assistant", "content": ending_message})
#
#         else:
#             reset_prompt_message = "Please only send Q, I, C, or J."
#             with st.chat_message("assistant"):
#                 st.markdown(reset_prompt_message)
#             st.session_state.messages.append({"role": "assistant", "content": reset_prompt_message})
#
#
# if __name__ == '__main__':
#     main()
