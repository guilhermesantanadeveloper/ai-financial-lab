import json
from dotenv import load_dotenv
from openai import OpenAI
from ai_financial_lab.tools.simulate_purchase import simulate_purchase
from ai_financial_lab.tools.month_summary import get_month_summary


##
#   {
#       "name": "simulate_purchase",
#       "arguments": "{\"amount\":8000,\"installments\":10}"
#   }
# 
#   handler(**arguments) -> dictionary unpacking
# #
def execute_tool_call(tool_call, tool_handlers):
    if tool_call.name not in tool_handlers:
        raise ValueError("Unknown tool: {tool_call.name}")

    arguments = json.loads(tool_call.arguments)

    handler = tool_handlers[tool_call.name]

    print(f"\n ---- EXECUTING TOOL: {tool_call.name} -----")
    print(f"Arguments: {arguments}")

    result = handler(**arguments)

    print(f"Result: {result}")

    return {
        "type": "function_call_output",
        "call_id": tool_call.call_id,
        "output": json.dumps(result),
    }


def main(): 
    load_dotenv()

    client = OpenAI()

    question = "Posso comprar um notebook de R$ 8.000,00?"

    tool_handlers = {
        "get_month_summary": get_month_summary,
        "simulate_purchase": simulate_purchase
    }

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


    while True:
        tool_calls = [
            item
            for item in response.output
            if item.type == "function_call"
        ]

        if not tool_calls:
            print("\n  --- FINAL ANSWER ---")
            print(response.output_text)
            break

        tool_outputs = []

        for tool_call in tool_calls:
            output = execute_tool_call(
                tool_call,
                tool_handlers
            )

            tool_outputs.append(output)

        response = client.responses.create(
            model="gpt-5.6-luna",
            previous_response_id=response.id,
            tools=tools,
            input=tool_outputs
        )
        

if __name__ == "__main__":
    main()