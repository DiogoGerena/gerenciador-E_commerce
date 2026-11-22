## Context

Consulte `proposal.md` e `specs/sales-detail-ui/spec.md`. A tela `render_vendas` mantém a listagem paginada do Xano em `st.session_state["vendas_list_result"]`; cada linha possui o ID retornado. O cliente já disponibiliza `consultar_venda(token, venda_id)`, que valida o envelope detalhado `sale`, `items`, `costs` e `financial_summary` sem recalcular o resumo. Os arquivos de testes da listagem usam Streamlit `AppTest` e mocks do cliente.

## Goals / Non-Goals

**Goals:**
- Permitir selecionar uma venda da página exibida e carregar o detalhe sob demanda.
- Apresentar somente dados confirmados pelo cliente e resposta validada do Xano.
- Preservar a consulta da listagem quando o usuário retorna dos detalhes.
- Validar renderização, tratamento de erros e valores financeiros com testes mockados.

**Non-Goals:**
- Alterar endpoints ou validações do cliente Xano.
- Adicionar cadastro, edição, cancelamento, exclusão ou importação de vendas.
- Refazer a listagem, incluir dados ausentes ou calcular valores financeiros no frontend.

## Decisions

- **Acessar detalhes sob demanda por ID.** Usar o identificador do cabeçalho já exibido e chamar o cliente existente apenas após seleção; evitar consultar detalhes de todas as linhas.
- **Guardar seleção e resultado detalhado na sessão.** Usar estado persistente para a venda selecionada/detalhe, mantendo `vendas_list_result`, filtros e página originais para retorno sem nova consulta à lista.
- **Apresentar estruturas retornadas separadamente.** Exibir dados de `sale`, tabela de `items`, tabela de `costs` e resumo financeiro somente quando cada dado vier na resposta; usar indicação de indisponibilidade para campos opcionais ausentes.
- **Não converter nem recomputar valores.** A interface formata para leitura sem alterar os valores subjacentes; CMV, rateio, resultado e margem continuam sendo responsabilidade do Xano.
- **Tratar falhas sem sucesso presumido.** Capturar HTTP 401/403/404, falhas de transporte e resposta inválida, exibindo mensagens de acordo com status sem inventar um objeto de venda alternativo.
- **Validar com AppTest e mocks.** Testar seleção, argumento ID/token, estruturas apresentadas, valores financeiros iguais aos recebidos, erros, retorno e preservação do estado da lista.

## Risks / Trade-offs

- [Campos opcionais variam entre vendas] → Renderização guiada pelos campos efetivamente presentes; ausência não vira zero ou valor substituto.
- [Detalhe pode falhar depois da seleção] → Manter o estado da listagem e comunicar falha na área de detalhe, sem apresentar dados antigos como correspondentes à venda selecionada.
- [Resposta financeira não deve ser interpretada como lucro líquido contábil] → Mostrar os rótulos recebidos do resumo e não introduzir alegações contábeis nem cálculo adicional.
