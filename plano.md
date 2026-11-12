# alerta-investimentos — Plano de evolução

## Contexto

Hoje o projeto monitora ações da B3 durante o pregão e envia alertas no Telegram quando uma ação
passa de um limite de variação (ex.: 3%), mostrando o resultado da posição pelo preço médio.
Stack atual: Python 3.12, uv, httpx, pydantic, PostgreSQL (Neon) com psycopg 3, brapi.dev,
Telegram Bot API, pytest, ruff, GitHub Actions (CI + cron).

### Problemas identificados

- **Atraso dos dados:** a brapi tem delay de ~30 min no plano gratuito (~15 min no Startup, ~5 min no Pro).
  Nenhum plano é tempo real. Um alerta de preço atrasado perde para o app da corretora.
- **Cron do GitHub Actions não é confiável:** execuções agendadas atrasam ou são descartadas em horários
  de carga alta, e workflows agendados são desativados após 60 dias sem atividade em repositórios públicos.
- **Polling desalinhado:** o cron roda a cada 15 min, mas o dado gratuito só muda a cada ~30 min.

### Mudança de foco

O projeto deixa de responder "a ação caiu?" (que qualquer app responde) e passa a responder
**"o que aconteceu com a minha carteira, por quê, e onde devo aportar?"**.
Para isso, atraso de 30 minutos não importa.

## Visão do produto

Um **relatório semanal inteligente da carteira inteira** (renda fixa, Tesouro Direto e ações),
enviado no Telegram toda sexta após o fechamento, mais **avisos imediatos só para o que é urgente**
(fatos relevantes da CVM).

### Dores que o sistema resolve

| Dor | Funcionalidade |
|---|---|
| Não sei por que uma ação se mexeu | Seção "O que mexeu": notícias da semana resumidas por IA |
| Perco notícias importantes das empresas | Monitor de fatos relevantes da CVM + aviso imediato |
| Não sei onde colocar o próximo aporte | Seção "Para o próximo aporte": alocação atual vs. alocação-alvo |

### Exemplo do relatório

```
📊 Sua semana — 03 a 07/nov

Carteira: +0,82% na semana | +9,4% no ano
CDI no período: +0,21% | Ibovespa: +1,10%

Renda fixa   45% (meta 50%)  +0,23%
Tesouro      25% (meta 25%)  +0,31%
Ações        30% (meta 25%)  +2,10%

O que mexeu
• ITUB4 −4,2%: balanço do 3º tri mostrou alta na inadimplência.
• VALE3 +6,1%: alta do minério após estímulos na China.

Fatos relevantes da semana
• WEGE3 anunciou aquisição na Europa (resumo: ...)

Próxima semana
• Balanço da PETR4 (quinta) • Data-com de dividendos de BBAS3

Para o próximo aporte
Renda fixa está 5 p.p. abaixo da meta e ações 5 p.p. acima.
Priorizar renda fixa traz a carteira de volta ao equilíbrio.
```

## Princípios

- **A IA explica, o código calcula.** Todo número (rentabilidade, alocação, variação) é calculado
  por código testado. O LLM só escreve texto em cima desses números. Nunca inventa valores
  e nunca recomenda "compre" ou "venda".
- **Decimal/NUMERIC para dinheiro.** Nada de float em valores financeiros (já é assim hoje).
- **Regras como funções puras.** Cálculos sem rede nem banco, testáveis sem mocks (já é assim com `rules.py`).
- **RSS e dados abertos em vez de scraping.** Feeds e APIs oficiais são estáveis; scraping quebra
  quando o site muda e pode violar termos de uso.
- **Segurança mantida:** tokens fora de URLs e logs, actions fixadas por SHA, permissões mínimas.
- **Migrations versionadas** em `migrations/`, como hoje.

## Arquitetura

### Fontes de dados

| Dado | Fonte |
|---|---|
| Cotações de ações | brapi.dev |
| Preços e taxas do Tesouro Direto | Dados públicos do Tesouro |
| CDI, IPCA, Selic | API SGS do Banco Central |
| Notícias por ticker | Feeds RSS (ex.: Google News por busca) |
| Fatos relevantes e comunicados | Dados abertos / sistemas da CVM |
| Texto das explicações | LLM via Groq |

