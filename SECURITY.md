# Segurança

FrotaD lida com dados operacionais empresariais, dados de usuários, localização potencial e evidências documentais.

## Regras mínimas

- isolamento multi-tenant obrigatório;
- autenticação e autorização em todas as rotas privadas;
- TLS em produção;
- secrets nunca versionados;
- URLs de arquivos privadas por padrão;
- upload com limite de tamanho e validação de tipo;
- logs não devem armazenar tokens, senhas ou documentos completos desnecessariamente;
- trilha de auditoria para operações sensíveis;
- política de retenção de dados definida por contrato/configuração;
- princípio do menor privilégio.

## LGPD

O produto deve suportar inventário de dados pessoais, finalidade, retenção e mecanismos operacionais para atender solicitações aplicáveis. Evite coletar dados pessoais que não tenham finalidade operacional clara.

## Vulnerabilidades

Não publique detalhes exploráveis em issues públicas. Utilize canal privado de segurança definido pela organização quando o repositório estiver hospedado.
