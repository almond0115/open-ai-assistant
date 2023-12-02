from dotenv import load_dotenv
import os
from openai import OpenAI
import streamlit as st

load_dotenv()
API_KEY = os.environ['OPENAI_API_KEY']

client = OpenAI(api_key=API_KEY)

# 스레드 ID 하나로 관리하기
# if 'thread_id' not in st.session_state:
#     thread = client.beta.threads.create()
#     st.session_state.thread_id = thread.id

assistant_id = "asst_F1QX8BTLh5DBirDQ9RoEbwxP"
thread_id = "thread_XJFOUcYAVM0hBTtdWve56Brl"

thread_messages = client.beta.threads.messages.list(thread_id, order="asc")

st.header("현진건 작가님과의 대화")

for msg in thread_messages.data:
    with st.chat_message(msg.role):
        st.write(msg.content[0].text.value)

prompt = st.chat_input("물어보고 싶은 것을 입력하세요!")

if prompt:
    st.write(f"User has sent the following prompt: {prompt}")