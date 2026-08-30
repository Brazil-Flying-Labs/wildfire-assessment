# Plano de migração da AWS para VPS Contabo

Data do plano: 2026-08-29

## 1. Objetivo

Executar o Wildfire Assessment em Docker Compose, primeiro na máquina local e
depois em uma VPS Contabo, removendo toda dependência da AWS e fazendo o menor
número possível de alterações funcionais na aplicação.

O ambiente será criado do zero. Não existe banco, objeto, imagem, segredo ou
outro dado na AWS que precise ser recuperado ou migrado.

## 2. Decisões já tomadas

- Manter Google Earth Engine (GEE).
- Manter o bucket GCS científico `wildfire-analyser-outputs`.
- Substituir o S3 da aplicação por Google Cloud Storage.
- Remover Auth0 e não instalar Keycloak ou outro provedor SSO na V1.
- Usar autenticação nativa do Django por e-mail e senha, com acesso sujeito à
  aprovação administrativa.
- Manter Redis.
- Manter o Celery Worker e remover o Celery Beat na V1.
- Remover a limpeza periódica de notificações lidas; o volume será observado e
  uma política de retenção poderá ser adicionada depois.
- Mover a detecção de entregáveis científicos abandonados para a consulta de
  status já feita pela UI, permitindo informar falha e oferecer nova tentativa
  sem um scheduler permanente. Resultados do Celery expiram (~24h); uma tarefa
  sem resultado será tratada como "não está mais rodando".
- Usar PostgreSQL comum, sem PostGIS.
- Usar Docker Compose, sem Terraform ou Kubernetes.
- Usar o Nginx Proxy Manager já existente na VPS.
- Permitir Nginx Proxy Manager local para testar a integração com proxy.
- Não adicionar um Secrets Manager na V1.
- Não colocar segredos no código ou no Git; usar `.env` e arquivo GCP montado
  como somente leitura.
- Manter a geração de relatórios por IA desativada inicialmente.
- Manter os providers OpenAI e Gemini existentes; nenhum exige chave para
  iniciar a aplicação.
- Usar o backend de e-mail de console no desenvolvimento local.
- Usar o Docker Mailserver já existente na VPS quando a conta SMTP dedicada e
  sua senha forem fornecidas.
- Remover todo código e configuração mobile (Expo Push, `expo_push_token`,
  `eas.json`); a V1 é somente web e não adicionará outro sistema de push.
- Usar somente logs de console, healthchecks e rotação de logs na V1.
- Desativar e remover o Grafana Faro e o PostHog da UI; a V1 não envia
  telemetria ou analytics do frontend para serviços externos.
- Não instalar Grafana, Alloy, Prometheus, Loki ou Tempo na V1.
- Não criar um mecanismo de backup específico da aplicação na V1.
- Remover arquivos e configurações AWS obsoletos, pois não precisam ser
  preservados neste workspace.

## 3. Arquitetura-alvo da V1

```text
Nginx Proxy Manager existente
        |
        +-- UI React compilada e servida por Nginx
        |
        +-- Django API executada por Gunicorn
                  |
          +-------+--------+
          |                |
      PostgreSQL         Redis
          ^                ^
          +---- Celery ----+
                  |
                  +-- Google Earth Engine
                  +-- GCS científico
                  +-- GCS de arquivos da aplicação
                  +-- SMTP autenticado da VPS
```

Containers principais:

1. `api`
2. `ui`
3. `postgres`
4. `redis`
5. `celery-worker`

O Nginx Proxy Manager da VPS não fará parte deste Compose. Os serviços `api` e
`ui` serão conectados à rede Docker externa `proxy_network`, já utilizada pelo
proxy e pelo mailserver.

Domínios definidos:

```text
UI:  wildfire.droneai.com.br
API: api-wildfire.droneai.com.br
```

No Cloudflare, criar dois registros `A` com proxy habilitado, apontando
`wildfire` e `api.wildfire` para `62.171.139.124`. Manter o modo SSL/TLS em
`Full (strict)`.

No Nginx Proxy Manager, criar Proxy Hosts separados:

- `wildfire.droneai.com.br` -> serviço Docker `ui`, porta `80`, HTTP interno.
- `api-wildfire.droneai.com.br` -> serviço Docker `api`, porta `8000`, HTTP interno.

Emitir certificados Let's Encrypt para os dois nomes exatos no NPM. O
certificado `*.droneai.com.br` (Cloudflare e NPM) cobre **um** nível à
esquerda — por isso o nome da API é `api-wildfire.droneai.com.br` (rótulo
único com hífen): o nome original `api.wildfire.droneai.com.br` tem dois
níveis e quebra o TLS de borda da Cloudflare (alerta 552 no handshake; o
Universal SSL free não cobre nomes com dois níveis). A decisão também
reserva um namespace por aplicação (`api-wildfire`, futuramente
`api-moodle` etc.) em vez de reivindicar o `api.` genérico.
Habilitar `Force SSL` e HTTP/2 após validar a emissão; habilitar HSTS somente
depois do teste completo de HTTPS.

No ambiente local, haverá duas formas de acesso:

- Acesso direto por portas locais, para desenvolvimento rápido.
- Profile opcional de proxy, para testar com Nginx Proxy Manager local.

### 3.1 Inventário confirmado da VPS

Auditoria somente leitura realizada em 2026-08-29:

| Item | Estado confirmado |
|------|-------------------|
| Host | `vmi2602761.contaboserver.net` (`62.171.139.124`) |
| Sistema | Debian GNU/Linux 12, `x86_64`, kernel `6.1.0-52-amd64` |
| CPU | 6 CPUs lógicas |
| Memória | 11 GiB total, aproximadamente 6,8 GiB disponíveis na auditoria |
| Swap | Swapfile de 8 GiB configurado em 2026-08-29 (`/swapfile`, persistente via fstab) |
| Disco raiz | 194 GiB, aproximadamente 97 GiB livres na auditoria |
| Docker | Serviço ativo e habilitado no boot |
| Docker CLI | `29.7.2` |
| Docker Compose | `v5.4.0` |
| Acesso Docker | Socket `root:docker`; usuário `marcelo` não pertence ao grupo `docker` |
| Nginx Proxy Manager | `jc21/nginx-proxy-manager:2.12.1`, container `npm` |
| Rede do proxy | Rede externa `proxy_network` |
| Portas do proxy | `80` e `443` públicas; administração `81` somente em `127.0.0.1` |
| Mailserver | Docker Mailserver em `mail.droneai.com.br` |
| Imagem do mailserver | `ghcr.io/docker-mailserver/docker-mailserver:latest` |
| SMTP | Portas `25`, `465` e `587`; autenticação `PLAIN` e `LOGIN` disponível |
| IMAP | Portas `143` e `993` |
| TLS do mailserver | Let's Encrypt, certificado válido para `*.droneai.com.br` na auditoria |

