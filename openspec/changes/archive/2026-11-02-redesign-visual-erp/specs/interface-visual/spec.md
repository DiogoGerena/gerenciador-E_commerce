## Purpose

Define padrões permanentes para a apresentação das telas do CodBar ERP, mantendo uma experiência visual coerente, legível e adaptável ao uso cotidiano.

## ADDED Requirements

### Requirement: Fluxo separado de boas-vindas e login
O sistema SHALL apresentar as telas de boas-vindas e de login como etapas separadas.

#### Scenario: Acessar o login
- **WHEN** a pessoa seleciona “Acessar sistema” na tela de boas-vindas
- **THEN** a tela de login substitui a tela de boas-vindas sem mantê-la visível ou reservar espaço para ela

#### Scenario: Retornar às boas-vindas
- **WHEN** a pessoa seleciona a ação de retorno na tela de login
- **THEN** o sistema volta à tela de boas-vindas

### Requirement: Identidade visual consistente
Todas as telas do sistema SHALL usar uma linguagem visual consistente, com fundos claros, superfícies de conteúdo claras, cores de destaque quentes, tipografia legível e contraste adequado.

#### Scenario: Apresentar telas do sistema
- **WHEN** uma pessoa navega entre as telas disponíveis
- **THEN** navegação, cabeçalhos, controles e áreas de conteúdo mantêm padrões visuais consistentes sem usar amarelo intenso como cor dominante

### Requirement: Layout responsivo e compacto
O sistema SHALL organizar o conteúdo para permanecer claro e utilizável em larguras de tela comuns, evitando espaços vazios excessivos e rolagem desnecessária quando o conteúdo couber na área disponível.

#### Scenario: Ajustar conteúdo à largura disponível
- **WHEN** a largura da tela é reduzida
- **THEN** o conteúdo se reorganiza sem sobreposições e sem depender de margens negativas

### Requirement: Gráficos e tabelas legíveis
Gráficos e tabelas SHALL usar superfícies claras, texto legível e cores consistentes, preservando os dados apresentados.

#### Scenario: Exibir gráficos e tabelas
- **WHEN** gráficos ou tabelas são apresentados em qualquer tela
- **THEN** seus fundos, títulos, eixos, rótulos, valores e células permanecem legíveis e não usam grandes áreas escuras que prejudiquem a leitura

### Requirement: Mensagens de autenticação amigáveis
Falhas de autenticação SHALL ser apresentadas em linguagem clara, sem expor respostas técnicas, códigos HTTP ou JSON bruto do backend.

#### Scenario: Credenciais inválidas
- **WHEN** a autenticação falha por credenciais inválidas
- **THEN** o sistema informa que o e-mail ou a senha estão incorretos, sem revelar detalhes técnicos retornados pelo backend
