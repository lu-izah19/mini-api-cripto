# 🔐 API de Criptografia

API em **FastAPI** que expõe operações criptográficas como endpoints REST: geração de chaves RSA, assinatura e verificação digital, geração de chaves AES-256 e cifragem/decifragem autenticada com AES-GCM. Cada chave tem um **nome**, então várias chaves convivem sem uma sobrescrever a outra. Roda em **Docker** com hot-reload.

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
| Testes | pytest + `TestClient` (em andamento) |

---

## 📁 Estrutura

```
.
├── src/
│   ├── main.py        # instancia o FastAPI e inclui o router
│   ├── router.py      # rotas /chaves/*
│   └── schemas.py     # modelos Pydantic de request
├── chaves/            # chaves geradas (criada automaticamente, NÃO versionada)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .gitignore
└── README.md
```

> 🔒 As chaves ficam na pasta `chaves/`, separadas do código. A pasta é criada automaticamente quando a API sobe e está no `.gitignore`, junto com `*.pem` e `*.key`. **Chave privada nunca vai pro repositório.**

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

## 🏷️ Nome das chaves

Toda rota recebe um campo `nome`, que identifica qual chave usar. Ele vira parte do nome do arquivo:

| Tipo | Arquivos gerados |
|---|---|
| RSA | `chaves/{nome}_privada.pem` e `chaves/{nome}_publica.pem` |
| AES | `chaves/{nome}_aes.key` |

O `nome` é validado por **allowlist**: só aceita letras, números, hífen e sublinhado (`^[a-zA-Z0-9_-]+$`). Qualquer outra coisa (`../`, barra, espaço, nome vazio) é recusada com **422** antes de chegar na rota. Isso impede **path traversal**, ou seja, ler ou sobrescrever arquivos fora da pasta `chaves/`.

---

## 📡 Endpoints

Todas as rotas ficam sob o prefixo `/chaves`.

### RSA: assinatura digital

#### `POST /chaves/rsa`

Gera um par de chaves RSA-2048 e salva os dois arquivos em formato **PEM**.

**Request**
```json
{ "nome": "lu" }
```

**Resposta**
```json
{ "message": "Par de chaves RSA gerado com sucesso" }
```

---

#### `POST /chaves/assinar`

Assina um texto com a chave privada usando **RSA-PSS + SHA-256**. A assinatura volta em **base64** (porque JSON não carrega bytes).

**Request**
```json
{ "nome": "lu", "texto": "contrato do estagio" }
```

**Resposta**
```json
{ "assinatura": "kj3h2K...==" }
```

**Erros:** `404` se a chave privada não existir.

---

#### `POST /chaves/verificar`

Confere se uma assinatura é válida para um texto, usando a chave pública.

**Request**
```json
{
  "nome": "lu",
  "texto_assinado": "contrato do estagio",
  "assinatura_b64": "kj3h2K...=="
}
```

**Resposta**
```json
{ "valida": true }
```

Se o texto ou a assinatura tiverem sido alterados, volta `{ "valida": false }`.

Internamente: o `verify()` não retorna `True`. Quando falha, ele **lança `InvalidSignature`**, que é capturado com `try/except`.

**Erros:** `404` se a chave pública não existir.

---

### AES-256-GCM: cifragem simétrica

#### `POST /chaves/aes`

Gera uma chave AES-256 (32 bytes aleatórios com `os.urandom`).

**Request**
```json
{ "nome": "lu" }
```

**Resposta**
```json
{ "message": "Chave AES gerada com sucesso" }
```

---

#### `POST /chaves/cifrar`

Cifra um texto com **AES-GCM**. Um **nonce** de 12 bytes é gerado aleatoriamente a cada chamada, então o mesmo texto cifrado duas vezes gera resultados diferentes.

**Request**
```json
{ "nome": "lu", "texto": "oi lu" }
```

**Resposta**
```json
{ "cifrado": "Xk9a...==", "nonce": "a1B2c3...==" }
```

> ⚠️ Guarde o `nonce`: sem ele não dá pra decifrar.

**Erros:** `404` se a chave AES não existir.

---

#### `POST /chaves/decifrar`

Decifra o texto usando a chave e o nonce.

**Request**
```json
{
  "nome": "lu",
  "texto_cifrado": "Xk9a...==",
  "nonce": "a1B2c3...=="
}
```

**Resposta**
```json
{ "texto": "oi lu" }
```

**Erros:**
- `404` se a chave AES não existir
- `400` se o texto cifrado ou o nonce tiverem sido adulterados (o GCM detecta e lança `InvalidTag`)

---

## 🚦 Códigos de resposta

| Código | Quando acontece |
|---|---|
| `200` | Deu certo |
| `400` | Dados cifrados adulterados ou nonce errado |
| `404` | Chave com esse nome não existe |
| `422` | Request inválido (ex.: `nome` fora da allowlist) |

---

## 🧠 Conceitos aplicados

- **Assinatura digital:** a chave privada assina, a pública verifica. Garante autenticidade e integridade, não sigilo.
- **Criptografia simétrica:** no AES, a mesma chave cifra e decifra.
- **AES-GCM:** além de cifrar, autentica os dados. Qualquer alteração no cifrado ou no nonce faz a decifragem falhar, em vez de devolver lixo silenciosamente (como aconteceria no AES-CBC).
- **Nonce:** valor aleatório usado uma única vez por cifragem. Nunca deve se repetir com a mesma chave.
- **Tamanho de chave:** AES-256 tem 256 bits de segurança; RSA-2048 equivale a cerca de 112, porque RSA pode ser atacado por fatoração em vez de força bruta.
- **PEM:** formato texto para guardar chaves RSA em arquivo.
- **PSS:** padding probabilístico para assinaturas RSA, mais seguro que o PKCS#1 v1.5.
- **Base64:** transporte de bytes dentro de JSON sem perda.
- **Allowlist:** validar aceitando só o que é conhecido, em vez de tentar bloquear tudo que é perigoso.

---

## ✅ Status

- [x] Estrutura FastAPI + Docker Compose com hot-reload
- [x] `/chaves/rsa`, `/chaves/assinar`, `/chaves/verificar`
- [x] `/chaves/aes`, `/chaves/cifrar`, `/chaves/decifrar`
- [x] Chaves nomeadas, sem sobrescrita entre nomes diferentes
- [x] Validação do `nome` por allowlist (proteção contra path traversal)
- [x] Chaves isoladas na pasta `chaves/`
- [x] Tratamento de erros: `404`, `400`, `422`
- [ ] Suíte de testes com pytest

### Limitações conhecidas

- Chamar `/rsa` ou `/aes` com um nome que **já existe** sobrescreve a chave anterior.
- Base64 malformado no `/verificar` ou no `/decifrar` ainda retorna `500`.

---

## ⚠️ Aviso

Projeto **educacional**. Em produção, chaves privadas não ficam em arquivo no disco: ficam em um KMS, Vault ou HSM.

---

Feito por [Luiza Souza](https://luizasouza.eti.br) · [@lu-izah19](https://github.com/lu-izah19)
