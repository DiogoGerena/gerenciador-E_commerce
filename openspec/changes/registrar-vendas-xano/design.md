## Context

Consulte `proposal.md` e `specs/sales-registration-ui/spec.md`. `render_vendas` já mantém filtros e paginação da listagem e consulta detalhes sob demanda; abaixo dessa área, o cadastro manual ainda é um conjunto de controles demonstrativos. `app.xano_client` já implementa `criar_venda(token, dados)`, valida canal, itens, custos e campos opcionais, envia `POST /sale`, não faz retry e diferencia resposta incompleta (`RespostaVendaInconclusivaError`) de timeout/conexão (`OperacaoVendaInconclusivaError`). A tela também possui acesso ao catálogo de produtos e tratamento centralizado de erros HTTP.

## Goals / Non-Goals

**Goals:**
- Integrar o formulário existente sem alterar navegação, cliente Xano ou telas não relacionadas.
- Representar os produtos por IDs reais do catálogo e manter estado estável entre adições/remoções de linhas.
- Fazer uma única tentativa explícita por submissão e preservar dados quando o resultado não puder ser confirmado.
- Atualizar a consulta da listagem somente após confirmação válida.

**Non-Goals:**
- Alterar payload, endpoints, validações ou configuração do cliente Xano.
- Reproduzir no frontend validações de estoque ou qualquer cálculo financeiro.
- Implementar fluxos de importação, cancelamento, edição ou exclusão.
- Alterar a listagem e consulta detalhada além do necessário para atualizá-las após confirmação.

## Decisions

- **Reutilizar `criar_venda` e seu contrato.** A tela constrói somente `sales_channel`, opcionais documentados (`order_number`, `sale_date`, `notes`), `items` e custos globais `costs`. O cliente continua sendo a autoridade para normalizar e validar o payload; o frontend valida os mesmos limites observáveis para dar retorno imediato, sem ampliar regras.
- **Selecionar produtos do catálogo existente.** Reutilizar o fluxo existente de consulta/listagem de produtos para apresentar IDs reais, em vez de aceitar nomes livres ou inventar entidades. A consulta de produtos ativos pode apoiar a seleção, mas a validade e o estoque disponível continuam sendo confirmados pelo Xano ao registrar.
- **Manter itens e custos em estado separado do envio.** Cada linha recebe uma identidade estável para que adicionar/remover controles não desloque valores de outras linhas em reruns. Custos permanecem em uma lista global, não vinculada aos itens. Alternativa descartada: um único campo textual serializado, por dificultar validação individual e preservar valores.
- **Serializar a data conforme o contrato confirmado.** Converter datas ISO 8601 para timestamp Unix inteiro em milissegundos; interpretar valores sem fuso como UTC. Preservar a data/hora informada pelo usuário e omitir `sale_date` quando vazia.
- **Tratar o POST como operação não repetível automaticamente.** Desabilitar o envio enquanto está em andamento. Em HTTP inválido ou resposta incompleta, exibir falha sem sucesso; em timeout/conexão, manter os dados e indicar resultado inconclusivo, sem repetir o POST. Erros do Xano sobre produto inativo ou estoque devem ser mostrados como falhas do backend, não como sucesso.
- **Atualizar a listagem via seu mecanismo atual após confirmação.** Depois da resposta válida, limpar o formulário de maneira controlada, manter filtros, solicitar atualização usando o fluxo existente, voltar à primeira página se a página atual puder deixar a inclusão invisível e exibir uma mensagem temporária somente após o rerun. Uma falha ou resultado inconclusivo não invalida a listagem como se a venda estivesse confirmada.
- **Vincular UUID v4 ao payload efetivamente validado.** Serializar o payload do cliente com chaves de objeto ordenadas, separadores determinísticos e sem incluir `idempotency_key`, então calcular SHA-256 sem transformar valores, arrays ou casas decimais. A ordem dos arrays é preservada naturalmente pela serialização; opcionais omitidos continuam diferentes de opcionais explicitamente presentes. Guardar fingerprint e UUID juntos no `st.session_state`; reutilizar ambos apenas enquanto o fingerprint coincidir, preservando a chave após falha não confirmada e limpando-a somente após confirmação válida.
- **Classificar os conflitos pelo `message` do Xano.** `IDEMPOTENCY_LOCKED`, `IDEMPOTENCY_CONCURRENT_REQUEST` e `IDEMPOTENCY_LOCK_FAILED` mantêm a operação e sua chave, com aviso específico e sem envio automático. `IDEMPOTENCY_PAYLOAD_MISMATCH` bloqueia nova submissão para o fingerprint conflitante; uma mudança efetiva do payload obtém nova chave. Outros códigos HTTP mantêm o tratamento atual.
- **Testar com Streamlit AppTest e mocks.** Isolar `criar_venda` e chamadas do catálogo; verificar payload, interações de linhas, ausência de retry, mensagens de resultado, preservação de dados no inconclusivo e atualização da listagem após confirmação.

## Risks / Trade-offs

- [O catálogo pode conter produto ativo sem estoque suficiente] → Não prometer sucesso ou disponibilidade na interface; o Xano valida produto e estoque na transação e a UI apresenta a rejeição retornada.
- [Timeout ou resposta incompleta pode ocorrer após persistência] → Tratar como inconclusivo, não reenviar automaticamente e orientar consulta da listagem antes de uma nova tentativa manual.
- [`sale_date` usa timestamp Unix em milissegundos] → Converter no fluxo manual e no Excel com a mesma rotina; rejeitar timestamps em segundos para impedir datas próximas de 1970.
- [Filtros atuais podem excluir a venda recém-registrada] → Preservar filtros como solicitado e atualizar a consulta; a confirmação temporária informa o registro mesmo quando os filtros ativos não mostram a venda na tabela.
