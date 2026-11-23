"""ScreenSpec as consumed by GenUi2's ScreenSpecParser and ScreenResolver."""

from __future__ import annotations

import re
from graphlib import CycleError, TopologicalSorter
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Field(Model):
    type: Literal["integer", "decimal"]


class ScreenField(Field):
    fractionAsPercent: bool = False


class Reference(Model):
    ref: str


class Calculation(Model):
    op: Literal["divide", "multiply", "add"]
    args: list[Reference | Calculation]

    @model_validator(mode="after")
    def check_arity(self):
        if len(self.args) < 2 or (self.op == "divide" and len(self.args) != 2):
            raise ValueError(f"Quantidade de argumentos inválida para {self.op}")
        return self


class Caption(Model):
    text: str


class Binding(Model):
    bind: str
    format: Literal["", "BRL"] = ""


class TextNode(Model):
    id: str
    type: Literal["text"]
    role: Literal["body", "title", "highlight"] = "body"


class LiteralText(TextNode, Caption):
    pass


class BoundText(TextNode, Binding):
    pass


class Input(Model):
    id: str
    type: Literal["input"]
    label: str
    bind: str
    suffix: str = ""


class Row(Model):
    id: str
    title: str


class LiteralRow(Row, Caption):
    pass


class BoundRow(Row, Binding):
    pass


class ListNode(Model):
    id: str
    type: Literal["list"]
    items: list[LiteralRow | BoundRow]


class Button(Model):
    id: str
    type: Literal["button"]
    label: str
    action: Literal["reset_fields"]


class Card(Model):
    id: str
    type: Literal["card"]
    children: list[Node]


Node = LiteralText | BoundText | Input | ListNode | Button | Card
Expression = Reference | Calculation


def references(expr: Expression):
    if isinstance(expr, Reference):
        yield expr.ref
    else:
        for arg in expr.args:
            yield from references(arg)


class ScreenSpec(Model):
    schemaVersion: Literal[1, 2]
    fields: dict[str, ScreenField]
    initialState: dict[str, str]
    computed: dict[str, Expression]
    children: list[Node]

    @model_validator(mode="after")
    def validate_links(self):
        if self.schemaVersion == 1 and any(f.fractionAsPercent for f in self.fields.values()):
            raise ValueError("A conversão de fração em porcentagem exige a ScreenSpec v2")
        names = self.fields.keys() | self.computed.keys()
        if self.fields.keys() & self.computed.keys() or any(not n.strip() for n in names):
            raise ValueError("Campos e cálculos precisam de nomes únicos e preenchidos")
        for name, raw in self.initialState.items():
            if name not in self.fields:
                raise ValueError(f"Campo inicial desconhecido: {name}")
            pattern = r"[0-9]+" if self.fields[name].type == "integer" else r"[0-9]+([.,][0-9]+)?"
            if raw and not re.fullmatch(pattern, raw):
                raise ValueError(f"Valor inicial inválido para {name}")
        graph = TopologicalSorter()
        for name, expr in self.computed.items():
            deps = set(references(expr))
            if missing := deps - names:
                raise ValueError(f"{name} referencia nomes desconhecidos: {sorted(missing)}")
            graph.add(name, *deps)
        try:
            graph.prepare()
        except CycleError as exc:
            raise ValueError(f"Ciclo entre cálculos: {exc.args[1]}") from exc

        def visit(items):
            ids = set()
            for item in items:
                if not item.id.strip() or item.id in ids:
                    raise ValueError(f"ID vazio ou repetido no grupo: {item.id!r}")
                ids.add(item.id)
                if isinstance(item, Input) and item.bind not in self.fields:
                    raise ValueError(f"Input vinculado a campo desconhecido: {item.bind}")
                if isinstance(item, Binding) and item.bind not in names:
                    raise ValueError(f"Referência desconhecida: {item.bind}")
                if isinstance(item, Card):
                    visit(item.children)
                elif isinstance(item, ListNode):
                    visit(item.items)

        visit(self.children)
        return self
