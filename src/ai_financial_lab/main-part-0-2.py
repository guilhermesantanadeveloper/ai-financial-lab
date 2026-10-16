import json
from dotenv import load_dotenv
from openai import OpenAI
from ai_financial_lab.tools.month_summary import get_month_summary


### Ele responde com base no que?

def main(): 
    load_dotenv()

    client = OpenAI()

    question = "Posso comprar um notebook de R$ 8.000,00?"

    tools = [
        {
            "type": "function",
            "name": "get_month_summary",
            "description": (
                "Retorna um resumo financeiro do mês atual do usuário, "
                "incluindo renda, despesas, meta de investimento e margem livre. "
                "Use quando precisar saber se o usuário possui espaço financeiro "
                "para assumir um gasto ou entender sua situação mensal."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
            "strict": True,
        }
    ]


    response = client.responses.create(
        model="gpt-5.6-luna",
        input=question,
        tools=tools
    )

    # chamar a tool
    for item in response.output:
        if item.type == "function_call":
            print("\n--- MODEL REQUESTED TOOL ---")
            print(item.name)

            if item.name == "get_month_summary":
                result = get_month_summary()

                print("\n--- TOOL RESULT ---")
                print(result)

                ## mas o que fazer com essa função?
                ## Final Answer

if __name__ == "__main__":
    main()