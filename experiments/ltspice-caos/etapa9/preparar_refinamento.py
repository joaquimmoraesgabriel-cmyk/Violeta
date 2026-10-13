from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
main=json.loads((ROOT/'casos_selecao.json').read_text())
refs=[]
for c in main:
    if c['perfil'] not in ['saudaveis','quatro_falhas','erro_comum','ruido_alto'] or c['politica_selecao'] not in ['nove_fixos','adaptativo']:continue
    name=c['nome']+'_ref'
    text=(ROOT/(c['nome']+'.cir')).read_text().replace('passo=5u','passo=2.5u')
    (ROOT/(name+'.cir')).write_text(text,encoding='utf-8')
    (ROOT/(name+'_supervisor.json')).write_text((ROOT/(c['nome']+'_supervisor.json')).read_text(),encoding='utf-8')
    refs.append(dict(c,nome=name,passo_us=2.5,original=c['nome']))
(ROOT/'casos_refinamento.json').write_text(json.dumps(refs,indent=2),encoding='utf-8')
print('Oito decks de refinamento: 16 trajetorias adicionais.')
