from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'comparacoes.json').read_text(encoding='utf-8'))
checked=json.loads((ROOT/'verificacao_entrega.json').read_text(encoding='utf-8'))
assert checked['aprovado']
f=data['familias']
s={x['arquivo']:x for x in json.loads((ROOT/'resumo.json').read_text(encoding='utf-8'))}
marker='## Etapa 17 — coordenador associado a E'
block='\n\n'+marker+'\n\n'
block+=f"Concluídas {checked['trajetorias_novas']} trajetórias novas no LTspice, com orçamento operacional de 90 µA incluindo E (até 5 µA). "
block+='Comparação funcional de coordenador comum e grupos ABC / D+E; cotas com transporte de 20 µs e filtro de 50 µs. '
block+='Cotas complementares e arbitragem única impedem concessões duplicadas.\n\n'
block+='| Arquitetura | Janelas corretas | Corretas nos dois passos |\n|---|---:|---:|\n'
for k,label in [('referencia','Referência anterior'),('comum_E','Comum com supervisor E'),('grupos_E','Grupos com empréstimo e supervisor E')]:
    v=f[k];block+=f"| {label} | {v['corretas']}/272 | {v['comuns']}/136 |\n"
block+='\nO saldo de uma janela no novo comum não demonstra ganho robusto; a sensibilidade ao terceiro passo permanece. A coordenação comum segue como base de pesquisa, com verificação da idade e da coerência das cotas ainda pendente.\n'
block+='\nControle saudável 45/45: '+str(s['G_fixo_f0']['corretas'])+'/68. '
block+=f"Ajuste exploratório L2: {s['L2_filtrado']['corretas']}/68 com filtro e {s['L2_instantaneo']['corretas']}/68 com cotas ideais instantâneas. "
block+='O ajuste foi motivado pelo déficit em Y, sem acesso à resposta AND; não recebeu a matriz completa de falhas nem terceiro passo.\n\n'
block+=f"Corrente: pico físico {checked['pico_fisico_uA']:.6f} µA; critério herdado <=100,005 µA. "
block+='Falhas de heartbeat e soma de cotas têm fallback 45/45. Uma cota válida, mas enviesada, exige verificação distinta da discrepância entre comando e atuação. '
block+='O supervisor continua sendo uma dependência compartilhada dos grupos.\n\n'
block+='Os resultados não validam chips/coordenadores fisicamente independentes, a pirâmide completa de 45 sensores ou PCB. '
block+='Modelos antigos e ondas de referência foram preservados. '
block+='Relatório e evidências: [Etapa 17](etapa17/ETAPA17_RESULTADOS.txt), [comparação](etapa17/comparacao_coordenadores.svg), '
block+='[verificação](etapa17/verificacao_entrega.json).\n'
for name in ['PIRAMIDE_CANDIDATA.md','PESQUISA_HIPOTESE_PILARES.md']:
    p=ROOT.parent/name
    old=p.read_text(encoding='utf-8')
    if marker in old:raise RuntimeError('Secao ja existe; revisar antes de alterar: '+name)
    p.write_text(old.rstrip()+block,encoding='utf-8')
print('Historico da pesquisa atualizado, preservando as secoes anteriores.')
