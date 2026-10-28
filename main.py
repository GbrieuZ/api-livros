# API de Livros

# GET, POST, PUT e DELETE

# GET - Buscar os dados dos livros (Create)
# POST - Adicionar novos livros (Read)
# PUT - Atualizar informações dos livros (Update)
# DELETE - Deletar informações dos livros (Delete)

# Vamos acessar nosso ENDPOINT
# E vamos acessar os PATH's desse endpoint
# Query Strings

#CRUD - Create, Read, Update, Delete

# Documentação Swagger - Documentar os endpoints da nossa API (aplicação)

# Acesse minha documentação swagger: http://127.0.0.1:8000/docs#/

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import os
import redis
import json
from fastapi import BackgroundTasks
from tasks import fatorial, somar
from celery_app import celery_app
from celery.result import AsyncResult
from dotenv import load_dotenv
from kafka_producer import enviar_evento # Publica eventos no Kafka (tópico livros_eventos)

load_dotenv()  # Carrega o arquivo .env quando a API roda fora do container.
# No Docker/Podman Compose as variáveis já vêm do env_file, e o load_dotenv não atrapalha.


from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session, sessionmaker

import asyncio

"""

| Biblioteca         | Pra que serve                                     |
| ------------------ | ------------------------------------------------- |
| FastAPI            | Criar a API                                       |
| FastAPI Security   | Autenticação                                      |
| Pydantic           | Validação de dados                                |
| typing             | Tipagem (Python padrão)                           |
| secrets            | Segurança (tokens, senhas)                        |
| os                 | Sistema operacional                               |
| SQLAlchemy         | Banco de dados (ORM)                              |
| redis              | Cache de dados e broker/backend do Celery         |
| json               | Serializar/desserializar dados salvos no Redis    |
| python-dotenv      | Carregar variáveis de ambiente do .env            |
| tasks (local)      | Tarefas assíncronas do Celery (soma e fatorial)   |
| celery_app (local) | Configuração/instância do Celery                  |
| celery.result      | Consultar status/resultado de tarefas assíncronas |
| kafka-python       | Publicar eventos no Kafka                         |
| Pytest             | Teste de códigos                                  |

"""

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./livros.db") # Aqui é a url do banco de dados


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True) # Config para rodar de forma local

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
# Cria a conexão com o banco de dados usando a URL informada.
# O "check_same_thread=False" permite que o SQLite seja usado em múltiplas threads (necessário em APIs como FastAPI).

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Cria uma fábrica de sessões (Session) para interagir com o banco.
# autocommit=False: você controla quando salvar (commit).
# autoflush=False: evita enviar alterações automaticamente antes de consultas.
# bind=engine: conecta essa sessão ao banco criado acima.

Base = declarative_base()
# Base usada para criar os modelos (tabelas) do banco de dados com ORM.
# Todas as classes de modelo irão herdar dessa Base.

app = FastAPI(
    title="API de Livros",
    description="API para gerenciar uma coleção de livros",
    version="1.0.0",
    contact={
        "name":"Gabriel Martins",
        "email":"gabrieuz.martins@gmail.com"
    }
)

# Variáveis de ambiente, ficam no arquivo .env
MEU_USUARIO = os.getenv("MEU_USUARIO")
MINHA_SENHA = os.getenv("MINHA_SENHA")

if not MEU_USUARIO or not MINHA_SENHA:
    raise RuntimeError(
        "MEU_USUARIO e MINHA_SENHA não foram definidos. "
        "Crie o arquivo .env na raiz do projeto a partir do .env.example."
    )

security = HTTPBasic()

class LivroDB(Base):
    __tablename__ = "livros"
    id = Column(Integer, primary_key=True, index=True) # primary_key=True é para dizer que essa coluna é a chave primária do banco de dados, ou seja, o identificador único de cada registro
    nome_livro = Column(String, index=True)
    autor_livro = Column(String, index=True)
    ano_livro = Column(Integer)

class Livro(BaseModel):
    nome_livro: str
    autor_livro: str
    ano_livro: int

