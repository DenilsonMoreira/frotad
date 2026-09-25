# ADR 0008 — Login, empresas e dois níveis de administração

## Decisões e permissões

O administrador do sistema é uma identidade global (`users.is_system_admin`), provisionada somente pelo operador no servidor. Não é um valor selecionável de Membership.role e nenhum endpoint público permite conceder esse privilégio.

O painel `/admin` permite listar empresas e criar cada empresa junto de seu administrador responsável (OWNER). O administrador da empresa (OWNER/ADMIN) acessa `/usuarios` para cadastrar usuários e ativar/desativar vínculos da sua própria empresa. OWNER pode criar ADMIN; ADMIN não cria outros administradores nem desativa OWNER, outro ADMIN ou a própria conta. Não há transferência de propriedade nesta fase.

Somente OWNER/ADMIN criam e publicam formulários. MANAGER mantém leitura, mas perde `forms:write`, atendendo à regra do usuário. O administrador do sistema pode administrar definições de formulário com contexto explícito de empresa; isso não libera acesso implícito a dados operacionais, frota ou usuários dessa empresa. As alterações continuam auditadas na empresa selecionada. O editor visual de formulários é a próxima fase.

Cadastro público `/cadastro` cria uma nova empresa com OWNER, nunca um administrador do sistema. E-mails são normalizados em minúsculas. Uma conta já existente não é vinculada a outra empresa por meio de senha fornecida por terceiros; convites e seleção de múltiplas empresas são trabalho futuro. No login, usa-se o primeiro vínculo ativo; o admin global sem vínculo abre o painel do sistema.

## Autenticação e sessão

As senhas usam PBKDF2-HMAC-SHA256, 600.000 iterações e salt aleatório de 32 bytes, com comparação constante. A escolha utiliza a biblioteca padrão; referência: [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html). Cadastro exige 15–128 caracteres, sem remover espaços da senha. Contas inexistentes também executam derivação de senha. Cinco falhas consecutivas bloqueiam login da conta por cinco minutos; estado persistido e alteração serializada no PostgreSQL.

Tokens opacos expiram em oito horas e só têm SHA-256 armazenado no banco. Login/logout/troca de senha e provisionamento global geram registros em `system_audit_events`. Logout revoga o token apresentado. Troca de senha exige a atual e revoga todos os tokens do usuário. Recuperação por e-mail, verificação de e-mail, MFA e limitação global de tentativas por IP não estão incluídas.

O navegador usa um proxy Next.js restrito a rotas conhecidas (`/api/backend`). Tokens ficam em cookies HttpOnly, SameSite=Strict e Secure em produção. Não são retornados ao JavaScript nem armazenados em localStorage. Requisições de alteração verificam Origin; respostas de dados usam no-store. A API continua aceitando Bearer para integrações e valida sempre a identidade e o contexto de empresa.

## Banco e configuração

Migration `bf981f93a230` adiciona password_hash opcional, failed_logins, locked_until e is_system_admin em users, além da tabela system_audit_events. Contas legadas sem hash continuam válidas para seus tokens existentes, mas não ganham senha padrão.

No servidor web, `API_URL` pode apontar para a API interna; fallback em NEXT_PUBLIC_API_URL e http://localhost:8000. `APP_ORIGIN` define a origem pública exata quando existir proxy reverso (ex.: https://app.exemplo.com). Sem essa variável, usa protocolo e Host da requisição. Produção exige HTTPS para os cookies Secure. Não configurar API_URL para o servidor de testes.

## Primeiro acesso

1. Inicie PostgreSQL com `docker compose up -d postgres`.
2. Em `apps/api`, execute `..\..\.venv\Scripts\alembic upgrade head`.
3. No mesmo diretório, em terminal local interativo, execute:

```powershell
..\..\.venv\Scripts\python -m frotad.system_admin --email SEU_EMAIL --name "SEU NOME"
```

O comando solicita a senha sem eco e confirmação; não passe senha como argumento ou pela conversa. Ele recusa promover/substituir e-mails existentes. Não inclui credenciais padrão nem cria conta real automaticamente.

4. Inicie a API (`..\..\.venv\Scripts\uvicorn frotad.main:app --reload`) e a web (`npm run dev` em apps/web).
5. Abra http://localhost:3000/login, entre como administrador do sistema e cadastre a empresa com seu responsável. Esse responsável entra pelo mesmo login e gerencia a equipe.

Usuários DRIVER recebem também cadastro de Driver vinculado, mas a atribuição de operações continua explícita. Funcionários podem alterar sua senha em `/conta`.

## Validação

Testes da API exercitam atomicidade do cadastro, conflitos, hash/token não expostos, login/logout, bloqueio temporário, troca de senha, revogação, separação global/empresa, tentativas de elevação de privilégio e permissões de formulários. A suíte completa é executada em PostgreSQL de testes.

Playwright usa um upstream de teste isolado (porta 8101) para validar o proxy real Next.js, cookies HttpOnly, Origin, navegação, recarga, cadastro de empresa/usuário, desconexão e responsividade em desktop/360px. As regras do backend real são cobertas pelos testes Python; o fixture do navegador não é componente de produção.
