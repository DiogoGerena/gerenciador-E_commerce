# Design: Redesign visual do sistema

## Abordagem

Manter a aplicação Streamlit e reorganizar a apresentação visual usando os recursos já existentes no projeto. O redesign deve ser aplicado às telas atuais sem alterar a comunicação com o Xano ou as regras de negócio.

## Identidade visual

- Fundo principal: `#FFFDF8`
- Superfícies e cartões: `#FFFFFF`
- Cor de destaque principal: `#E87522`
- Destaque secundário: `#F2B544`
- Texto principal: `#242424`
- Texto secundário: `#686868`
- Bordas: `#E8E1D8`

Usar laranja e âmbar com moderação, principalmente em ações principais, navegação e indicadores. Garantir contraste adequado para textos e controles.

## Estrutura das telas

- Organizar o conteúdo próximo ao topo, evitando áreas vazias desnecessárias.
- Padronizar cabeçalhos, navegação, espaçamentos, botões, formulários e tabelas.
- Separar o fluxo de boas-vindas e login em estados distintos: apenas uma dessas telas deve ser exibida por vez.
- Na tela de login, usar uma composição clara com área de apresentação e formulário, adaptada à largura disponível.
- Reaproveitar componentes e estilos para manter consistência entre as páginas.

## Gráficos e tabelas

- Utilizar fundos claros e cores coerentes com a identidade visual.
- Manter títulos, eixos, legendas e valores legíveis.
- Evitar estilos escuros que reduzam a legibilidade.
- Preservar os dados e cálculos já utilizados pelos gráficos.

## Tratamento de erros de login

Traduzir falhas de credenciais inválidas para uma mensagem amigável, como “E-mail ou senha incorretos”. Não exibir JSON bruto, códigos HTTP ou detalhes técnicos do backend ao usuário.

## Compatibilidade e limites

- Preservar autenticação, endpoints, payloads, permissões e regras de negócio.
- Não alterar o banco de dados nem adicionar funcionalidades.
- Não usar margens negativas para corrigir o layout.
- Validar o fluxo de boas-vindas, login, retorno à tela inicial e exibição de erros.