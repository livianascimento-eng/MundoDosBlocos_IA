#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar_plano.py  --  confere um plano SEM usar o SAT (simulador independente).

Simula, passo a passo, as pre-condicoes de move(b, y, p) da Secao 2.6 do manual, a regra
de estabilidade (Secao 2.7) e a exclusao horizontal.  Serve para comparar o plano manual
com o plano do SAT e para descobrir erros de codificacao.

Uso:
    python3 verificar_plano.py resultado1.txt [--cenario 1]
"""
import argparse
import os
import sys

from bw2cnf_var import BLOCKS, CENARIOS, MAX_LEVEL, TABLE, span, spans_overlap, valid_positions
from interpretar import carregar_mapa, extrair, ler_resultado, frase


def ocupacao(estado, ignorar=None):
    """(slot, nivel) -> bloco.  Levanta ValueError se dois blocos dividem a mesma celula."""
    occ = {}
    for b, (p, l) in estado.items():
        if b == ignorar:
            continue
        for s in span(p, BLOCKS[b]):
            if (s, l) in occ:
                raise ValueError(f"'{b}' e '{occ[(s, l)]}' dividem o slot {s} no nivel {l}")
            occ[(s, l)] = b
    return occ


def estavel(estado, b):
    p, l = estado[b]
    if l == 0:
        return True
    occ = ocupacao(estado)
    sob = sum(1 for s in span(p, BLOCKS[b]) if (s, l - 1) in occ)
    return sob >= (BLOCKS[b] + 1) // 2


def livre_topo(estado, y):
    py, ly = estado[y]
    return not any(o != y and lo == ly + 1 and spans_overlap(y, py, o, po)
                   for o, (po, lo) in estado.items())


def estado_valido(estado):
    ocupacao(estado)
    for b in estado:
        if not estavel(estado, b):
            raise ValueError(f"'{b}' esta instavel em {estado[b]}")


def aplicar(estado, b, y, p):
    if p not in valid_positions(BLOCKS[b]):
        raise ValueError("posicao invalida")
    if not livre_topo(estado, b):
        raise ValueError(f"o topo de '{b}' nao esta livre")
    if y != TABLE:
        if not spans_overlap(b, p, y, estado[y][0]):
            raise ValueError(f"'{b}' em p={p} nao encosta em '{y}'")
        nivel = estado[y][1] + 1
    else:
        nivel = 0
    if nivel > MAX_LEVEL:
        raise ValueError("nivel maximo excedido")
    if estado[b] == (p, nivel):
        raise ValueError("no-op (destino igual a posicao atual)")
    for o, (po, lo) in estado.items():        # slots do destino e vao acima livres
        if o != b and spans_overlap(b, p, o, po) and lo >= nivel:
            raise ValueError(f"destino ocupado/bloqueado por '{o}' (nivel {lo})")
    novo = dict(estado)
    novo[b] = (p, nivel)
    estado_valido(novo)
    return novo


def verificar(acoes, estados, meta=None):
    est = estados[0]
    estado_valido(est)
    for i, (t, b, y, p) in enumerate(acoes):
        est = aplicar(est, b, y, p)
        if est != estados[t + 1]:
            raise ValueError(f"passo {i + 1}: o estado simulado difere do estado do SAT")
    if meta:
        for b, pl in meta.items():
            if est[b] != pl:
                raise ValueError(f"meta nao atingida: {b} esta em {est[b]}, esperado {pl}")
    return est


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('resultado')
    ap.add_argument('--mapa')
    ap.add_argument('--cenario', help="se dado, tambem confere a meta desse cenario")
    args = ap.parse_args()
    caminho_mapa = args.mapa or os.path.join(os.path.dirname(os.path.abspath(args.resultado)),
                                             'trab01_blocos2SAT.map')
    verd = ler_resultado(args.resultado)
    if verd is None:
        sys.exit("resultado INSATISFATIVEL: nada para verificar")
    acoes, estados = extrair(carregar_mapa(caminho_mapa), verd)
    meta = CENARIOS[args.cenario]['goal'] if args.cenario else None
    try:
        verificar(acoes, estados, meta)
    except ValueError as e:
        print(f"PLANO INVALIDO: {e}")
        sys.exit(1)
    print(f"PLANO VALIDO ({len(acoes)} acoes)" + (" e atinge a meta" if meta else ""))


if __name__ == '__main__':
    main()
