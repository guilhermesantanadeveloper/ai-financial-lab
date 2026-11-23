import argparse
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from .contract import ScreenSpec
from .generator import configured_model, generate_screen


def main():
    parser = argparse.ArgumentParser(description="Gera uma ScreenSpec para o GenUi2")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("pedido", nargs="?", help="Descrição da tela em linguagem natural")
    source.add_argument("--schema", action="store_true", help="Exporta o JSON Schema do Android")
    parser.add_argument("--output", type=Path, help="Destino do JSON (padrão: stdout)")
    parser.add_argument("--model", help="Modelo da OpenAI com suporte a saída estruturada")
    args = parser.parse_args()
    try:
        if args.schema:
            document = ScreenSpec.model_json_schema()
        else:
            load_dotenv()
            if not args.pedido.strip():
                parser.error("Informe um pedido com texto")
            model = args.model or configured_model()
            spec = generate_screen(OpenAI(), args.pedido, model)
            document = spec.model_dump(exclude_defaults=True)
        result = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.write_text(result, encoding="utf-8")
        else:
            print(result, end="")
    except (ValueError, OpenAIError, OSError) as exc:
        parser.exit(1, f"Falha ao gerar a saída: {exc}\n")
