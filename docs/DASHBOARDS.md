# Dashboards sugeridos

## 1. Operacional em tempo real

Pergunta respondida: **o que a frota está fazendo agora?**

Cards:

- veículos em operação;
- ciclos em andamento;
- aguardando em obra;
- descarregando;
- retornando;
- alertas críticos.

Lista/board por status atual, derivado do `PERIOD` ativo.

Cada card de veículo deve mostrar:

- veículo;
- motorista;
- obra/destino;
- status;
- início do status;
- tempo corrido;
- ciclo atual.

## 2. Jornada e ciclos

- jornadas iniciadas/concluídas;
- número de ciclos;
- tempo médio por etapa;
- tempo médio do ciclo completo;
- gargalo do dia;
- distribuição de espera;
- ciclos recentes.

Etapas típicas configuráveis:

- abastecimento;
- deslocamento obra;
- aguardando;
- descarregando;
- retorno.

## 3. Eficiência e diesel

- diesel total;
- volume entregue;
- L/m³;
- meta/referência configurada;
- desvio da referência;
- evolução diária/semanal;
- L/m³ por veículo;
- impacto associado a espera;
- volume por motorista;
- viagens por veículo.

Não apresentar ranking como avaliação de culpa do motorista. Mostrar contexto disponível.

## 4. Obras/clientes

P1:

- espera média por obra;
- tempo de descarga;
- quantidade de entregas;
- volume entregue;
- obras com maior fila;
- horário/dia com mais demora.

Essa visão é potencialmente uma forte ferramenta comercial/operacional.

## 5. Manutenção

P1:

- preventiva a vencer/vencida;
- veículos indisponíveis;
- ocorrências abertas;
- reincidência por sistema/componente;
- tempo médio até resolução.
