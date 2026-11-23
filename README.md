# AI Financial Lab

Laboratório Python para experimentar chamadas de ferramentas financeiras e geração de telas. Requer Python 3.14 e usa `uv`. Os comandos que consultam o modelo leem `OPENAI_API_KEY` do ambiente ou do arquivo local `.env`.

## Gerar uma tela para o GenUi2

Na raiz do repositório, execute:

```sh
uv run generate-screen "Quero variar o número de parcelas sem juros de um notebook de R$ 8.000. Comece com 8 parcelas." --output notebook.json
```

O comando envia o pedido ao modelo e grava o JSON após validar componentes, referências, IDs e dependências entre cálculos. O modelo padrão acompanha o exemplo do lab (`gpt-5.6-luna`). Use `--model` ou `OPENAI_MODEL` para selecionar outro modelo com suporte a saídas estruturadas.

Para conferir no Android, na versão do [GenUi2 que lê o asset local](https://github.com/guilhermesantanadeveloper/GenUi2/pull/1), substitua temporariamente o conteúdo de `app/src/main/assets/meu_carro.json` pelo JSON exportado e execute o aplicativo. Com o preço de R$ 8.000, a prestação deve passar de R$ 1.000 em 8 vezes para R$ 800 em 10 vezes.

O arquivo [examples/notebook.json](examples/notebook.json) é um exemplo fixo para comparação. O contrato aceita `text`, `input`, `card`, `list` e `button`, operações `add`, `multiply` e `divide` e a ação `reset_fields`. Para exportar o JSON Schema v1 sem chamar a API:

```sh
uv run generate-screen --schema --output screen-spec-v1.schema.json
```

O modelo devolve listas de campos e cálculos nomeados. O gerador converte essas listas nos mapas `fields`, `initialState` e `computed` usados pelo parser Kotlin. A ordem dos componentes em `children` é preservada.

## Exercício de ferramentas financeiras

`uv run ai-financial-lab` executa o exemplo de consulta ao resumo mensal e simulação de compra.
