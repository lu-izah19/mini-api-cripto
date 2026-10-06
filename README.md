# 🔐 API de Criptografia

API em **FastAPI** que expõe operações criptográficas básicas como endpoints REST: geração de chaves RSA, assinatura digital, verificação de assinatura e (em breve) cifragem simétrica com AES. Roda em **Docker** com hot-reload.

Projeto de estudo desenvolvido durante o estágio de back-end na CERMOB Tecnologia.

---

## 🧱 Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3 |
| Framework | FastAPI + Uvicorn |
| Criptografia | [`cryptography`](https://cryptography.io/) |
| Validação | Pydantic |
| Container | Docker + Docker Compose |
| Testes | pytest + `TestClient` (planejado) |

---

## 📁 Estrutura

```
.
├── src/
│   ├── main.py        # instancia o FastAPI e inclui o router
│   ├── router.py      # rotas /chaves/*
│   └── schemas.py     # modelos Pydantic de request/response
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .gitignore
└── README.md
```

> As chaves geradas (`privada.pem` e `publica.pem`) ficam no disco e **não são versionadas** — `*.pem` está no `.gitignore`.

---

## 🚀 Como rodar

**Pré-requisitos:** Docker e Docker Compose.

```bash
# primeira vez (ou depois de mexer no requirements.txt)
docker compose up --build

# nas próximas vezes
docker compose up -d
```

A API sobe em `http://localhost:8000` e a documentação interativa fica em:

- Swagger UI → `http://localhost:8000/docs`
- ReDoc → `http://localhost:8000/redoc`

O Uvicorn observa a pasta `/app`, então qualquer alteração no código recarrega a API sozinha.

---

## 📡 Endpoints

Todas as rotas ficam sob o prefixo `/chaves`.

### `POST /chaves/rsa` ✅

Gera um par de chaves RSA e salva os dois arquivos em formato **PEM**.

**Resposta**
```json
{ "message": "Par de chaves RSA gerado com sucesso" }
```

Arquivos criados: `privada.pem` e `publica.pem`.

---

### `POST /chaves/assinar` ✅

Assina um texto com a chave privada usando **RSA-PSS + SHA-256**. A assinatura volta codificada em **base64** (porque JSON não carrega bytes).

**Request**
```json
{ "texto": "contrato do estagio" }
```

**Resposta**
```json
{ "assinatura": "kj3h2K...==" }
```

---

### `POST /chaves/verificar` 🚧

Confere se uma assinatura é válida para um texto, usando a chave pública.

**Request**
```json
{
  "texto": "contrato do estagio",
  "assinatura": "kj3h2K...=="
}
```

**Resposta (planejada)**
```json
{ "valida": true }
```

Internamente: decodifica a assinatura de base64 e chama `verify()`. Como `verify()` não retorna `True` — ele **lança `InvalidSignature`** quando falha — o resultado é tratado com `try/except`.

---

### Próximos endpoints 📝

| Endpoint | O que faz |
|---|---|
| `POST /chaves/aes` | Gera uma chave AES-256 (32 bytes) com gerador seguro (`os.urandom` / `secrets`) |
| `POST /chaves/cifrar` | Cifra um texto com AES; IV/nonce aleatório a cada chamada |
| `POST /chaves/decifrar` | Decifra o texto; deve **falhar** com IV/nonce ou dados adulterados |

> 💡 O modo escolhido para o AES importa: **AES-GCM** autentica os dados e detecta adulteração; AES-CBC com IV errado só devolve lixo sem avisar.

---

## 🧠 Conceitos aplicados

- **Assinatura digital:** a chave privada assina, a pública verifica. Garante autenticidade e integridade, não sigilo.
- **PEM:** formato texto para guardar chaves em arquivo (`private_bytes` / `public_bytes` para salvar, `load_pem_private_key` / `load_pem_public_key` para carregar).
- **PSS:** esquema de padding probabilístico para assinaturas RSA, mais seguro que o PKCS#1 v1.5.
- **Base64:** transporte de bytes dentro de JSON sem perda.

---

## ✅ Status

- [x] Estrutura FastAPI + Docker Compose com hot-reload
- [x] `/chaves/rsa`
- [x] `/chaves/assinar`
- [ ] `/chaves/verificar` (falta o `verify()` com tratamento de `InvalidSignature`)
- [ ] `/chaves/aes`
- [ ] `/chaves/cifrar`
- [ ] `/chaves/decifrar`
- [ ] Suíte de testes com pytest

---

## ⚠️ Aviso

Projeto **educacional**. Em produção, chaves privadas não ficam em arquivo solto no disco — ficam em um KMS, Vault ou HSM.

---

Feito por [Luiza Souza](https://luizasouza.eti.br) · [@lu-izah19](https://github.com/lu-izah19)
