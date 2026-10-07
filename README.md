# 🔐 API de Criptografia

API em **FastAPI** que expõe operações criptográficas como endpoints REST: geração de chaves RSA, assinatura e verificação digital, geração de chaves AES-256 e cifragem/decifragem autenticada com AES-GCM. Cada chave tem um **nome**, então várias chaves convivem sem uma sobrescrever a outra. Roda em **Docker** com hot-reload e tem uma suíte de testes com **pytest**.

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
| Testes | pytest + `TestClient` + httpx |

---

## 📁 Estrutura

```
.
├── src/
│   ├── main.py          # instancia o FastAPI e inclui o router
│   ├── router.py        # rotas da API
│   └── schemas.py       # modelos Pydantic de request
├── tests/
│   └── test_router.py   # testes dos endpoints com pytest
├── chaves/              # chaves geradas (criada automaticamente, NÃO vai pro repositório)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

> 🔒 As chaves ficam na pasta `chaves/`, separadas do código. A pasta é criada automaticamente quando a API sobe. **Chave privada nunca vai pro repositório:** ao subir o projeto, a pasta `chaves/` e qualquer arquivo `.pem` ou `.key` ficam de fora.

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

### RSA: assinatura digital

#### `POST /rsa`

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

#### `POST /assinar`

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

#### `POST /verificar`

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

#### `POST /aes`

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

#### `POST /cifrar`

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
>
> ⚠️ Repare que o campo **sai** do `/cifrar` como `cifrado`, mas **entra** no `/decifrar` como `texto_cifrado`.

**Erros:** `404` se a chave AES não existir.

---

#### `POST /decifrar`

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

## 🧪 Testes

Os testes ficam em `tests/test_router.py` e usam o `TestClient` do FastAPI, que faz requisições à API sem precisar subir servidor.

### Como rodar

Com o container de pé:

```bash
docker compose exec api pytest
```

> `api` é o nome do serviço no `docker-compose.yml`.

Dependências necessárias no `requirements.txt`: `pytest` e `httpx` (o `TestClient` usa o `httpx` por baixo).

### O que é testado

| Teste | O que prova |
|---|---|
| `test_gerar_par_de_chaves_cria_os_dois_arquivos` | `/rsa` cria a chave privada e a pública no disco |
| `test_assinar_verificar_mesmo_texto_devolve_verdadeiro` | Uma assinatura válida é aceita pelo `/verificar` |
| `test_texto_alterado_em_uma_letra_reprova_verificacao` | Mudar **uma letra** do texto faz a verificação falhar |
| `test_cifrar_decifrar_devolve_texto_original` | Cifrar e decifrar devolve exatamente o texto original |
| `test_cifrar_mesmo_texto_duas_vezes_da_resultados_DIFERENTES` | Com a **mesma chave**, o mesmo texto gera cifrados diferentes (nonce aleatório) |
| `test_decifrar_com_iv_errado_falha` | Decifrar com o nonce de **outra** cifragem é barrado com `400` |

### Padrões usados

- **Chamadas encadeadas:** a resposta de uma rota alimenta a próxima (ex.: a assinatura do `/assinar` vai pro `/verificar`).
- **Ler a resposta:** `resposta.json()["campo"]` transforma o corpo em dicionário e pega o campo.
- **Conferir erro:** `resposta.status_code == 400` confere o código HTTP direto, sem `.json()`.
- **Nonce errado de verdade:** em vez de inventar um texto qualquer (que nem seria base64 válido), o teste usa o nonce de uma segunda cifragem. Assim ele é válido, mas pertence à mensagem errada, e o teste prova que o GCM detecta isso.

---

## 🧠 Conceitos aplicados

- **Assinatura digital:** a chave privada assina, a pública verifica. Garante autenticidade e integridade, não sigilo.
- **Criptografia simétrica:** no AES, a mesma chave cifra e decifra.
- **AES-GCM:** além de cifrar, autentica os dados. Qualquer alteração no cifrado ou no nonce faz a decifragem falhar, em vez de devolver lixo silenciosamente (como aconteceria no AES-CBC).
- **Nonce / IV:** valor aleatório usado uma única vez por cifragem. No GCM costuma se chamar nonce; no CBC, IV (vetor de inicialização). Nunca deve se repetir com a mesma chave.
- **Tamanho de chave:** AES-256 tem 256 bits de segurança; RSA-2048 equivale a cerca de 112, porque RSA pode ser atacado por fatoração em vez de força bruta.
- **PEM:** formato texto para guardar chaves RSA em arquivo.
- **PSS:** padding probabilístico para assinaturas RSA, mais seguro que o PKCS#1 v1.5.
- **Base64:** transporte de bytes dentro de JSON sem perda.
- **Allowlist:** validar aceitando só o que é conhecido, em vez de tentar bloquear tudo que é perigoso.
- **400 vs 500:** `400` é erro tratado (o cliente mandou dado ruim e a API sabia o que fazer); `500` é erro não tratado (a API quebrou).

---

## ✅ Status

- [x] Estrutura FastAPI + Docker Compose com hot-reload
- [x] `/rsa`, `/assinar`, `/verificar`
- [x] `/aes`, `/cifrar`, `/decifrar`
- [x] Chaves nomeadas, sem sobrescrita entre nomes diferentes
- [x] Validação do `nome` por allowlist (proteção contra path traversal)
- [x] Chaves isoladas na pasta `chaves/`
- [x] Tratamento de erros: `404`, `400`, `422`
- [x] Suíte de testes com pytest escrita (6 testes)
- [ ] Rodar a suíte e deixar tudo verde

### Pendências

- **Import do `src`:** o `main.py` importa `from router import ...`, mas o `router.py` importa `from src.schemas import ...`. Essa mistura faz o pytest falhar com `ModuleNotFoundError: No module named 'src'`. Correção prevista: padronizar para `from schemas import ...`.
- **Testes dependentes:** os testes de assinatura usam a chave `teste01`, criada pelo teste de geração. Se rodarem sozinhos, quebram. Ideal: cada teste gerar a própria chave no início.

### Limitações conhecidas

- Chamar `/rsa` ou `/aes` com um nome que **já existe** sobrescreve a chave anterior.
- Base64 malformado no `/verificar` ou no `/decifrar` ainda retorna `500`.

---

## ⚠️ Aviso

Projeto **educacional**. Em produção, chaves privadas não ficam em arquivo no disco: ficam em um KMS, Vault ou HSM.

---

Feito por [Luiza Souza](https://luizasouza.eti.br) · [@lu-izah19](https://github.com/lu-izah19)
