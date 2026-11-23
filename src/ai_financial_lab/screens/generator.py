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


class ScreenDraft(Model):
    title: str
    fields: list[DraftField]
    computed: list[DraftCalculation]
    layout: Literal["inputs_first", "results_first"]
    show_breakdown: bool
    allow_reset: bool

    def to_screen(self) -> ScreenSpec:
        fields = {f.name: Field(type=f.type) for f in self.fields}
        computed = {c.name: c.expression for c in self.computed}
        if len(fields) != len(self.fields) or len(computed) != len(self.computed):
            raise ValueError("Nome duplicado na saída do modelo")
        if not fields or not computed:
            raise ValueError("A calculadora precisa de campos de entrada e de um cálculo")
        if not self.title.strip() or any(not item.label.strip() for item in [*self.fields, *self.computed]):
            raise ValueError("Informe o título da tela e os rótulos dos campos e cálculos")

        inputs = [
            Input(id=f"input_{f.name}", type="input", bind=f.name,
                  label=f.label.strip(), suffix=f.suffix.strip())
            for f in self.fields
        ]
        # A calculation consumed by another calculation is an intermediate result.
        dependencies = {name for expr in computed.values() for name in references(expr)}
        results: list[Node] = []
        details = []
        for calc in self.computed:
            name = calc.name
            label = calc.label.strip()
            if name in dependencies:
                if self.show_breakdown:
                    details.append(BoundRow(id=name, title=label, bind=name, format=calc.format))
            else:
                results.append(Card(id=f"result_{name}", type="card", children=[
                    LiteralText(id="label", type="text", text=label),
                    BoundText(id="value", type="text", bind=name, format=calc.format, role="highlight"),
                ]))

        children: list[Node] = [
            LiteralText(id="title", type="text", role="title", text=self.title.strip())
        ]
        if self.layout == "inputs_first":
            children.extend([*inputs, *results])
        else:
            children.extend([*results, *inputs])
        if details:
            children.append(ListNode(id="breakdown", type="list", items=details))
        if self.allow_reset:
            children.append(Button(id="reset", type="button", label="Restaurar valores iniciais",
                                   action="reset_fields"))
        return ScreenSpec(
            schemaVersion=1,
            fields=fields,
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
Escolha a ordem dos campos e dos cálculos. Use results_first ou inputs_first
conforme o objetivo. show_breakdown exibe etapas intermediárias e allow_reset
permite restaurar os valores iniciais. O aplicativo monta os componentes visuais."""


def generate_screen(client: OpenAI, request: str, model: str) -> ScreenSpec:
    messages = [{"role": "user", "content": request}]
    response_format = {
        "type": "json_schema", "name": "screen_draft",
        "schema": ScreenDraft.model_json_schema(), "strict": True,
    }
    for attempt in range(2):
        response = client.responses.create(
            model=model, instructions=INSTRUCTIONS, input=messages,
            text={"format": response_format},
        )
        if response.status != "completed" or not response.output_text:
            raise ValueError(f"A API não retornou uma tela completa (status: {response.status})")
        try:
            return ScreenDraft.model_validate_json(response.output_text).to_screen()
        except ValueError as exc:
            if attempt == 1:
                raise ValueError(f"Tela inválida após a correção: {exc}") from exc
            messages.extend([
                {"role": "assistant", "content": response.output_text},
                {"role": "user", "content": f"Corrija a tela inteira mantendo o pedido original. Erros: {str(exc)[:2000]}"},
            ])