Conclusões operacionais:

- Não instalar outro proxy na VPS.
- Não publicar portas da API ou UI no host em produção; o NPM alcançará os
  serviços pelos nomes Docker na `proxy_network`.
- Não publicar PostgreSQL ou Redis no host.
- Usar `sudo docker ...` e `sudo docker compose ...` na VPS. Adicionar
  `marcelo` ao grupo `docker` não é necessário para a V1 e concederia acesso
  equivalente a root.
- A VPS já executa outros projetos Docker. A aplicação não deve reservar portas
  como `8087`, `8088`, `8092`, `8765` ou `9443`.
- A capacidade atual é suficiente para a V1. Swap de 8 GiB já configurado
  (2026-08-29), eliminando o risco de picos de memória. Iniciar o Celery
  Worker com concorrência baixa e medir o uso antes de aumentar paralelismo.
- Não alterar o Compose, as contas ou a configuração interna do mailserver;
  apenas consumi-lo como SMTP autenticado.

### 3.2 Operação do Nginx Proxy Manager — lições da primeira intervenção

Conhecimento obtido ao repontar um domínio em 2026-08-29; seguir à risca para
não repetir os mesmos erros:

- **SSH**: `marcelo@62.171.139.124` funciona por chave, sem senha.
- **sudo sem senha só para `docker`**. Qualquer outra operação root (ler
  `/var/lib/docker/volumes`, sqlite3, editar arquivos do sistema) exige senha
  interativa. Fazer tudo por dentro de containers.
- **Dados do NPM**: banco SQLite no volume `npm_npm_data`
  (`/var/lib/docker/volumes/npm_npm_data/_data/database.sqlite`); certificados
  em `npm_npm_letsencrypt`; Compose em `/home/marcelo/deploy/npm/compose.yaml`;
  admin UI somente em `127.0.0.1:81`.
- **O host não tem `sqlite3`**; consultar o banco com um container
  descartável local:

  ```bash
  sudo docker run --rm -v npm_npm_data:/data nginx:alpine sh -c \
    "apk add --no-cache sqlite && sqlite3 /data/database.sqlite \"SELECT id, domain_names, forward_scheme, forward_host, forward_port, enabled FROM proxy_host;\""
  ```

- **Tabelas úteis**: `proxy_host`, `redirection_host`, `stream`. Atenção ao
  campo `enabled`: acumulam-se várias linhas por domínio (antigas ficam
  desativadas); identificar a linha ativa antes de mexer.
- **REGRA DE OURO — editar o SQLite NÃO atualiza os confs do nginx.** O NPM só
  regenera `/data/nginx/proxy_host/<id>.conf` quando o host é salvo pela
  API/UI. Reiniciar o container `npm` não regenera. Sequência obrigatória para
  edição direta:
  1. backup datado do banco dentro do volume
     (`database.sqlite.bak-<motivo>-YYYYMMDD-HHMMSS`);
  2. `UPDATE` no banco;
  3. editar o `.conf` correspondente no volume com os mesmos valores;
  4. `sudo docker exec npm nginx -s reload` (avisos
     `listen ... http2 deprecated` são normais e preexistentes).
- **Quoting**: nunca aninhar aspas em ssh → docker → sqlite. Passar SQL e
  scripts em base64: `echo <b64> | base64 -d | sudo docker run --rm -i ...`
  (para scripts usar `sh -s`).
- **Testar pelo próprio host**: porta 80 mostra o redirect do Force SSL; HTTPS
  exige forçar o SNI correto:
  `curl -sk --resolve dominio.com.br:443:127.0.0.1 https://dominio.com.br/`
  (sem `--resolve` o handshake falha com `unrecognized name`). Confirmar o
  `<title>` da resposta para garantir qual backend respondeu — HTTP 200
  sozinho não basta (já vimos conteúdo obsoleto com 200).
- **Backends** são alcançados pelo nome do serviço Docker na rede externa
  `proxy_network` (alias do Compose). Conferir quem está na rede com
  `sudo docker network inspect proxy_network`. Parar/remover uma stack:
  `sudo docker compose -f <caminho>/docker-compose.yml down`.
- **Preferir a API/UI do NPM** (admin em `127.0.0.1:81`) quando houver
  credenciais; edição direta do banco é último recurso e sempre com backup.

## 4. Estratégia de buckets GCS

### 4.1 Bucket científico

Manter:

```text
wildfire-analyser-outputs
```

Uso exclusivo:

- Exportações científicas iniciadas pelo GEE.
- GeoTIFFs científicos.
- URLs dos campos `scientific_*_url`.

Substituir o valor fixo em `processor.py` por:

```env
GCS_BUCKET_NAME=wildfire-analyser-outputs
```

### 4.2 Bucket da aplicação

Criar um bucket separado, com nome globalmente disponível, por exemplo:

```text
wildfire-assessment-assets
```

Esse é o nome definido, sujeito à confirmação de disponibilidade global. Caso já
esteja ocupado, escolheremos uma variação antes da criação. Evitar pontos no nome
para não vincular a criação à verificação de propriedade de domínio.

Estrutura:

```text
dev/polygons/
dev/images/
prod/polygons/
prod/images/
```

Configuração:

```env
GCS_APP_BUCKET_NAME=wildfire-assessment-assets
GCS_APP_PREFIX=dev
```

Na VPS, usar `GCS_APP_PREFIX=prod`.

Não misturar os objetos normais da aplicação com os entregáveis científicos.
Isso evita alterações nas permissões, ciclo de vida e organização do bucket
utilizado pelo GEE.

## 5. Gerenciamento simples de configuração e segredos

Não instalar Vault, OpenBao ou outro Secrets Manager na V1.

Arquivos locais não versionados:

```text
.env
secrets/gcp-service-account.json
```

Regras:

