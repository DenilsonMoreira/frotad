# ADR 0007 — Dashboard operacional do piloto

## Decisão

GET /api/v1/dashboard usa o mesmo contexto autenticado do Runner: empresa, unidade e motorista atribuído. Não aceita empresa no corpo. A resposta não pode ser armazenada em cache.

O quadro consulta PERIOD sem fim, inclusive iniciado antes do dia selecionado. Durações vêm do relógio do servidor e são atualizadas por polling de 30 segundos. Contadores de veículos e ciclos são distintos; períodos concorrentes permanecem visíveis, sem escolher arbitrariamente um único status.

Resultados diários consideram somente SUBMITTED pela data de submitted_at, no fuso da unidade (quando configurado) ou empresa. A tendência contém sete dias. Volume e diesel usam Decimal e colunas tipadas. L/m³ é razão dos totais, arredondada para quatro casas; fica nulo sem volume positivo ou com medições ausentes. Abastecimento não equivale necessariamente ao consumo efetivo no mesmo dia.

## Configuração

A configuração administrativa existente Company.settings pode conter:

```json
{"dashboard": {
  "cycle_form": "FORM02", "volume_field": "volume_m3",
  "fuel_form": "FORM03", "fuel_field": "liters",
  "waiting_status": "WAITING_AT_SITE", "target_liters_per_m3": "2.50"
}}
```

Esses são os valores padrão, exceto a referência, que é nula. A configuração aponta para códigos de formulários e chaves estáveis, preservando versões históricas. Não somar novamente os agregados FORM01. Medições ausentes geram aviso de totais parciais. A instalação de templates e edição administrativa dessa configuração têm tarefas próprias no backlog.

## Interface e acesso

A página substitui os números fictícios do starter por dados da API. O acesso inicial do piloto usa UUID da empresa e token emitido pelo bootstrap administrativo existente. O token permanece somente na memória da página, nunca em localStorage, URL ou logs; recarregar exige nova conexão. Não implementa login público ou fila offline.

NEXT_PUBLIC_API_URL continua apontando à API (padrão http://localhost:8000). Em implantação HTTPS, configurar também API HTTPS e CORS correspondente. Não há nova variável obrigatória ou migration.

Componentes usam tokens CSS, controles com pelo menos 44px e layout responsivo a 360px. Filtros de veículo/motorista/status aplicam-se apenas ao quadro ao vivo; a data aplica-se aos resultados. Falhas de atualização mantêm o último snapshot com aviso explícito.

## Limites

Este recorte entrega status, espera ativa, viagens, volume, diesel, índice e tendência tabular. Destino/obra, alertas de manutenção, distribuição de espera e análises por veículo/motorista dependem de próximas projeções e cadastros; não são inventados. Não há ranking de culpa. A consulta usa joins transacionais e janela de sete dias; projeções e paginação do quadro deverão preceder operações com grande volume.

## Validação

Testes de API cobrem empresas distintas, permissões, escopo de motorista, relógio do servidor, períodos antigos, fuso local, exclusão de drafts, configuração das métricas, razão dos totais e medições ausentes. Executar pytest com TEST_DATABASE_URL apontando exclusivamente a frotad_test; lint, typecheck e build no frontend.