Base.metadata.create_all(bind=engine) # Aqui eu crio as tabelas do banco de dados, ou seja, a tabela livros com as colunas id, nome_livro, autor_livro e ano_livro

def salvar_livros_redis(livro_id: int, livro: Livro):
    redis_client.setex(f"livro:{livro_id}", 30, json.dumps(livro.model_dump()))

def deletar_livro_redis(livro_id: int):
    redis_client.delete(f"livro:{livro_id}")


def sessao_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
def autenticar_usuario(credentials: HTTPBasicCredentials = Depends(security)):
    is_username_correct = secrets.compare_digest(credentials.username, MEU_USUARIO)
    is_password_correct = secrets.compare_digest(credentials.password, MINHA_SENHA)

    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=401,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Basic"}
        )

@app.get("/")
def hello_world():
    return {"message": "Hello World!"}

@app.post("/calcular/soma")
def calcular_soma(a: int, b: int):
    tarefa = somar.delay(a, b)
    redis_client.lpush("tarefas_ids", tarefa.id)
    redis_client.ltrim("tarefas_ids", 0, 49)
    return {
        "task_id": tarefa.id,
        "message": "Tarefa de soma enviada para a execução."
    }

@app.post("/calcular/fatorial")
def calcular_fatorial(n: int):
    tarefa = fatorial.delay(n)
    redis_client.lpush("tarefas_ids", tarefa.id)
    redis_client.ltrim("tarefas_ids", 0, 49)
    return{
        "task_id": tarefa.id,
        "message": "Tarefa de fatorial enviada para a execução."
    }

@app.get("/tarefas/recentes")
def listar_tarefas_recentes():
    ids = redis_client.lrange("tarefas_ids", 0, -1)
    tarefas = []

    for task_id in ids:
        resultado = AsyncResult(task_id, app=celery_app)
        tarefas.append({
            "task_id": task_id,
            "status": resultado.status,
            "resultado": resultado.result if resultado.successful() else None
        })

    return {
        "tarefas": tarefas
    }

@app.get("/debug/redis")
def ver_livros_redis():
    chaves = redis_client.scan_iter("livro:*")
    livros = []

    for chave in chaves:
        valor = redis_client.get(chave)
        ttl = redis_client.ttl(chave)

        livros.append({"chave": chave, "valor": json.loads(valor), "ttl": ttl})

    return livros

@app.get("/livros")
def get_livros(
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(sessao_db),
    credentials: HTTPBasicCredentials = Depends(autenticar_usuario)
):
    if page < 1 or limit < 1:
        raise HTTPException(status_code=400, detail="Page ou limit estão com valores inválidos!") 

    cache_key = f"livros:page={page}&limit={limit}"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    livros = db.query(LivroDB).offset((page - 1) * limit). limit(limit).all()

    if not livros:
        return {"message": "Não existe nenhum livro cadastrado!"}

    total_livros = db.query(LivroDB).count()

    resposta = {
        "page": page,
        "limit": limit,
        "total": total_livros,
        "livros": [
            {
                "id": livro.id,
                "nome_livro": livro.nome_livro,
                "autor_livro": livro.autor_livro,
                "ano_livro": livro.ano_livro
            } for livro in livros

        ]
    }

    redis_client.setex(cache_key, 30, json.dumps(resposta))

    return resposta

"""
# Chamadas externas

async def chamadas_externas_1():
    await asyncio.sleep(2)
    return "Resutado chamada externa 1"

async def chamadas_externas_2():
    await asyncio.sleep(2)
    return "Resutado chamada externa 2"

async def chamadas_externas_3():
    await asyncio.sleep(2)
    return "Resutado chamada externa 3"


@app.get("/chamadas-externas")
async def chamadas_externas():
    tarefa1 = asyncio.create_task(chamadas_externas_1())
    tarefa2 = asyncio.create_task(chamadas_externas_2())
    tarefa3 = asyncio.create_task(chamadas_externas_3())

    resultado1 = await tarefa1
    resultado2 = await tarefa2
    resultado3 = await tarefa3

    return{
        "mensagem": "Todas as chamadas nas API's foram concluidas com sucesso",
        "resultado": [resultado1, resultado2, resultado3]
    }
"""