- Adicionar `.env` e `secrets/` ao `.gitignore`.
- Criar `.env.example` apenas com nomes e exemplos não sensíveis.
- Aplicar permissão `600` ao `.env` e à credencial GCP na VPS.
- Montar o JSON GCP no `api` e `celery-worker` como somente
  leitura. O app nunca inicializa o GEE por conta própria: passa a string
  JSON à lib `wildfire-analyser`, que autentica. A credencial é necessária
  nos dois containers porque a análise básica roda sincronamente no request
  HTTP (Gunicorn) e os entregáveis científicos rodam no Celery; o polling
  `ee.data.getTaskStatus()` em `processor.py` usa a sessão inicializada pela
  lib no mesmo processo.
- Usar `GOOGLE_APPLICATION_CREDENTIALS` para o SDK GCS.
- Ler o mesmo arquivo quando o `wildfire-analyser` precisar do JSON do GEE.
- Gerar um novo `DJANGO_SECRET_KEY`.
- Gerar novas senhas para PostgreSQL e demais integrações.

Exemplo:

```env
GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcp-service-account.json
GEE_PRIVATE_KEY_FILE=/run/secrets/gcp-service-account.json
```

O código não deverá mais consultar AWS Secrets Manager.

Divisão por tipo de segredo:

- **No `.env` (variáveis de ambiente)** — tudo que não é o JSON GCP:
  - `DJANGO_SECRET_KEY` (gerado novo);
  - credenciais do PostgreSQL (`POSTGRES_DB`/`POSTGRES_USER`/
    `POSTGRES_PASSWORD`, geradas novas — o banco não é publicado no host);
  - conta SMTP dedicada (`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD`) e
    `DEFAULT_FROM_EMAIL`;
  - `OPENAI_API_KEY`/`GEMINI_API_KEY` (quando existirem; opcionais);
  - configurações como `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, origem CORS.
- **Em `secrets/` (arquivos montados como somente leitura)** — apenas o JSON
  do service account GCP, usado por GCS e GEE.

O Compose injeta o `.env` via `env_file`/interpolação; nenhum segredo é
gravado em imagem (build-args vazam para o histórico de camadas). Rotação =
editar o arquivo e reiniciar o serviço afetado.

## 6. Fases de execução

### Fase 0 — Preparação e linha de base

Objetivo: conhecer o estado inicial e preservar evidências de comportamento.

Tarefas:

- Registrar o estado atual do Git.
- Executar os testes unitários existentes com `api.test_settings`.
- Registrar testes que já falhavam antes da migração.
- Identificar todos os imports e mocks de `svc.aws`.
- Identificar todas as variáveis AWS nos arquivos de configuração.
- Confirmar os fluxos que precisam de GCS:
  - upload/download/delete de polígonos;
  - upload/delete de imagens;
  - geração de URLs assinadas;
  - exportação científica do GEE.

Critério de aceite:

- Relatório curto com testes aprovados e falhas preexistentes.
- Linha de base de cobertura registrada (o projeto exige 100% em todas as
  fases).
- Nenhum arquivo funcional alterado nesta fase.

### Fase 1 — Remover configuração e segredos AWS

Objetivo: fazer Django, Celery e GEE iniciarem sem AWS.

Tarefas:

- Remover `get_aws_secret_manager_secret()` do carregamento dos settings.
- Remover `SKIP_AWS_SECRETS`.
- Ler configurações diretamente de variáveis de ambiente.
- Criar validação clara das variáveis obrigatórias.
- Separar configurações de desenvolvimento e produção somente quando isso
  reduzir risco; evitar uma hierarquia complexa de settings.
- Substituir a leitura de `GEE_PRIVATE_KEY_JSON` por leitura de
  `GEE_PRIVATE_KEY_FILE` (ler o conteúdo do arquivo e continuar passando a
  string JSON ao `PostFireAssessment`, cuja interface não muda).
- Substituir a leitura da senha Gmail pelo backend de e-mail configurável do
  Django.
- Criar `.env.example` do zero (não existe hoje), com nomes e exemplos não
  sensíveis.
- Adicionar testes de configuração sem AWS.

Critério de aceite:

- `api` e `celery-worker` importam os settings sem credenciais
  AWS.
- Não existe chamada ao Secrets Manager em runtime.
- Nenhum segredo real está versionado.

### Fase 2 — Substituir S3 por GCS

Objetivo: armazenar polígonos e imagens comuns no bucket GCS da aplicação.

Tarefas:

- Adicionar a dependência oficial `google-cloud-storage`.
- Testar sem GCP real: os testes unitários continuam mockando a camada de
  storage (mesmo padrão dos mocks atuais de S3). Não existe emulador oficial
  do Google para Cloud Storage; para validação local opcional antes da
  credencial chegar, usar o emulador `fake-gcs-server` em container com
  `STORAGE_EMULATOR_HOST` (suportado nativamente pelo client oficial). O
  fluxo do GEE sempre exige credencial real.
- Criar `wildfire_assessment/svc/object_storage.py`.
- Implementar:
  - `upload_polygon`;
  - `download_polygon`;
  - `delete_polygon`;
  - `upload_image`;
  - `delete_image`;
  - `get_signed_image_url`.
- Atualizar serializers, admin e services para usarem a nova camada.
- Atualizar os imports das migrations históricas `0016_backfill_centroids` e
  `0028_backfill_area_ha`, que importam `svc.aws` — o banco novo da VPS roda
  todas as migrations e quebraria com `aws.py` removido.
- Atualizar testes e mocks.
- Preservar a estrutura lógica `polygons/` e `images/` abaixo do prefixo do
  ambiente.
- Tornar o bucket científico configurável via `GCS_BUCKET_NAME`.
- Remover `boto3` e `botocore` quando nenhum uso permanecer.
- Remover `svc/aws.py` quando todos os imports tiverem sido substituídos.

Critério de aceite:

- É possível criar, ler, atualizar e apagar uma área de interesse usando GCS.
- Imagens de uma análise recebem URL assinada válida.
- O fluxo científico continua exportando para `wildfire-analyser-outputs`.
- `rg -i 'boto3|secretsmanager|amazonaws|upload_.*_to_s3'` não encontra código
  de runtime.

### Fase 3 — Simplificar integrações da V1

Objetivo: retirar integrações que não participarão da primeira implantação.

Tarefas:

- Desativar IA por padrão com `AI_ENABLED=false`.
- Retornar resposta funcional e clara quando IA estiver desativada.
- Manter o provider OpenAI existente preparado para uma futura
  `OPENAI_API_KEY`, sem exigir a chave para iniciar a aplicação.
- Manter os providers OpenAI e Gemini existentes. DeepSeek fica fora: o input
  da análise inclui imagens, que ele não suporta.
- Remover todo código mobile: `send_push_notification` e `EXPO_PUSH_URL` em
  `notification.py`, a chamada em `processor.py`, o campo
  `UserProfile.expo_push_token` (model e nova migration para removê-lo), o
  campo no serializer de `/me/` e o `eas.json` da raiz. A V1 é somente web.
- Remover configuração e documentação do Gmail.
- Usar `django.core.mail.backends.console.EmailBackend` localmente.
- Manter a interface de e-mail configurável para SMTP na VPS.
- Remover inicialização e exportação para Grafana Cloud.
- Remover Alloy do Compose.
- Remover dependências OpenTelemetry que não forem mais usadas.
- Desativar e remover o Grafana Faro e o PostHog da UI (`faroConfig.js`,
  `posthogConfig.js`, `@grafana/faro-*` e `posthog-js`).
- Manter logs Python/Django/Celery enviados ao stdout.
- Condicionar as URLs `/api/schema/` ao ambiente de desenvolvimento, pois o
  `drf_spectacular` não estará instalado como app em produção.

Critério de aceite:

- A aplicação inicia sem exigir chaves de IA (OpenAI, Gemini) e sem Gmail,
  Expo, Grafana, Faro ou PostHog.
- Uma notificação por e-mail local aparece nos logs sem conexão SMTP.
- As notificações internas no banco e na interface continuam funcionando.

### Fase 4 — Atualizar banco e imagens Docker

Objetivo: criar containers adequados para desenvolvimento e produção.

Tarefas de banco:

- Trocar `postgis/postgis` por PostgreSQL comum.
- Usar uma versão principal fixada, inicialmente `postgres:16-bookworm`.
- Confirmar que a migration `UnaccentExtension` funciona na imagem escolhida.
- Usar volume nomeado para `/var/lib/postgresql/data`.
- Adicionar healthcheck com `pg_isready`.
- Não publicar a porta do banco em produção.

Tarefas de Redis:

- Fixar uma versão principal da imagem Redis.
- Adicionar healthcheck.
- Usar volume nomeado se a persistência do broker/result backend for
  habilitada.
- Não publicar a porta Redis em produção.

Tarefas de backend:

- Manter build multi-stage.
- Executar como usuário não-root.
- Remover certificados TLS do container.
- Usar Gunicorn em produção.
- Habilitar a reciclagem de workers do Gunicorn como rede de segurança contra
  memory leak: `--max-requests 1000 --max-requests-jitter 100` e
  `--graceful-timeout 600` (proteger streams longos durante a reciclagem;
  o padrão de 30s cortaria um stream de IA em andamento). Ajustar os valores
  após a medição da Fase 6.
- Manter servidor de desenvolvimento somente no override local.
- Adicionar healthcheck HTTP.
- Executar migrations de maneira controlada antes da API.
- Compartilhar a mesma imagem entre API e worker.

Tarefas de frontend:

- Criar build multi-stage com Node.
- Executar `npm ci` durante o build, não na inicialização.
- Compilar o React para arquivos estáticos.
- Servir o build com uma imagem Nginx pequena.
- Manter hot reload somente no override de desenvolvimento.
- Não armazenar segredos no build React; somente configurações públicas.

Critério de aceite:

- `docker compose build` conclui.
- Todos os containers ficam healthy ou running.
- Nenhum container da aplicação precisa rodar como root, salvo justificativa
  documentada para uma imagem de infraestrutura.
- Reiniciar o Compose não apaga o banco.

### Fase 5 — Organizar Docker Compose local e produção

Objetivo: usar a mesma arquitetura nos dois ambientes sem duplicação excessiva.

Arquivos previstos:

```text
compose.yml
compose.override.yml
compose.prod.yml
```

Responsabilidades:

- `compose.yml`: serviços, redes, volumes e defaults comuns.
- `compose.override.yml`: portas locais, mounts do código e comandos de dev.
- `compose.prod.yml`: comandos de produção, rede externa do proxy e ausência de
  mounts do código.

Boas práticas:

- Remover `container_name` para permitir isolamento pelo nome do projeto.
- Regra anti-armadilha: o `compose.override.yml` é carregado implicitamente
  pelo `docker compose up`, mas **passar `-f` desativa esse carregamento
  implícito**. Na VPS usar sempre
  `docker compose -f compose.yml -f compose.prod.yml ...`, para o override de
  desenvolvimento nunca ser aplicado em produção.
- Não herdar do compose atual os mounts `./svc`, `./polygons` e `./db`, que
  não correspondem a diretórios existentes na raiz; o banco passa a usar
  volume nomeado.
- Usar `restart: unless-stopped` em produção.
- Usar `depends_on` com healthchecks onde aplicável.
- Configurar rotação dos logs Docker.
- Iniciar o Celery Worker com concorrência baixa e aumentar somente depois de
  medir o consumo real das análises. O polling do GEE ocupa o worker por
  longos períodos; com o swap configurado, o impacto de picos de memória é
  mitigado, mas a medição antes de aumentar paralelismo continua obrigatória.
- Usar `--max-tasks-per-child 50` no Celery — reciclagem equivalente à do
  Gunicorn no processo que carrega GEE/GDAL; o child encerra somente após
  terminar a tarefa em andamento.
- Definir limites de memória conservadores depois da medição local, levando em
  conta que a VPS possui 11 GiB, já usa aproximadamente 4,8 GiB e não possui
  swap.
- Publicar portas somente em `127.0.0.1` no desenvolvimento sem proxy.
- Não expor PostgreSQL ou Redis na VPS.
- Conectar somente `api` e `ui` à rede externa `proxy_network`; banco e Redis
  permanecem também em uma rede privada própria do projeto.

Critério de aceite:

- Ambiente local inicia com um único comando.
- Ambiente de produção pode ser validado localmente com o compose de produção.
- Não há referência a endpoints AWS no resultado de `docker compose config`.

### Fase 6 — Teste local completo

Objetivo: validar toda a aplicação antes de tocar na VPS.

Fluxo de teste obrigatório:

1. Criar o banco vazio e executar todas as migrations.
2. Criar superusuário.
3. Solicitar acesso com nome e e-mail e confirmar a criação do usuário inativo.
4. Aprovar o usuário pelo Django Admin.
5. Confirmar o link de definição de senha nos logs de e-mail locais.
6. Definir a senha pelo link de uso único e autenticar.
7. Criar uma área de interesse com GeoJSON.
8. Confirmar o objeto em `dev/polygons/` no GCS.
9. Iniciar uma análise.
10. Confirmar execução pelo Celery.
11. Confirmar processamento pelo GEE.
12. Confirmar imagens comuns em `dev/images/`.
13. Confirmar entregável científico em `wildfire-analyser-outputs`.
14. Solicitar um entregável científico assíncrono.
15. Confirmar atualização de status e notificação interna.
16. Confirmar representação do e-mail nos logs.
17. Confirmar que o recurso de IA desativado não quebra o restante da
    aplicação.
18. Reiniciar todos os containers e repetir as verificações principais.

Dados de exemplo para o teste (fonte: repositório `wildfire-analyser`,
commit fixado `1ae1409` em `requirements.txt`):

- Polígonos no diretório `polygons/` do repo:
  - `ccanakkale01.geojson` — pré-fogo 2023-07-01, pós-fogo 2023-07-21
    (incêndio de Çanakkale);
  - `eejatai.geojson` — pré-fogo 2024-09-26, pós-fogo 2024-10-05.
- URLs fixas no commit:
  `https://raw.githubusercontent.com/Brazil-Flying-Labs/wildfire-analyser/1ae1409/polygons/ccanakkale01.geojson`
  e
  `https://raw.githubusercontent.com/Brazil-Flying-Labs/wildfire-analyser/1ae1409/polygons/eejatai.geojson`.
