import openai, os
import streamlit as st


def foo(prompt):
    return f"hello {prompt}"


def process_pdfs(uploaded_files):
    pdf_names = [file.name for file in uploaded_files]
    return pdf_names


def main():
    uploaded_files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)

    if uploaded_files:
        st.subheader("Uploaded PDFs:")
        pdf_names = process_pdfs(uploaded_files)
        for pdf_name in pdf_names:
            st.write(pdf_name)

    st.subheader("Chat Interface")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Message"):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        assistant_response = foo(prompt)

        with st.chat_message("assistant"):
            st.markdown(assistant_response)

        st.session_state.messages.append({"role": "assistant", "content": assistant_response})

if __name__ == '__main__':
    main()
