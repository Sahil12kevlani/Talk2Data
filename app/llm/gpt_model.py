from openai import OpenAI

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="your_groq_api_key_here"
)

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {"role": "system", "content": "You are Talk2Data assistant."},
        {"role": "user", "content": "Test message from backend!"}
    ]
)

print(response.choices[0].message.content)