- Os arquivos são `FeatureCollection` com features `MultiPolygon` — formato
  aceito pelo serializer, desde que nenhuma parte tenha área < 10 m²
  (`MIN_MULTIPOLYGON_PART_AREA_M2`) e a área total não exceda 110 000 ha
  (`MAX_AREA_HA`).
- Parâmetros padrão do analisador, compatíveis com os do app:
  `days_before_after=30`, `cloud_threshold=100`, mosaico
  `best_available_per_tile_mosaic`, `roi_only=True`,
  `roi_only_bg_color="black"`.

Critério de aceite:

- O fluxo completo funciona sem credenciais ou endpoints AWS.
- Testes automatizados aprovam.
- Não há erros inesperados nos logs.

### Fase 7 — Integrar Nginx Proxy Manager local

Objetivo: reproduzir localmente a forma de acesso da VPS.

Tarefas:

- Criar um profile ou Compose auxiliar para Nginx Proxy Manager local
  (ex.: `compose.npm.yml` com `profiles: [proxy]`, ativado com
  `docker compose -f compose.yml -f compose.override.yml -f compose.npm.yml
  --profile proxy up -d` — o arquivo extra não é carregado implicitamente,
  então a cadeia `-f` é obrigatória).
- Usar a mesma imagem existente na VPS como referência:
  `jc21/nginx-proxy-manager:2.12.1`.
