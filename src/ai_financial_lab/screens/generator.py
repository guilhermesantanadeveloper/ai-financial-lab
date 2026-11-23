from openai import OpenAI

from .contract import Expression, Field, Model, Node, ScreenSpec


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
        return ScreenSpec(
            schemaVersion=1,
            fields=fields,
            initialState={f.name: f.initial for f in self.fields},
            computed=computed,
            children=self.children,
        )


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
Para comparar parcelamentos sem juros, deixe o número de parcelas editável e
mostre o valor por parcela calculado, preservando o preço fornecido."""


def generate_screen(client: OpenAI, request: str, model: str) -> ScreenSpec:
    response = client.responses.create(
        model=model,
        instructions=INSTRUCTIONS,
        input=request,
        text={"format": {
            "type": "json_schema", "name": "screen_draft",
            "schema": generation_schema(), "strict": True,
        }},
    )
    if response.status != "completed" or not response.output_text:
        raise ValueError(f"A API não retornou uma tela completa (status: {response.status})")
    return ScreenDraft.model_validate_json(response.output_text).to_screen()
