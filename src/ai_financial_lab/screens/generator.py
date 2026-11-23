import json
import os
from collections.abc import Callable
from typing import Literal

from openai import OpenAI

from .contract import (
    BoundRow, BoundText, Button, Card, Expression, Field, Input, ListNode,
    LiteralText, Model, Node, ScreenSpec, references,
)


class DraftField(Field):
    name: str
    label: str
    initial: str
    suffix: str


class DraftCalculation(Model):
    name: str
    label: str
    format: Literal["", "BRL"]
    expression: Expression


class Section(Model):
    title: str
    presentation: Literal["inputs", "comparison", "results"]
    refs: list[str]


class Layout(Model):
    sections: list[Section]


class ScreenDraft(Model):
    title: str
    fields: list[DraftField]
    computed: list[DraftCalculation]
    allow_reset: bool
    sections: list[Section]

    def to_screen(self) -> ScreenSpec:
        field_by_name = {f.name: f for f in self.fields}
        calc_by_name = {c.name: c for c in self.computed}
        if len(field_by_name) != len(self.fields) or len(calc_by_name) != len(self.computed):
            raise ValueError("Nome duplicado na saída do modelo")
        if not self.fields or not self.computed:
            raise ValueError("A calculadora precisa de campos de entrada e de um cálculo")
        if not self.title.strip() or any(not item.label.strip() for item in [*self.fields, *self.computed]):
            raise ValueError("Informe o título da tela e os rótulos dos campos e cálculos")

        children: list[Node] = [
            LiteralText(id="title", type="text", role="title", text=self.title.strip())
        ]
        visible: set[str] = set()
        for index, section in enumerate(self.sections):
            if not section.refs or (section.presentation == "comparison" and len(section.refs) < 2):
                raise ValueError("Seção vazia ou comparação com menos de dois resultados")
            if section.title.strip():
                children.append(LiteralText(id=f"section_{index}", type="text",
                                            role="title", text=section.title.strip()))
            rows = []
            for name in section.refs:
                if name in visible:
                    raise ValueError(f"Referência repetida no layout: {name}")
                visible.add(name)
                if section.presentation == "inputs":
                    if name not in field_by_name:
                        raise ValueError(f"Campo desconhecido na seção de entradas: {name}")
                    field = field_by_name[name]
                    children.append(Input(id=f"input_{name}", type="input", bind=name,
                                          label=field.label.strip(), suffix=field.suffix.strip()))
                    continue
                if name not in calc_by_name:
                    raise ValueError(f"Cálculo desconhecido na seção de resultados: {name}")
                calc = calc_by_name[name]
                if section.presentation == "comparison":
                    rows.append(BoundRow(id=name, title=calc.label.strip(), bind=name, format=calc.format))
                else:
                    children.append(Card(id=f"result_{name}", type="card", children=[
                        LiteralText(id="label", type="text", text=calc.label.strip()),
                        BoundText(id="value", type="text", bind=name, format=calc.format, role="highlight"),
                    ]))
            if rows:
                children.append(ListNode(id=f"comparison_{index}", type="list", items=rows))

        computed = {c.name: c.expression for c in self.computed}
        dependencies = {name for expr in computed.values() for name in references(expr)}
        required = field_by_name.keys() | (computed.keys() - dependencies)
        if missing := required - visible:
            raise ValueError(f"Campos ou resultados finais ausentes no layout: {sorted(missing)}")
        if self.allow_reset:
            children.append(Button(id="reset", type="button", label="Restaurar valores iniciais",
                                   action="reset_fields"))
        return ScreenSpec(
            schemaVersion=1,
            fields={f.name: Field(type=f.type) for f in self.fields},
            initialState={f.name: f.initial for f in self.fields},
            computed=computed,
            children=children,
        )


INSTRUCTIONS = """Planeje uma calculadora interativa em português brasileiro.
Dê à tela um título curto. Defina campos editáveis com nomes estáveis, rótulos,
unidades e valores iniciais. Preserve os números do pedido. Use strings numéricas
sem separador de milhar. Para valores desconhecidos, use initial vazio ou indique
que o valor é uma hipótese editável. Use suffix vazio quando não houver unidade.
Defina cada cálculo com nome, rótulo, formato (BRL para dinheiro, vazio para
outros valores) e expressão. Use ref para ler um campo ou outro cálculo.
divide aceita dois argumentos na ordem numerador, divisor. Em parcelamentos sem
juros, divida o preço pelo número editável de parcelas.
Para rótulos de resultados que dependem de uma entrada editável, evite fixar
no texto o valor inicial da entrada. Use, por exemplo, "Custo na porção alvo".
allow_reset permite restaurar os valores iniciais."""

LAYOUT_INSTRUCTIONS = """Organize sections na ordem de leitura. Cada seção tem title
(string vazia se dispensável), presentation e refs com os nomes exatos em ordem.
inputs reúne campos editáveis. comparison compara dois ou mais cálculos em uma lista.
results destaca cálculos em cards. Para comparar opções, reúna seus resultados
na mesma comparison. Priorize o resultado e as entradas que o usuário costuma mudar.
Agrupe as demais entradas por assunto. Inclua cada campo e cada cálculo final uma
vez. Cálculos intermediários podem ser omitidos. Nunca repita uma referência."""


class ScreenPreview(Model):
    draft: ScreenDraft
    screen: ScreenSpec


def configured_model() -> str:
    return os.getenv("OPENAI_MODEL") or "gpt-5.6-luna"


def generate_preview(client: OpenAI, request: str, model: str) -> ScreenPreview:
    def build(raw: str) -> ScreenPreview:
        draft = ScreenDraft.model_validate_json(raw)
        return ScreenPreview(draft=draft, screen=draft.to_screen())

    return _request_preview(client, model, request, INSTRUCTIONS, ScreenDraft, build)


def generate_screen(client: OpenAI, request: str, model: str) -> ScreenSpec:
    return generate_preview(client, request, model).screen


def revise_preview(client: OpenAI, draft: ScreenDraft, feedback: str, model: str) -> ScreenPreview:
    def build(raw: str) -> ScreenPreview:
        layout = Layout.model_validate_json(raw)
        revised = draft.model_copy(update={"sections": layout.sections})
        return ScreenPreview(draft=revised, screen=revised.to_screen())

    request = json.dumps({"current": draft.model_dump(), "feedback": feedback}, ensure_ascii=False)
    return _request_preview(client, model, request, "Ajuste apenas o layout do plano atual conforme o feedback.",
                            Layout, build)


def _request_preview(client: OpenAI, model: str, request: str, instructions: str,
                     schema: type[Model], build: Callable[[str], ScreenPreview]) -> ScreenPreview:
    messages = [{"role": "user", "content": request}]
    response_format = {
        "type": "json_schema", "name": schema.__name__,
        "schema": schema.model_json_schema(), "strict": True,
    }
    for attempt in range(2):
        response = client.responses.create(
            model=model, instructions=instructions + "\n" + LAYOUT_INSTRUCTIONS, input=messages,
            text={"format": response_format},
        )
        if response.status != "completed" or not response.output_text:
            raise ValueError(f"A API não retornou uma tela completa (status: {response.status})")
        try:
            return build(response.output_text)
        except ValueError as exc:
            if attempt == 1:
                raise ValueError(f"Tela inválida após a correção: {exc}") from exc
            messages.extend([
                {"role": "assistant", "content": response.output_text},
                {"role": "user", "content": f"Corrija a resposta mantendo o pedido original. Erros: {str(exc)[:2000]}"},
            ])