- Diferença local: no dev o serviço `ui` serve na porta 3000
  (react-scripts), então o Proxy Host local aponta `ui:3000`; na VPS a
  imagem final de nginx serve na porta 80 e o Proxy Host usa `ui:80`.
- Criar localmente uma rede externa chamada `proxy_network`, igual à VPS.
- Usar portas locais não conflitantes para o NPM local (ex.: `8080:80`,
  `8443:443`, `8181:81`) e hosts locais em `/etc/hosts`
  (ex.: `wildfire.droneai.test` e `api.wildfire.droneai.test` → `127.0.0.1`).
- Testar a integração via HTTP (o NPM local não emite certificados para
  domínios fictícios); HTTPS real só é validado na VPS.
- Validado em 2026-08-30: UI e API servidas pelos nomes locais
  (`wildfire.droneai.test` / `api.wildfire.droneai.test`, porta 8080),
  login/sessão/CSRF/CORS funcionando através do proxy; Proxy Hosts criados
  via API do NPM (POST `/api/tokens` + `/api/nginx/proxy-hosts`); o
  `.env` local ganhou `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
  e `CORS_ALLOWED_ORIGINS` com os domínios de teste. Acesso direto por
  portas continua sendo o fluxo padrão de desenvolvimento.
- Validar headers encaminhados, CORS, cookies de sessão e CSRF.
- Configurar `SECURE_PROXY_SSL_HEADER` e `USE_X_FORWARDED_HOST` (somente em
  produção, confiando no proxy) e `CSRF_TRUSTED_ORIGINS` com os dois domínios.
- Não tornar o proxy local obrigatório para o ciclo rápido de desenvolvimento
  (acesso direto por portas continua sendo o fluxo padrão).

Critério de aceite:

- UI e API funcionam pelos nomes locais configurados no proxy.
- Login por e-mail e senha mantém uma sessão segura entre UI e API.
- Django reconhece origem e protocolo encaminhados pelo proxy.

### Fase 8 — Limpar infraestrutura AWS obsoleta

Objetivo: deixar o repositório representando apenas a arquitetura nova.

Remoções previstas, após confirmar que não são mais referenciadas:

- `iac/`.
- `.github/ecs/`.
- Workflows GitHub exclusivos de ECS, ECR, S3, CloudFront e Terraform.
- Diagramas AWS.
- Configuração Alloy/Grafana Cloud.
- Certificados e chaves TLS locais versionados.
- Documentação de deployment AWS.
- Variáveis e scripts AWS.
- Dependências Python AWS.

Atualizações previstas:

- Reescrever `README.md` com setup local e deploy VPS.
- Atualizar `SERVICES.md` ou removê-lo se ficar redundante.
- Atualizar `CLAUDE.md` se ele continuar no repositório.
- Atualizar Makefile com comandos não destrutivos e específicos do projeto.
- Documentar como criar `.env`, credencial GCP e buckets.

Cuidados:

- Migrations Django continuam necessárias para criar o schema vazio. Em
  2026-08-30, as migrations 0001–0035 foram condensadas em um único
  `0001_initial` (squash, helpers RunPython portadas manualmente; índice da
  Notification criado já com o nome final — o `RenameIndex` quebrava no
  PostgreSQL porque o `CREATE INDEX` cai no SQL diferido e roda depois do
  rename). O banco novo valida o schema em um passo e o mecanismo de
  migrations do Django permanece para evoluções futuras.
- Antes de cada remoção, confirmar referências com `rg`.
- Fazer remoções em commits separados para facilitar revisão e reversão pelo
  Git.

Critério de aceite:

- O repositório não contém infraestrutura AWS ativa ou documentação enganosa.
- O projeto constrói e testa depois das remoções.

### Fase 9 — Preparar e implantar na VPS

Objetivo: iniciar uma instalação nova e vazia na Contabo.

Pré-requisitos ainda fornecidos pelo responsável:

- Acesso SSH.
- Configuração de DNS/Cloudflare.
- Credencial GCP/GEE recriada.
- Confirmação da disponibilidade global do nome do novo bucket.
- Conta SMTP dedicada e respectiva senha.
- Endereço que será usado em `DEFAULT_FROM_EMAIL`.

Tarefas:

- ~~Criar um swapfile de 8 GiB antes de subir os containers~~ — já executado em
  2026-08-29: `/swapfile` de 8 GiB ativo e registrado no `/etc/fstab`.
- Usar o Docker Engine já ativo e o Docker Compose `v5.4.0` já instalado.
- Executar comandos Docker com `sudo`, pois `marcelo` não possui acesso ao
  socket Docker.
- Clonar este workspace/repositório em `/home/marcelo/deploy/wildfire-assessment`
  ou outro diretório explicitamente escolhido.
- Criar `.env` de produção e o arquivo GCP com permissões restritas.
- Conectar `api` e `ui` à rede externa existente `proxy_network`.
- Construir as imagens na própria VPS na V1.
- Subir PostgreSQL e Redis.
- Executar migrations.
- Criar o primeiro superusuário.
- Subir API, worker e UI.
- Configurar Proxy Hosts no Nginx Proxy Manager.
- Configurar no Cloudflare os registros `wildfire` e `api.wildfire`.
- Configurar no NPM os hosts `wildfire.droneai.com.br` e
  `api-wildfire.droneai.com.br`, com certificados próprios.
- Validar HTTPS e headers do proxy.
- Executar o smoke test completo em produção.

Critério de aceite:

- Aplicação acessível pelos domínios finais.
- A aplicação não adiciona nenhuma porta pública; permanece acessível apenas
  pelo NPM. As portas públicas já existentes de SSH, proxy e mailserver não são
  alteradas por este projeto.
- Análise completa GEE/GCS funciona na VPS.
- Containers reiniciam corretamente após reboot da VPS.

### 9.1 Roteiro de execução (passo a passo)

Pré-requisitos do responsável: conta SMTP dedicada, registros A no
Cloudflare, decisão sobre o diretório de clone.

1. **Levar o código até a VPS** (uma das opções):
   - Push do branch + `git clone` na VPS (preferido, requer autorização de
     push); ou
   - `rsync`/`scp` do worktree para
     `/home/marcelo/deploy/wildfire-assessment/` (sem push).
2. **Credencial GCP**: copiar `secrets/gcp-service-account.json` para a VPS
   e ajustar o dono para o usuário do container (o Docker preserva a
   permissão do arquivo de origem; o `appuser` é 10001):
   `sudo chown 10001:10001 secrets/gcp-service-account.json && chmod 400 ...`
3. **`.env` de produção** (base: `.env.example`), com:
   `DJANGO_DEBUG=false`, `ENV=prod`, `DJANGO_ALLOWED_HOSTS=api-wildfire.droneai.com.br`,
   `DJANGO_CSRF_TRUSTED_ORIGINS=https://wildfire.droneai.com.br,https://api-wildfire.droneai.com.br`,
   `CORS_ALLOWED_ORIGINS=https://wildfire.droneai.com.br`,
   `DB_*` novas, `EMAIL_BACKEND=smtp`, `EMAIL_HOST=mail.droneai.com.br`,
   `EMAIL_PORT=587`, `EMAIL_USE_TLS=true`, credenciais SMTP dedicadas,
   `DEFAULT_FROM_EMAIL`, `AI_ENABLED=true`, `DEEPSEEK_API_KEY=<chave>`,
   `GCS_APP_PREFIX=prod`, `UI_BASE_URL=https://wildfire.droneai.com.br`.
