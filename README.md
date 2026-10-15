# 🔐 API de Criptografia

API em **FastAPI** que expõe operações criptográficas como endpoints REST: geração de chaves RSA, assinatura e verificação digital, geração de chaves AES-256 e cifragem/decifragem autenticada com AES-GCM. Cada chave tem um **nome**, então várias chaves convivem sem uma sobrescrever a outra. Roda em **Docker** com hot-reload e tem uma suíte de testes com **pytest**.

Na **Parte 2**, as chaves deixam de ficar em arquivo e passam a viver dentro de um **cofre (HSM simulado com SoftHSM)**, acessado via **PKCS#11**. A chave nasce lá dentro e nunca sai: a API só pede para o cofre fazer o trabalho.

No **RF-08**, a API ganhou um **painel de monitoramento** (`GET /monitoramento`) que mostra quantas chaves existem, quantas operações foram feitas, quanto espaço as chaves ocupam no disco e há quanto tempo a API está no ar.

Projeto de estudo desenvolvido durante o estágio de back-end na CERMOB Tecnologia. **Status: ✅ finalizado.**

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
│   ├── main.py          # instancia o FastAPI, inclui o router, middleware de contagem e rotas /saude e /monitoramento
│   ├── router.py        # rotas da API (Parte 1 e Parte 2), com prefixo /chaves
│   ├── schemas.py       # modelos Pydantic de request e da resposta do monitoramento
│   ├── metricas.py      # métricas do monitoramento: tempo no ar, operações, chaves e disco
│   └── hsm.py           # funções que conversam com o cofre (PKCS#11)
├── tests/
│   ├── test_router.py         # testes das rotas da Parte 1
│   ├── test_cripto.py         # testes do cofre (Parte 2)
│   └── test_monitoramento.py  # testes do painel de monitoramento (RF-08)
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

### Com Docker

**Pré-requisitos:** Docker e Docker Compose.

```bash
# primeira vez (ou depois de mexer no requirements.txt)
docker compose up --build

# nas próximas vezes
docker compose up -d
```

O Uvicorn observa a pasta `/app`, então qualquer alteração no código recarrega a API sozinha.

Para conferir se está de pé: `docker compose ps` (o container deve aparecer como `Running`) ou abrir o Swagger.

### Sem Docker (Windows)

Funciona para a Parte 1 e para o monitoramento. O cofre (Parte 2) **não** roda assim (ver Limitações).

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --app-dir src
```

> ⚠️ Se o projeto veio de um `.zip` do GitHub, ele costuma ficar numa pasta dentro de outra com o mesmo nome. Os comandos precisam rodar na pasta **de dentro**, a que tem o `src/`. Senão aparece `Could not import module "main"`.

### Documentação interativa

- Swagger UI → `http://localhost:8000/docs`
- ReDoc → `http://localhost:8000/redoc`

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

Lista as chaves RSA que estão dentro do cofre, com label e tipo. Percorre os objetos com `sessao.get_objects(...)` e devolve só os metadados: nenhuma chave sai.

**Resposta**
```json
[
  { "label": "lu", "tipo": "RSA" }
]
```

