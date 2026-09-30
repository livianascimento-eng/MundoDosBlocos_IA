#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
resolver.py  --  automatiza: gerar CNF -> rodar miniSAT -> interpretar, para T = 1, 2, 3, ...
O primeiro T que da SATISFIABLE e o comprimento MINIMO do plano (Secao 8 do manual).

Uso:
    python3 resolver.py 2                       # Situacao 2, salva em situacao2/
    python3 resolver.py 1 --saida situacao1
    python3 resolver.py 1 --ordem 'a,0,1<d,2,0' # com ordem parcial
"""
import argparse
import os
import subprocess
import sys

from bw2cnf_var import CENARIOS, escrever, gerar_cnf, _parse_phi
from interpretar import carregar_mapa, extrair, ler_resultado, frase, descrever_on
from verificar_plano import verificar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cenario', help="1, 1-sf1, 1-sf2, 1-sf3, 2 ou 3")
    ap.add_argument('--saida', help="pasta de saida (padrao: situacao<cenario>)")
    ap.add_argument('--resultado', help="nome do arquivo de resultado (padrao: resultado<N>.txt)")
    ap.add_argument('--tmax', type=int, default=14)
    ap.add_argument('--ordem', action='append', default=[])
    args = ap.parse_args()

    cen = CENARIOS[args.cenario]
    saida = args.saida or f"situacao{args.cenario}"
    resultado = args.resultado or f"resultado{args.cenario[0]}.txt"
    ordem = []
    for o in args.ordem:
        a, b = o.split('<')
        ordem.append((_parse_phi(a), _parse_phi(b)))
    os.makedirs(saida, exist_ok=True)

    log = [f"Busca do horizonte minimo -- {cen['nome']}"]
    if ordem:
        log.append("Ordem parcial: " + ", ".join(f"{a} antes de {b}" for a, b in ordem))
    for T in range(1, args.tmax + 1):
        cnf = gerar_cnf(cen['initial'], cen['goal'], T, ordem)
        c, m = escrever(cnf, 'trab01_blocos2SAT', saida)
        r = os.path.join(saida, resultado)
        subprocess.run(['minisat', c, r], capture_output=True, text=True)
        verd = ler_resultado(r)
        linha = f"T={T}: {cnf.n} variaveis, {len(cnf.clauses)} clausulas -> " + ("SATISFIABLE" if verd else "UNSATISFIABLE")
        print(linha)
        log.append(linha)
        if verd:
            acoes, estados = extrair(carregar_mapa(m), verd)
            verificar(acoes, estados, cen['goal'])          # confere com o simulador independente
            log.append(f"Plano minimo: {T} acoes (verificado pelo simulador independente)")
            for i, a in enumerate(acoes, 1):
                log.append(f"  {i}. {frase(a)}")
            print("\n".join(log[-(T + 1):]))
            break
    else:
        log.append(f"Nenhum plano encontrado ate T={args.tmax}")
        print(log[-1])
    with open(os.path.join(saida, 'busca_horizonte.txt'), 'w') as f:
        f.write("\n".join(log) + "\n")


if __name__ == '__main__':
    main()