4. **Subir**:
   `sudo docker compose -f compose.yml -f compose.prod.yml up -d --build`
   (a cadeia `-f` desativa o override de dev).
5. **Migrate + superusuário + seed** (o entrypoint já roda o migrate; o
   superusuário é criado manualmente; as UCs de SP são semeadas pelo
   comando, que baixa do DataGEO, unifica as partes e sobe ao GCS —
   idempotente, pula nomes existentes e unidades acima de 110.000 ha):
   `sudo docker compose -f ... exec api python manage.py createsuperuser`
   `sudo docker compose -f ... exec api python manage.py register_ucs`
   O provider de IA ativo (DeepSeek) é definido pela migration 0003.
6. **Rede do proxy**: confirmar que api e ui entraram na `proxy_network`
   (`sudo docker network inspect proxy_network`).
7. **Proxy Hosts no NPM** (API, mesmo procedimento do local):
   token → `POST /api/nginx/proxy-hosts` para `wildfire.droneai.com.br` →
   `ui:80` e `api-wildfire.droneai.com.br` → `api:8000`; solicitar
   certificados Let's Encrypt para os dois nomes; habilitar Force SSL.
8. **Cloudflare**: registros `A` `wildfire` e `api.wildfire` →
   `62.171.139.124`, proxy habilitado, SSL/TLS `Full (strict)`.
9. **Smoke test na VPS** (espelha a Fase 6): health, solicitar acesso,
   aprovação, login, criar AOI, análise GEE, entregável científico,
   e-mail real, report AI (DeepSeek), restart dos containers.

## 7. Observabilidade mínima da V1

Implementar somente:

- Logs Django, Gunicorn e Celery no stdout/stderr.
- Logs de acesso do Nginx que serve a UI.
- Healthcheck da API.
- Healthchecks de PostgreSQL e Redis.
- Rotação dos logs Docker com `max-size` e `max-file`.
- Inspeção por `docker compose ps` e `docker compose logs`.
- `restart: unless-stopped` na VPS.

