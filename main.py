import streamlit as st
import json
import re
from llm import llm_qa, llm_condense, embeddings, acs
from streamlit_chat import message
from langchain.chains import ConversationalRetrievalChain


# Setup Streamlit  -------------------------------------------------------------------------------------------
st.set_page_config(page_title='Chat with your pdf')

css_streamlit = f"""
<style>
    .stTextInput {{
      position: fixed;
      bottom: 3rem;
    }}
</style>
"""

st.markdown(css_streamlit, unsafe_allow_html=True)

# Initialize Streamlit session states ------------------------------------------------------------------------
if 'query' not in st.session_state:
    st.session_state.query = ""

if 'chat_history' not in st.session_state:    
    st.session_state.chat_history = [('How many people are participating in the match?', 'A soccer match is played by two teams, each consisting of not more than eleven players, one of whom is the goalkeeper.'),
                                     ('What is the criteria for a team to win the match?', "The team scoring the greater number of goals during a match is the winner.")]

if 'chat' not in st.session_state:
    st.session_state.chat = []

if 'conversation' not in st.session_state:
    st.session_state.conversation = []


# Function to handle form submission ------------------------------------------------------------------------
def submit():
    st.session_state.query = st.session_state.widget
    st.session_state.widget = ""


def get_chat_history(inputs) -> str:
    res = []
    for human, ai in inputs:
        res.append(f"Human:{human}\nAI:{ai}")
    return "\n".join(res)


def transform_to_json(data):
    json_objects = []
    for item in data:

        question, answer = item
        json_data = {
            "question": question,
            "answer": answer
        }
        json_objects.append(json_data)
    return json_objects


# Steamlit input form --------------------------------------------------------------------------------------
with st.container():
    st.write("## :blue[Query your A.I. about FIFA Soccer Rules] :soccer:")
    st.text_input(label="Kick your query :point_down: ",
                  key="widget",
                  on_change=submit,
                  label_visibility="visible"
                  )


if st.session_state.query != "":

    try:
        qa = ConversationalRetrievalChain.from_llm(
            llm=llm_qa,
            retriever=acs.as_retriever(search_kwargs={"k": 3}),
            return_source_documents=True,
            condense_question_llm=llm_condense,
            verbose=True
        )

        response = qa({"question": st.session_state.query,
                       "chat_history": st.session_state.chat_history})

        st.session_state.chat_history.append(
            (st.session_state.query, response['answer']))

    except Exception as e:
        print(e)

    # Source Documents list ------------------------------------------------------------------------------------
    metadata_patterns = {
        'document': r"'document': '(.*?)'",
        'page': r"'page': (\d+)",
        'category': r"'category': '(.*?)'",
    }

    metadata_json_list = []
    generated_file_names = []

    for doc in response['source_documents']:
        extracted_metadata = {}

        for key, pattern in metadata_patterns.items():
            match = re.search(pattern, str(doc))
            if match:
                extracted_metadata[key] = match.group(
                    1) if key != 'page' else int(match.group(1))

        if extracted_metadata not in metadata_json_list:
            document_name_without_extension = extracted_metadata['document'].replace(
                '.pdf', '')
            new_file_name = f"{document_name_without_extension}-{extracted_metadata['page']}.pdf"
            metadata_json_list.append(extracted_metadata)
            generated_file_names.append(new_file_name)

    phrase_list = ["I don't", "I'm sorry"]

    answer = response["answer"] + "\n\n" + "References: \n"
    for filename in generated_file_names:
        answer += f"[{str(filename)}](https://pdfdepot.blob.core.windows.net/soccer-rules/{str(filename)}) \n"

    for text in phrase_list:
        if text in response["answer"]:
            answer = response["answer"]
            break

    # Streamlit chat ------------------------------------------------------------------------------------------
    st.session_state.chat.append(
        (st.session_state.query, answer))

    st.session_state.conversation = transform_to_json(
        st.session_state.chat)

    for i in range(len(st.session_state.conversation)):
        message(st.session_state.conversation[i]["question"], is_user=True,
                avatar_style="initials", seed="?", key="question" + str(i))
        message(st.session_state.conversation[i]["answer"],
                avatar_style="initials", seed="AI", key="answer" + str(i))

    if len(st.session_state.chat_history) > 5:
        st.session_state.chat_history.pop(0)


# Streamlit sidebar --------------------------------------------------------------------------------------------
with st.sidebar:
    pass
