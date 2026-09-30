#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rodar.py -- roda os cenarios: para T = 0, 1, 2, ... gera o CNF, chama o miniSAT e para no
primeiro T SATISFIABLE (o menor T que satisfaz e o comprimento minimo do plano).

Uso:
    python3 rodar.py               # roda todos os cenarios
    python3 rodar.py situacao2     # roda so um
"""
import os
import shutil
import subprocess
import sys

from bw2cnf_var import CENARIOS, gerar_cnf, escrever_arquivos

# (cenario, pasta, nome do arquivo de resultado)
EXECUCOES = [
    ('situacao1',           'situacao1',                   'resultado1.txt'),
    ('situacao1_sf1',       'situacao1/sf1',               'resultado_sf1.txt'),
    ('situacao1_sf2',       'situacao1/sf2',               'resultado_sf2.txt'),
    ('situacao1_sf3',       'situacao1/sf3',               'resultado_sf3.txt'),
    ('situacao2',           'situacao2',                   'resultado2.txt'),
    ('situacao3',           'situacao3',                   'resultado3.txt'),
    ('situacao3_sem_ordem', 'situacao3/sem_ordem',         'resultado3_sem_ordem.txt'),
    ('situacao3_ordem_inversa', 'situacao3/ordem_inversa', 'resultado3_ordem_inversa.txt'),
]
HORIZONTE_MAXIMO = 12


def rodar(nome, pasta, resultado):
    c = CENARIOS[nome]
    log = [f"Busca do menor horizonte para '{nome}' (T = 0, 1, 2, ...)", ""]
    log.append(f"{'T':>3} {'variaveis':>10} {'clausulas':>10}  resultado")
    for T in range(HORIZONTE_MAXIMO + 1):
        n, cl, nomes = gerar_cnf(c['initial'], c['goal'], T, c['order'])
        cnf, mapa = escrever_arquivos(n, cl, nomes, pasta, comentario=f"{nome} horizonte T={T}")
        saida = os.path.join(pasta, resultado)
        subprocess.run(['minisat', cnf, saida], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(saida) as f:
            veredito = f.readline().strip()
        log.append(f"{T:>3} {n:>10} {len(cl):>10}  {'SATISFIABLE' if veredito == 'SAT' else 'UNSATISFIABLE'}")
        if veredito == 'SAT':
            log.append("")
            log.append(f"Menor T que satisfaz: {T}  =>  plano de comprimento minimo (no maximo {T} acoes).")
            break
    else:
        log.append(f"Nenhum plano ate T={HORIZONTE_MAXIMO}.")
    with open(os.path.join(pasta, 'busca_horizonte.txt'), 'w') as f:
        f.write('\n'.join(log) + '\n')
    print('\n'.join(log))
    return veredito == 'SAT'


if __name__ == '__main__':
    if shutil.which('minisat') is None:
        sys.exit("minisat nao encontrado. Instale com: sudo apt install minisat")
    escolhidos = sys.argv[1:]
    for nome, pasta, resultado in EXECUCOES:
        if not escolhidos or nome in escolhidos:
            print('=' * 60)
            rodar(nome, pasta, resultado)
