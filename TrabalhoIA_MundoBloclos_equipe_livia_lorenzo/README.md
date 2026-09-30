# Mundo dos Blocos de Tamanho Variável via SAT Solver

**Fundamentos de Inteligência Artificial** — Prof. Edjard Mota — IComp/UFAM
**1º Trabalho** — Equipe Livia_Lorenzo

Integrantes: Livia Karolina Gomes do Nascimento, Lorenzo Augusto da Costa Freitas

Este repositório resolve o planejamento no Mundo dos Blocos com blocos de comprimentos diferentes (a=1, b=1, c=2, d=3) sobre uma mesa de 6 slots. O problema é descrito em lógica de primeira ordem (LPO), traduzido para lógica proposicional (CNF) e resolvido com o miniSAT. Os planos são conferidos por um verificador independente.

## Conteúdo da pasta

```
README.md               este documento (documentação em Markdown)
bw2cnf_var.py           gera o CNF (.cnf) e o mapa (.map) de um cenário
interpretar.py          traduz a saída do miniSAT para um plano em português
rodar.py                roda os cenários e busca o menor horizonte T
situacao1/              Situação 1, S0 → Sf4      (resultado1.txt)
  sf1/ sf2/ sf3/        Situação 1, S0 → Sf1, Sf2, Sf3
situacao2/              Situação 2, S0 → S5       (resultado2.txt)
situacao3/              Situação 3, S0 → S7       (resultado3.txt)
  sem_ordem/            mesma meta, sem restrição de ordem parcial
  ordem_inversa/        mesma meta, com a ordem parcial invertida
latex/                  descrição da solução em LaTeX (main.tex e main.pdf)
```

Cada pasta de cenário contém `trab01_blocos2SAT.cnf`, `trab01_blocos2SAT.map`, o arquivo de resultado do miniSAT e `busca_horizonte.txt` (a busca T = 0, 1, 2, ... até o primeiro SATISFIABLE).

## 1. Introdução ao problema

No Mundo dos Blocos clássico todos os blocos têm o mesmo tamanho. Aqui os blocos têm comprimentos diferentes, podem ficar em qualquer posição horizontal da mesa, podem ficar em ponte sobre dois blocos com um vão no meio, e um bloco só fica de pé se estiver apoiado o bastante. O plano precisa respeitar tudo isso.

A ação de movimento é **qualitativa**: em vez de "mover para o nível 2, posição 3", dizemos "mover o bloco d para cima do bloco c, começando no ponto 0". O plano fica legível em português.

## 2. Descrição formal do mundo dos blocos de tamanho variado

### 2.1 Termos

| Símbolo | Significado |
|---|---|
| B = {a, b, c, d} | blocos, com comprimentos ℓ(a)=1, ℓ(b)=1, ℓ(c)=2, ℓ(d)=3 |
| T | a mesa |
| X = {0,…,6} | **pontos** do eixo da mesa |
| sᵢ = [i, i+1], i = 0..5 | **slots** (6 slots, não 7) |
| l ∈ {0,…,3} | níveis (0 = mesa) |
| t | instante (passo de planejamento) |

Um bloco b que começa no ponto p cobre os slots p, p+1, …, p+ℓ(b)−1. As posições válidas são p ∈ {0,…,6−ℓ(b)}.

### 2.2 Predicados

| Predicado | Tipo | Significado |
|---|---|---|
| at(b,p,t) | estado | b começa no ponto p no instante t |
| lev(b,l,t) | estado | b está no nível l no instante t |
| clr(b,t) | estado | nada está sobre b no instante t |
| cov(b,s,t) | derivado | b cobre o slot s: p ≤ s < p+ℓ(b) |
| on(b,y,t) | derivado | b está apoiado em y (bloco ou mesa T) |
| stable(b,p,l,t) | derivado | b em (p,l) tem apoio suficiente |
| move(b,y,p,t) | ação | mover b para cima de y (ou da mesa), começando em p |

Relação `on` (derivada, **não** codificada no CNF):

on(b,y,t) ↔ ∃p,pᵧ,l. at(b,p,t) ∧ at(y,pᵧ,t) ∧ lev(b,l,t) ∧ lev(y,l−1,t) ∧ overlap(b,p,y,pᵧ)

e on(b,T,t) ↔ lev(b,0,t). Um bloco pode ter vários apoios (ponte): d sobre a e b ao mesmo tempo.

### 2.3 Regra de estabilidade

Um bloco b no nível l > 0, começando em p, só é estável se pelo menos ⌈ℓ(b)/2⌉ dos slots sob ele estiverem ocupados por outros blocos no nível l−1.

- d (ℓ=3) precisa de 2 slots apoiados. Pode ficar em ponte sobre a e b com um vão no meio, mas não pode ficar apoiado em um único slot.
- c (ℓ=2) precisa de 1 slot apoiado.
- a e b (ℓ=1) precisam de 1 slot, ou seja, ficam totalmente apoiados.

### 2.4 Ação move(b, y, p, t) e efeitos (adds e deletes)

**Pré-condições**

