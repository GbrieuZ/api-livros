from fastapi.testclient import TestClient
from main import app
import os
import pytest

client = TestClient(app)

os.environ["MEU_USUARIO"] = "admin"
os.environ["MINHA_SENHA"] = "admin"

@pytest.fixture(autouse=True)
def mock_redis(mocker):
    mock_redis_client =mocker.patch("main.redis_client", autospec=True)
    mock_redis_client.get.return_value = None


# Teste de login com sucesso
def test_autenticacao_usuario_com_sucesso():
    response = client.get(
        "/livros",
        auth=("admin", "admin")
    )

    assert response.status_code == 200

# Teste de login com erro no usuário
def test_autenticacao_usuario_com_erro():
    response = client.get(
        "/livros",
        auth=("usuario_incorreto", "admin")
    )

    assert response.status_code == 401
    assert response.json()["detail"]== "Usuário ou senha incorretos"

# Teste de login com erro na senha
def test_autenticacao_senha_com_erro():
    response = client.get(
        "/livros",
        auth=("admin", "senha_errada")
    )

    assert response.status_code == 401
    assert response.json()["detail"]== "Usuário ou senha incorretos"