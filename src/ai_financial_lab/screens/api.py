from typing import Annotated

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import APITimeoutError, AuthenticationError, OpenAI, OpenAIError, RateLimitError
from pydantic import BaseModel, StringConstraints

from .contract import ScreenSpec
from .generator import configured_model, generate_screen

app = FastAPI(title="GenUi2")


class GenerateRequest(BaseModel):
    prompt: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


@app.post("/screens/generate", response_model_exclude_defaults=True)
def generate(request: GenerateRequest) -> ScreenSpec:
    try:
        with OpenAI(timeout=45.0, max_retries=0) as client:
            return generate_screen(client, request.prompt, configured_model())
    except APITimeoutError as exc:
        raise HTTPException(504, "O modelo demorou para responder. Tente novamente.") from exc
    except AuthenticationError as exc:
        raise HTTPException(502, "Verifique a chave da API no servidor.") from exc
    except RateLimitError as exc:
        raise HTTPException(429, "O provedor atingiu o limite de uso. Confira a cota no servidor.") from exc
    except OpenAIError as exc:
        raise HTTPException(502, "Falha ao consultar o modelo. Verifique a configuração do servidor.") from exc
    except ValueError as exc:
        raise HTTPException(502, "O modelo gerou uma tela inválida. Tente reformular o pedido.") from exc


def main():
    load_dotenv()
    uvicorn.run(app, host="127.0.0.1", port=8000)
