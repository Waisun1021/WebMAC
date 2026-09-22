import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url="https://api.openai.com/v1")

# class GPT3_5():
#     def __init__(self, message):
#         self.message = message

def gpt(model, message):
    completion = client.chat.completions.create(
        model=model,
        stream=False,
        messages=message
    )

    return completion.choices[0].message.content


if __name__ == '__main__':
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    b = gpt(model="gpt-4.1-mini", message=messages)
    print(b)