# API de Livros

API REST desenvolvida em Python com FastAPI para o gerenciamento de uma coleção de livros. O projeto implementa um CRUD completo, autenticação, cache com Redis, processamento assíncrono com Celery, banco de dados via ORM e execução em containers (Podman/Docker), seguindo boas práticas de desenvolvimento back-end.

## Sumário

- [Funcionalidades](#funcionalidades)
- [Tecnologias utilizadas](#tecnologias-utilizadas)
- [Endpoints](#endpoints)
- [Como executar](#como-executar)
  - [Variáveis de ambiente](#variáveis-de-ambiente-env)
  - [Podman Compose](#executando-a-aplicação-com-podman-compose)
  - [API e worker locais](#execução-local-da-api-e-do-worker)
- [Kubernetes no Docker Desktop](#execução-com-kubernetes-no-docker-desktop-windows)
- [Como testar o Redis](#como-testar-o-redis)
- [Processamento assíncrono com Celery](#processamento-assíncrono-com-celery)
- [Mensageria com Kafka](#mensageria-com-kafka)
- [Documentação](#documentação)
- [O que este projeto demonstra](#o-que-este-projeto-demonstra)
- [Pytest](#pytest)

## Funcionalidades

- **CRUD completo de livros**: criar, listar, atualizar e remover
- **Autenticação HTTP Basic** para proteger os endpoints
- **Cache com Redis** nas consultas, com expiração automática (TTL de 30 segundos)
- **Processamento assíncrono com Celery**, usando Redis como broker/backend de filas
- **Paginação** na listagem de livros (parâmetros `page` e `limit`)
- **Validação de dados** de entrada com Pydantic
- **Documentação interativa** gerada automaticamente com Swagger
- **Prevenção de registros duplicados**

## Tecnologias utilizadas

- **Python 3.14 ou superior**
- **FastAPI** — framework para construção da API
- **SQLAlchemy** — ORM para acesso ao banco de dados
- **SQLite** — banco de dados
- **Redis** — cache de consultas e broker de filas
- **Celery** — processamento de tarefas assíncronas em background
- **Uvicorn** — servidor ASGI
- **Poetry** — gerenciamento de dependências
- **Podman / Docker Compose** — containerização da aplicação
- **Kubernetes** — execução da API em um cluster local no Docker Desktop
- **Apache Kafka** — mensageria/streaming de eventos entre serviços
- **kafka-python** — cliente Python usado para publicar mensagens no Kafka


## Endpoints

| Método | Rota                     | Descrição                                     |
| ------ | ------------------------ | ---------------------------------------------- |
| GET    | `/livros`                | Lista os livros com paginação                  |
| POST   | `/adiciona`              | Adiciona um novo livro                         |
| PUT    | `/atualiza/{id_livro}`   | Atualiza um livro existente                    |
| DELETE | `/deletar/{id_livro}`    | Remove um livro                                |
| GET    | `/debug/redis`           | Exibe os dados atualmente em cache             |
| POST   | `/calcular/soma`         | Soma dois números como tarefa assíncrona       |
| POST   | `/calcular/fatorial`     | Calcula o fatorial de um número como tarefa assíncrona |
| GET    | `/tarefas/recentes`      | Lista o status/resultado das últimas tarefas do Celery |

Os endpoints de CRUD (`/livros`, `/adiciona`, `/atualiza/{id_livro}` e `/deletar/{id_livro}`) exigem autenticação HTTP Basic. A documentação, a página inicial e os endpoints de tarefas e depuração não exigem autenticação no código atual.

---

## Como executar

### Pré-requisitos

- Git e um terminal para obter o projeto e executar os comandos.
- Para executar a API e o worker localmente: **Python 3.14 ou superior**, pip e Poetry.
- Para executar com containers: Podman com `podman-compose` ou Docker Desktop com Docker Compose. O Python da API é instalado na imagem.
- Para executar com Kubernetes: consulte os pré-requisitos da seção específica abaixo.

### Antes de começar

Clone o repositório e entre na pasta do projeto:

```bash
git clone https://github.com/GbrieuZ/api-livros
cd api-livros
```

### Instalação do Podman

Instale o Podman de acordo com o seu sistema operacional:

- **Linux:** `sudo apt update && sudo apt install -y podman`
- **Mac:** `brew install podman`
- **Windows:** `choco install podman-cli`

Em seguida, instale o podman-compose (independente do sistema operacional):

```bash
pip install podman-compose
```

O arquivo `docker-compose.yml` é responsável por definir os serviços, portas, volumes e variáveis de ambiente da aplicação. O Compose define seis serviços: **API** (`app`), **Redis** (`redis`), **worker Celery** (`celery`), **ZooKeeper** (`zookeeper`), **Kafka** (`kafka`) e **Kafka UI** (`kafka-ui`).

As dependências do projeto (FastAPI, Celery, Redis, SQLAlchemy, etc.) estão listadas no `pyproject.toml`/`poetry.lock` e são instaladas automaticamente pelo **Poetry** durante o build da imagem usada pela API e pelo worker (`podman-compose up --build`), não sendo necessário rodar `poetry install` manualmente.

### Variáveis de ambiente (.env)

Para executar pelo Compose, crie um arquivo `.env` na raiz do projeto. Na execução local, ele também é usado para carregar as configurações; alternativamente, elas podem ser definidas no ambiente do processo. No Kubernetes, as variáveis da API estão no `deployment.yaml`. O `.env` guarda as credenciais de autenticação e os dados de conexão do banco e do Redis, por isso **não é versionado** (está no `.gitignore`). O repositório traz um `.env.example` como modelo.

O `.dockerignore` exclui `.env` do build para que suas configurações não sejam incorporadas à imagem pelo `COPY . .`. O Compose continua recebendo essas variáveis pelo `env_file`; na execução local, a aplicação usa `load_dotenv()`.

Crie o seu a partir do exemplo:

```bash
cp .env.example .env
```

No Windows (PowerShell):

```powershell
copy .env.example .env
```

Depois abra o `.env` e preencha os valores:

| Variável       | Descrição                            | Valor no Compose           | Valor rodando local          |
| -------------- | ------------------------------------ | -------------------------- | ---------------------------- |
| `MEU_USUARIO`  | Usuário da autenticação HTTP Basic   | definido por você          | definido por você            |
| `MINHA_SENHA`  | Senha da autenticação HTTP Basic     | definida por você          | definida por você            |
| `DATABASE_URL` | URL de conexão do banco (SQLAlchemy) | `sqlite:///./livros.db`    | `sqlite:///./livros.db`      |
| `REDIS_HOST`   | Host do Redis                        | `redis`                    | `localhost`                  |
| `REDIS_PORT`   | Porta do Redis                       | `6379`                     | `6379`                       |
| `REDIS_URL`    | URL do broker/backend do Celery      | `redis://redis:6379/0`     | `redis://localhost:6379/0`   |
| `KAFKA_SERVER` | Endereço do broker Kafka | `kafka:9092` | `localhost:9092` |

Exemplo de `.env` para execução via Docker/Podman Compose:

```dotenv
MEU_USUARIO=admin
MINHA_SENHA=troque-esta-senha
DATABASE_URL=sqlite:///./livros.db
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0
KAFKA_SERVER=kafka:9092
```

> **Importante:** ao executar via Compose, `REDIS_HOST` precisa ser **`redis`** (o nome do serviço no `docker-compose.yml`), e não `localhost`. Dentro do container, `localhost` aponta para o próprio container da API — onde não existe Redis rodando — e tanto o cache quanto o Celery falhariam ao conectar. Só use `localhost` se for rodar a API fora de container.

O `docker-compose.yml` carrega esse arquivo automaticamente nos serviços `app` e `celery` através do `env_file`:

```yaml
services:
  app:
    env_file:
      - .env
  celery:
    env_file:
      - .env
```

### Executando a aplicação com Podman Compose

**Passo 1** — No Windows e macOS, crie a máquina virtual do Podman, caso ainda não exista. No Linux com Podman nativo, pule os passos 1 e 2:

```bash
podman machine init
```

**Passo 2** — Inicie a VM, caso esteja parada:

```bash
podman machine start
```

**Passo 3** — Construa a imagem da aplicação e inicie os seis serviços (API, Redis, Celery, ZooKeeper, Kafka e Kafka UI) em segundo plano. O Compose publica a API na porta 8000 do computador:

```bash
podman-compose up --build -d
```

**Passo 4** — Acesse o backend no navegador:

```text
http://localhost:8000/livros
```

**Passo 5** — Pare e remova os containers da aplicação:

```bash
podman-compose down
```
> **Docker Compose:** se preferir Docker Desktop, mantenha-o em execução e use `docker compose up --build -d` e `docker compose down`. Nesse caso, não execute os comandos `podman machine`.

O **Uvicorn** pega a API FastAPI, sobe um servidor e a deixa acessível via navegador ou Postman.

### Execução local da API e do worker

Nesta alternativa, a API e o worker rodam no computador. Redis e Kafka continuam sendo serviços externos, que podem rodar em containers. Use um terminal para preparar os serviços, um para a API e outro para manter o worker em execução.

Para testar a criação de livros e a publicação de eventos, disponibilize também um broker Kafka acessível pelo computador. O Compose atual anuncia o endereço interno `kafka:9092`; apenas expor a porta 9092 não configura o acesso de clientes externos à rede do Compose. Para executar toda a integração sem ajustar os listeners do Kafka, utilize a opção com Compose.

**Passo 1** — Instale o Poetry e as dependências do projeto:

```bash
pip install poetry
poetry install
```

**Passo 2** — Crie o `.env` conforme a seção de variáveis de ambiente, preencha as credenciais e ajuste o Redis local:

```dotenv
REDIS_HOST=localhost
REDIS_URL=redis://localhost:6379/0
```

Se houver um broker Kafka configurado para acesso local na porta 9092, defina também `KAFKA_SERVER=localhost:9092`. O endereço anunciado pelo broker precisa ser acessível a partir do computador.

**Passo 3** — Suba o Redis na porta 6379. A forma mais simples é via container:

```bash
podman run -d -p 6379:6379 --name livros-redis redis:7-alpine
```

**Passo 4** — No segundo terminal, inicie a API FastAPI:

```bash
poetry run uvicorn main:app --reload
```

**Passo 5** — No terceiro terminal, inicie o worker do Celery na fila `livros`:

```bash
poetry run celery -A celery_app:celery_app worker -Q livros --loglevel=info
```

> No Windows, acrescente `--pool=solo` ao comando do worker:
> `poetry run celery -A celery_app:celery_app worker -Q livros --loglevel=info --pool=solo`

Ao iniciar, o worker deve exibir a fila e as tarefas registradas. Se isso não aparecer, as tarefas não serão executadas:

```text
[queues]
  .> livros           exchange=livros(direct) key=livros

[tasks]
  . tasks.fatorial
  . tasks.somar
```

---

## Execução com Kubernetes no Docker Desktop (Windows)

Esta alternativa executa a API no Kubernetes local do Docker Desktop.

### Pré-requisitos

- Docker Desktop instalado e em execução, usando containers Linux.
- Kubernetes ativado no Docker Desktop.
- Comando `kubectl` disponível.
- Git Bash para executar o arquivo `script.sh`.

Não é necessário instalar o Minikube ao utilizar o Kubernetes do Docker Desktop.

### 1. Ativar o Kubernetes

No Docker Desktop, acesse **Kubernetes → Create cluster** ou
**Settings → Kubernetes → Enable Kubernetes**, conforme a versão.

Aguarde a inicialização e execute no terminal:

```bash
kubectl config use-context docker-desktop
kubectl get nodes
```

O nó `docker-desktop` deve apresentar o status **Ready**.

### 2. Configurar o .dockerignore

Na raiz do projeto, ao lado do `Dockerfile`, crie o arquivo `.dockerignore`:

```text
.venv
__pycache__
*.pyc
.env
```

Isso impede que o ambiente virtual local seja enviado ao build e evita
o erro `invalid file request .venv/bin/python3`. A entrada `.env` evita incorporar as configurações locais à imagem.

### 3. Criar a imagem Docker

No terminal, dentro da raiz do projeto, execute:

```bash
docker build -t livros-api:latest .
```

Aguarde o build terminar com sucesso antes de continuar.

O nome da imagem deve corresponder ao definido no `deployment.yaml`:

```yaml
image: livros-api:latest
imagePullPolicy: Never
```

Essa configuração utiliza a imagem local, que precisa estar disponível
no ambiente do Kubernetes.

### 4. Executar o script

Abra o terminal **Git Bash** na raiz do projeto e execute:

```bash
bash script.sh
```

Ao executar dessa forma, não é necessário usar `chmod +x`.

O script aplica os arquivos `deployment.yaml` e `service.yaml`, aguarda
o Deployment ficar disponível e inicia o encaminhamento da porta local
8000 para a porta 80 do serviço, que direciona à porta 8000 da API.
A porta local 8000 precisa estar livre; não mantenha outra instância da API
ou outro encaminhamento usando essa mesma porta.

Se aparecer o aviso de que o Minikube não está instalado, ele pode ser
ignorado desde que o contexto seja `docker-desktop` e o Kubernetes esteja
funcionando.

### 5. Acessar a API

- Página inicial: http://localhost:8000/
- Documentação Swagger: http://localhost:8000/docs

Mantenha o terminal do script aberto enquanto utiliza a aplicação.
Encerrar o encaminhamento de portas interrompe o acesso por localhost,
mas não remove os recursos do Kubernetes.

### Verificar problemas

Confira o estado dos recursos:

```bash
kubectl get deployments,pods,services
```

Consulte os logs da API:

```bash
kubectl logs deployment/livros-api --tail=100
```

Se o navegador apresentar conexão recusada, execute o encaminhamento
manualmente para visualizar possíveis erros:

```bash
kubectl port-forward svc/livros-api-service 8000:80
```

Quando aparecer `Forwarding from`, mantenha o terminal aberto e acesse
novamente a documentação.

> O script atual abre o navegador mesmo quando alguma etapa falha.
> A mensagem “Aplicação disponível” não substitui a verificação dos
> erros apresentados no terminal.

### Atualizar a aplicação após mudanças no código

Refaça a imagem e reinicie os pods para utilizarem o novo build:

```bash
docker build -t livros-api:latest .
kubectl rollout restart deployment/livros-api
kubectl rollout status deployment/livros-api
```

Se a conexão com o navegador for interrompida, execute novamente o
`port-forward`.

### Limitações desta configuração

Os manifestos atuais configuram somente a API. Redis, Kafka e o worker
Celery precisam ser disponibilizados e configurados separadamente para
as funcionalidades que dependem deles.

As variáveis definidas no `deployment.yaml` são fornecidas ao container.
O Kubernetes não carrega automaticamente o `.env` como o Compose faz
com `env_file`. Como esse arquivo está excluído pelo `.dockerignore`, ele não
é copiado para a imagem; as configurações necessárias devem ser fornecidas
no ambiente do container. O manifesto atual define `DATABASE_URL`,
`MEU_USUARIO` e `MINHA_SENHA`; os valores de autenticação `admin` são exemplos
para uso local.

O SQLite não possui volume persistente nessa configuração; alterações
nos dados dentro do container podem ser perdidas quando ele for recriado.

---

## Como testar o Redis

**Passo 1** — Abra o terminal e inicie o FastAPI:

```bash
poetry run fastapi dev main.py
```

> Rodando dessa forma (fora do container), lembre-se de ajustar o `.env` para `REDIS_HOST=localhost` e `REDIS_URL=redis://localhost:6379/0`, e de ter o Redis disponível na porta 6379.

**Passo 2** — No Insomnia (ou programa similar), adicione as requisições (GET, POST, PUT, DELETE) de acordo com o código.

**Passo 3** — No endpoint `GET /debug/redis` você verá o tempo (TTL) decrescendo de 30 conforme atualiza, representando o tempo que o livro fica salvo em cache.

---

## Processamento assíncrono com Celery

Além do cache, o projeto usa **Celery** para executar tarefas em segundo plano (background), utilizando o **Redis** como broker e backend de resultados.

### Como funciona

- O **Celery** pega tarefas definidas em `tasks.py` e as executa de forma assíncrona, sem travar a API enquanto elas processam.
- O **Redis** funciona como o sistema de filas: quando uma tarefa é criada, ela é enviada para o Redis, e o worker do Celery a retira de lá para executar.
- Juntos, Redis e Celery formam a base do processamento assíncrono de tarefas da aplicação.

### Estrutura

- O serviço `celery` foi adicionado ao `docker-compose.yml`, junto com o `redis` já existente, usando o mesmo build da API
- O `celery_app.py` configura a conexão do Celery com o Redis (broker e backend), lendo o host/porta a partir das variáveis de ambiente
- O `main.py` foi ajustado para conectar no Redis do container (`redis`) em vez de `localhost`, também via variáveis de ambiente
- As tarefas (`somar` e `fatorial`) ficam em `tasks.py` e são registradas na fila `livros`

### Fila e registro das tarefas

Para que a tarefa saia da API e chegue até o worker, dois pontos precisam estar alinhados no `celery_app.py`:

```python
celery_app = Celery(
    "tarefas_livros",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks"],  # garante que o worker carregue e registre as tarefas de tasks.py
)

celery_app.conf.update(
    # A API publica e o worker consome na MESMA fila ("livros")
    task_default_queue="livros",
    task_routes={
        "tasks.somar": {"queue": "livros"},
        "tasks.fatorial": {"queue": "livros"},
    },
)
```

- **`include=["tasks"]`** — sem isso, o worker sobe sem conhecer as tarefas e não consegue executá-las.
- **`task_default_queue` + `task_routes`** — definem que a API publica na fila `livros`, a mesma que o worker escuta via `-Q livros` no `docker-compose.yml`:

```yaml
  celery:
    command: ["poetry", "run", "celery", "-A", "celery_app:celery_app", "worker", "-Q", "livros", "--loglevel=info"]
```

> Se a fila da API e a do worker forem diferentes, ou se o `tasks.py` não for carregado, as tarefas ficam permanentemente com status `PENDING` e `resultado: null` — no Celery, `PENDING` significa tanto "ainda na fila" quanto "tarefa desconhecida".

### Tarefas disponíveis

| Endpoint               | Descrição                                       |
| ------------------------ | ------------------------------------------------ |
| `POST /calcular/soma`     | Envia uma tarefa que soma dois números          |
| `POST /calcular/fatorial` | Envia uma tarefa que calcula o fatorial de `n`  |
| `GET /tarefas/recentes`   | Consulta status e resultado das últimas tarefas enviadas |

Cada chamada em `/calcular/soma` ou `/calcular/fatorial` retorna um `task_id`, que fica salvo em uma lista no Redis (`tarefas_ids`, limitada às 50 tarefas mais recentes) e pode ser consultado depois em `/tarefas/recentes`.

### Como testar

**Passo 1** — Suba a aplicação via Docker/Podman Compose (isso já sobe API, Redis e Celery juntos):

```bash
podman-compose up --build
```

**Passo 2** — No Insomnia (ou similar), faça uma requisição `POST` para `/calcular/soma` ou `/calcular/fatorial`, informando os parâmetros (`a`/`b` ou `n`).

**Passo 3** — Acompanhe os logs no terminal: o worker do Celery vai pegar a tarefa da fila (Redis) e executá-la em segundo plano, exibindo o processamento no log do container `celery`.

**Passo 4** — Faça uma requisição `GET` para `/tarefas/recentes` para ver o status (`PENDING`, `SUCCESS`, etc.) e o resultado das tarefas processadas.

> As tarefas atuais não possuem uma pausa artificial e podem concluir rapidamente. Dependendo do momento da consulta, o resultado pode aparecer diretamente como `SUCCESS`. O processamento exige Redis acessível e o worker Celery em execução.

---


## Mensageria com Kafka

Além do Celery, o projeto usa **Apache Kafka** para publicar eventos sempre que um livro é criado, permitindo que outros serviços consumam essas mensagens de forma assíncrona e desacoplada da API.

### Como funciona

- O `kafka_producer.py` cria um `KafkaProducer` conectado ao broker definido em `KAFKA_SERVER` e expõe a função `enviar_evento(topico, evento)`, que serializa o evento em JSON e publica no tópico informado.
- No `POST /adiciona`, depois de salvar o livro no banco e no Redis, a API publica um evento no tópico `livros_eventos` com a ação realizada e os dados do livro.
- O **ZooKeeper** coordena o Kafka na configuração utilizada pelo Compose; o **Kafka UI** oferece uma interface web para visualizar tópicos e mensagens.

### Estrutura

- Os serviços `zookeeper`, `kafka` e `kafka-ui` foram adicionados ao `docker-compose.yml`
- A dependência foi instalada via `poetry add kafka-python`
- A variável `KAFKA_SERVER` foi adicionada ao `.env` e repassada ao serviço `app` no Compose

### Como testar

**Passo 1** — Suba os serviços e reconstrua a imagem da aplicação quando houver mudanças no código ou nas dependências:

```bash
podman-compose up --build
```

**Passo 2** — No Insomnia (ou similar), faça uma requisição `POST` para `/adiciona` com um livro novo.

**Passo 3** — Acesse o Kafka UI em `http://localhost:8080`, entre no tópico `livros_eventos` e confira a mensagem publicada com os dados do livro.

---

## Documentação

Com a aplicação rodando, acesse a documentação interativa (Swagger) em:

```text
http://127.0.0.1:8000/docs
```

---

## O que este projeto demonstra

- Construção de uma API REST completa com FastAPI
- Uso de ORM (SQLAlchemy) para acesso a banco de dados relacional
- Implementação de cache com Redis para otimização de consultas
- Processamento assíncrono de tarefas com Celery, usando Redis como broker
- Autenticação e boas práticas de segurança (comparação segura de credenciais e uso de variáveis de ambiente)
- Containerização de aplicações com Podman / Docker Compose (múltiplos serviços orquestrados)
- Execução da API no Kubernetes local do Docker Desktop
- Gerenciamento moderno de dependências com Poetry
- Publicação de eventos assíncronos com Kafka (mensageria/streaming)

---

## Pytest

O pytest executa testes automatizados para verificar o comportamento da aplicação. Os testes ficam na pasta `tests/`.

A configuração abaixo já está definida no `pyproject.toml` e permite importar os módulos a partir da raiz do projeto:

```toml
[tool.pytest.ini_options]
pythonpath = ["."]
```

Instale as dependências, incluindo o grupo de desenvolvimento usado pelos mocks:

```bash
poetry install --with dev
```

Execute os testes na raiz do projeto:

```bash
poetry run pytest tests/
```

Para gerar o relatório de cobertura, use o `pytest-cov`, que já é uma dependência do projeto:

```bash
poetry run pytest --cov=. tests/
```

Os testes importam a aplicação, portanto precisam das variáveis de autenticação disponíveis antes da importação. Os testes atuais de autenticação e banco usam `admin` como usuário e senha; use uma configuração local de testes compatível.

> O teste `test_database.py` ainda depende dos dados do banco utilizado pela aplicação: ele espera três livros e verifica os dados de “Harry Potter 1”. Embora crie um banco em memória, não substitui a dependência `sessao_db` da API. Por isso, a suíte ainda não é independente do estado do banco local.

### Fixtures no Pytest

Fixtures são funções que preparam recursos necessários para os testes, como uma conexão com o banco de dados ou um objeto de configuração. São declaradas com `@pytest.fixture` e também podem liberar os recursos após o teste.

### Mocks

Mocks substituem dependências para controlar seus resultados e verificar como foram chamadas, incluindo os argumentos e a quantidade de chamadas. Neste projeto, são usados para simular operações do Redis e o envio de tarefas ao Celery.

### Stubs

Stubs fornecem respostas predefinidas para dependências durante um teste. São úteis quando o objetivo é controlar os dados recebidos pelo código testado, sem verificar as interações com a dependência.

### Test-Driven Development (TDD)

TDD é uma abordagem em que se escreve um teste que falha, implementa-se o código necessário para fazê-lo passar e depois se refatora a solução mantendo os testes aprovados.

### Testes das funções

- `tests/test_hello_world.py`: verifica a resposta da rota `/`, implementada por `hello_world`.
- `tests/test_task_celery.py`: verifica `somar` e `fatorial` com a execução local das tarefas via `.apply().get()`.
- `tests/test_tasks_endpoit.py`: verifica os endpoints de soma e fatorial com mocks do envio de tarefas e das operações do Redis.
- `tests/test_auth.py`: verifica autenticação com credenciais válidas e inválidas.
- `tests/test_database.py`: verifica a listagem de livros, com a dependência do estado do banco descrita acima.

## kubernetes
Configurações nos arquivos
service.yaml
script.sh
deployment.yaml

Para executar, script.sh no console.
