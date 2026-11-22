## Context

Consulte `proposal.md` e `specs/sales-list-ui/spec.md`. A função `render_vendas` atualmente renderiza filtros sem keys, uma tabela estática com clientes fictícios e áreas demonstrativas de cadastro/importação. `app/erp_modules.py` já obtém o token por `st.session_state["auth_token"]` e usa `st.form`, chaves de sessão e `st.spinner` nas consultas de estoque e catálogo. O cliente `listar_vendas` já aceita os filtros documentados e retorna o envelope validado de paginação.

## Goals / Non-Goals

**Goals:**
- Adaptar somente a listagem em `render_vendas`, consumindo `listar_vendas` com o token existente.
- Preservar consulta/filtros/página por chaves de sessão e renderizar os cabeçalhos sem inventar esquema de coluna.
- Cobrir visualmente sucesso, lista vazia, falta de sessão, erro HTTP e falha de conexão com AppTest e mocks.

**Non-Goals:**
- Alterar o formulário demonstrativo, importação, navegação, cliente Xano ou outras telas.
- Buscar detalhes por venda ou apresentar valores financeiros ausentes do cabeçalho.

## Decisions

- **Usar `listar_vendas` importada de `app.xano_client`.** Reutilizar o cliente já testado em vez de criar outra lógica HTTP ou um formato de payload.
- **Enviar filtros em formulário.** Um submit explícito evita consultas repetidas a cada tecla. Usar campos com keys estáveis; status “todos” vira parâmetro ausente. Ao aplicar filtros diferentes, voltar à página 1.
- **Manter datas como texto bruto.** O formato/unidade dos timestamps segue não especificado, e o cliente não converte datas; campos de texto permitem enviar exatamente o que o usuário informou sem inventar serialização.
- **Navegar por metadados do envelope.** Usar `prevPage` e `nextPage` para habilitar/desabilitar navegação e `curPage`, `pageTotal`, `itemsTotal` e `itemsReceived` para informar posição/contagem. Reutilizar o tamanho de página documentado.
- **Renderizar as colunas que vierem no resultado.** Construir a tabela diretamente dos dicionários em `items`, sem lista de campos presumida nem colunas calculadas. Lista vazia recebe mensagem própria.
- **Guardar o resultado consultado na sessão.** Renderizar o último resultado em reruns sem novo request, exceto ao enviar filtros ou navegar. Capturar erros HTTP/status, timeout/conexão e estrutura inválida com mensagens apropriadas; não chamar o cliente sem token.
- **Testar AppTest com mock da função importada.** Exercitar a interação Streamlit e conferir argumentos enviados, linhas/campos renderizados, estado de paginação, estados de erro e ausência das linhas demo na tabela.

## Risks / Trade-offs

- [O formato dos timestamps não foi confirmado] → Campos textuais e encaminhamento sem conversão; o Xano continua responsável por validar a semântica das datas.
- [Os campos presentes nos cabeçalhos podem variar] → Tabela deriva suas colunas da resposta; se não houver colunas em registros, a listagem informa ausência de vendas.
- [A tela também contém outros controles de demonstração] → A alteração fica restrita à listagem operacional; cadastro/importação não serão conectados ou removidos nesta etapa.
