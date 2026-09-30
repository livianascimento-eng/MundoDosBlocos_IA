#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bw2cnf_var.py  --  Mundo dos Blocos de Tamanho Variavel  ->  CNF (DIMACS) para o miniSAT

Uso basico (igual ao manual):
    1. edite INITIAL, GOAL e HORIZON aqui embaixo, e rode:   python3 bw2cnf_var.py
    2. ou escolha um cenario pronto:                          python3 bw2cnf_var.py --cenario 2 --horizonte 5
Gera dois arquivos:  trab01_blocos2SAT.cnf  e  trab01_blocos2SAT.map
(o .map traduz cada numero do CNF para o simbolo, ex.: 50 -> move(d, on=c, p=0, t=0)).

Convencao das coordenadas (ver manual, Secao 2):
    - a mesa vai do ponto 0 ao ponto 6  ->  6 slots: [0,1], [1,2], ..., [5,6]
    - um bloco b que comeca no ponto p cobre os slots p, p+1, ..., p+len(b)-1
    - INITIAL / GOAL: { bloco: (ponto_inicial p, nivel l) }   (nivel 0 = mesa)
"""
import argparse
import itertools
import os
import sys

# ----------------------------------------------------------------------------
# Dominio
# ----------------------------------------------------------------------------
BLOCKS = {'a': 1, 'b': 1, 'c': 2, 'd': 3}   # bloco -> comprimento (uc)
MAX_POINT = 6                               # pontos 0..6  => 6 slots
MAX_LEVEL = 3                               # niveis 0..3
TABLE = 'T'                                 # a mesa

# ----------------------------------------------------------------------------
# Cenario editavel (como no manual).  Por padrao: Situacao 1, S0 -> Sf4.
# ----------------------------------------------------------------------------
INITIAL = {'c': (0, 0), 'a': (3, 0), 'b': (5, 0), 'd': (3, 1)}
GOAL    = {'c': (0, 0), 'a': (0, 1), 'd': (2, 0), 'b': (5, 0)}
HORIZON = 4

# Cenarios prontos do enunciado (desenhos das paginas 5, 6 e 7 do PDF)
S0_SIT1 = {'c': (0, 0), 'a': (3, 0), 'b': (5, 0), 'd': (3, 1)}
CENARIOS = {
    # Situacao 1: S0 -> um dos estados finais Sf1..Sf4
    '1':     dict(nome='Situacao 1: S0 -> Sf4', initial=S0_SIT1,
                  goal={'c': (0, 0), 'a': (0, 1), 'd': (2, 0), 'b': (5, 0)}),
    '1-sf1': dict(nome='Situacao 1: S0 -> Sf1', initial=S0_SIT1,
                  goal={'d': (3, 0), 'a': (4, 1), 'b': (5, 1), 'c': (4, 2)}),
    '1-sf2': dict(nome='Situacao 1: S0 -> Sf2', initial=S0_SIT1,
                  goal={'d': (3, 0), 'c': (4, 1), 'a': (4, 2), 'b': (5, 2)}),
    '1-sf3': dict(nome='Situacao 1: S0 -> Sf3', initial=S0_SIT1,
                  goal={'c': (0, 0), 'a': (2, 0), 'd': (0, 1), 'b': (5, 0)}),
    # Situacao 2: S0 -> S5
    '2':     dict(nome='Situacao 2: S0 -> S5',
                  initial={'c': (0, 0), 'a': (0, 1), 'b': (1, 1), 'd': (3, 0)},
                  goal={'d': (3, 0), 'c': (4, 1), 'a': (4, 2), 'b': (5, 2)}),
    # Situacao 3: S0 -> S7
    '3':     dict(nome='Situacao 3: S0 -> S7', initial=S0_SIT1,
                  goal={'c': (0, 0), 'a': (0, 1), 'b': (1, 1), 'd': (3, 0)}),
}


# ----------------------------------------------------------------------------
# Funcoes geometricas (Secao 2.2 e 2.3 do manual)
# ----------------------------------------------------------------------------
def valid_positions(L):
    """Pontos iniciais validos para um bloco de comprimento L."""
    return range(MAX_POINT - L + 1)


def span(p, L):
    """Slots cobertos por um bloco de comprimento L que comeca no ponto p."""
    return range(p, p + L)


def spans_overlap(b1, p1, b2, p2):
    """Os intervalos [p1, p1+len(b1)] e [p2, p2+len(b2)] compartilham algum slot?"""
    return p1 < p2 + BLOCKS[b2] and p2 < p1 + BLOCKS[b1]


# ----------------------------------------------------------------------------
# Contêiner de variaveis e clausulas
# ----------------------------------------------------------------------------
class Cnf:
    def __init__(self):
        self.n = 0
        self.names = {}      # id -> simbolo (vira o arquivo .map)
        self.clauses = []

    def new_var(self, name):
        self.n += 1
        self.names[self.n] = name
        return self.n

    def add(self, *lits):
        self.clauses.append(list(lits))

    def exactly_one(self, lits):
        self.add(*lits)                                   # pelo menos um
        for x, y in itertools.combinations(lits, 2):      # no maximo um
            self.add(-x, -y)


def gerar_cnf(initial, goal, horizon, ordem=()):
    """
    Constroi o CNF para 'horizon' passos.
    ordem: lista de pares ((b1,p1,l1), (b2,p2,l2)) = meta phi1 deve ocorrer antes de phi2.
    Retorna o objeto Cnf.
    """
    T = horizon
    cnf = Cnf()
    B = list(BLOCKS)
    LEVELS = range(MAX_LEVEL + 1)
    SLOTS = range(MAX_POINT)

    # ---- variaveis (Secao 3.1 do manual) -----------------------------------
    at, lev, clr, mv = {}, {}, {}, {}
    occ = {}          # AUXILIAR: occ(s,l,t) = "o slot s esta ocupado no nivel l" (cov do manual)
    for t in range(T + 1):
        for b in B:
            for p in valid_positions(BLOCKS[b]):
                at[(b, p, t)] = cnf.new_var(f"at({b}, p={p}, t={t})")
            for l in LEVELS:
                lev[(b, l, t)] = cnf.new_var(f"lev({b}, l={l}, t={t})")
            clr[(b, t)] = cnf.new_var(f"clr({b}, t={t})")
        for s in SLOTS:
            for l in LEVELS:
                occ[(s, l, t)] = cnf.new_var(f"occ(s={s}, l={l}, t={t})")
    for t in range(T):
        for b in B:
            for y in B + [TABLE]:
                if y == b:
                    continue
                for p in valid_positions(BLOCKS[b]):
                    mv[(b, y, p, t)] = cnf.new_var(f"move({b}, on={y}, p={p}, t={t})")

    # ---- 3.1 ESTADO INICIAL ------------------------------------------------
    for b, (p, l) in initial.items():
        cnf.add(at[(b, p, 0)])
        cnf.add(lev[(b, l, 0)])

    # ---- 3.2 META ----------------------------------------------------------
    for b, (p, l) in goal.items():
        cnf.add(at[(b, p, T)])
        cnf.add(lev[(b, l, T)])

    for t in range(T + 1):
        # ---- 3.3 (A) unicidade de posicao / (B) unicidade de nivel ----------
        for b in B:
            cnf.exactly_one([at[(b, p, t)] for p in valid_positions(BLOCKS[b])])
            cnf.exactly_one([lev[(b, l, t)] for l in LEVELS])

        # ---- 3.3 (C) exclusao horizontal: mesmo nivel nao pode dividir slot --
        for b1, b2 in itertools.combinations(B, 2):
            for p1 in valid_positions(BLOCKS[b1]):
                for p2 in valid_positions(BLOCKS[b2]):
                    if spans_overlap(b1, p1, b2, p2):
                        for l in LEVELS:
                            cnf.add(-at[(b1, p1, t)], -at[(b2, p2, t)],
                                    -lev[(b1, l, t)], -lev[(b2, l, t)])

        # ---- ocupacao occ(s,l,t) <-> algum bloco cobre o slot s no nivel l ---
        for b in B:
            for p in valid_positions(BLOCKS[b]):
                for l in LEVELS:
                    for s in span(p, BLOCKS[b]):
                        cnf.add(-at[(b, p, t)], -lev[(b, l, t)], occ[(s, l, t)])
        for s in SLOTS:
            for l in LEVELS:
                # occ -> OR_b (cobre(b,s) AND lev(b,l)); expandido em CNF (2^4 clausulas)
                cobre = {b: [at[(b, p, t)] for p in valid_positions(BLOCKS[b])
                             if p <= s < p + BLOCKS[b]] for b in B}
                for escolha in itertools.product([0, 1], repeat=len(B)):
                    clause = [-occ[(s, l, t)]]
                    for b, e in zip(B, escolha):
                        clause += cobre[b] if e == 0 else [lev[(b, l, t)]]
                    cnf.add(*clause)

        # ---- 3.3 (D) estabilidade: >= ceil(len/2) slots sob o bloco ocupados --
        for b in B:
            n = BLOCKS[b]
            k = (n + 1) // 2                       # ceil(n/2)
            for p in valid_positions(n):
                for l in range(1, MAX_LEVEL + 1):
                    sob = [occ[(s, l - 1, t)] for s in span(p, n)]
                    # "pelo menos k de n"  <=>  todo subconjunto de n-k+1 tem um verdadeiro
                    for sub in itertools.combinations(sob, n - k + 1):
                        cnf.add(-at[(b, p, t)], -lev[(b, l, t)], *sub)

        # ---- 3.3 (E) clear: clr(b,t) <-> nada acima de b ---------------------
        for b in B:
            n = BLOCKS[b]
            for p in valid_positions(n):
                for l in LEVELS:
                    if l == MAX_LEVEL:
                        cnf.add(-at[(b, p, t)], -lev[(b, l, t)], clr[(b, t)])
                        continue
                    acima = [occ[(s, l + 1, t)] for s in span(p, n)]
                    for o in acima:        # clr -> nada acima
                        cnf.add(-clr[(b, t)], -at[(b, p, t)], -lev[(b, l, t)], -o)
                    # nada acima -> clr
                    cnf.add(clr[(b, t)], -at[(b, p, t)], -lev[(b, l, t)], *acima)

    for t in range(T):
        # ---- 3.4 (G) PRE-CONDICOES de move(b, y, p, t) ------------------------
        for (b, y, p, _t), m in [(k, v) for k, v in mv.items() if k[3] == t]:
            n = BLOCKS[b]
            outros = [x for x in B if x != b]
            # 1. topo de b livre
            cnf.add(-m, clr[(b, t)])
            if y != TABLE:
                # 2. (adaptada) o manual pede clr(y,t), o topo INTEIRO de y livre.  Isso impede
                #    pousar um 2o bloco sobre y quando outro ja esta em cima de y (ex.: a e b
                #    juntos sobre c na Situacao 2).  Basta o TRECHO de y sob o destino estar
                #    livre, e isso ja e exigido por 5. abaixo.
                # (nivel maximo) nao da para empilhar acima de MAX_LEVEL
                cnf.add(-m, -lev[(y, MAX_LEVEL, t)])
                # 4. o span de b (em p) precisa sobrepor o span de y
                for py in valid_positions(BLOCKS[y]):
                    if not spans_overlap(b, p, y, py):
                        cnf.add(-m, -at[(y, py, t)])
            # 3. o destino nao pode ser a posicao atual (evita no-op)
            if y == TABLE:
                cnf.add(-m, -at[(b, p, t)], -lev[(b, 0, t)])
            else:
                for l in range(MAX_LEVEL):
                    cnf.add(-m, -at[(b, p, t)], -lev[(b, l + 1, t)], -lev[(y, l, t)])
            # 5. slots do destino livres de OUTROS blocos, no nivel-alvo
            # 6. vao livre acima do destino (o guindaste solta o bloco de cima para baixo;
            #    por isso o slot embaixo de uma ponte tambem nao pode receber bloco)
            for o in outros:
                for po in valid_positions(BLOCKS[o]):
                    if not spans_overlap(b, p, o, po):
                        continue
                    if y == TABLE:
                        for lo in LEVELS:                 # nivel-alvo = 0 e tudo acima
                            cnf.add(-m, -at[(o, po, t)], -lev[(o, lo, t)])
                    else:
                        for l in range(MAX_LEVEL):        # nivel-alvo = l+1 e tudo acima
                            for lo in range(l + 1, MAX_LEVEL + 1):
                                cnf.add(-m, -lev[(y, l, t)], -at[(o, po, t)], -lev[(o, lo, t)])

            # ---- 3.4 (H) EFEITOS de move ------------------------------------
            cnf.add(-m, at[(b, p, t + 1)])                          # 1. at(b,p,t+1)
            if y == TABLE:
                cnf.add(-m, lev[(b, 0, t + 1)])                     # 2. nivel 0
            else:
                for l in range(MAX_LEVEL):
                    cnf.add(-m, -lev[(y, l, t)], lev[(b, l + 1, t + 1)])   # 2. nivel(y)+1
                cnf.add(-m, -clr[(y, t + 1)])                       # 3. y deixa de estar livre
            # 4. b deixa a posicao/nivel anteriores: garantido pela unicidade em t+1

        # ---- 3.5 FRAME AXIOMS (at e lev persistem se b nao se move) -----------
        # (clr nao precisa de frame: e definido em todo t por 3.3 (E))
        for b in B:
            moves_b = [v for (bb, y, p, tt), v in mv.items() if bb == b and tt == t]
            for p in valid_positions(BLOCKS[b]):
                cnf.add(-at[(b, p, t)], at[(b, p, t + 1)], *moves_b)
            for l in LEVELS:
                cnf.add(-lev[(b, l, t)], lev[(b, l, t + 1)], *moves_b)

        # ---- 3.6 ACAO UNICA por passo -----------------------------------------
        cnf.exactly_one([v for k, v in mv.items() if k[3] == t])

    # ---- 3.7 ORDEM PARCIAL  phi1 --P--> phi2  ------------------------------------
    # phi = (bloco, ponto, nivel).  hold(phi,t) <-> at(b,p,t) & lev(b,l,t)
    # regra do manual: para todo t:  -phi2(t)  v  phi1(t') para algum t' <= t
    hold = {}

    def get_hold(phi, t):
        if (phi, t) not in hold:
            b, p, l = phi
            h = cnf.new_var(f"hold({b}, p={p}, l={l}, t={t})")
            hold[(phi, t)] = h
            cnf.add(-h, at[(b, p, t)])
            cnf.add(-h, lev[(b, l, t)])
            cnf.add(h, -at[(b, p, t)], -lev[(b, l, t)])
        return hold[(phi, t)]

    for phi1, phi2 in ordem:
        for t in range(T + 1):
            cnf.add(-get_hold(phi2, t), *[get_hold(phi1, tp) for tp in range(t + 1)])

    return cnf


def escrever(cnf, prefixo, saida='.'):
    os.makedirs(saida, exist_ok=True)
    caminho_cnf = os.path.join(saida, prefixo + '.cnf')
    caminho_map = os.path.join(saida, prefixo + '.map')
    with open(caminho_cnf, 'w') as f:
        f.write(f"p cnf {cnf.n} {len(cnf.clauses)}\n")
        for c in cnf.clauses:
            f.write(' '.join(map(str, c)) + ' 0\n')
    with open(caminho_map, 'w') as f:
        f.write("# mapa: id da variavel -> simbolo do dominio\n")
        for i in range(1, cnf.n + 1):
            f.write(f"{i} -> {cnf.names[i]}\n")
    return caminho_cnf, caminho_map


def _parse_phi(txt):
    b, p, l = txt.split(',')
    return (b.strip(), int(p), int(l))


def main():
    ap = argparse.ArgumentParser(description="Gera o CNF do Mundo dos Blocos de tamanho variavel.")
    ap.add_argument('--cenario', help="1, 1-sf1, 1-sf2, 1-sf3, 2 ou 3 (padrao: usa INITIAL/GOAL/HORIZON do topo do arquivo)")
    ap.add_argument('--horizonte', '-T', type=int, help="numero de passos T")
    ap.add_argument('--saida', default='.', help="pasta de saida (padrao: pasta atual)")
    ap.add_argument('--prefixo', default='trab01_blocos2SAT')
    ap.add_argument('--ordem', action='append', default=[],
                    help="ordem parcial 'b,p,l<b,p,l' = a 1a meta antes da 2a. Ex.: --ordem 'd,2,0<a,0,1'")
    args = ap.parse_args()

    initial, goal, horizon = INITIAL, GOAL, HORIZON
    if args.cenario:
        if args.cenario not in CENARIOS:
            sys.exit(f"cenario desconhecido: {args.cenario}. Opcoes: {', '.join(CENARIOS)}")
        initial, goal = CENARIOS[args.cenario]['initial'], CENARIOS[args.cenario]['goal']
    if args.horizonte is not None:
        horizon = args.horizonte
    ordem = []
    for o in args.ordem:
        a, b = o.split('<')
        ordem.append((_parse_phi(a), _parse_phi(b)))

    cnf = gerar_cnf(initial, goal, horizon, ordem)
    c, m = escrever(cnf, args.prefixo, args.saida)
    print(f"Gerado: {cnf.n} variaveis, {len(cnf.clauses)} clausulas")
    print(f"Arquivos: {c}, {m}")


if __name__ == '__main__':
    main()
