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
│   └── test_cripto.py   # testes do cofre (Parte 2)
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

Toda rota recebe um campo `nome`, que identifica qual chave usar. Na Parte 1 ele vira parte do nome do arquivo; na Parte 2 vira o **label** da chave dentro do cofre.

| Tipo | Parte 1 (arquivos) | Parte 2 (cofre) |
|---|---|---|
| RSA | `chaves/{nome}_privada.pem` e `chaves/{nome}_publica.pem` | par RSA com label `{nome}` |
| AES | `chaves/{nome}_aes.key` | chave secreta com label `{nome}` |

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

Internamente: o `verify()` da `cryptography` não retorna `True`. Quando falha, ele **lança `InvalidSignature`**, que é capturado com `try/except`.

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
| Assinatura RSA | RSA-PSS + SHA-256 | `SHA256_RSA_PKCS` (PKCS#1 v1.5) |
| Mecanismo AES | AES-GCM | AES-GCM |
| Assinatura inválida | `verify()` **lança** `InvalidSignature` | `verify()` **devolve** `False` |

> Como o padding da assinatura é diferente nas duas partes, uma assinatura feita no `/chaves/assinar` não é verificável no `/chaves/cofre/verificar`, e vice-versa.

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
| `verificar_no_cofre(label, texto, assinatura)` | Pede ao cofre para verificar a assinatura e devolve `True`/`False` |
| `gerar_aes_no_cofre(label)` | Gera uma chave AES-256 dentro do cofre. Não devolve nada: a chave não sai |
| `cifrar_aes_no_cofre(label, texto)` | Gera o nonce, pede ao cofre para cifrar com `AES_GCM` e devolve a tupla `(cifrado, nonce)` |
| `decifrar_aes_no_cofre(label, cifrado, nonce)` | Pede ao cofre para decifrar com o nonce recebido e devolve o texto já decodificado (`str`) |

**Atributos da chave RSA privada:** `TOKEN`, `PRIVATE`, `SENSITIVE: True`, `EXTRACTABLE: False`, `SIGN`.

**Atributos da chave AES:** `TOKEN`, `PRIVATE`, `SENSITIVE: True`, `EXTRACTABLE: False` (nunca sai do cofre), `ENCRYPT` e `DECRYPT` (só pode cifrar e decifrar, nada além: **princípio do menor privilégio**).

**Parâmetros do GCM no cofre:** `mechanism_param=(nonce, b"", 128)`, ou seja, o IV de 12 bytes, dados adicionais autenticados vazios e tag de **128 bits** (16 bytes).

### O papel das rotas

As rotas do cofre são **finas**: chamam a função do `hsm.py`, convertem bytes para base64 (ou o contrário) e devolvem um dicionário. Toda a criptografia acontece dentro do cofre. Nada de `rsa.generate_private_key`, `AESGCM` ou arquivo `.pem` aqui.

---

## 📡 Endpoints: Parte 2 (cofre)

Também sob o prefixo `/chaves`.

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

### RSA no cofre

#### `POST /chaves/cofre/rsa`

Gera um par RSA-2048 **dentro do cofre**. A privada fica lá; a resposta traz só o **módulo da chave pública** em base64.

**Request**
```json
{ "nome": "lu" }
```

**Resposta**
```json
{ "chave_publica": "u7Hq...==" }
```

---

#### `POST /chaves/cofre/assinar`

Pede ao cofre para assinar o texto com a privada guardada lá.

**Request**
```json
{ "nome": "lu", "texto": "contrato do estagio" }
```

**Resposta**
```json
{ "texto_assinado": "kj3h2K...==" }
```

> ⚠️ O valor de `texto_assinado` é a **assinatura** em base64. É ele que vai no campo `assinatura_b64` do `/cofre/verificar`.

---

#### `POST /chaves/cofre/verificar`

Pede ao cofre para verificar a assinatura com a pública.

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

Diferente da Parte 1, aqui não tem `try/except`: o `python-pkcs11` **devolve** `True` ou `False` em vez de lançar exceção. Assinatura que não bate **não é erro**: a API entendeu o pedido e respondeu, então volta `200` com `{ "valida": false }`.

---

### AES no cofre

#### `POST /chaves/cofre/aes`

Gera uma chave AES-256 dentro do cofre. Como a chave é `SENSITIVE` e não `EXTRACTABLE`, a resposta é só uma confirmação.

**Request**
```json
{ "nome": "lu" }
```

**Resposta**
```json
{ "message": "Chave AES gerada com sucesso" }
```

---

#### `POST /chaves/cofre/cifrar`

Cifra o texto dentro do cofre com AES-GCM. A função do `hsm.py` devolve uma **tupla** `(cifrado, nonce)`, que a rota desempacota em duas variáveis e converte para base64.

**Request**
```json
{ "nome": "lu", "texto": "oi lu" }
```

**Resposta**
```json
{ "cifrado": "Xk9a...==", "nonce": "a1B2c3...==" }
```

> ⚠️ Igual à Parte 1: sai como `cifrado`, entra no `/cofre/decifrar` como `texto_cifrado`.

---

#### `POST /chaves/cofre/decifrar`

Decifra dentro do cofre. A rota só converte o base64 de volta para bytes; o texto já volta decodificado do `hsm.py`.

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

---

## 🚦 Códigos de resposta

| Código | Quando acontece |
|---|---|
| `200` | Deu certo (inclusive `{ "valida": false }`: assinatura que não bate é resposta, não erro) |
| `400` | Dados cifrados adulterados ou nonce errado (Parte 1) |
| `404` | Chave com esse nome não existe (Parte 1) |
| `422` | Request inválido (ex.: `nome` fora da allowlist) |
| `500` | Erros ainda não tratados nas rotas do cofre (ver Limitações) |

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

> O pytest só reconhece funções que **começam com `test_`**.

### Parte 1: `test_router.py`

| Teste | O que prova |
|---|---|
| `test_gerar_par_de_chaves_cria_os_dois_arquivos` | `/rsa` cria a chave privada e a pública no disco |
| `test_assinar_verificar_mesmo_texto_devolve_verdadeiro` | Uma assinatura válida é aceita pelo `/verificar` |
| `test_texto_alterado_em_uma_letra_reprova_verificacao` | Mudar **uma letra** do texto faz a verificação falhar |
| `test_cifrar_decifrar_devolve_texto_original` | Cifrar e decifrar devolve exatamente o texto original |
| `test_cifrar_mesmo_texto_duas_vezes_da_resultados_DIFERENTES` | Com a **mesma chave**, o mesmo texto gera cifrados diferentes (nonce aleatório) |
| `test_decifrar_com_iv_errado_falha` | Decifrar com o nonce de **outra** cifragem é barrado com `400` |

### Parte 2: `test_cripto.py`

| Teste | O que prova |
|---|---|
| `test_cofre_status_responde_com_label_do_token` | A API conversa com o cofre e lê o label `cofre-treino` |
| `test_gerar_chave_no_cofre_devolve_parte_pública` | `/cofre/rsa` responde `200` com uma `chave_publica` não vazia |
| `test_chave_privada_NÃO_pode_ser_lida_nem_exportada` | A privada está marcada `SENSITIVE` e não `EXTRACTABLE`, e tentar ler o `PRIVATE_EXPONENT` estoura `AttributeSensitive` |
| `test_assinar_verificar_pelo_cofre_funciona` | Assinar e verificar o mesmo texto no cofre devolve `valida: true` |
| `test_texto_alterado_reprova_verificação` | Verificar com outro texto devolve `200` e `valida: false` |
| `test_cifrar_decifrar_pelo_cofre_devolve_original` | Gerar AES → cifrar → decifrar devolve exatamente o texto original |
| `test_listar_chaves_devolve_as_que_foram_criadas` | Uma chave RSA recém-criada aparece no `/cofre/chaves` |

### Padrões usados

- **Chamadas encadeadas:** a resposta de uma rota alimenta a próxima (ex.: a assinatura do `/assinar` vai pro `/verificar`).
- **Cada teste cria a própria chave:** nunca depende de uma chave que outro teste (ou o Swagger) criou.
- **Nome único com `uuid`:** no cofre, a chave **não some** quando o teste acaba. Por isso cada teste usa `f"teste_cofre_{uuid.uuid4().hex}"`, e rodar o pytest várias vezes não gera labels duplicados.
- **Texto numa variável:** `texto = "..."` usado no assinar e no verificar (ou no cifrar e no decifrar) garante que os dois passos falam da mesma coisa.
- **Status antes do conteúdo:** o `assert` do `status_code` vem primeiro. Se a rota falhar, o erro fica claro ("esperava 200, veio 404") em vez de um `KeyError` confuso.
- **Ler a resposta:** `resposta.json()["campo"]` transforma o corpo em dicionário e pega o campo.
- **Procurar numa lista de dicionários:** montar uma lista só com os labels (`for` + `.append(chave["label"])`) e aí usar `nome in lista`.
- **Conferir erro de rota:** `resposta.status_code == 400` confere o código HTTP direto, sem `.json()`.
- **Conferir que algo DÁ erro:** `with pytest.raises(AttributeSensitive):` só passa se o código de dentro estourar essa exceção.
- **Falar direto com o cofre:** quando nenhuma rota faz o que o teste precisa (como tentar ler a privada), o teste abre `sessao_hsm()` sozinho. Tudo que usa a sessão fica **dentro** do `with`.
- **Nonce errado de verdade:** em vez de inventar um texto qualquer (que nem seria base64 válido), o teste usa o nonce de uma segunda cifragem. Assim ele é válido, mas pertence à mensagem errada, e o teste prova que o GCM detecta isso.
- **Depurar `KeyError`:** quando `resposta.json()["campo"]` dá `KeyError`, a rota devolveu erro em vez de sucesso, ou o nome do campo não bate com o `return` da rota. Um `print(resposta.status_code, resposta.json())` antes mostra o que veio.

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
- **Resposta vs erro:** assinatura inválida é uma resposta legítima (`200` + `false`), não um erro do cliente.
- **HSM / PKCS#11:** a chave fica num cofre e o código só pede operações. Chave marcada como `SENSITIVE` e não `EXTRACTABLE` não pode ser lida nem pelo próprio dono.
- **Chave secreta (`SECRET_KEY`):** no PKCS#11, chave simétrica (AES) não é privada nem pública, é "secreta".
- **Menor privilégio:** a chave só recebe as permissões de que precisa (`ENCRYPT`/`DECRYPT` para AES, `SIGN`/`VERIFY` para RSA).
- **Tupla e desempacotamento:** uma função que faz `return a, b` devolve uma tupla, que pode ser recebida direto em duas variáveis: `x, y = funcao()`.
- **Escopo local:** uma variável criada dentro de uma função só existe ali, então duas rotas podem usar o mesmo nome de variável sem conflito.

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
- [x] Rotas que usam o cofre para RSA (`/cofre/rsa`, `/cofre/assinar`, `/cofre/verificar`)
- [x] Rotas que usam o cofre para AES (`/cofre/aes`, `/cofre/cifrar`, `/cofre/decifrar`)
- [x] Testes do cofre em `tests/test_cripto.py` escritos (7 testes)
- [ ] Rodar o `test_cripto.py` e deixar tudo verde
- [ ] Listar também as chaves AES (`SECRET_KEY`) no `/cofre/chaves`
- [ ] Tratar os erros do cofre (ver Limitações)

### Pendências

- **Import do `src`:** o `main.py` importa `from router import ...`, mas o `router.py` importa `from src.schemas import ...`. Essa mistura faz o pytest falhar com `ModuleNotFoundError: No module named 'src'`. Correção prevista: padronizar para `from schemas import ...`.
- **Testes dependentes (Parte 1):** alguns testes usam uma chave que não criam. Exemplo: `test_texto_alterado_em_uma_letra_reprova_verificacao` assina com `teste02` sem gerar a chave antes, e falha com `KeyError: 'assinatura'` (a rota devolve `404`). Correção: cada teste gera a própria chave no início (`client.post("chaves/rsa", json={"nome": "teste02"})`).
- **Campo da assinatura no cofre:** a rota `/cofre/assinar` devolve `texto_assinado`, mas os testes leem `assinatura_cofre.json()["assinatura"]`. Os dois precisam usar o mesmo nome, senão o teste dá `KeyError`.
- **Aviso do VS Code no `from main import app`:** o editor não acha o `main.py` porque ele está em `src/` e os testes em `tests/`. Dentro do Docker o pytest pode encontrar normalmente; conferir rodando.

### Limitações conhecidas

- Chamar `/rsa` ou `/aes` (Parte 1) com um nome que **já existe** sobrescreve a chave anterior.
- No **cofre** é diferente: gerar duas vezes com o mesmo nome **não sobrescreve**, cria uma segunda chave com o mesmo label. Depois disso, `assinar`, `verificar`, `cifrar` e `decifrar` com esse nome estouram `MultipleObjectsReturned` (`500`).
- Pedir uma chave que não existe no cofre estoura `NoSuchKey` (`500`). O `except FileNotFoundError` da Parte 1 não serve aqui, porque no cofre não há arquivo.
- Base64 malformado no `/verificar`, no `/decifrar` e nas rotas equivalentes do cofre ainda retorna `500`.
- Nonce ou cifrado adulterado no `/cofre/decifrar` ainda não foi tratado como `400`.
- O PIN e o label do token estão fixos no `hsm.py`. Como é um cofre de treino, tudo bem; num projeto real iriam para o `.env`.

---

## ⚠️ Aviso

Projeto **educacional**. Em produção, chaves privadas não ficam em arquivo no disco: ficam em um KMS, Vault ou HSM. A Parte 2 simula exatamente isso com o SoftHSM.

---

Feito por [Luiza Souza](https://luizasouza.eti.br) · [@lu-izah19](https://github.com/lu-izah19)