> ℹ️ O filtro busca `ObjectClass.PRIVATE_KEY`, então chaves AES (que são `SECRET_KEY`) não aparecem na lista.

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
{ "assinatura": "kj3h2K...==" }
```

O campo tem o mesmo nome da `/assinar` da Parte 1. O valor de `assinatura` é o que vai no campo `assinatura_b64` do `/cofre/verificar`.

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

## 📊 Monitoramento (RF-08)

### `GET /monitoramento`

Painel com o estado atual da API. Fica no `main.py`, e **não** no `router.py`: o router tem `prefix="/chaves"`, então a rota viraria `/chaves/monitoramento`.

**Resposta**
```json
{
  "disco":     { "bytes": 6593, "legivel": "6.44 KB" },
  "chave":     { "total": 7, "rsa": 3, "aes": 4 },
  "operacoes": { "total": 4, "rota": { "/docs": 1, "/openapi.json": 1, "/monitoramento": 1, "/": 1 } },
  "tempo":     { "segundos": 30, "legivel": "0h 0min 30s" }
}
```

A resposta é validada por `MonitoramentoResponse`, um schema que junta quatro schemas menores: `Chave`, `Operacoes`, `Disco` e `Tempo_no_ar`.

### Como cada métrica é calculada (`src/metricas.py`)

| Métrica | Como funciona | Onde fica |
|---|---|---|
| Tempo no ar | A hora de subida é guardada no **topo do módulo**, que roda uma vez só, no primeiro `import`. A rota calcula a diferença até agora | memória |
| Operações | Um **middleware** no `main.py` registra o caminho de toda requisição antes de repassar para a rota (`call_next`). Conta o total e por rota | memória |
| Chaves | Conta os arquivos da pasta `chaves/` pelo padrão do nome (`_privada.pem` = RSA, `_aes.key` = AES) | disco |
| Disco | Soma o tamanho dos arquivos de chave com `pathlib` + `stat()` | disco |

### Decisões

| # | Pergunta | Decisão | Por quê |
|---|---|---|---|
| 1 | Um par RSA conta como 1 ou 2 chaves? | **1** | Pública e privada são as duas metades de uma mesma chave, geradas juntas numa única chamada |
| 2 | A `/monitoramento` conta ela mesma? | **Sim** (previsto e confirmado) | O middleware registra **antes** do `call_next`. Na primeira chamada depois de reiniciar, o total já vem `1` |
| 3 | O que acontece com os números quando a API reinicia? | Operações e tempo no ar **zeram**; chaves e disco **continuam** | Os dois primeiros ficam em variáveis (RAM); os dois últimos vêm de arquivos (disco). Um histórico exigiria salvar o contador em arquivo ou banco |

> 👀 Abrir o `/docs` no navegador conta **2 operações a mais** (`/docs` e `/openapi.json`), porque o próprio navegador faz essas requisições para montar a página.

### Requisito original × o que foi pedido

| RF-08 (original) | Tabela da tarefa | O que aconteceu |
|---|---|---|
| Chaves **por partição** | Chaves **por tipo** | ⚠️ Trocado: a mini API não tem partições, todas as chaves ficam na mesma pasta. O único critério que existe é o tipo |
| Uso de **memória** e disco | Espaço em **disco** | ⚠️ Memória tirada: a mini API não tem uma memória de HSM pra medir, as chaves vivem em arquivos |
| Número de operações | Operações por rota | ✅ Mantido (e detalhado por rota) |
| Tempo real / máx. 60s | — | ❌ Tirado: a rota é um `GET` e só responde quando alguém chama. Atualizar a cada 60s é papel de quem consome a API |
| — | **Tempo no ar** | ➕ Acrescentado: como o contador zera ao reiniciar, o tempo no ar mostra desde quando ele está contando |

---

## 🚦 Códigos de resposta

| Código | Quando acontece |
|---|---|
| `200` | Deu certo (inclusive `{ "valida": false }`: assinatura que não bate é resposta, não erro) |
| `400` | Dados cifrados adulterados ou nonce errado (Parte 1) |
| `404` | Chave com esse nome não existe (Parte 1) |
| `422` | Request inválido (ex.: `nome` fora da allowlist) |
| `500` | Erros não tratados nas rotas do cofre (ver Limitações) |

---

## 🧪 Testes

Os testes ficam em `tests/` e usam o `TestClient` do FastAPI, que faz requisições à API sem precisar subir servidor.

### Como rodar

Com Docker (container de pé):

```bash
docker compose exec api pytest
```

Sem Docker (Windows, PowerShell):

```powershell
$env:PYTHONPATH="src"; pytest
```

> `api` é o nome do serviço no `docker-compose.yml`. Para ver `print` durante os testes, use `pytest -s`.
>
> Sem Docker, o `PYTHONPATH="src"` é o que faz o `from main import app` funcionar. O VS Code pode sublinhar esse import de amarelo (`could not be resolved`), mas o pytest roda normal.

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

### Monitoramento: `test_monitoramento.py`

| Teste | O que prova |
|---|---|
| `test_monitoramento_responde` | `/monitoramento` responde `200` com as quatro seções (`disco`, `chave`, `operacoes`, `tempo`) |
| `test_gerar_chave_aumenta_total` | Gerar um par RSA aumenta o total de chaves em **1** (Decisão 1) |
| `test_3_chamadas_aumenta_total` | 3 chamadas aumentam o total de operações em **4**: as 3 + a própria `/monitoramento` do `depois` (prova automática da Decisão 2) |
| `test_tempo_no_ar_maior_que_zero` | O tempo no ar em segundos é maior que zero |
| `test_gerar_chave_aumenta_espaco_disco` | Gerar uma chave aumenta os bytes ocupados no disco (`>`, porque o tamanho exato varia) |

### Padrões usados

- **Chamadas encadeadas:** a resposta de uma rota alimenta a próxima (ex.: a assinatura do `/assinar` vai pro `/verificar`).
- **Antes e depois:** lê a métrica, faz a ação, lê de novo e compara. É o esqueleto dos testes de monitoramento.
- **Contar todas as requisições:** no teste de operações, a chamada que lê o `depois` também passa pelo middleware e entra na conta.
- **Cada teste cria a própria chave:** nunca depende de uma chave que outro teste (ou o Swagger) criou.
- **Nome único com `uuid`:** no cofre, a chave **não some** quando o teste acaba. Por isso cada teste usa `f"teste_cofre_{uuid.uuid4().hex}"`, e rodar o pytest várias vezes não gera labels duplicados.
- **Texto numa variável:** `texto = "..."` usado no assinar e no verificar (ou no cifrar e no decifrar) garante que os dois passos falam da mesma coisa.
- **Status antes do conteúdo:** o `assert` do `status_code` vem primeiro. Se a rota falhar, o erro fica claro ("esperava 200, veio 404") em vez de um `KeyError` confuso.
- **Ler a resposta:** `resposta.json()["campo"]` transforma o corpo em dicionário e pega o campo. Para JSON aninhado, encadeia: `["chave"]["total"]`.
- **Procurar numa lista de dicionários:** montar uma lista só com os labels (`for` + `.append(chave["label"])`) e aí usar `nome in lista`.
- **Conferir erro de rota:** `resposta.status_code == 400` confere o código HTTP direto, sem `.json()`.
- **Conferir que algo DÁ erro:** `with pytest.raises(AttributeSensitive):` só passa se o código de dentro estourar essa exceção.
- **Falar direto com o cofre:** quando nenhuma rota faz o que o teste precisa (como tentar ler a privada), o teste abre `sessao_hsm()` sozinho. Tudo que usa a sessão fica **dentro** do `with`.
- **Nonce errado de verdade:** em vez de inventar um texto qualquer (que nem seria base64 válido), o teste usa o nonce de uma segunda cifragem. Assim ele é válido, mas pertence à mensagem errada, e o teste prova que o GCM detecta isso.
- **Depurar `KeyError`:** quando `resposta.json()["campo"]` dá `KeyError`, a rota devolveu erro em vez de sucesso, ou o nome do campo não bate com o `return` da rota. Um `print(resposta.status_code, resposta.json())` antes mostra o que veio.
- **Depurar `500`:** o `/docs` só mostra "Internal Server Error". O motivo real fica no **final** do traceback no terminal (traceback se lê de baixo pra cima). Um `ResponseValidationError` com `input: None` quer dizer que a rota esqueceu o `return`.

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
- **Partição (HSM):** área isolada dentro do cofre, com chaves, PIN e usuários próprios, como apartamentos num prédio.
- **Chave secreta (`SECRET_KEY`):** no PKCS#11, chave simétrica (AES) não é privada nem pública, é "secreta".
- **Menor privilégio:** a chave só recebe as permissões de que precisa (`ENCRYPT`/`DECRYPT` para AES, `SIGN`/`VERIFY` para RSA).
- **Tupla e desempacotamento:** uma função que faz `return a, b` devolve uma tupla, que pode ser recebida direto em duas variáveis: `x, y = funcao()`.
- **Escopo local:** uma variável criada dentro de uma função só existe ali, então duas rotas podem usar o mesmo nome de variável sem conflito.
- **Middleware:** código que roda em toda requisição, antes e depois da rota, sem precisar mexer em cada rota.
- **Código no topo do módulo:** roda uma vez só, no primeiro `import`. Bom lugar para guardar a hora de subida.
- **Memória (RAM) vs disco:** o que está em variável some quando o programa para; o que está em arquivo continua.
- **Schemas aninhados:** um modelo Pydantic pode ter outros modelos como campos (`disco: Disco`), formando um JSON em camadas.
- **`GET` não empurra dados:** a rota só responde quando é chamada. Atualização periódica é responsabilidade de quem consome.

---

## ✅ Status: projeto finalizado

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
- [x] Suíte de testes com pytest (6 testes) rodando

### Parte 2

- [x] `hsm.py`: sessão com o cofre e funções RSA (gerar, assinar, verificar)
- [x] `hsm.py`: funções AES (`gerar_aes_no_cofre`, `cifrar_aes_no_cofre`, `decifrar_aes_no_cofre`)
- [x] `GET /chaves/cofre/status`
- [x] `GET /chaves/cofre/chaves`
- [x] Rotas que usam o cofre para RSA (`/cofre/rsa`, `/cofre/assinar`, `/cofre/verificar`)
- [x] Rotas que usam o cofre para AES (`/cofre/aes`, `/cofre/cifrar`, `/cofre/decifrar`)
- [x] Testes do cofre em `tests/test_cripto.py` (7 testes) rodando

### RF-08: monitoramento

- [x] `metricas.py`: tempo no ar, contador de operações, contagem de chaves e espaço em disco
- [x] Middleware contando toda requisição
- [x] Schemas `Chave`, `Operacoes`, `Disco`, `Tempo_no_ar` e `MonitoramentoResponse`
- [x] `GET /monitoramento` no `main.py`
- [x] Decisões 1, 2 e 3 testadas e registradas
- [x] Testes em `tests/test_monitoramento.py` (5 testes) rodando
- [x] Entrega 2: comparação com o requisito original e perguntas para quem escreveu o requisito

### Limitações conhecidas

- Chamar `/rsa` ou `/aes` (Parte 1) com um nome que **já existe** sobrescreve a chave anterior.
- No **cofre** é diferente: gerar duas vezes com o mesmo nome **não sobrescreve**, cria uma segunda chave com o mesmo label. Depois disso, `assinar`, `verificar`, `cifrar` e `decifrar` com esse nome estouram `MultipleObjectsReturned` (`500`).
- Pedir uma chave que não existe no cofre estoura `NoSuchKey` (`500`). O `except FileNotFoundError` da Parte 1 não serve aqui, porque no cofre não há arquivo.
- Base64 malformado no `/verificar`, no `/decifrar` e nas rotas equivalentes do cofre retorna `500`.
- Nonce ou cifrado adulterado no `/cofre/decifrar` não é tratado como `400`.
- O PIN e o label do token estão fixos no `hsm.py`. Como é um cofre de treino, tudo bem; num projeto real iriam para o `.env`.
- **O cofre não roda sem Docker no Windows:** o `hsm.py` carrega o SoftHSM pelo caminho de Linux (`/usr/lib/softhsm/libsofthsm2.so`), que só existe dentro do container. Limitação de ambiente, não de código.
- **O monitoramento conta só as chaves em arquivo** (Parte 1). As chaves do cofre ficam de fora, pelo mesmo motivo acima.
- **Os contadores do monitoramento zeram** quando a API reinicia (ficam em memória).
- **Os testes `test_gerar_chave_aumenta_total` e `test_gerar_chave_aumenta_espaco_disco` usam nomes fixos.** Na segunda rodada do pytest a chave já existe e é sobrescrita, então o total e o disco não aumentam e o teste falha. É preciso apagar `testeMonitoramento` e `testeEspacoDisco` da pasta `chaves/` antes de rodar de novo (ou usar `uuid`, como nos testes do cofre).

---

## ⚠️ Aviso

Projeto **educacional**. Em produção, chaves privadas não ficam em arquivo no disco: ficam em um KMS, Vault ou HSM. A Parte 2 simula exatamente isso com o SoftHSM.

---

Feito por [Luiza Souza](https://luizasouza.eti.br) · [@lu-izah19](https://github.com/lu-izah19)
