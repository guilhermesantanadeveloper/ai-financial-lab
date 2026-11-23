from openai import OpenAI

from .contract import (
    Binding, Card, Expression, Field, ListNode, Model, Node, ScreenSpec, references,
)


class DraftField(Field):
    name: str
    initial: str


class DraftCalculation(Model):
    name: str
    expression: Expression


class ScreenDraft(Model):
    fields: list[DraftField]
    computed: list[DraftCalculation]
    children: list[Node]

    def to_screen(self) -> ScreenSpec:
        fields = {f.name: Field(type=f.type) for f in self.fields}
        computed = {c.name: c.expression for c in self.computed}
        if len(fields) != len(self.fields) or len(computed) != len(self.computed):
            raise ValueError("Nome duplicado na saída do modelo")
        screen = ScreenSpec(
            schemaVersion=1,
            fields=fields,
            initialState={f.name: f.initial for f in self.fields},
            computed=computed,
            children=self.children,
        )

        validate_generated_layout(screen)
        return screen


def validate_generated_layout(screen: ScreenSpec) -> None:
    """Check calculator usability after validating the Android wire contract."""
    visible = set()
    problems = []

    def visit(items):
        for item in items:
            if isinstance(item, Binding):
                visible.add(item.bind)
            elif isinstance(item, Card):
                if not item.children:
                    problems.append(f"Card vazio: {item.id}")
                elif len(item.children) == 1 and isinstance(item.children[0], Card):
                    problems.append(f"Remova o card redundante: {item.id}")
                visit(item.children)
            elif isinstance(item, ListNode):
                visit(item.items)

    visit(screen.children)
    dependencies = {name for expr in screen.computed.values() for name in references(expr)}
    results = screen.computed.keys() - dependencies
    if not results:
        problems.append("Declare o resultado da calculadora em computed")
    elif not results.intersection(visible):
        problems.append(f"Exiba um resultado usando text.bind ou um item de lista: {sorted(results)}")
    if problems:
        raise ValueError(". ".join(problems))


def generation_schema() -> dict:
    """Strict structured outputs require every property of each object to be present."""
    schema = ScreenDraft.model_json_schema()
    for definition in [schema, *schema["$defs"].values()]:
        if "properties" in definition:
            definition["required"] = list(definition["properties"])
            for prop in definition["properties"].values():
                prop.pop("default", None)
    return schema


INSTRUCTIONS = """Crie uma calculadora interativa em português brasileiro para o pedido.
Escolha quais valores a pessoa vai variar e crie inputs ligados a esses campos.
Preserve os números informados. Para dados desconhecidos, use initial vazio ou um
valor inicial explicitamente descrito como cenário editável. Use strings numéricas
sem separadores de milhar. Mantenha as fórmulas em computed: ref aponta para um
campo ou outro cálculo; divide aceita dois argumentos na ordem numerador, divisor.
Use format BRL para resultados monetários. Use format e suffix vazios quando
dispensáveis. Dê IDs estáveis aos componentes e organize os children na ordem de
leitura. Só use reset_fields quando fizer sentido restaurar os valores iniciais.
Comece com um text literal de role title. Card agrupa conteúdo visível; evite
containers vazios ou que apenas envolvem outro card. Para exibir uma prestação,
por exemplo, use este children dentro do card, adaptando o bind ao cálculo real:
[{"id":"rotulo","type":"text","text":"Valor da parcela","role":"body"},
 {"id":"valor","type":"text","bind":"valor_parcela","format":"BRL","role":"highlight"}].
O id identifica um componente; para mostrar um valor calculado, use bind.
Para comparar parcelamentos sem juros, deixe o número de parcelas editável e
mostre o valor por parcela calculado, preservando o preço fornecido."""


def generate_screen(client: OpenAI, request: str, model: str) -> ScreenSpec:
    messages = [{"role": "user", "content": request}]
    response_format = {
        "type": "json_schema", "name": "screen_draft",
        "schema": generation_schema(), "strict": True,
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