### Jobs (cada um vira um CronJob no Kubernetes)

| Job | Frequência | Responsabilidade |
|---|---|---|
| `quotes-collector` | Diário, após o fechamento | Cotações de ações, preços do Tesouro, CDI/IPCA |
| `news-collector` | Algumas vezes ao dia | Notícias por ticker via RSS, sem duplicatas |
| `cvm-monitor` | A cada hora | Fatos relevantes; **único job com aviso imediato** |
| `weekly-report` | Sexta à noite | Calcula números, chama o Groq, envia o relatório |

O alerta de preço intradiário atual sai ou fica só para movimentos extremos (ex.: ≥ 8%).

### Banco (proposta inicial, a refinar)

- `positions`: classe do ativo (ação, Tesouro, renda fixa), identificador, quantidade, preço médio,
  indexador (CDI, IPCA, pré), taxa contratada, vencimento
- `quotes`: preços diários por ativo
- `index_values`: séries de CDI, IPCA e Selic
- `news`: notícias coletadas por ticker (com chave única para deduplicar)
- `filings`: fatos relevantes da CVM já vistos/notificados
- `allocation_targets`: meta de alocação por classe
- `reports`: relatórios gerados (histórico)

## Infraestrutura

- **CI continua no GitHub Actions** (pytest, ruff). A cada push na `main`, publica a imagem Docker
  no GitHub Container Registry (GHCR).
- **Agendamento sai do Actions** e vai para CronJobs num cluster **k3s** rodando numa VM gratuita
  (ex.: Oracle Cloud Always Free; conferir limites atuais).
- Segredos (Telegram, brapi, Neon, Groq) em `Secret` do Kubernetes.
- Alternativa só para confiabilidade, sem Kubernetes: disparar `workflow_dispatch` por um cron externo
  (ex.: cron-job.org).

Exemplo de CronJob:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: weekly-report
spec:
  schedule: "0 19 * * 5"
  timeZone: "America/Sao_Paulo"
  concurrencyPolicy: Forbid
  startingDeadlineSeconds: 300
  jobTemplate:
    spec:
      backoffLimit: 2
      template:
        spec:
          restartPolicy: Never
          containers:
            - name: weekly-report
              image: ghcr.io/felipezina/alerta-investimentos:latest
              args: ["weekly-report"]
              envFrom:
                - secretRef:
                    name: alerta-secrets
```

## Roadmap

### Fase 1 — Base multi-ativo e relatório só com números
- Expandir o schema para renda fixa e Tesouro Direto
- Coletar preços do Tesouro e CDI/IPCA do Banco Central
- Calcular rentabilidade por ativo, por classe e da carteira vs. CDI e Ibovespa
- Enviar o relatório semanal no Telegram, **sem IA**
- **Pronto quando:** recebo toda sexta a carteira consolidada com números corretos e testados

### Fase 2 — Notícias e IA (momento de migrar para Kubernetes)
- `news-collector` com RSS por ticker
- Seção "O que mexeu" escrita pelo Groq a partir das notícias e das variações calculadas
- Dockerfile com uv, publicação no GHCR, k3s e CronJobs
- **Pronto quando:** o relatório explica os maiores movimentos da semana com base em notícias reais

### Fase 3 — Monitor da CVM
- `cvm-monitor` detecta fatos relevantes das empresas da carteira
- Aviso imediato no Telegram com resumo do documento
- Seção "Fatos relevantes da semana" no relatório
- **Pronto quando:** sou avisado de um fato relevante sem precisar procurar

### Fase 4 — Alocação-alvo e próximo aporte
- Cadastro de metas por classe de ativo
- Cálculo de desvio e sugestão de qual classe priorizar
- Seção "Próxima semana" (balanços, datas-com)
- **Pronto quando:** o relatório me diz, com base nas minhas metas, onde aportar

## Ideias futuras

- Agente no Telegram (LangChain) para perguntas sobre a carteira, consultando o banco como ferramenta
- Acompanhar ativos que ainda não tenho (watchlist) para apoiar a decisão de novos aportes