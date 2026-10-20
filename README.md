# 🔐 API de Criptografia

API em **FastAPI** que expõe operações criptográficas como endpoints REST: geração de chaves RSA, assinatura e verificação digital, geração de chaves AES-256 e cifragem/decifragem autenticada com AES-GCM. Cada chave tem um **nome**, então várias chaves convivem sem uma sobrescrever a outra. Roda em **Docker** com hot-reload e tem uma suíte de testes com **pytest**.

Na **Parte 2**, as chaves deixam de ficar em arquivo e passam a viver dentro de um **cofre (HSM simulado com SoftHSM)**, acessado via **PKCS#11**. A chave nasce lá dentro e nunca sai: a API só pede para o cofre fazer o trabalho.

No **RF-08**, a API ganhou um **painel de monitoramento** (`GET /monitoramento`) que mostra quantas chaves existem, quantas operações foram feitas, quanto espaço as chaves ocupam no disco e há quanto tempo a API está no ar.

O painel ganhou uma **tela**: uma página em **HTML e JavaScript puro**, servida pela própria API em `http://localhost:8000/`, que consome a `/monitoramento` e se atualiza sozinha a cada 10 segundos.

Por fim, no **RF-07**, a API ganhou um **limite máximo de chaves**, configurável por variável de ambiente. Quando o limite é atingido, a criação de novas chaves é recusada, e o painel mostra quanto do limite já foi usado.

Projeto de estudo desenvolvido durante o estágio de back-end na CERMOB Tecnologia. **Status: ✅ finalizado** (faltam os testes das mudanças do RF-07).

---

