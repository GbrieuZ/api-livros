import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import Base, LivroDB, app, sessao_db
from fastapi.testclient import TestClient
import os
from sqlalchemy.pool import StaticPool

DATABASE_URL_TEST = "sqlite:///:memory:"
engine_test = create_engine(DATABASE_URL_TEST, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine_test)

Base.metadata.create_all(bind=engine_test)

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_redis(mocker):
    mock_redis_client =mocker.patch("main.redis_client", autospec=True)
    mock_redis_client.get.return_value = None

@pytest.fixture(scope="function")
def db():
    db = TestingSessionLocal()

    def override_sessao_db():
        yield db

    app.dependency_overrides[sessao_db] = override_sessao_db

    try:
        db.add_all([
            LivroDB(
                nome_livro=f"Harry Potter {numero}",
                autor_livro="ebac",
                ano_livro=2026,
            )
            for numero in range(1, 4)
        ])
        db.commit()

        yield db
    finally:
        db.rollback()
        db.query(LivroDB).delete()
        db.commit()
        app.dependency_overrides.pop(sessao_db, None)
        db.close()
        
def test_get_books(db):
    response = client.get("/livros", auth=("admin", "admin"))
    assert response.status_code == 200

    data = response.json()
    assert len(data["livros"]) == 3

    livros_por_nome = {
        livro["nome_livro"]: livro
        for livro in data["livros"]
    }

    assert "Harry Potter 1" in livros_por_nome
    livro = livros_por_nome["Harry Potter 1"]
    assert livro["autor_livro"] == "ebac"
    assert livro["ano_livro"] == 2026
