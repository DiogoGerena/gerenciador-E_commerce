# Proposta: Controle Financeiro e de Estoque para E-commerce

## Objetivo

Desenvolver um sistema para auxiliar proprietários de e-commerce no controle de estoque e no acompanhamento financeiro das vendas, permitindo visualizar custos, CMV, resultados e indicadores relevantes para a gestão do negócio.

## Motivação

O controle separado de estoque, compras e vendas dificulta o acompanhamento dos custos reais dos produtos e da rentabilidade das operações. O sistema centralizará essas informações para facilitar a consulta, a análise e a tomada de decisões.

## Escopo da primeira versão

- Cadastro e gerenciamento de produtos, categorias e fornecedores.
- Associação de produtos a múltiplos fornecedores.
- Registro de entradas de mercadorias e respectivos custos de aquisição.
- Controle de estoque por meio de movimentações rastreáveis.
- Cálculo do custo médio ponderado e do Custo das Mercadorias Vendidas (CMV).
- Registro manual e importação de vendas por arquivos CSV e Excel.
- Cálculo da receita, dos custos das vendas, do resultado após custos e da margem percentual.
- Dashboard com indicadores financeiros e de estoque.
- Autenticação de usuários e controle de permissões por perfil.
- Histórico das operações para conferência e auditoria.

## Perfis de usuário

- **Adm:** responsável pela administração do sistema, gerenciamento de usuários e configurações gerais.
- **aux.ecommerce:** responsável pelas atividades operacionais autorizadas, incluindo consulta e manutenção de dados, registro de movimentações e importação de vendas.

## Tecnologias previstas

- **Backend:** Xano, com regras de negócio e APIs.
- **Frontend:** Streamlit.
- **Especificação e organização do desenvolvimento:** OpenSpec.
- **Importação de vendas:** arquivos CSV e Excel.

## Fora do escopo da primeira versão

- Realização de vendas ou processamento de pagamentos.
- Integração automática com a API do Mercado Livre ou de outros marketplaces.
- Substituição de um sistema contábil completo.

## Resultado esperado

Entregar uma aplicação funcional que centralize o controle de estoque e os registros financeiros, preserve o histórico das operações e apresente indicadores confiáveis para apoiar a gestão do e-commerce.

## Escopo financeiro ampliado

Além do controle de estoque e dos custos das vendas, a primeira versão incluirá recursos de análise financeira gerencial:

- Cadastro e acompanhamento de despesas fixas mensais.
- Classificação dos custos e despesas associados às vendas, incluindo custos variáveis.
- Indicadores de CMV, margem bruta, margem de contribuição, ponto de equilíbrio, lucro operacional, lucro líquido gerencial e ticket médio.
- Fluxo de caixa realizado e projetado, com distinção explícita entre valores efetivamente recebidos/pagos e valores previstos.
- Filtros por período e, quando aplicável, por produto e canal de venda.

Os indicadores têm finalidade de análise gerencial e não substituem escrituração contábil, apuração fiscal ou demonstrações contábeis oficiais. As regras de cálculo e os componentes incluídos em cada indicador deverão ser documentados e aplicados de forma consistente.
