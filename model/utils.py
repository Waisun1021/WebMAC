import time

import requests
import json
import os

import os
from openai import OpenAI

def get_response_from_llm(model_name, messages, api_key=None, api_endpoint=None, max_tokens=4096):

    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")

    if not api_endpoint:
        api_endpoint = "https://api.rcouyi.com/v1/"

    if not api_key:
        print("API 密钥未提供！")
        return None

    client = OpenAI(
        api_key=api_key,
        base_url=api_endpoint
    )

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=max_tokens
        )

        return completion.choices[0].message.content

    except Exception as e:
        print(f"ERROR: {e}")
        return None