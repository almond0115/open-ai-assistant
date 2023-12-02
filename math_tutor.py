from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()
API_KEY = os.environ['OPENAI_API_KEY']

client = OpenAI(api_key=API_KEY)

# 어시스턴스
# asst_po6vDmeTpP9QSkA5He0I645b
# assistant = client.beta.assistants.create(
#     name = "Math Tutor",
#     instructions="You are a personal math tutor. Write and run code to answer math questions",
#     tools = [{"type": "code_interpreter"}],
#     model = "gpt-3.5-turbo-16k"
# )
# print(assistant)

# 스레드
# thread_mIHx2AXaj8ZlGbeqAL14XSGD
# thread = client.beta.threads.create()
# print(thread)

# 메세지
# msg_8dqVAisIDD0bZFuJnr1SLSta
# message = client.beta.threads.messages.create(
#     thread_id = "thread_mIHx2AXaj8ZlGbeqAL14XSGD",
#     role = "user",
#     content = "I need to solve the equation `3x + 11 = 14`. Can you help me?"
# )
# print(message)

# 작동
# run_9UUuANPJdw8rwqcP9eNvaTeK
# run = client.beta.threads.runs.create(
#     thread_id="thread_mIHx2AXaj8ZlGbeqAL14XSGD",
#     assistant_id="asst_po6vDmeTpP9QSkA5He0I645b",
#     instructions="Please address the user as Jane Doe. The user has a premium account."
# )
# print(run)

# run = client.beta.threads.runs.retrieve(
#     thread_id="thread_mIHx2AXaj8ZlGbeqAL14XSGD",
#     run_id="run_9UUuANPJdw8rwqcP9eNvaTeK"
# )
# print(run)

messages = client.beta.threads.messages.list(
    thread_id="thread_mIHx2AXaj8ZlGbeqAL14XSGD"
)

print(messages.data[0].content[0].text.value)