1. clr(b,t): o topo de b está livre.
2. Se y é bloco, o span de b em p sobrepõe o span de y.
3. O destino é diferente da posição atual de b (evita ação vazia).
4. Os slots que b ocuparia no nível-alvo (lev(y)+1, ou 0 se y = T) estão livres de outros blocos.
5. stable(b, p, nível-alvo, t+1): o apoio sob b é suficiente.
6. O nível-alvo não passa de 3.

**Efeitos**

| Elemento | Add | Delete |
|---|---|---|
| at | at(b,p) | at(b,pₐₙₜₑᵣᵢₒᵣ) |
| lev | lev(b, lev(y)+1) (ou lev(b,0) se y = T) | lev(b,lₐₙₜₑᵣᵢₒᵣ) |
| clr | clr(z) para todo bloco z que estava sob b e ficou sem nada em cima | clr(y), se y é bloco (b passa a ficar sobre y) |
| on (derivado) | on(b,y') para cada y' que fica sob b | on(b,y'') para cada apoio antigo |

Todos os outros blocos permanecem como estavam (frame axioms).

### 2.5 Ajuste em relação ao manual: pré-condição clr(y)

O manual exige **clr(y,t)**, isto é, o topo de y **inteiramente** livre. Testamos essa regra e ela torna inalcançáveis os estados Sf1 e Sf2 (Situação 1), S5 (Situação 2) e S7 (Situação 3), porque em todos eles dois blocos ficam lado a lado sobre o mesmo bloco (por exemplo, a e b sobre c). Com clr(y) exigido, o segundo bloco nunca consegue subir, pois o primeiro já está em cima de y. O miniSAT respondeu UNSATISFIABLE para todo T até 12 nesses quatro cenários.

Por isso a pré-condição foi trocada por "**os slots do topo de y que b ocupará estão livres**". Isso é a pré-condição 4 acima (que o próprio manual já lista como pré-condição 5) e vale para qualquer y. Com essa troca, o clr(y) deixa de ser necessário e o clr de cada bloco continua definido a partir de quem está por cima. Como efeito colateral, o bloco também pode deslizar lateralmente sobre o mesmo apoio, o que o enunciado chama de "movimentos laterais". O Sf4 e todos os demais cenários continuam funcionando.

### 2.6 Ordem parcial

Escrevemos φ₁ ≺ φ₂ para "a meta φ₁ tem de ter sido atingida antes (ou no mesmo instante) de φ₂ valer". Cada φ é um par (bloco, ponto, nível). A regra, para todo t:

¬φ₂(t) ∨ φ₁(0) ∨ φ₁(1) ∨ … ∨ φ₁(t)

## 3. Codificação CNF

### 3.1 Variáveis proposicionais (para T passos)

| Variável | Índices |
|---|---|
| at(b,p,t) | b ∈ B, p ∈ [0, 6−ℓ(b)], t ∈ [0,T] |
| lev(b,l,t) | b ∈ B, l ∈ [0,3], t ∈ [0,T] |
| clr(b,t) | b ∈ B, t ∈ [0,T] |
| mv(b,y,p,t) | b ∈ B, y ∈ B∪{T}, y ≠ b, p ∈ [0,6−ℓ(b)], t ∈ [0,T−1] |
| acima(x,y,t) | auxiliar: x está imediatamente acima de y (usada para definir clr) |
| ordₖ(b,p,l,t) | auxiliar da ordem parcial: (b,p,l) vale em t |

A relação `on` **não** vira variável. O `interpretar.py` a reconstrói depois.

### 3.2 Grupos de cláusulas

1. **Estado inicial:** cláusulas unitárias com at e lev em t = 0.
2. **Meta:** cláusulas unitárias com at e lev em t = T.
3. **Unicidade de posição e de nível:** cada bloco tem exatamente uma posição e um nível em cada t (uma cláusula "pelo menos um" e cláusulas ¬x₁ ∨ ¬x₂ para "no máximo um").
4. **Exclusão horizontal:** dois blocos no mesmo nível não compartilham slots: ¬at(b₁,p₁,t) ∨ ¬at(b₂,p₂,t) ∨ ¬lev(b₁,l,t) ∨ ¬lev(b₂,l,t) sempre que os spans se sobrepõem.
5. **Estabilidade:** para b em (p,l>0), enumeramos onde estão os outros blocos no nível l−1; toda combinação com menos de ⌈ℓ(b)/2⌉ slots apoiados é proibida.
6. **Clear:** acima(x,y,t) ↔ x está no nível lev(y)+1 e o span de x sobrepõe o de y; e clr(y,t) ↔ nenhum x está acima de y.
7. **Pré-condições e efeitos de move:** cláusulas da forma ¬mv(b,y,p,t) ∨ (condição), conforme a seção 2.4. A pré-condição 4 e o efeito "y deixa de estar livre" ficam garantidos pelos grupos 4, 5 e 6 no estado t+1.
8. **Frame axioms:** ¬at(b,p,t) ∨ at(b,p,t+1) ∨ (b foi movido em t), e o mesmo para lev.
9. **No máximo uma ação por passo:** para cada par de ações no mesmo t, ¬mv₁ ∨ ¬mv₂. Não exigimos "pelo menos uma", então um plano de k ações também vale para todo T ≥ k.
10. **Ordem parcial (opcional):** a cláusula da seção 2.6, com variáveis auxiliares ordₖ.

## 4. Exemplos: os 3 cenários codificados

Formato: `bloco: (ponto inicial p, nível l)`.

**Situação 1** — S0: `c:(0,0)  a:(3,0)  b:(5,0)  d:(3,1)`

```
   |.|.|.|d|d|d|
   |c|c|.|a|.|b|
   slots: 0 1 2 3 4 5
```

on em S0: on(c,T), on(a,T), on(b,T), on(d,a) ∧ on(d,b). O slot 4 fica vazio sob d, e d está em ponte.

| Meta | Representação | Desenho |
|---|---|---|
| Sf1 | `d:(3,0) a:(4,1) b:(5,1) c:(4,2)` | c sobre a e b, que estão sobre d |
| Sf2 | `d:(3,0) c:(4,1) a:(4,2) b:(5,2)` | a e b lado a lado sobre c, que está sobre d |
| Sf3 | `c:(0,0) a:(2,0) d:(0,1) b:(5,0)` | d em ponte sobre c e a |
| Sf4 | `c:(0,0) a:(0,1) d:(2,0) b:(5,0)` | a sobre c, d na mesa em p=2 |

**Situação 2** — S0: `c:(0,0) a:(0,1) b:(1,1) d:(3,0)` (a e b sobre c). Meta S5: `d:(3,0) c:(4,1) a:(4,2) b:(5,2)`.

**Situação 3** — S0 igual ao da Situação 1. Meta S7: `c:(0,0) a:(0,1) b:(1,1) d:(3,0)`. A ordem parcial usada é (a em p=0, nível 1) ≺ (b em p=1, nível 1).

## 5. Mapeamento: descrição formal → código

| Regra formal | Código (`bw2cnf_var.py`) |
|---|---|
| Blocos e comprimentos | `BLOCKS = {'a':1,'b':1,'c':2,'d':3}` |
| Pontos do eixo | `MAX_POINT = 6` |
| Posições válidas | `valid_positions(L) = range(MAX_POINT - L + 1)` |
| Slots cobertos | `span(b, p)` |
| Sobreposição de span | `spans_overlap(b1,p1,b2,p2)` |
| Apoio mínimo ⌈ℓ/2⌉ | `min_apoio(b)` |
| at(b,p,t), lev(b,l,t), clr(b,t), mv(b,y,p,t) | dicionários `at`, `lev`, `clr`, `mv` (cada entrada chama `new_var`) |
| Estado inicial / meta | blocos `# 3.1 ESTADO INICIAL`, `# 3.2 META` |
| Unicidade posição/nível | bloco `# 3.3 (A),(B)` |
| Exclusão horizontal | bloco `# 3.3 (C)` |
| Estabilidade | bloco `# 3.3 (D)` |
| Clear | bloco `# 3.3 (E)`, com a variável auxiliar `acima` |
| Pré-condições e efeitos de move | bloco `# 3.4 (G)` |
| Frame axioms | bloco `# 3.5` |
| Uma ação por passo | bloco `# 3.6` |
| Ordem parcial | bloco `# 3.7`, campo `order` de cada cenário |
| Relação on (derivada) | `interpretar.py`, função `derivar_on` |
| Cenários | dicionário `CENARIOS` no topo de `bw2cnf_var.py` |

## 6. Execução passo a passo

**Instalação (uma vez).** Precisa de Python 3 e do miniSAT:

```
sudo apt install minisat        # Linux ou WSL no Windows
brew install minisat            # macOS
```

**Um cenário, passo a passo:**

```
python3 bw2cnf_var.py situacao1 --horizon 4 --saida situacao1
minisat situacao1/trab01_blocos2SAT.cnf situacao1/resultado1.txt
python3 interpretar.py situacao1/resultado1.txt --verbose
```

O primeiro comando imprime `Gerado: N variaveis, M clausulas` e cria `trab01_blocos2SAT.cnf` e `trab01_blocos2SAT.map`. Para trocar de cenário, mude o nome (`situacao2`, `situacao3`, …) e o `--horizon`.

**Todos os cenários de uma vez, procurando o menor T:**

```
python3 rodar.py
```

Resultados obtidos (menor T com SATISFIABLE; todos os T menores deram UNSATISFIABLE):

| Cenário | Menor T | Variáveis | Cláusulas | Arquivo |
|---|---|---|---|---|
| Situação 1, S0 → Sf4 | 4 | 601 | 72179 | `situacao1/resultado1.txt` |
| Situação 1, S0 → Sf1 | 8 | 1149 | 133299 | `situacao1/sf1/resultado_sf1.txt` |
| Situação 1, S0 → Sf2 | 9 | 1286 | 148579 | `situacao1/sf2/resultado_sf2.txt` |
| Situação 1, S0 → Sf3 | 2 | 327 | 41619 | `situacao1/sf3/resultado_sf3.txt` |
| Situação 2, S0 → S5 | 5 | 738 | 87459 | `situacao2/resultado2.txt` |
| Situação 3, S0 → S7 (a ≺ b) | 6 | 882 | 102760 | `situacao3/resultado3.txt` |
| Situação 3, S0 → S7 (sem ordem) | 6 | 875 | 102739 | `situacao3/sem_ordem/…` |
| Situação 3, S0 → S7 (b ≺ a) | 7 | 1020 | 118043 | `situacao3/ordem_inversa/…` |

A ordem parcial b ≺ a força o plano a ficar uma ação mais longo: o a precisa esperar em cima do d até o b subir no c. Isso mostra que a restrição está de fato agindo.

## 7. Interpretação da saída do SAT solver

O miniSAT só devolve inteiros: a lista dos IDs das variáveis verdadeiras. Quem sabe o que cada ID significa é o arquivo `.map`. Por exemplo, a linha `50	mv(d,c,0,0)` diz que a variável 50 é a ação "mover d para cima de c, começando em 0, no instante 0".

O `interpretar.py` faz três coisas:

1. **Lê o mapa** e associa cada ID ao seu símbolo.
2. **Filtra** os literais positivos e mantém as ações `mv`, ordenando por t.
3. **Traduz** cada ação para uma frase e reconstrói o estado em cada t a partir de `at` e `lev`.

A relação `on` do estado final é derivada: se lev(b) = 0, b está na mesa; senão, b está sobre todo bloco y com lev(y) = lev(b) − 1 cujo span sobrepõe o de b. Um bloco com dois apoios é uma ponte.

**Regra de ouro:** sem o `.map`, a saída do miniSAT é só uma lista de números. Nunca interprete sem o mapa do mesmo cenário.

Com `--verbose`, o script também desenha cada estado e roda uma **verificação independente**, que confere as regras físicas (sem sobreposição, estabilidade, topo livre, só o bloco movido muda) sem usar o CNF. Todos os planos deste repositório passaram nela.

## 8. Execução manual dos cenários (item 3 do enunciado)

Cada passo abaixo mostra o movimento, as pré-condições conferidas e o estado resultante. Nos desenhos, cada coluna é um slot, a linha de baixo é a mesa (nível 0), e `.` é vazio.

#### Situação 1: S0 → Sf4

Estado inicial (t=0):

```
   |.|.|.|d|d|d|
   |c|c|.|a|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 1: `move(d,c,0)`** — mover d para cima do bloco c, começando no ponto 0.

- `clr(d)` verdadeiro em t=0: nada está sobre d.
- Slots [0, 1, 2] livres no nível 1; slots apoiados no nível 0: [0, 1] (2 ≥ ⌈3/2⌉ = 2).
- Efeitos: `at(d,0)`, `lev(d,1)`; d sai de `at(d,3)`, `lev(d,1)`.

Estado em t=1:

```
   |d|d|d|.|.|.|
   |c|c|.|a|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 2: `move(a,b,5)`** — mover a para cima do bloco b, começando no ponto 5.

- `clr(a)` verdadeiro em t=1: nada está sobre a.
- Slots [5] livres no nível 1; slots apoiados no nível 0: [5] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(a,5)`, `lev(a,1)`; a sai de `at(a,3)`, `lev(a,0)`.

Estado em t=2:

```
   |d|d|d|.|.|a|
   |c|c|.|.|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 3: `move(d,T,2)`** — mover d para a mesa, começando no ponto 2.

- `clr(d)` verdadeiro em t=2: nada está sobre d.
- Slots [2, 3, 4] livres no nível 0; nível 0 (mesa): não precisa de apoio.
- Efeitos: `at(d,2)`, `lev(d,0)`; d sai de `at(d,0)`, `lev(d,1)`.

Estado em t=3:

```
   |.|.|.|.|.|a|
   |c|c|d|d|d|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 4: `move(a,c,0)`** — mover a para cima do bloco c, começando no ponto 0.

- `clr(a)` verdadeiro em t=3: nada está sobre a.
- Slots [0] livres no nível 1; slots apoiados no nível 0: [0] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(a,0)`, `lev(a,1)`; a sai de `at(a,5)`, `lev(a,1)`.

Estado em t=4:

```
   |a|.|.|.|.|.|
   |c|c|d|d|d|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

Relações `on` no estado final: a esta sobre: c; b esta na MESA; c esta na MESA; d esta na MESA.

#### Situação 1: S0 → Sf1

Estado inicial (t=0):

```
   |.|.|.|d|d|d|
   |c|c|.|a|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 1: `move(d,c,0)`** — mover d para cima do bloco c, começando no ponto 0.

- `clr(d)` verdadeiro em t=0: nada está sobre d.
- Slots [0, 1, 2] livres no nível 1; slots apoiados no nível 0: [0, 1] (2 ≥ ⌈3/2⌉ = 2).
- Efeitos: `at(d,0)`, `lev(d,1)`; d sai de `at(d,3)`, `lev(d,1)`.

Estado em t=1:

```
   |d|d|d|.|.|.|
   |c|c|.|a|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 2: `move(a,T,2)`** — mover a para a mesa, começando no ponto 2.

- `clr(a)` verdadeiro em t=1: nada está sobre a.
- Slots [2] livres no nível 0; nível 0 (mesa): não precisa de apoio.
- Efeitos: `at(a,2)`, `lev(a,0)`; a sai de `at(a,3)`, `lev(a,0)`.

Estado em t=2:

```
   |d|d|d|.|.|.|
   |c|c|a|.|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 3: `move(d,c,1)`** — mover d para cima do bloco c, começando no ponto 1.

- `clr(d)` verdadeiro em t=2: nada está sobre d.
- Slots [1, 2, 3] livres no nível 1; slots apoiados no nível 0: [1, 2] (2 ≥ ⌈3/2⌉ = 2).
- Efeitos: `at(d,1)`, `lev(d,1)`; d sai de `at(d,0)`, `lev(d,1)`.

Estado em t=3:

```
   |.|d|d|d|.|.|
   |c|c|a|.|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 4: `move(b,c,0)`** — mover b para cima do bloco c, começando no ponto 0.

- `clr(b)` verdadeiro em t=3: nada está sobre b.
- Slots [0] livres no nível 1; slots apoiados no nível 0: [0] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(b,0)`, `lev(b,1)`; b sai de `at(b,5)`, `lev(b,0)`.

Estado em t=4:

```
   |b|d|d|d|.|.|
   |c|c|a|.|.|.|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 5: `move(d,T,3)`** — mover d para a mesa, começando no ponto 3.

- `clr(d)` verdadeiro em t=4: nada está sobre d.
- Slots [3, 4, 5] livres no nível 0; nível 0 (mesa): não precisa de apoio.
- Efeitos: `at(d,3)`, `lev(d,0)`; d sai de `at(d,1)`, `lev(d,1)`.

Estado em t=5:

```
   |b|.|.|.|.|.|
   |c|c|a|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 6: `move(b,d,5)`** — mover b para cima do bloco d, começando no ponto 5.

- `clr(b)` verdadeiro em t=5: nada está sobre b.
- Slots [5] livres no nível 1; slots apoiados no nível 0: [5] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(b,5)`, `lev(b,1)`; b sai de `at(b,0)`, `lev(b,1)`.

Estado em t=6:

```
   |.|.|.|.|.|b|
   |c|c|a|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 7: `move(c,b,4)`** — mover c para cima do bloco b, começando no ponto 4.

- `clr(c)` verdadeiro em t=6: nada está sobre c.
- Slots [4, 5] livres no nível 2; slots apoiados no nível 1: [5] (1 ≥ ⌈2/2⌉ = 1).
- Efeitos: `at(c,4)`, `lev(c,2)`; c sai de `at(c,0)`, `lev(c,0)`.

Estado em t=7:

```
   |.|.|.|.|c|c|
   |.|.|.|.|.|b|
   |.|.|a|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 8: `move(a,d,4)`** — mover a para cima do bloco d, começando no ponto 4.

- `clr(a)` verdadeiro em t=7: nada está sobre a.
- Slots [4] livres no nível 1; slots apoiados no nível 0: [4] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(a,4)`, `lev(a,1)`; a sai de `at(a,2)`, `lev(a,0)`.

Estado em t=8:

```
   |.|.|.|.|c|c|
   |.|.|.|.|a|b|
   |.|.|.|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

Relações `on` no estado final: a esta sobre: d; b esta sobre: d; c esta sobre: a, b (ponte); d esta na MESA.

#### Situação 1: S0 → Sf2

Estado inicial (t=0):

```
   |.|.|.|d|d|d|
   |c|c|.|a|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 1: `move(c,T,1)`** — mover c para a mesa, começando no ponto 1.

- `clr(c)` verdadeiro em t=0: nada está sobre c.
- Slots [1, 2] livres no nível 0; nível 0 (mesa): não precisa de apoio.
- Efeitos: `at(c,1)`, `lev(c,0)`; c sai de `at(c,0)`, `lev(c,0)`.

Estado em t=1:

```
   |.|.|.|d|d|d|
   |.|c|c|a|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 2: `move(d,c,0)`** — mover d para cima do bloco c, começando no ponto 0.

- `clr(d)` verdadeiro em t=1: nada está sobre d.
- Slots [0, 1, 2] livres no nível 1; slots apoiados no nível 0: [1, 2] (2 ≥ ⌈3/2⌉ = 2).
- Efeitos: `at(d,0)`, `lev(d,1)`; d sai de `at(d,3)`, `lev(d,1)`.

Estado em t=2:

```
   |d|d|d|.|.|.|
   |.|c|c|a|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 3: `move(a,T,0)`** — mover a para a mesa, começando no ponto 0.

- `clr(a)` verdadeiro em t=2: nada está sobre a.
- Slots [0] livres no nível 0; nível 0 (mesa): não precisa de apoio.
- Efeitos: `at(a,0)`, `lev(a,0)`; a sai de `at(a,3)`, `lev(a,0)`.

Estado em t=3:

```
   |d|d|d|.|.|.|
   |a|c|c|.|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 4: `move(d,c,1)`** — mover d para cima do bloco c, começando no ponto 1.

- `clr(d)` verdadeiro em t=3: nada está sobre d.
- Slots [1, 2, 3] livres no nível 1; slots apoiados no nível 0: [1, 2] (2 ≥ ⌈3/2⌉ = 2).
- Efeitos: `at(d,1)`, `lev(d,1)`; d sai de `at(d,0)`, `lev(d,1)`.

Estado em t=4:

```
   |.|d|d|d|.|.|
   |a|c|c|.|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 5: `move(b,a,0)`** — mover b para cima do bloco a, começando no ponto 0.

- `clr(b)` verdadeiro em t=4: nada está sobre b.
- Slots [0] livres no nível 1; slots apoiados no nível 0: [0] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(b,0)`, `lev(b,1)`; b sai de `at(b,5)`, `lev(b,0)`.

Estado em t=5:

```
   |b|d|d|d|.|.|
   |a|c|c|.|.|.|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 6: `move(d,T,3)`** — mover d para a mesa, começando no ponto 3.

- `clr(d)` verdadeiro em t=5: nada está sobre d.
- Slots [3, 4, 5] livres no nível 0; nível 0 (mesa): não precisa de apoio.
- Efeitos: `at(d,3)`, `lev(d,0)`; d sai de `at(d,1)`, `lev(d,1)`.

Estado em t=6:

```
   |b|.|.|.|.|.|
   |a|c|c|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 7: `move(c,d,4)`** — mover c para cima do bloco d, começando no ponto 4.

- `clr(c)` verdadeiro em t=6: nada está sobre c.
- Slots [4, 5] livres no nível 1; slots apoiados no nível 0: [4, 5] (2 ≥ ⌈2/2⌉ = 1).
- Efeitos: `at(c,4)`, `lev(c,1)`; c sai de `at(c,1)`, `lev(c,0)`.

Estado em t=7:

```
   |b|.|.|.|c|c|
   |a|.|.|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 8: `move(b,c,5)`** — mover b para cima do bloco c, começando no ponto 5.

- `clr(b)` verdadeiro em t=7: nada está sobre b.
- Slots [5] livres no nível 2; slots apoiados no nível 1: [5] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(b,5)`, `lev(b,2)`; b sai de `at(b,0)`, `lev(b,1)`.

Estado em t=8:

```
   |.|.|.|.|.|b|
   |.|.|.|.|c|c|
   |a|.|.|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 9: `move(a,c,4)`** — mover a para cima do bloco c, começando no ponto 4.

- `clr(a)` verdadeiro em t=8: nada está sobre a.
- Slots [4] livres no nível 2; slots apoiados no nível 1: [4] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(a,4)`, `lev(a,2)`; a sai de `at(a,0)`, `lev(a,0)`.

Estado em t=9:

```
   |.|.|.|.|a|b|
   |.|.|.|.|c|c|
   |.|.|.|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

Relações `on` no estado final: a esta sobre: c; b esta sobre: c; c esta sobre: d; d esta na MESA.

#### Situação 1: S0 → Sf3

Estado inicial (t=0):

```
   |.|.|.|d|d|d|
   |c|c|.|a|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 1: `move(d,c,0)`** — mover d para cima do bloco c, começando no ponto 0.

- `clr(d)` verdadeiro em t=0: nada está sobre d.
- Slots [0, 1, 2] livres no nível 1; slots apoiados no nível 0: [0, 1] (2 ≥ ⌈3/2⌉ = 2).
- Efeitos: `at(d,0)`, `lev(d,1)`; d sai de `at(d,3)`, `lev(d,1)`.

Estado em t=1:

```
   |d|d|d|.|.|.|
   |c|c|.|a|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 2: `move(a,T,2)`** — mover a para a mesa, começando no ponto 2.

- `clr(a)` verdadeiro em t=1: nada está sobre a.
- Slots [2] livres no nível 0; nível 0 (mesa): não precisa de apoio.
- Efeitos: `at(a,2)`, `lev(a,0)`; a sai de `at(a,3)`, `lev(a,0)`.

Estado em t=2:

```
   |d|d|d|.|.|.|
   |c|c|a|.|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

Relações `on` no estado final: a esta na MESA; b esta na MESA; c esta na MESA; d esta sobre: a, c (ponte).

#### Situação 2: S0 → S5

Estado inicial (t=0):

```
   |a|b|.|.|.|.|
   |c|c|.|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 1: `move(a,T,2)`** — mover a para a mesa, começando no ponto 2.

- `clr(a)` verdadeiro em t=0: nada está sobre a.
- Slots [2] livres no nível 0; nível 0 (mesa): não precisa de apoio.
- Efeitos: `at(a,2)`, `lev(a,0)`; a sai de `at(a,0)`, `lev(a,1)`.

Estado em t=1:

```
   |.|b|.|.|.|.|
   |c|c|a|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 2: `move(b,a,2)`** — mover b para cima do bloco a, começando no ponto 2.

- `clr(b)` verdadeiro em t=1: nada está sobre b.
- Slots [2] livres no nível 1; slots apoiados no nível 0: [2] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(b,2)`, `lev(b,1)`; b sai de `at(b,1)`, `lev(b,1)`.

Estado em t=2:

```
   |.|.|b|.|.|.|
   |c|c|a|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 3: `move(c,d,4)`** — mover c para cima do bloco d, começando no ponto 4.

- `clr(c)` verdadeiro em t=2: nada está sobre c.
- Slots [4, 5] livres no nível 1; slots apoiados no nível 0: [4, 5] (2 ≥ ⌈2/2⌉ = 1).
- Efeitos: `at(c,4)`, `lev(c,1)`; c sai de `at(c,0)`, `lev(c,0)`.

Estado em t=3:

```
   |.|.|b|.|c|c|
   |.|.|a|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 4: `move(b,c,5)`** — mover b para cima do bloco c, começando no ponto 5.

- `clr(b)` verdadeiro em t=3: nada está sobre b.
- Slots [5] livres no nível 2; slots apoiados no nível 1: [5] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(b,5)`, `lev(b,2)`; b sai de `at(b,2)`, `lev(b,1)`.

Estado em t=4:

```
   |.|.|.|.|.|b|
   |.|.|.|.|c|c|
   |.|.|a|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 5: `move(a,c,4)`** — mover a para cima do bloco c, começando no ponto 4.

- `clr(a)` verdadeiro em t=4: nada está sobre a.
- Slots [4] livres no nível 2; slots apoiados no nível 1: [4] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(a,4)`, `lev(a,2)`; a sai de `at(a,2)`, `lev(a,0)`.

Estado em t=5:

```
   |.|.|.|.|a|b|
   |.|.|.|.|c|c|
   |.|.|.|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

Relações `on` no estado final: a esta sobre: c; b esta sobre: c; c esta sobre: d; d esta na MESA.

#### Situação 3: S0 → S7 (com ordem parcial a ≺ b)

Estado inicial (t=0):

```
   |.|.|.|d|d|d|
   |c|c|.|a|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 1: `move(d,c,0)`** — mover d para cima do bloco c, começando no ponto 0.

- `clr(d)` verdadeiro em t=0: nada está sobre d.
- Slots [0, 1, 2] livres no nível 1; slots apoiados no nível 0: [0, 1] (2 ≥ ⌈3/2⌉ = 2).
- Efeitos: `at(d,0)`, `lev(d,1)`; d sai de `at(d,3)`, `lev(d,1)`.

Estado em t=1:

```
   |d|d|d|.|.|.|
   |c|c|.|a|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 2: `move(a,b,5)`** — mover a para cima do bloco b, começando no ponto 5.

- `clr(a)` verdadeiro em t=1: nada está sobre a.
- Slots [5] livres no nível 1; slots apoiados no nível 0: [5] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(a,5)`, `lev(a,1)`; a sai de `at(a,3)`, `lev(a,0)`.

Estado em t=2:

```
   |d|d|d|.|.|a|
   |c|c|.|.|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 3: `move(d,T,2)`** — mover d para a mesa, começando no ponto 2.

- `clr(d)` verdadeiro em t=2: nada está sobre d.
- Slots [2, 3, 4] livres no nível 0; nível 0 (mesa): não precisa de apoio.
- Efeitos: `at(d,2)`, `lev(d,0)`; d sai de `at(d,0)`, `lev(d,1)`.

Estado em t=3:

```
   |.|.|.|.|.|a|
   |c|c|d|d|d|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 4: `move(a,c,0)`** — mover a para cima do bloco c, começando no ponto 0.

- `clr(a)` verdadeiro em t=3: nada está sobre a.
- Slots [0] livres no nível 1; slots apoiados no nível 0: [0] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(a,0)`, `lev(a,1)`; a sai de `at(a,5)`, `lev(a,1)`.

Estado em t=4:

```
   |a|.|.|.|.|.|
   |c|c|d|d|d|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 5: `move(b,c,1)`** — mover b para cima do bloco c, começando no ponto 1.

- `clr(b)` verdadeiro em t=4: nada está sobre b.
- Slots [1] livres no nível 1; slots apoiados no nível 0: [1] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(b,1)`, `lev(b,1)`; b sai de `at(b,5)`, `lev(b,0)`.

Estado em t=5:

```
   |a|b|.|.|.|.|
   |c|c|d|d|d|.|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 6: `move(d,T,3)`** — mover d para a mesa, começando no ponto 3.

- `clr(d)` verdadeiro em t=5: nada está sobre d.
- Slots [3, 4, 5] livres no nível 0; nível 0 (mesa): não precisa de apoio.
- Efeitos: `at(d,3)`, `lev(d,0)`; d sai de `at(d,2)`, `lev(d,0)`.

Estado em t=6:

```
   |a|b|.|.|.|.|
   |c|c|.|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

Relações `on` no estado final: a esta sobre: c; b esta sobre: c; c esta na MESA; d esta na MESA.

#### Situação 3: S0 → S7 (ordem parcial invertida, b ≺ a)

Estado inicial (t=0):

```
   |.|.|.|d|d|d|
   |c|c|.|a|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 1: `move(d,c,0)`** — mover d para cima do bloco c, começando no ponto 0.

- `clr(d)` verdadeiro em t=0: nada está sobre d.
- Slots [0, 1, 2] livres no nível 1; slots apoiados no nível 0: [0, 1] (2 ≥ ⌈3/2⌉ = 2).
- Efeitos: `at(d,0)`, `lev(d,1)`; d sai de `at(d,3)`, `lev(d,1)`.

Estado em t=1:

```
   |d|d|d|.|.|.|
   |c|c|.|a|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 2: `move(a,b,5)`** — mover a para cima do bloco b, começando no ponto 5.

- `clr(a)` verdadeiro em t=1: nada está sobre a.
- Slots [5] livres no nível 1; slots apoiados no nível 0: [5] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(a,5)`, `lev(a,1)`; a sai de `at(a,3)`, `lev(a,0)`.

Estado em t=2:

```
   |d|d|d|.|.|a|
   |c|c|.|.|.|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 3: `move(d,T,2)`** — mover d para a mesa, começando no ponto 2.

- `clr(d)` verdadeiro em t=2: nada está sobre d.
- Slots [2, 3, 4] livres no nível 0; nível 0 (mesa): não precisa de apoio.
- Efeitos: `at(d,2)`, `lev(d,0)`; d sai de `at(d,0)`, `lev(d,1)`.

Estado em t=3:

```
   |.|.|.|.|.|a|
   |c|c|d|d|d|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 4: `move(a,d,3)`** — mover a para cima do bloco d, começando no ponto 3.

- `clr(a)` verdadeiro em t=3: nada está sobre a.
- Slots [3] livres no nível 1; slots apoiados no nível 0: [3] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(a,3)`, `lev(a,1)`; a sai de `at(a,5)`, `lev(a,1)`.

Estado em t=4:

```
   |.|.|.|a|.|.|
   |c|c|d|d|d|b|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 5: `move(b,c,1)`** — mover b para cima do bloco c, começando no ponto 1.

- `clr(b)` verdadeiro em t=4: nada está sobre b.
- Slots [1] livres no nível 1; slots apoiados no nível 0: [1] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(b,1)`, `lev(b,1)`; b sai de `at(b,5)`, `lev(b,0)`.

Estado em t=5:

```
   |.|b|.|a|.|.|
   |c|c|d|d|d|.|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 6: `move(a,c,0)`** — mover a para cima do bloco c, começando no ponto 0.

- `clr(a)` verdadeiro em t=5: nada está sobre a.
- Slots [0] livres no nível 1; slots apoiados no nível 0: [0] (1 ≥ ⌈1/2⌉ = 1).
- Efeitos: `at(a,0)`, `lev(a,1)`; a sai de `at(a,3)`, `lev(a,1)`.

Estado em t=6:

```
   |a|b|.|.|.|.|
   |c|c|d|d|d|.|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

**Passo 7: `move(d,T,3)`** — mover d para a mesa, começando no ponto 3.

- `clr(d)` verdadeiro em t=6: nada está sobre d.
- Slots [3, 4, 5] livres no nível 0; nível 0 (mesa): não precisa de apoio.
- Efeitos: `at(d,3)`, `lev(d,0)`; d sai de `at(d,2)`, `lev(d,0)`.

Estado em t=7:

```
   |a|b|.|.|.|.|
   |c|c|.|d|d|d|
   slots: 0 1 2 3 4 5   (pontos 0..6)
```

Relações `on` no estado final: a esta sobre: c; b esta sobre: c; c esta na MESA; d esta na MESA.

## 9. Comparação: planos manuais × planos do SAT

Os planos da seção 8 são os mesmos que o miniSAT encontrou, e o SAT ainda prova que nenhum plano menor existe (todos os T menores deram UNSATISFIABLE em `busca_horizonte.txt`). Por exemplo, na Situação 1 → Sf4 o menor plano tem 4 ações. Não existe plano de 3 ações porque o a fica embaixo do d no início, e não sobra slot livre na mesa onde estacioná-lo sem atrapalhar o d na meta: ele precisa esperar em cima do b.

## 10. Limitações e observações

- A pré-condição clr(y) do manual foi relaxada (seção 2.5). Com o clr(y) original, quatro dos cenários pedidos não têm plano.
- Sem "pelo menos uma ação por passo", o solver pode devolver menos ações que T; o `interpretar.py` mostra as ações que realmente ocorrem.
- O número de níveis está limitado a 3 (`MAX_LEVEL`), o que basta para 4 blocos. Para mais blocos, ajuste `BLOCKS` e `MAX_LEVEL`.
- O manual também traz um exemplo de plano na Situação 1 em que o a vai para a mesa em p=4 e depois o d vai para a mesa em p=2; nessa sequência os dois ocupam o slot 4. A saída correta estaciona o a sobre o b (seção 8).
