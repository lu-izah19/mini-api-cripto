# 🔐 API de Criptografia

API em **FastAPI** que expõe operações criptográficas como endpoints REST: geração de chaves RSA, assinatura e verificação digital, geração de chaves AES-256 e cifragem/decifragem autenticada com AES-GCM. Cada chave tem um **nome**, então várias chaves convivem sem uma sobrescrever a outra. Roda em **Docker** com hot-reload e tem uma suíte de testes com **pytest**.

Na **Parte 2**, as chaves deixam de ficar em arquivo e passam a viver dentro de um **cofre (HSM simulado com SoftHSM)**, acessado via **PKCS#11**. A chave nasce lá dentro e nunca sai: a API só pede para o cofre fazer o trabalho.

Projeto de estudo desenvolvido durante o estágio de back-end na CERMOB Tecnologia.

---

## 🧱 Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3 |
| Framework | FastAPI + Uvicorn |
| Criptografia | [`cryptography`](https://cryptography.io/) |
| Cofre (HSM) | SoftHSM2 + [`python-pkcs11`](https://python-pkcs11.readthedocs.io/) |
| Validação | Pydantic |
| Container | Docker + Docker Compose |
| Testes | pytest + `TestClient` + httpx |

---

## 📁 Estrutura

```
.
├── src/
│   ├── main.py          # instancia o FastAPI e inclui o router
│   ├── router.py        # rotas da API (Parte 1 e Parte 2)
│   ├── schemas.py       # modelos Pydantic de request
│   └── hsm.py           # funções que conversam com o cofre (PKCS#11)
├── tests/
│   ├── test_router.py   # testes das rotas da Parte 1
│   └── test_cripto.py   # testes do cofre (Parte 2, a escrever)
├── chaves/              # chaves geradas na Parte 1 (criada automaticamente, NÃO vai pro repositório)
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

> 🔒 As chaves da Parte 1 ficam na pasta `chaves/`, separadas do código. A pasta é criada automaticamente quando a API sobe. **Chave privada nunca vai pro repositório:** o `.gitignore` deixa de fora a pasta `chaves/`, qualquer arquivo `.pem` ou `.key`, o `.env` e os caches do Python.

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

Para conferir se está de pé: `docker compose ps` (o container deve aparecer como `Running`) ou abrir o Swagger.

---

## 🏷️ Nome das chaves

Toda rota da Parte 1 recebe um campo `nome`, que identifica qual chave usar. Ele vira parte do nome do arquivo:

| Tipo | Arquivos gerados |
|---|---|
| RSA | `chaves/{nome}_privada.pem` e `chaves/{nome}_publica.pem` |
| AES | `chaves/{nome}_aes.key` |

O `nome` é validado por **allowlist**: só aceita letras, números, hífen e sublinhado (`^[a-zA-Z0-9_-]+$`). Qualquer outra coisa (`../`, barra, espaço, nome vazio) é recusada com **422** antes de chegar na rota. Isso impede **path traversal**, ou seja, ler ou sobrescrever arquivos fora da pasta `chaves/`.

---

## 📡 Endpoints: Parte 1 (chaves em arquivo)

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
>
> ⚠️ Repare que o campo **sai** do `/cifrar` como `cifrado`, mas **entra** no `/decifrar` como `texto_cifrado`.

**Erros:** `404` se a chave AES não existir (RSA e AES são chaves diferentes: gerar o par RSA não cria a chave AES).

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

## 🔬 Experimentos da Parte 1

Feitos à mão pelo Swagger, para ver cada conceito acontecendo.

| # | Experimento | Resultado | O que prova |
|---|---|---|---|
| 1 | Assinar `"contrato do estagio"` e verificar com o texto original e com **uma letra trocada** | Original → `true`; alterado → `false` | **Integridade:** qualquer mudança gera outro hash SHA-256 e a assinatura deixa de bater |
| 2 | Abrir `chaves/lu_privada.pem` no editor e copiar para outra pasta | O arquivo está em texto puro, sem senha | Quem copia a chave privada **assina no seu nome**. É o problema que a Parte 2 resolve |
| 3 | Cifrar `"oi lu"` duas vezes com a mesma chave | Cifrados e nonces diferentes | O nonce aleatório impede perceber que duas mensagens são iguais |
| 4 | Decifrar com o nonce certo e com o nonce de **outra** cifragem | Certo → `"oi lu"`; errado → `400` | Sem o nonce certo não há decifragem, e a **tag** do GCM recusa em vez de devolver lixo |

> Curiosidade: o `texto_cifrado` é maior que o texto original porque carrega junto os **16 bytes da tag de autenticação** do GCM.

---

## 🏦 Parte 2: cofre (HSM)

### A ideia

Na Parte 1, a chave mora num arquivo e o **Python** faz a conta. Na Parte 2, a chave **nasce dentro do cofre** e nunca sai de lá: o Python só entrega o texto e pede "assina/cifra isso pra mim". É como um caixa de banco: você não pega o dinheiro do cofre, pede para a operação acontecer lá dentro.

| | Parte 1 | Parte 2 |
|---|---|---|
| Onde a chave mora | arquivo `.pem` / `.key` | dentro do cofre |
| Quem faz a conta | Python | cofre |
| Quem gera o nonce/IV | a API (`os.urandom(12)`) | a API (`os.urandom(12)`) |
| Mecanismo AES | AES-GCM | AES-GCM |

### Vocabulário PKCS#11

- **Biblioteca:** o arquivo `.so` que o Python carrega (`/usr/lib/softhsm/libsofthsm2.so`). É a porta de entrada.
- **Token:** o cofre em si, identificado por um **label** (`cofre-treino`).
- **PIN:** a senha do token.
- **Sessão:** a conexão aberta com o token. Abre, trabalha, fecha.

### `src/hsm.py`

| Função | O que faz |
|---|---|
| `sessao_hsm()` | Context manager: carrega a biblioteca, acha o token pelo label, abre a sessão com o PIN e garante o fechamento com `try/finally` |
| `gerar_par_no_cofre(label)` | Gera um par RSA-2048 dentro do cofre e devolve só o módulo da chave **pública** |
| `assinar_no_cofre(label, texto)` | Pede ao cofre para assinar com `SHA256_RSA_PKCS` |
| `verificar_no_cofre(label, texto, assinatura)` | Pede ao cofre para verificar a assinatura |
| `gerar_aes_no_cofre(label)` | Gera uma chave AES-256 dentro do cofre. Não devolve nada: a chave não sai |
| `cifrar_aes_no_cofre(label, texto)` | Gera o nonce, pede ao cofre para cifrar com `AES_GCM` e devolve `(cifrado, nonce)` |
| `decifrar_aes_no_cofre(label, cifrado, nonce)` | Pede ao cofre para decifrar com o nonce recebido e devolve o texto |

**Atributos da chave AES:** `TOKEN`, `PRIVATE`, `SENSITIVE: True`, `EXTRACTABLE: False` (nunca sai do cofre), `ENCRYPT` e `DECRYPT` (só pode cifrar e decifrar, nada além: **princípio do menor privilégio**).

**Parâmetros do GCM no cofre:** `mechanism_param=(nonce, b"", 128)`, ou seja, o IV de 12 bytes, dados adicionais autenticados vazios e tag de **128 bits** (16 bytes).

### Endpoints do cofre

#### `GET /chaves/cofre/status`

Abre uma sessão com o cofre e devolve o label do token. Serve para provar que a conexão funciona: o label é lido **do token de verdade**, não da constante do código.

**Resposta**
```json
{ "token": "cofre-treino" }
```

---

#### `GET /chaves/cofre/chaves`

Lista as chaves que estão dentro do cofre, com label e tipo. Percorre os objetos com `sessao.get_objects(...)` e devolve só os metadados: nenhuma chave sai.

**Resposta**
```json
[
  { "label": "lu", "tipo": "RSA" }
]
```

> ⚠️ Por enquanto o filtro busca só `ObjectClass.PRIVATE_KEY`, então chaves AES (que são `SECRET_KEY`) **não aparecem** na lista.

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

Os testes ficam em `tests/` e usam o `TestClient` do FastAPI, que faz requisições à API sem precisar subir servidor.

### Como rodar

Com o container de pé:

```bash
docker compose exec api pytest
```

> `api` é o nome do serviço no `docker-compose.yml`. Para ver `print` durante os testes, use `pytest -s`.

Dependências necessárias no `requirements.txt`: `pytest` e `httpx` (o `TestClient` usa o `httpx` por baixo).

### O que é testado (`test_router.py`)

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
- **Depurar `KeyError`:** quando `resposta.json()["campo"]` dá `KeyError`, a rota devolveu erro em vez de sucesso. Um `print(resposta.status_code, resposta.json())` antes mostra o que veio.

---

## 🧠 Conceitos aplicados

- **Assinatura digital:** a chave privada assina, a pública verifica. Garante autenticidade e integridade, não sigilo.
- **Criptografia simétrica:** no AES, a mesma chave cifra e decifra.
- **AES-GCM:** além de cifrar, autentica os dados. Qualquer alteração no cifrado ou no nonce faz a decifragem falhar, em vez de devolver lixo silenciosamente (como aconteceria no AES-CBC).
- **Nonce / IV:** valor aleatório usado uma única vez por cifragem. No GCM costuma se chamar nonce; no CBC, IV (vetor de inicialização). Nunca deve se repetir com a mesma chave.
- **Tag de autenticação:** 16 bytes (128 bits) que o GCM gruda no cifrado e que denunciam qualquer adulteração.
- **Tamanho de chave:** AES-256 tem 256 bits de segurança; RSA-2048 equivale a cerca de 112, porque RSA pode ser atacado por fatoração em vez de força bruta.
- **PEM:** formato texto para guardar chaves RSA em arquivo.
- **PSS:** padding probabilístico para assinaturas RSA, mais seguro que o PKCS#1 v1.5.
- **Base64:** transporte de bytes dentro de JSON sem perda.
- **Allowlist:** validar aceitando só o que é conhecido, em vez de tentar bloquear tudo que é perigoso.
- **400 vs 500:** `400` é erro tratado (o cliente mandou dado ruim e a API sabia o que fazer); `500` é erro não tratado (a API quebrou).
- **HSM / PKCS#11:** a chave fica num cofre e o código só pede operações. Chave marcada como `SENSITIVE` e não `EXTRACTABLE` não pode ser lida nem pelo próprio dono.
- **Chave secreta (`SECRET_KEY`):** no PKCS#11, chave simétrica (AES) não é privada nem pública, é "secreta".
- **Menor privilégio:** a chave só recebe as permissões de que precisa (`ENCRYPT`/`DECRYPT` para AES, `SIGN`/`VERIFY` para RSA).

---

## ✅ Status

### Parte 1

- [x] Estrutura FastAPI + Docker Compose com hot-reload
- [x] `/rsa`, `/assinar`, `/verificar`
- [x] `/aes`, `/cifrar`, `/decifrar`
- [x] Chaves nomeadas, sem sobrescrita entre nomes diferentes
- [x] Validação do `nome` por allowlist (proteção contra path traversal)
- [x] Chaves isoladas na pasta `chaves/`
- [x] Tratamento de erros: `404`, `400`, `422`
- [x] Experimentos 1 a 4 feitos e anotados
- [x] `.gitignore` criado
- [x] Suíte de testes com pytest escrita (6 testes)
- [ ] Rodar a suíte e deixar tudo verde

### Parte 2

- [x] `hsm.py`: sessão com o cofre e funções RSA (gerar, assinar, verificar)
- [x] `hsm.py`: funções AES (`gerar_aes_no_cofre`, `cifrar_aes_no_cofre`, `decifrar_aes_no_cofre`)
- [x] `GET /chaves/cofre/status`
- [x] `GET /chaves/cofre/chaves` (só chaves RSA por enquanto)
- [ ] Rotas que usam o cofre para RSA (gerar, assinar, verificar)
- [ ] Rotas que usam o cofre para AES (gerar, cifrar, decifrar)
- [ ] Listar também as chaves AES (`SECRET_KEY`) no `/cofre/chaves`
- [ ] Testes do cofre em `tests/test_cripto.py`

### Pendências

- **Import do `src`:** o `main.py` importa `from router import ...`, mas o `router.py` importa `from src.schemas import ...`. Essa mistura faz o pytest falhar com `ModuleNotFoundError: No module named 'src'`. Correção prevista: padronizar para `from schemas import ...`.
- **Testes dependentes:** alguns testes usam uma chave que não criam. Exemplo: `test_texto_alterado_em_uma_letra_reprova_verificacao` assina com `teste02` sem gerar a chave antes, e falha com `KeyError: 'assinatura'` (a rota devolve `404`). Correção: cada teste gera a própria chave no início (`client.post("chaves/rsa", json={"nome": "teste02"})`).

### Limitações conhecidas

- Chamar `/rsa` ou `/aes` com um nome que **já existe** sobrescreve a chave anterior.
- Base64 malformado no `/verificar` ou no `/decifrar` ainda retorna `500`.
- O PIN e o label do token estão fixos no `hsm.py`. Como é um cofre de treino, tudo bem; num projeto real iriam para o `.env`.

---

## ⚠️ Aviso

Projeto **educacional**. Em produção, chaves privadas não ficam em arquivo no disco: ficam em um KMS, Vault ou HSM. A Parte 2 simula exatamente isso com o SoftHSM.

---

Feito por [Luiza Souza](https://luizasouza.eti.br) · [@lu-izah19](https://github.com/lu-izah19)