@app.post("/adiciona")
async def post_livros(livro: Livro, db: Session = Depends(sessao_db), credentials: HTTPBasicCredentials = Depends(autenticar_usuario)):
    # esse db é a conexão com o banco de dados.
    db_livro = db.query(LivroDB).filter(LivroDB.nome_livro == livro.nome_livro, LivroDB.autor_livro == livro.autor_livro, LivroDB.ano_livro == livro.ano_livro).first()
    # Aqui eu verifico se já existe um livro com as mesmas informações (nome, autor e ano) no banco de dados, para evitar duplicidade de registros.

    if db_livro:
        raise HTTPException(status_code=400, detail="Livro já cadastrado")
    
    novo_livro = LivroDB(nome_livro = livro.nome_livro, autor_livro = livro.autor_livro, ano_livro = livro.ano_livro)
    db.add(novo_livro)
    db.commit()
    db.refresh(novo_livro) # Aqui eu atualizo o objeto novo_livro com as informações do banco de dados, como o id gerado automaticamente pelo banco de dados.

    salvar_livros_redis(novo_livro.id, livro)

    # Publica um evento no Kafka para que outros serviços possam reagir
    # à criação do livro de forma assíncrona, sem acoplar a API a eles.
    enviar_evento("livros_eventos",{
        "acao": "criar",
        "livro": livro.dict()
    })

    return {"message": f"Livro {novo_livro.nome_livro} adicionado com sucesso!"}

@app.put("/atualiza/{id_livro}")
async def put_livros(id_livro: int, livro: Livro, db: Session = Depends(sessao_db), credentials: HTTPBasicCredentials = Depends(autenticar_usuario)):
    # esse db é a conexão com o banco de dados.
    db_livro = db.query(LivroDB).filter(LivroDB.id == id_livro).first()
    # coenxão especificamente com uma tabela do banco de dados, no caso a tabela livros, e eu filtro essa tabela para encontrar o livro com o id fornecido na URL da requisição, e depois eu pego o primeiro resultado encontrado (que deve ser o único resultado, já que o id é único).
    # Aqui eu verifico se existe um livro com o id fornecido no banco de dados, para que eu possa atualizar as informações desse livro.
    
    if not db_livro:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    
    db_livro.nome_livro = livro.nome_livro
    db_livro.autor_livro = livro.autor_livro
    db_livro.ano_livro = livro.ano_livro
    db.commit()
    db.refresh(db_livro)

    return {"message": "Livro atualizado com sucesso!"}

    # Aqui eu atualizo as informações do livro encontrado no banco de dados com as novas informações fornecidas no corpo da requisição, e depois eu salvo as alterações no banco de dados com o commit().

@app.delete("/deletar/{id_livro}")
async def delete_livro(id_livro: int, db: Session = Depends(sessao_db), credentials: HTTPBasicCredentials = Depends(autenticar_usuario)):
    db_livro = db.query(LivroDB).filter(LivroDB.id == id_livro).first()
    if not db_livro:
        raise HTTPException(status_code=404, detail="Livro não encontrado")
    
    db.delete(db_livro)
    db.commit()

    deletar_livro_redis(id_livro)

    return {"message": f"Livro {db_livro.nome_livro} deletado com sucesso!"}

# http://127.0.0.1:8000/livros?page=1&limit=100
# aqui eu escolho a página e a quantidade de livros que eu quero ver por página

# ORM - Object Relational Mapping - é uma técnica de programação que permite que os desenvolvedores trabalhem com bancos de dados relacionais usando objetos em vez de escrever consultas SQL diretamente.
# FastAPI / Django / Flask / Node / Express / Nest.js / Laravel / Spring Boot -> Frameworks Backends todos possuem suporte a ORM.
# Vantagens -> A gente vai ganhar agilidade no desenvolvimento
# Desvantagens -> A gente pode perder performance no Banco de Dados