Não implementar nesta versão:

- Alertas por e-mail.
- Grafana.
- Prometheus.
- Loki.
- Tempo.
- Alloy.
- APM externo.
- Faro (telemetria do frontend).
- PostHog (analytics).

## 8. E-mail

Desenvolvimento local:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

O e-mail será impresso nos logs do worker. Nenhum servidor SMTP local é
necessário para o primeiro teste.

Produção, usando o Docker Mailserver já instalado:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=mail.droneai.com.br
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
DEFAULT_FROM_EMAIL=
```

O endpoint `mail.droneai.com.br:587` oferece STARTTLS e autenticação SMTP
`PLAIN`/`LOGIN`. O mailserver está configurado com `PERMIT_DOCKER=none`, então a
aplicação não deve tentar relay anônimo pela rede Docker. Deve ser criada ou
escolhida uma conta SMTP dedicada para este projeto.

A auditoria encontrou a aplicação existente `/home/marcelo/Code/mailsender`
configurada para a porta `587`, com uma conta existente de `droneai.com.br` e
senha presente no `.env`. Isso confirma um uso real do SMTP, mas não autoriza a
reutilização ou cópia dessa credencial. Criar preferencialmente
`wildfire@droneai.com.br` (ou outro remetente definido pelo responsável) com
senha própria. Dentro do container da aplicação, não usar `localhost`: ele
apontaria para o próprio container, e não para o mailserver.

Não fixar remetente, usuário ou senha no código. Não modificar o Compose do
mailserver como parte desta migração.

## 8.1 Autenticação nativa da V1

Não usar Auth0, Keycloak, SSO ou JWT externo na V1. Reaproveitar o sistema de
usuários, senhas, sessões e tokens de definição de senha do Django.

Fluxo de acesso:

1. O interessado informa nome e e-mail em uma tela pública de solicitação.
2. A API sempre apresenta uma resposta genérica, sem revelar se o e-mail já
   existe.
3. O backend cria um usuário inativo, usando o e-mail normalizado como login e
   uma senha inutilizável.
4. A solicitação aparece no Django Admin; não haverá alerta administrativo por
   e-mail na V1.
5. O administrador aprova o usuário por uma ação explícita no Admin.
6. A aprovação ativa a conta e envia um link temporário e de uso único para
   definição da primeira senha.
7. Depois de definir a senha, o usuário pode autenticar e usar a aplicação.

Implementação:

- Remover `@auth0/auth0-react`, `social_django`, o backend social Auth0, a
  Auth0 Management API e todas as variáveis `AUTH0_*`.
- Remover o botão Auth0 do Django Admin; o administrador entra com a conta
  local criada por `createsuperuser`.
- Usar `SessionAuthentication` do Django REST Framework.
- Adicionar `django.middleware.csrf.CsrfViewMiddleware` ao MIDDLEWARE (ausente
  hoje); sem ele o Django Admin ficaria sem proteção CSRF na autenticação por
  sessão.
- Trocar `AUTHENTICATION_BACKENDS` — hoje um `set` com Auth0 — por uma lista
  contendo apenas `django.contrib.auth.backends.ModelBackend`.
- Criar endpoints mínimos para solicitar acesso, obter CSRF, login, logout,
  consultar a sessão atual, definir a primeira senha e recuperar senha.
- Fazer a UI enviar cookies somente com `credentials: "include"` e incluir o
  token CSRF nas operações de escrita.
- Instalar o `corsheaders` também em produção (hoje só existe em local/dev)
  aceitando exclusivamente `https://wildfire.droneai.com.br`; remover
  `CORS_ALLOW_ALL_ORIGINS`.
- Usar cookies `Secure`, `HttpOnly` para a sessão e `SameSite=Lax`, mantendo a
  proteção CSRF do Django.
- Configurar validade curta para o link inicial e permitir que o administrador
  reenvie um novo link quando necessário.
- Aplicar throttling por IP e e-mail aos endpoints públicos de solicitação,
  login e recuperação de senha.
- Atualizar testes, textos de privacidade e interface que mencionam Auth0.

Para facilitar SSO no futuro, preservar o e-mail normalizado e verificado como
identificador da conta. Um provedor OIDC posterior poderá ser associado ao
mesmo usuário, sem recriar seus dados da aplicação.

## 9. Inteligência artificial

Decisão revisada em 2026-08-30: a V1 **ativa a IA apenas via DeepSeek
(texto)**, com os fluxos de análise/chat/report. O DeepSeek não aceita
imagens, então os prompts ganharam modo somente texto (`include_images=False`)
e o relatório não baixa imagens para esse provider.

```env
AI_ENABLED=true
DEEPSEEK_API_KEY=<chave>
```

- Provider ativo: `deepseek` / `deepseek-chat` no singleton `AIProvider`.
- A aplicação continua iniciando sem chave de IA; os endpoints respondem
  503 previsível quando `AI_ENABLED=false`.
- Providers OpenAI e Gemini permanecem preparados (com imagens) para uso
  futuro.
- O idioma da análise segue o perfil do usuário; o idioma do relatório é
  enviado pelo cliente (a UI envia o idioma atual do app).

## 10. Itens fora do escopo da V1

- Recuperação ou migração de dados da AWS.
- Compatibilidade com AWS.
- Terraform/OpenTofu.
- Kubernetes.
- Registry privado de imagens.
- CI/CD de deploy automático.
- Backup específico desta aplicação.
- Alta disponibilidade.
- Escala horizontal.
- PostGIS.
- Observabilidade completa.
- Aplicativos mobile e Electron (a V1 é somente web; código mobile removido).
- IA local ou automática sem API configurada.
- Alterações no mailserver da VPS antes de receber suas especificações.

## 11. Informações pendentes do responsável

Antes da fase de integração/produção, obter:

- ~~Projeto e service account GCP que substituirão a credencial perdida.~~ —
  resolvido (projeto `post-fire-assessment` intacto, chave reemitida).
- ~~Confirmação de acesso desse service account ao Earth Engine.~~ — resolvido.
- ~~Confirmar a disponibilidade global de `wildfire-assessment-assets`~~ —
  resolvido (bucket criado em 2026-08-30).
