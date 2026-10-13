"""Anexa conclusao revisada e evidencia; preserva o historico das etapas."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent
v=json.loads((ROOT/'verificacao_entrega.json').read_text(encoding='utf-8'))
assert v['trajetorias']==64 and v['janelas_conferidas_raw']==1088
conclusion=(ROOT/'CONCLUSAO_REVISADA.txt').read_text(encoding='utf-8').strip()
marker='## Etapa 18 — Fiscalizacao das cotas e recuperacao local'
block=f'''\n\n{marker}

{conclusion}

Executadas 64 trajetorias completas novas (1088 janelas), com 56 da
matriz V1/controles/refinamento e oito da confirmacao V2. Comparacao
logica conferida tambem diretamente nos RAWs; plano e adendos preservados.

- [Relatorio completo](etapa18/ETAPA18_RESULTADOS.txt)
- [Comparacao visual](etapa18/comparacao_etapa18.svg)
- [Diagnostico da confirmacao](etapa18/diagnostico_confirmacao.svg)
- [Contrato para proximos modelos](etapa18/INTERFACE_PARA_PROXIMOS_MODELOS.txt)
- [Verificacao da entrega](etapa18/verificacao_entrega.json)
- [Errata da integracao de indicadores](etapa18/ERRATA_INTEGRACAO_INDICADORES.txt)
- [Correcao dos dados anteriores](etapa18/correcao_fracoes_anteriores.json)

Corrigido o helper compartilhado: integrar indicadores booleanos exige
conversao a float. Recalculadas 162 trajetorias unicas, corrigindo 184
registros das Etapas16/17 e a tabela impressa da Etapa16, com backups.
A referencia saudavel superava 91 uA em 62.15% do tempo (antes 31.12%).
Contagens de janelas, picos, alarmes, RMS e variacao total de g(x)
foram preservados.

Mantida a ressalva: 90 uA e cota de atuacao; controle/metadados ainda
comportamentais, 45 subpilares conceituais, nenhuma PCB ou chip especifico
validado. Os resultados desta matriz nao substituem a matriz 198/272 anterior.
'''
for name in ['PIRAMIDE_CANDIDATA.md','PESQUISA_HIPOTESE_PILARES.md']:
    p=ROOT.parent/name;text=p.read_text(encoding='utf-8')
    assert marker not in text,f'Etapa ja consolidada: {name}'
    p.write_text(text.rstrip()+block,encoding='utf-8')
print('Dois diarios de pesquisa atualizados com a etapa18.')
