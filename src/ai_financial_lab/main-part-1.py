import json
from dotenv import load_dotenv
from openai import OpenAI
from ai_financial_lab.tools.simulate_purchase import simulate_purchase
from ai_financial_lab.tools.month_summary import get_month_summary

def main(): 
    load_dotenv()

    client = OpenAI()

    question = "Posso comprar um notebook de R$ 8.000,00 em 10x?"

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
            "strict": True
        },
        {
            "type": "function",
            "name": "simulate_purchase",
            "description": (
                "Simula o impacto mensal de uma compra sobre a margem livre atual "
                "do usuário. Use somente quando o valor total da compra e a quantidade "
                "de parcelas forem conhecidos. Não invente a quantidade de parcelas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Valor total da compra em reais.",
                    },
                    "installments": {
                        "type": "integer",
                        "description": "Quantidade de parcelas informada pelo usuário.",
                    },
                },
                "required": [
                    "amount",
                    "installments",
                ],
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

    print("\n--- OUTPUT ---")

    for item in response.output:
        if item.type == "function_call":
            print("\n--- MODEL REQUESTED TOOL ---")
            print(item.name)

            if item.name == "get_month_summary":
                result = get_month_summary()
                print("\n--- TOOL RESULT ---")
                print(result)

                next_response = client.responses.create(
                    model="gpt-5.6-luna",
                    previous_response_id=response.id,
                    tools=tools,
                    input=[
                        {
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": json.dumps(result),
                        }
                    ],
                )
                print("\n--- NEXT ANSWER ---")
                print(next_response.output_text)

            elif item.name == "simulate_purchase":
                # result = simulate_purchase()
                print("\n--- TOOL RESULT ---")
                print(result)

                final_response = client.responses.create(
                    model="gpt-5.6-luna",
                    previous_response_id=response.id,
                    tools=tools,
                    input=[
                        {
                            "type": "function_call_output",
                            "call_id": item.call_id,
                            "output": json.dumps(result),
                        }
                    ],
                )
                print("\n--- FINAL ANSWER ---")
                print(final_response.output_text)

        elif item.type == "reasoning": 
            print("To pensando...")

if __name__ == "__main__":
    main()