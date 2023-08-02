import openai, os, pdfplumber
import streamlit as st


def foo(prompt, resume_texts):
    return f"hello {prompt}\n{resume_texts[0][:100]}"

def process_pdfs(uploaded_files):
    pdf_names = [file.name for file in uploaded_files]
    return pdf_names

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
        pdf_names = process_pdfs(uploaded_files)
        for i, pdf_file in enumerate(uploaded_files):
            new_name = f"resume{i}.pdf"
            with open(os.path.join(".", new_name), "wb") as f:
                f.write(pdf_file.getbuffer())
            st.write(f"Renamed to: {new_name}")


    if uploaded_files:
        st.subheader("Processed Resumes:")
        resume_texts = resume_to_text(pdf_names)
        for i, resume_text in enumerate(resume_texts):
            st.write(f"Resume {i}:")
            st.write(resume_text)

    # Chat Interface
    st.subheader("Chat Interface")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("What is up?"):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # The Assistant's response is now always "hello"
        assistant_response = foo(prompt, resume_texts)

        with st.chat_message("assistant"):
            st.markdown(assistant_response)

        st.session_state.messages.append({"role": "assistant", "content": assistant_response})


if __name__ == '__main__':
    main()
