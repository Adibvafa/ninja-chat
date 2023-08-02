import openai
import streamlit as st


def foo(prompt):
    return f"hello {prompt}"


def main():
    st.title("Ninja Chat! Let's Discuss Resumes")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask any question!"):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # The Assistant's response is now always "hello"
        assistant_response = foo(prompt)

        with st.chat_message("assistant"):
            st.markdown(assistant_response)

        st.session_state.messages.append({"role": "assistant", "content": assistant_response})


if __name__ == '__main__':
    main()
