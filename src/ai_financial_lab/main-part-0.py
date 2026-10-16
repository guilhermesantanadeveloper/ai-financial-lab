import json
from dotenv import load_dotenv
from openai import OpenAI

### Ele responde com base no que?

def main(): 
    load_dotenv()

    client = OpenAI()

    question = "Posso comprar um notebook de R$ 8.000,00?"

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=question
    )

    print("\n--- ANSWER ---")
    print(response.output_text)

    print("\n--- RESPONSE ID ---")
    print(response.id)            

    print("\n--- MODEL ---")
    print(response.model)

    print("\n--- USAGE ---")
    print(response.usage)

if __name__ == "__main__":
    main()