# Proposta: Sugestão inteligente de compras

## Problema

O responsável pelo e-commerce precisa decidir quais produtos comprar e em quais quantidades, considerando as vendas históricas, o estoque disponível e os custos. Sem uma estimativa padronizada, pode comprar mercadorias em excesso ou deixar faltar produtos.

## Mudança proposta

Criar uma funcionalidade que utilize exclusivamente os dados internos disponíveis no Xano para:

- Permitir selecionar o período histórico de vendas.
- Calcular a média diária de unidades vendidas por produto.
- Estimar a demanda para os próximos 15 dias.
- Recomendar quantidades de reposição considerando o estoque disponível e o estoque mínimo.
- Apresentar o investimento estimado e os indicadores financeiros que possam ser calculados com os dados existentes.
- Explicar as recomendações e informar quando os dados forem insuficientes.

## Escopo

- Consulta de vendas válidas no período selecionado.
- Consulta do estoque atual, estoque mínimo e custos disponíveis.
- Cálculo da demanda prevista para 15 dias.
- Recomendação de quantidade de compra.
- Estimativas financeiras identificadas claramente como projeções.
- Tratamento de dados ausentes ou inconsistentes.
- Respeito às permissões de acesso existentes.

## Fora de escopo

- Integração com APIs de marketplaces ou com a Cargoos.
- Criação automática de pedidos de compra.
- Alteração automática do estoque ao gerar recomendações.
- Substituição dos cálculos financeiros existentes.
- Apresentação de projeções como resultados realizados ou lucro líquido contábil.
- Desconto de compras pendentes sem existir uma fonte de dados confirmada para esses pedidos.

## Critérios de sucesso

- O usuário consegue selecionar o período histórico e compreender a previsão.
- A recomendação considera 15 dias de demanda estimada e as regras de estoque definidas.
- O investimento e os indicadores financeiros utilizam os custos disponíveis e as regras existentes.
- Dados insuficientes são identificados sem inventar valores.
- Consultar recomendações não modifica vendas, estoque ou movimentações.