## 🧱 Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3 |
| Framework | FastAPI + Uvicorn |
| Criptografia | [`cryptography`](https://cryptography.io/) |
| Cofre (HSM) | SoftHSM2 + [`python-pkcs11`](https://python-pkcs11.readthedocs.io/) 0.10.0 |
| Validação | Pydantic |
| Configuração | Variáveis de ambiente (`LIMITE_CHAVES`, `PIN`) |
| Tela do painel | HTML + JavaScript puro (sem framework, sem biblioteca de CSS) |
| Container | Docker + Docker Compose |
| Testes | pytest + `TestClient` + httpx |

---

## 📁 Estrutura

```
.
├── src/
│   ├── main.py          # instancia o FastAPI, inclui o router, middleware de contagem, rotas /saude e /monitoramento e serve a tela
│   ├── router.py        # rotas da API (Parte 1 e Parte 2), com prefixo /chaves, e as funções do limite de chaves
│   ├── schemas.py       # modelos Pydantic de request e da resposta do monitoramento
│   ├── metricas.py      # métricas do monitoramento: tempo no ar, operações, chaves e disco
│   ├── config.py        # lê as variáveis de ambiente (LIMITE_CHAVES e PIN)
│   └── hsm.py           # funções que conversam com o cofre (PKCS#11)
├── screen/              # tela do painel (front-end), separada do Python
│   ├── index.html       # estrutura da página: rótulos fixos e spans com id para os valores
│   ├── script.js        # busca a /monitoramento, preenche a tela e se repete a cada 10s
│   └── style.css        # visual da tela
├── tests/
│   ├── test_router.py         # testes das rotas da Parte 1
│   ├── test_cripto.py         # testes do cofre (Parte 2)
│   └── test_monitoramento.py  # testes do painel de monitoramento (RF-08)
├── chaves/              # chaves geradas na Parte 1 (criada automaticamente, NÃO vai pro repositório)
├── .gitignore
├── Dockerfile           # copia o src/ e a screen/ para dentro do container
├── docker-compose.yml   # define LIMITE_CHAVES e PIN em environment
├── requirements.txt
└── README.md
```

> 🔒 As chaves da Parte 1 ficam na pasta `chaves/`, separadas do código. A pasta é criada automaticamente quando a API sobe. **Chave privada nunca vai pro repositório:** o `.gitignore` deixa de fora a pasta `chaves/`, qualquer arquivo `.pem` ou `.key`, o `.env` e os caches do Python.

---

## 🚀 Como rodar

### Com Docker

**Pré-requisitos:** Docker e Docker Compose.

```bash
# primeira vez (ou depois de mexer no requirements.txt ou no Dockerfile)
docker compose up --build

# nas próximas vezes
docker compose up -d
```

O Uvicorn observa a pasta `/app`, então qualquer alteração no código recarrega a API sozinha.

Para conferir se está de pé: `docker compose ps` (o container deve aparecer como `Running`) ou abrir o Swagger.

> 📦 O `Dockerfile` precisa copiar a pasta `screen/` para dentro do container. Sem isso, a API não sobe e mostra `RuntimeError: Directory 'screen' does not exist`.

### Variáveis de ambiente

Ficam no `docker-compose.yml`, em `environment`, e são lidas pelo `src/config.py`.

| Variável | O que é | Valor no `docker-compose.yml` | Padrão (se não existir) |
|---|---|---|---|
| `LIMITE_CHAVES` | Número máximo de chaves (arquivos + cofre) | `5` | `10` |
| `PIN` | Senha do token do cofre | `5678` | `"5678"` |

Se a variável não estiver definida, a API usa o valor padrão e sobe normalmente.

### Sem Docker (Windows)

Funciona para a Parte 1, o monitoramento e a tela do painel. O cofre (Parte 2) **não** roda assim (ver Limitações).

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --app-dir src
```

> ⚠️ Se o projeto veio de um `.zip` do GitHub, ele costuma ficar numa pasta dentro de outra com o mesmo nome. Os comandos precisam rodar na pasta **de dentro**, a que tem o `src/`. Senão aparece `Could not import module "main"`.
>
> 💡 Use **dois terminais**: um só para o uvicorn e outro para pytest, ruff e o resto. Se você der `Ctrl+C` no uvicorn para rodar outra coisa, a API cai e o Swagger mostra `Failed to fetch`.

### Endereços

- Tela do painel → `http://localhost:8000/`
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

**Erros:** `507` se o limite de chaves foi atingido (ver RF-07).

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

**Erros:** `507` se o limite de chaves foi atingido (ver RF-07).

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
- **PIN:** a senha do token. Vem da variável de ambiente `PIN`, lida no `config.py`.
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

**Parâmetros do GCM no cofre:** `mechanism_param=GCMParams(nonce)`, com o IV de 12 bytes.

> ⚠️ A `python-pkcs11` 0.10.0 **não aceita mais a tupla** `(nonce, b"", 128)` no `AES_GCM`: dá `TypeError` sem mensagem nenhuma. A documentação oficial ainda diz que o AES_GCM não é suportado, mas a classe `GCMParams` existe nessa versão (confirmado no código-fonte da biblioteca).

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

> ℹ️ O filtro busca `ObjectClass.PRIVATE_KEY`, então chaves AES (que são `SECRET_KEY`) não aparecem na lista. Essa função também é usada na contagem do limite de chaves (ver RF-07).

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

**Erros:** `507` se o limite de chaves foi atingido (ver RF-07).

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

O valor de `texto_assinado` é o que vai no campo `assinatura_b64` do `/cofre/verificar`.

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

**Erros:** `507` se o limite de chaves foi atingido (ver RF-07).

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

## 🚧 Limite máximo de chaves (RF-07)

A API tem um número máximo de chaves, definido pela variável de ambiente `LIMITE_CHAVES`. Quando o limite é atingido, as rotas que criam chaves recusam o pedido com **507**:

```json
{ "detail": "Limite de 5 chaves atingido. Existem 5 chaves, por isso a criação foi recusada." }
```

### Como funciona (`src/router.py`)

| Função | O que faz |
|---|---|
| `contar_total_geral()` | Soma as chaves em arquivo (`contar_chaves()`, do `metricas.py`) com as chaves do cofre (`len(listar_chaves_cofre())`) e devolve o total |
| `verificar_limite()` | Chama a `contar_total_geral()` e, se o total for `>=` ao `LIMITE_CHAVES`, lança `HTTPException` com status `507` |

O `verificar_limite()` é a **primeira linha** das quatro rotas que criam chaves: `/chaves/rsa`, `/chaves/aes`, `/chaves/cofre/rsa` e `/chaves/cofre/aes`. Se viesse depois, a chave já estaria criada quando o erro estourasse.

### Decisões

| # | Pergunta | Decisão | Por quê |
|---|---|---|---|
| 1 | Limite e PIN no código ou fora dele? | **Variáveis de ambiente**, lidas no `config.py` | Muda o valor sem mexer no código. O `config.py` é separado para evitar import circular entre `main.py` e `router.py` |
| 2 | `os.getenv` ou `os.environ[...]`? | **`os.getenv` com valor padrão** | O `os.environ` quebra com `KeyError` se a variável não existir |
| 3 | Converter com `int()`? | **Só o limite** | Variável de ambiente sempre chega como texto. O PIN continua texto porque um PIN como `"0123"` viraria `123` |
| 4 | PIN com valor padrão? | **Sim, `"5678"`** | É um cofre de treino, e o padrão facilita subir o projeto |
| 5 | `>` ou `>=`? | **`>=`** | Com limite 5 e 5 chaves, a sexta é recusada. Com `>` passariam 6 |
| 6 | Qual status de erro? | **507 Insufficient Storage** | Descreve "não cabe mais chave". O 409 Conflict também foi considerado, já que 5xx costuma indicar falha do servidor |
| 7 | Par RSA conta como 1 ou 2? | **1** (mantendo o RF-08) | Nos arquivos, só o `_privada.pem` é contado; no cofre, só os objetos `PRIVATE_KEY` |
| 8 | O limite vale só para arquivos? | **Não, arquivos e cofre juntos** | Um limite que vale só para metade das chaves vira bagunça |
| 9 | Onde fica a contagem total? | **Numa função só, `contar_total_geral()`, no `router.py`** | O `verificar_limite()` e o `/monitoramento` usam a mesma função, então a API e o painel nunca mostram números diferentes. Não fica no `metricas.py` porque precisa da `listar_chaves_cofre()`, e o `metricas.py` importar o `router.py` criaria import circular |
| 10 | E se o limite já foi ultrapassado? (ex.: `LIMITE_CHAVES` baixou de 10 para 5 com 8 chaves criadas) | **Só recusar novas chaves e avisar no painel** | As chaves existentes continuam funcionando. Bloquear outras operações pararia a API por causa de uma configuração, e apagar chaves automaticamente deixaria dados cifrados impossíveis de abrir |

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
  "tempo":     { "segundos": 30, "legivel": "0h 0min 30s" },
  "limite":    { "maximo": 5, "usado": 3 }
}
```

A resposta é validada por `MonitoramentoResponse`, um schema que junta cinco schemas menores: `Chave`, `Operacoes`, `Disco`, `Tempo_no_ar` e `Limite`.

> ℹ️ O bloco `chave` conta **só as chaves em arquivo**. O `limite.usado` conta **arquivos + cofre**, porque é o mesmo número que o `verificar_limite()` usa. Por isso o limite tem um bloco próprio em vez de ficar dentro de `chave`: misturar os dois confundiria o que o `chave.total` significa.

### Como cada métrica é calculada (`src/metricas.py`)

| Métrica | Como funciona | Onde fica |
|---|---|---|
| Tempo no ar | A hora de subida é guardada no **topo do módulo**, que roda uma vez só, no primeiro `import`. A rota calcula a diferença até agora | memória |
| Operações | Um **middleware** no `main.py` registra o caminho de toda requisição antes de repassar para a rota (`call_next`). Conta o total e por rota | memória |
| Chaves | Conta os arquivos da pasta `chaves/` pelo padrão do nome (`_privada.pem` = RSA, `_aes.key` = AES) | disco |
| Disco | Soma o tamanho dos arquivos de chave com `pathlib` + `stat()` | disco |
| Limite | `maximo` vem do `LIMITE_CHAVES`; `usado` vem da `contar_total_geral()`, do `router.py` | variável de ambiente + disco + cofre |

### Decisões

| # | Pergunta | Decisão | Por quê |
|---|---|---|---|
| 1 | Um par RSA conta como 1 ou 2 chaves? | **1** | Pública e privada são as duas metades de uma mesma chave, geradas juntas numa única chamada |
| 2 | A `/monitoramento` conta ela mesma? | **Sim** (previsto e confirmado) | O middleware registra **antes** do `call_next`. Na primeira chamada depois de reiniciar, o total já vem `1` |
| 3 | O que acontece com os números quando a API reinicia? | Operações e tempo no ar **zeram**; chaves e disco **continuam** | Os dois primeiros ficam em variáveis (RAM); os dois últimos vêm de arquivos (disco). Um histórico exigiria salvar o contador em arquivo ou banco |
| 4 | Onde mostrar o limite na resposta? | **Num bloco próprio, `limite`** | O `chave.total` continua significando só as chaves em arquivo |

> 👀 Abrir o `/docs` no navegador conta **2 operações a mais** (`/docs` e `/openapi.json`), porque o próprio navegador faz essas requisições para montar a página.

### Requisito original × o que foi pedido

| RF-08 (original) | Tabela da tarefa | O que aconteceu |
|---|---|---|
| Chaves **por partição** | Chaves **por tipo** | ⚠️ Trocado: a mini API não tem partições, todas as chaves ficam na mesma pasta. O único critério que existe é o tipo |
| Uso de **memória** e disco | Espaço em **disco** | ⚠️ Memória tirada: a mini API não tem uma memória de HSM pra medir, as chaves vivem em arquivos |
| Número de operações | Operações por rota | ✅ Mantido (e detalhado por rota) |
| Tempo real / máx. 60s | — | ✅ Resolvido pela **tela do painel**: a rota continua sendo um `GET` que só responde quando chamada, e quem garante a atualização é o consumidor (a tela, a cada 10s) |
| — | **Tempo no ar** | ➕ Acrescentado: como o contador zera ao reiniciar, o tempo no ar mostra desde quando ele está contando |

---

## 🖥️ Tela do painel

Na Entrega 2 ficou registrado que atualizar a cada 60 segundos é responsabilidade de **quem consome** a API, não da rota. A tela é esse consumidor.

Abre em `http://localhost:8000/` e mostra chaves, operações, disco, tempo no ar e o uso do limite, cada um com rótulo, além do **status da conexão** e da **hora da última atualização**.

### Como a API entrega a página

A pasta `screen/` é servida pelo `StaticFiles` do FastAPI, montado na raiz:

```python
PASTA_SCREEN = Path(__file__).resolve().parent.parent / "screen"

app.mount("/", StaticFiles(directory=PASTA_SCREEN, html=True), name="painel")
```

- **`html=True`:** quando alguém pede `/`, entrega o `index.html` automaticamente.
- **O mount fica no final do `main.py`**, depois do router e das rotas. Montado em `/`, ele aceita qualquer caminho; se viesse antes, engoliria `/docs`, `/monitoramento` e as rotas `/chaves/...`.
- **O caminho é ancorado no próprio `main.py`** (`Path(__file__)`). Com o caminho relativo `"screen"`, a API não encontrava a pasta dependendo de onde o uvicorn era executado.
- **No Docker, o `Dockerfile` precisa copiar a pasta `screen/`** para dentro do container. Sem isso, a API não sobe (`Directory 'screen' does not exist`).
- **Por que servir pela API, e não abrir o arquivo com dois cliques:** aberto como arquivo, a página fica em outra origem e o navegador bloqueia o `fetch` por **CORS**. Servida pela API, página e rota estão na mesma origem, e o `fetch("/monitoramento")` usa só o caminho.

### Como a tela funciona (`screen/script.js`)

| Passo | O que faz |
|---|---|
| `fetch("/monitoramento")` + `await` | Pede os dados para a API e espera a resposta |
| `await resposta.json()` | Transforma a resposta em objeto JavaScript |
| `getElementById(...).textContent` | Escreve cada valor no `span` correspondente (`dados.chave.total`, `dados.disco.legivel`...) |
| Template string | O card do limite mostra dois valores juntos: `` `${dados.limite.usado} / ${dados.limite.maximo}` `` vira, por exemplo, `3 / 5` |
| `classList.toggle("acima-do-limite", usado > maximo)` | Liga a classe vermelha no card do limite quando o uso passa do máximo, e desliga sozinha quando volta ao normal |
| `try/catch` | Se a API não responder, cai no `catch`, que volta os valores para `--` e tira o vermelho do limite |
| `buscarDados()` | Primeira chamada assim que a página abre, para não ficar com `--` esperando o primeiro intervalo |
| `setInterval(buscarDados, 10000)` | Repete a cada 10 segundos, sem recarregar a página |

**No HTML**, o texto fixo (rótulo) e o valor ficam em elementos separados: só o `span` do valor tem `id`, porque é a única coisa que o JavaScript troca. Antes do primeiro dado chegar, os valores mostram `--`, para a tela não exibir um `0` que pareceria real.

### Visual (`screen/style.css`)

- Os cards ficam num **grid de 4 colunas** no `.containerMonitoramento`. Com o card do limite, o quinto card cai numa linha nova.
- O cabeçalho é centralizado com `margin: 0 auto`. O `text-align: center` só centraliza o texto de dentro, não a caixa.
- A classe `.acima-do-limite` deixa o texto do card do limite em vermelho.

### Decisões da tela

| # | Pergunta | Decisão | Por quê |
|---|---|---|---|
| 1 | De quanto em quanto tempo atualizar? | **10 segundos** | Chave e disco não mudam rápido, e o painel também conta como operação. Com 1 segundo, o contador subiu de 41 para 207 em cerca de 10 minutos |
| 2 | Quando a hora da última atualização muda? | **Só quando o fetch dá certo** | Fica no final do `try`. Se a API cair, a hora congela e mostra quando foi o último dado válido |
| 3 | O que fazer com os números quando a API cai? | **Apagar (voltar para `--`)** | Número velho com cara de atual leva quem olha a decidir com informação errada. O status muda para "sem conexão" e a hora continua mostrando quando foi o último dado bom |
| 4 | Quando o card do limite fica vermelho? | **Só quando `usado > maximo`** | Com `usado` igual a `maximo` (ex.: `5 / 5`), o limite está cheio, mas a API está funcionando como deveria. Acima disso, o limite foi ultrapassado (ver RF-07, decisão 10) |
| 5 | O vermelho fica quando a API cai? | **Não, o `catch` remove a classe** | Senão o `--` apareceria em vermelho, parecendo aviso de limite quando na verdade é falta de conexão |

### Verificação (manual)

- [x] `localhost:8000/` mostra os quatro números com rótulo
- [x] Gerei uma chave pelo `/docs` numa aba e o número mudou sozinho na outra, sem recarregar
- [x] Derrubei a API e a tela avisou "sem conexão" e apagou os números
- [x] Subi a API de novo e a tela voltou a atualizar sozinha
- [x] `/monitoramento`, `/docs` e `/chaves/rsa` continuam respondendo
- [x] Grid de 4 colunas aplicando no painel
- [ ] Card do limite mostrando `usado / maximo`
- [ ] Card do limite ficando vermelho acima do limite

> 💡 **Mexeu no `script.js`? Recarregue com `Ctrl+Shift+R` com a API de pé.** A aba continua rodando a versão do JavaScript que baixou quando abriu, e o `setInterval` segue chamando essa cópia antiga. Com a API derrubada nem dá para recarregar, porque é ela quem entrega o arquivo.
>
> 🔍 **Erro de front-end é silencioso:** a página só fica em branco ou com `--`. O motivo aparece no console do navegador (`F12` → aba **Console**). Um `getElementById` com id errado, por exemplo, devolve `null` e dá `Cannot set properties of null`.

---

## 🚦 Códigos de resposta

| Código | Quando acontece |
|---|---|
| `200` | Deu certo (inclusive `{ "valida": false }`: assinatura que não bate é resposta, não erro) |
| `400` | Dados cifrados adulterados ou nonce errado (Parte 1) |
| `404` | Chave com esse nome não existe (Parte 1), ou caminho que não é rota nem arquivo da `screen/` |
| `422` | Request inválido (ex.: `nome` fora da allowlist) |
| `500` | Erros não tratados nas rotas do cofre (ver Limitações) |
| `507` | Limite de chaves atingido ao tentar criar uma chave nova (RF-07) |

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
> Sem Docker, o `PYTHONPATH="src"` é o que faz o `from main import app` funcionar (é o equivalente do `--app-dir src` do uvicorn). Sem ele, aparece `ModuleNotFoundError: No module named 'main'`. O VS Code pode sublinhar esse import de amarelo (`could not be resolved`), mas o pytest roda normal.
>
> Sem Docker, os **7 testes do cofre falham** com `OS exception while loading /usr/lib/softhsm/libsofthsm2.so`: o SoftHSM só existe dentro do container. Os outros 11 passam.

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

> 🐛 O `test_gerar_chave_aumenta_espaco_disco` procurava a chave `"byes"` em vez de `"bytes"` e dava `KeyError`. Corrigido. O bug já existia antes da tela, e apareceu ao rodar a suíte para validá-la.

> ⚠️ **Limite de chaves × testes:** com `LIMITE_CHAVES=5` no `docker-compose.yml`, os testes que criam chaves podem receber `507` em vez de `200` quando já existem 5 chaves (contando as que sobraram de rodadas anteriores e do Swagger). Ao rodar a suíte, limpe as chaves ou suba o limite.

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
- **Depurar `KeyError`:** quando `resposta.json()["campo"]` dá `KeyError`, a rota devolveu erro em vez de sucesso, ou o nome do campo não bate com o `return` da rota (como no caso do `"byes"`). Um `print(resposta.status_code, resposta.json())` antes mostra o que veio.
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
- **Tupla e desempacotamento:** uma função que faz `return a, b` devolve uma tupla, que pode ser recebida direto em duas variáveis: `x, y = funcao()`. Se uma das partes não for usada, o nome começa com `_` (`publica, _privada = ...`). Usar `_` também evita que a variável esconda um módulo com o mesmo nome (como o `rsa` importado da `cryptography`).
- **Escopo local:** uma variável criada dentro de uma função só existe ali, então duas rotas podem usar o mesmo nome de variável sem conflito. Para usar o valor fora, a função precisa devolver com `return`, e quem chama precisa guardar o resultado numa variável.
- **Middleware:** código que roda em toda requisição, antes e depois da rota, sem precisar mexer em cada rota.
- **Código no topo do módulo:** roda uma vez só, no primeiro `import`. Bom lugar para guardar a hora de subida.
- **Memória (RAM) vs disco:** o que está em variável some quando o programa para; o que está em arquivo continua.
- **Schemas aninhados:** um modelo Pydantic pode ter outros modelos como campos (`disco: Disco`), formando um JSON em camadas. A classe usada como campo precisa estar definida **antes** do schema que usa ela.
- **`response_model`:** o FastAPI só devolve os campos declarados no schema. Campo calculado na rota mas ausente do schema some da resposta sem dar erro.
- **Variáveis de ambiente:** configuração que fica fora do código. Sempre chegam como texto, então número precisa de `int()`.
- **Import circular:** quando dois arquivos importam um ao outro, o Python não consegue terminar de carregar nenhum dos dois. A saída é tirar o que os dois precisam para um terceiro arquivo (como o `config.py`).
- **Uma fonte só para cada regra:** a contagem total fica numa função única, usada pela API e pelo painel. Duas cópias da mesma conta acabam divergindo quando uma muda e a outra não.
- **Nome de arquivo × nome de variável:** depois de `from router import router`, o `router` no código é o objeto `APIRouter`, não o arquivo `router.py`. Uma função importada pelo nome é chamada direto, sem prefixo.
- **507 Insufficient Storage:** status HTTP para "não há espaço para guardar isso".
- **`GET` não empurra dados:** a rota só responde quando é chamada. Atualização periódica é responsabilidade de quem consome, e a tela do painel é esse consumidor.
- **Arquivos estáticos:** HTML, JS e CSS entregues como estão, sem processamento. O `StaticFiles` serve uma pasta inteira a partir de um caminho.
- **Ordem das rotas:** um mount em `/` aceita qualquer caminho, então precisa vir depois das rotas da API.
- **Mesma origem e CORS:** o navegador bloqueia uma página de pedir dados a outra origem sem permissão. Servindo a tela pela própria API, as duas ficam na mesma origem.
- **Caminho ancorado no arquivo:** `Path(__file__)` aponta para o próprio arquivo e não depende de onde o programa foi executado. Caminho relativo depende.
- **`fetch` + `async`/`await`:** o mesmo padrão do middleware em Python (`resposta = await call_next(request)`), agora no navegador: `const resposta = await fetch(...)`.
- **`setInterval`:** repete uma função a cada X **milissegundos**. Recebe a função **sem parênteses**, para chamá-la depois, em vez de chamá-la na hora.
- **`try/catch`:** o `try/except` do JavaScript. O que fica depois de uma linha que falhou dentro do `try` não é executado.
- **Separar fixo de variável:** no HTML, só o que muda ganha `id`. O rótulo e o valor ficam em elementos diferentes.
- **Caminho com ponto no JS:** `dados.limite.usado` significa "entra em `dados`, depois em `limite`, depois pega `usado`". Valores irmãos (`usado` e `maximo`) são caminhos separados.
- **Template string:** texto entre crases (`` ` ``) em que `${ }` encaixa o valor de uma variável.
- **`classList.toggle(classe, condição)`:** coloca a classe quando a condição é verdadeira e tira quando é falsa. Como a tela atualiza a cada 10s, o estado é decidido de novo em toda atualização.
- **f-string em várias linhas:** em vez de quebrar dentro das `{ }`, que só funciona a partir do Python 3.12, a mensagem é dividida em pedaços de string lado a lado dentro dos parênteses, cada um com o seu `f`, e o Python junta tudo.

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
- [x] AES-GCM no cofre migrado para `GCMParams` (python-pkcs11 0.10.0)
- [x] `GET /chaves/cofre/status`
- [x] `GET /chaves/cofre/chaves`
- [x] Rotas que usam o cofre para RSA (`/cofre/rsa`, `/cofre/assinar`, `/cofre/verificar`)
- [x] Rotas que usam o cofre para AES (`/cofre/aes`, `/cofre/cifrar`, `/cofre/decifrar`)
- [x] Testes do cofre em `tests/test_cripto.py` (7 testes) rodando
- [ ] Testar cifrar e decifrar no cofre com `GCMParams`

### RF-08: monitoramento

- [x] `metricas.py`: tempo no ar, contador de operações, contagem de chaves e espaço em disco
- [x] Middleware contando toda requisição
- [x] Schemas `Chave`, `Operacoes`, `Disco`, `Tempo_no_ar` e `MonitoramentoResponse`
- [x] `GET /monitoramento` no `main.py`
- [x] Decisões 1, 2 e 3 testadas e registradas
- [x] Testes em `tests/test_monitoramento.py` (5 testes) rodando
- [x] Entrega 2: comparação com o requisito original e perguntas para quem escreveu o requisito

### Tela do painel

- [x] Pasta `screen/` separada do `src/`, com HTML e JavaScript puro
- [x] Página servida pela API em `localhost:8000/` com `StaticFiles`
- [x] Quatro números com rótulo
- [x] Atualização automática a cada 10s, sem recarregar
- [x] Hora da última atualização
- [x] Aviso de conexão perdida, com os números apagados
- [x] Rotas da API continuando a funcionar
- [x] `ruff check src/ tests/` limpo
- [x] `pytest`: 11 passed sem Docker (os 7 do cofre dependem do container)
- [x] CSS
- [x] Tela abrindo pelo container (`Dockerfile` copiando a `screen/`)

### RF-07: limite máximo de chaves

- [x] `config.py` lendo `LIMITE_CHAVES` e `PIN` de variáveis de ambiente
- [x] PIN fora do `hsm.py`
- [x] `LIMITE_CHAVES` e `PIN` no `docker-compose.yml`
- [x] `contar_total_geral()` somando arquivos + cofre
- [x] `verificar_limite()` com `507` nas quatro rotas de criação
- [x] Schema `Limite` e bloco `limite` no `/monitoramento`
- [x] Card do limite na tela, com aviso vermelho acima do limite
- [x] Decisões registradas
- [ ] Testar criação de chaves até bater no limite
- [ ] Testar o painel com o card do limite
- [ ] Rodar `pytest` e `ruff` depois das mudanças

### Limitações conhecidas

- Chamar `/rsa` ou `/aes` (Parte 1) com um nome que **já existe** sobrescreve a chave anterior.
- No **cofre** é diferente: gerar duas vezes com o mesmo nome **não sobrescreve**, cria uma segunda chave com o mesmo label. Depois disso, `assinar`, `verificar`, `cifrar` e `decifrar` com esse nome estouram `MultipleObjectsReturned` (`500`).
- Pedir uma chave que não existe no cofre estoura `NoSuchKey` (`500`). O `except FileNotFoundError` da Parte 1 não serve aqui, porque no cofre não há arquivo.
- Base64 malformado no `/verificar`, no `/decifrar` e nas rotas equivalentes do cofre retorna `500`.
- Nonce ou cifrado adulterado no `/cofre/decifrar` não é tratado como `400`: o `decrypt` do cofre lança exceção e a rota devolve `500`.
- O label do token continua fixo no `hsm.py`. O PIN já vem de variável de ambiente.
- **O cofre não roda sem Docker no Windows:** o `hsm.py` carrega o SoftHSM pelo caminho de Linux (`/usr/lib/softhsm/libsofthsm2.so`), que só existe dentro do container. Limitação de ambiente, não de código.
- **O bloco `chave` do monitoramento conta só as chaves em arquivo** (Parte 1). As chaves do cofre entram só no `limite.usado`.
- **A contagem do cofre usa a `listar_chaves_cofre()`, que filtra `PRIVATE_KEY`.** Chaves AES do cofre são `SECRET_KEY`, então ficam de fora do limite.
- **Sem Docker, o limite não funciona:** a `contar_total_geral()` abre uma sessão com o cofre, que só existe dentro do container.
- **Os contadores do monitoramento zeram** quando a API reinicia (ficam em memória).
- **Os testes `test_gerar_chave_aumenta_total` e `test_gerar_chave_aumenta_espaco_disco` usam nomes fixos.** Na segunda rodada do pytest a chave já existe e é sobrescrita, então o total e o disco não aumentam e o teste falha. É preciso apagar `testeMonitoramento` e `testeEspacoDisco` da pasta `chaves/` antes de rodar de novo (ou usar `uuid`, como nos testes do cofre).
- **A tela infla o contador de operações:** o middleware conta toda requisição, inclusive `/`, `/script.js`, `/style.css`, `/favicon.ico` e o `/monitoramento` a cada 10s. Deixar a tela aberta faz o número subir sozinho. Uma saída seria o middleware ignorar essas rotas.
- **`GET` em rota que só aceita `POST` devolve `404` em vez de `405`:** a rota recusa o método e o `StaticFiles` montado em `/` pega a requisição, procura um arquivo com esse caminho na `screen/` e não acha. Pelo método certo (pelo `/docs`, por exemplo) tudo funciona.
- **O `fetch` só cai no `catch` quando a rede falha.** Se a API estiver de pé mas devolver um erro (`500`, por exemplo), a tela não trata como "sem conexão". Conferir `resposta.ok` resolveria.
- **O navegador pede `/favicon.ico`** e recebe `404`, porque a tela não tem ícone. Inofensivo.

---

## ⚠️ Aviso

Projeto **educacional**. Em produção, chaves privadas não ficam em arquivo no disco: ficam em um KMS, Vault ou HSM. A Parte 2 simula exatamente isso com o SoftHSM.

---

Feito por [Luiza Souza](https://luizasouza.eti.br) · [@lu-izah19](https://github.com/lu-izah19)