- ~~Usuário, senha e remetente da conta SMTP dedicada.~~ — resolvido em
  2026-08-30: conta `wildfire@droneai.com.br` (autenticação STARTTLS 587
  validada). Credenciais no arquivo de produção local
  `~/.wildfire-deploy/env.prod` (não versionado).

### Como obter a credencial GCP/GEE (atualizado: o GCP está intacto)

Confirmado com o responsável: a conta GCP **não** foi apagada — projeto,
bucket científico `wildfire-analyser-outputs`, service account e o registro
dela no Earth Engine continuam existindo. Não é necessário recriar nada;
basta reemitir a chave e criar o bucket novo da aplicação:

1. No Google Cloud Console, selecionar o projeto do bucket científico.
2. IAM & Admin → Service Accounts → a SA existente usada pelo
   wildfire-analyser → Keys → Add Key → JSON. Salvar como
   `secrets/gcp-service-account.json` no worktree (gitignored; nunca
   versionar nem compartilhar — é a chave privada da SA). A chave antiga
   (perdida com a AWS) não importa: chaves são reemitidas à vontade e o
   registro no Earth Engine é da SA, não da chave.
3. Criar o bucket da aplicação `wildfire-assessment-assets` (ou variação se
   indisponível) em `us-central1`, storage class Standard.
4. Conceder `roles/storage.objectAdmin` à SA no bucket novo (Buckets →
   Permissions), caso o papel do projeto ainda não cubra.
5. Anotar: nome do projeto, e-mail da SA e região do bucket científico; a
   validação completa acontece no teste local da Fase 6.

Estado da validação (2026-08-30):

- Projeto: `post-fire-assessment`; SA:
  `gee-service-account@post-fire-assessment.iam.gserviceaccount.com`.
- Credencial normalizada em `secrets/gcp-service-account.json` (600) e
  validada: o GEE inicializa e responde — a SA está registrada no Earth
  Engine. A chave antiga do Fedora continuava válida.
- A SA não tem `storage.buckets.list` no projeto nem `buckets.get` no bucket
  científico — irrelevante para a aplicação (ela só guarda URLs), mas
  implica conceder `Storage Object Admin` **no bucket novo** explicitamente.
- ⚠️ **Pin obrigatório**: `earthengine-api==1.7.1` (adicionado ao
  `requirements.txt`). Versões novas (ex.: 1.7.41) quebram o fluxo de
  autenticação por service account da lib (`invalid_scope`). Como a lib é
  instalada via git (pyproject sem pin), a versão deve ser fixada por nós.
- Bucket da aplicação `wildfire-assessment-assets` criado (2026-08-30) com
  acesso público **impedido** (PAP enforced — o correto; imagens só via
  signed URLs) e `Storage Object Admin` concedido à SA. Ciclo completo de
  objetos validado: upload, download, signed URL V4, list e delete.

Informações que deixaram de estar pendentes após a auditoria:

- Domínios: `wildfire.droneai.com.br` e
  `api-wildfire.droneai.com.br`.
- Rede Docker do proxy: `proxy_network`.
- Proxy: Nginx Proxy Manager `2.12.1`.
- TLS do proxy: gerenciado pelo NPM, que já possui armazenamento persistente
  para Let's Encrypt; emitir/selecionar os certificados dos novos domínios ao
  criar os Proxy Hosts.
- SMTP: `mail.droneai.com.br:587`, STARTTLS.
- Existe uma aplicação na VPS usando uma conta autenticada desse SMTP; para este
  projeto será criada uma conta independente.
- Capacidade: 6 CPUs, 11 GiB de RAM e aproximadamente 97 GiB livres na data da
  auditoria.
- Docker e Docker Compose já instalados e ativos.

## 12. Definição de pronto da migração

A migração estará concluída quando:

- Não existir chamada de runtime para AWS.
- Dependências e configurações AWS tiverem sido removidas.
- A aplicação iniciar do zero com Docker Compose.
- PostgreSQL comum executar todas as migrations.
- Redis atender Celery e cache Django.
- Solicitação, aprovação administrativa, definição de senha, login, logout e
  recuperação de senha funcionarem localmente e na VPS.
- Polígonos e imagens comuns forem armazenados no bucket GCS de assets.
- GEE continuar processando análises.
- Entregáveis científicos forem exportados para
  `wildfire-analyser-outputs`.
- A simulação local de e-mail funcionar.
- IA permanecer desativada sem prejudicar o fluxo principal.
- A UI e a API forem publicadas pelo Nginx Proxy Manager existente.
- O fluxo completo tiver sido testado localmente antes do deploy.
- O repositório não contiver infraestrutura AWS obsoleta ou segredos reais.
- O repositório não contiver código ou configuração mobile (Expo) nem
  telemetria de frontend (Faro/PostHog).
- A cobertura dos testes do backend for de 100% (regra do projeto).
- A VPS tiver swap configurado antes da implantação (já satisfeito:
  8 GiB ativos desde 2026-08-29).

## 13. Estratégia de commits

Manter mudanças pequenas e revisáveis:

1. `config: remove AWS Secrets Manager dependency`
2. `storage: replace S3 operations with GCS`
3. `config: make scientific GCS bucket configurable`
4. `cleanup: disable AI and remove push, Faro/PostHog and cloud observability`
5. `docker: use PostgreSQL and production-ready images`
6. `docker: split local and production compose configuration`
7. `auth: replace Auth0 with native session authentication`
8. `test: cover GCS and no-AWS configuration`
9. `cleanup: remove AWS infrastructure and documentation`
10. `docs: document local setup and VPS deployment`

Executar testes relevantes após cada commit e o conjunto completo ao final de
cada fase, mantendo a cobertura do backend em 100% (regra obrigatória do
projeto) em todos os pontos.

Modo de execução:

- As fases 0→3 são **sequenciais** (tocam os mesmos arquivos do backend e os
  mesmos testes); cada fase termina com suíte completa verde e cobertura em
  100%, seguida de relatório e confirmação antes da fase seguinte.
- As fases 4-5 (Docker/compose) e a limpeza de UI podem rodar **em paralelo**
  com as fases de backend, pois editam arquivos disjuntos (`Dockerfile`,
  `compose*.yml`, `entrypoint.sh`, `ui/src`) — sem risco de conflito.
- As fases 6 e 9 aguardam os itens pendentes da seção 11 (credencial GCP/GEE,
  bucket, conta SMTP, DNS).
- Nenhum push acontece sem autorização explícita.
