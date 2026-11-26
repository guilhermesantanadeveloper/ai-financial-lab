from contextlib import contextmanager
from typing import Annotated

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import APITimeoutError, AuthenticationError, OpenAI, OpenAIError, RateLimitError
from pydantic import BaseModel, StringConstraints

from .contract import ScreenSpec
from .generator import ScreenDraft, ScreenPreview, configured_model, generate_screen, generate_preview, revise_preview

app = FastAPI(title="GenUi2")


class GenerateRequest(BaseModel):
    prompt: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class RevisionRequest(GenerateRequest):
    draft: ScreenDraft


@app.post("/screens/generate", response_model_exclude_defaults=True)
def generate(request: GenerateRequest) -> ScreenSpec:
    with model_client() as client:
        return generate_screen(client, request.prompt, configured_model())


@app.post("/screens/preview", response_model_exclude_defaults=True)
def preview(request: GenerateRequest) -> ScreenPreview:
    with model_client() as client:
        return generate_preview(client, request.prompt, configured_model())


@app.post("/screens/revise", response_model_exclude_defaults=True)
def revise(request: RevisionRequest) -> ScreenPreview:
    with model_client() as client:
        return revise_preview(client, request.draft, request.prompt, configured_model())


@contextmanager
def model_client():
    try:
        with OpenAI(timeout=45.0, max_retries=0) as client:
            yield client
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
