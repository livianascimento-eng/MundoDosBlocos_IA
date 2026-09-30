#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
interpretar.py  --  traduz a saida numerica do miniSAT para um plano em portugues.

Uso (igual ao manual):
    python3 interpretar.py resultado1.txt --verbose
    python3 interpretar.py resultado1.txt --passo-a-passo      (desenha cada estado)

O miniSAT so devolve inteiros; quem diz o que cada inteiro significa e o arquivo .map
(gerado pelo bw2cnf_var.py).  Por padrao o .map e procurado na mesma pasta do resultado.
"""
import argparse
import os
import re
import sys

from bw2cnf_var import BLOCKS, MAX_LEVEL, MAX_POINT, TABLE, span, spans_overlap

RE_MAP = re.compile(r"^(\d+) -> (\w+)\((.*)\)\s*$")


def carregar_mapa(caminho):
    """Le o .map: id -> (nome, {argumentos})."""
    mapa = {}
    with open(caminho) as f:
        for linha in f:
            m = RE_MAP.match(linha)
            if not m:
                continue
            i, nome, args = int(m.group(1)), m.group(2), m.group(3)
            campos = [a.strip() for a in args.split(',')]
            d = {'pos': []}
            for c in campos:
                if '=' in c:
                    k, v = c.split('=')
                    d[k] = v
                else:
                    d['pos'].append(c)
            mapa[i] = (nome, d)
    return mapa


def ler_resultado(caminho):
    """Retorna o conjunto de variaveis verdadeiras, ou None se o problema e insatisfativel."""
    with open(caminho) as f:
        linhas = [l.strip() for l in f if l.strip()]
    if not linhas or linhas[0] != 'SAT':
        return None
    verdadeiras = set()
    for l in linhas[1:]:
        for tok in l.split():
            v = int(tok)
            if v > 0:
                verdadeiras.add(v)
    return verdadeiras


def extrair(mapa, verdadeiras):
    """Filtra apenas os literais positivos relevantes: acoes move e estados at/lev."""
    acoes, at, lev = [], {}, {}
    for i in verdadeiras:
        if i not in mapa:
            continue
        nome, d = mapa[i]
        if nome == 'move':
            acoes.append((int(d['t']), d['pos'][0], d['on'], int(d['p'])))
        elif nome == 'at':
            at[(d['pos'][0], int(d['t']))] = int(d['p'])
        elif nome == 'lev':
            lev[(d['pos'][0], int(d['t']))] = int(d['l'])
    acoes.sort()
    T = max([t for (_, t) in at] or [0])
    estados = {t: {b: (at[(b, t)], lev[(b, t)]) for b in BLOCKS} for t in range(T + 1)}
    return acoes, estados


def derivar_on(estado):
    """on(b, y) derivado de at, lev e sobreposicao de spans (Secao 7.3 do manual)."""
    on = {}
    for b, (pb, lb) in estado.items():
        if lb == 0:
            on[b] = [TABLE]
        else:
            on[b] = sorted(y for y, (py, ly) in estado.items()
                           if y != b and ly == lb - 1 and spans_overlap(b, pb, y, py))
    return on


def frase(acao):
    t, b, y, p = acao
    if y == TABLE:
        return f"t={t}: mover bloco '{b}' para a MESA em p={p}"
    return f"t={t}: mover bloco '{b}' para CIMA de '{y}' em p={p}"


def desenhar(estado):
    """Desenho ASCII do estado (uma coluna de 3 caracteres por slot)."""
    nivel_max = max(max(l for (_, l) in estado.values()), 1)
    linhas = []
    for l in range(nivel_max, -1, -1):
        celulas = [' . '] * MAX_POINT
        for b, (p, lb) in estado.items():
            if lb == l:
                for s in span(p, BLOCKS[b]):
                    celulas[s] = f" {b} "
        linhas.append(f" {l} |" + ''.join(celulas))
    linhas.append("   +" + "---" * MAX_POINT)
    linhas.append("    " + ''.join(f"{i:<3}" for i in range(MAX_POINT + 1)))
    return '\n'.join(linhas)


def descrever_on(estado, prefixo="  "):
    saida = []
    for b, apoios in sorted(derivar_on(estado).items()):
        if apoios == [TABLE]:
            saida.append(f"{prefixo}{b} esta na MESA")
        else:
            extra = " (ponte)" if len(apoios) > 1 else ""
            saida.append(f"{prefixo}{b} esta sobre: {', '.join(apoios)}{extra}")
    return saida


def main():
    ap = argparse.ArgumentParser(description="Interpreta a saida do miniSAT usando o arquivo .map")
    ap.add_argument('resultado')
    ap.add_argument('--mapa', help="caminho do .map (padrao: trab01_blocos2SAT.map ao lado do resultado)")
    ap.add_argument('--verbose', '-v', action='store_true', help="mostra estado final e relacoes 'on'")
    ap.add_argument('--passo-a-passo', action='store_true', help="desenha o estado em cada instante t")
    args = ap.parse_args()

    caminho_mapa = args.mapa or os.path.join(os.path.dirname(os.path.abspath(args.resultado)),
                                             'trab01_blocos2SAT.map')
    if not os.path.exists(caminho_mapa):
        sys.exit(f"Sem o arquivo .map ({caminho_mapa}) a saida do miniSAT nao tem significado.")
    mapa = carregar_mapa(caminho_mapa)
    verdadeiras = ler_resultado(args.resultado)
    if verdadeiras is None:
        print("INSATISFATIVEL: nao existe plano com esse horizonte T.")
        return

    acoes, estados = extrair(mapa, verdadeiras)
    print(f"PLANO ENCONTRADO ({len(acoes)} acoes):")
    for i, a in enumerate(acoes, 1):
        print(f"  {i}. {frase(a)}")

    if args.passo_a_passo:
        for t, est in estados.items():
            print(f"\nESTADO t={t}" + ("" if t == 0 else f"   (apos: {frase(acoes[t - 1]).split(': ', 1)[1]})"))
            print(desenhar(est))
            for l in descrever_on(est, "    "):
                print(l)
    if args.verbose:
        T = max(estados)
        print(f"\nESTADO FINAL (t={T}):")
        for b in sorted(estados[T]):
            p, l = estados[T][b]
            print(f"  {b}: ponto inicial p={p}, nivel l={l}")
        print(f"\nRELACOES 'on' em t={T}:")
        for l in descrever_on(estados[T]):
            print(l)


if __name__ == '__main__':
    main()
