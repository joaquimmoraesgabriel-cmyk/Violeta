"""Relatorio deterministico a partir de resultados efetivamente completos."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parent
PROFILES={0:'Equilibrado',1:'AB',2:'CD',3:'Alta demanda'}
FAULTS={0:'Saudável',1:'Parada sem heartbeat',2:'Atraso de 500 µs',3:'Inversão',4:'Silêncio com heartbeat'}

def main():
    ts=json.loads((ROOT/'trajetorias.json').read_text())
    ss=json.loads((ROOT/'resumo.json').read_text())
    assert len(ts)==64, 'Nao emitir conclusao de lote incompleto'
    protected=[t for t in ts if t['detector']]
    healthy=[t for t in protected if t['falha_coord']==0]
    bykey={(t['perfil'],t['falha_coord'],t['detector'],t['passo'],t['x_inicial']):t for t in ts}
    lines=['# Etapa 15 — extensão dos atuadores não ideais', '',
           '64 trajetórias completas de 0,85 s, 1.088 janelas lógicas. O circuito e seus parâmetros foram preservados da Etapa 14. Foram ampliados os perfis e falhas e reduzido o passo máximo de 1,25 para 0,625 µs. As contagens são resultados determinísticos desta matriz; não estimativas estatísticas de confiabilidade.', '',
           '## Resultado com reserva', '',
           '| Perfil | Comando do topo | Acertos em 1,25 µs | Acertos em 0,625 µs | Corretas nos dois passos | Classificações diferentes |',
           '|---|---|---:|---:|---:|---:|']
    for s in ss:
        if not s['detector']:continue
        counts=s['acertos_por_passo']
        lines.append(f"| {PROFILES[s['perfil']]} | {FAULTS[s['falha']]} | {counts[str(1.25e-6)]}/34 | {counts[str(.625e-6)]}/34 | {s['corretas_ambos_passos']}/34 | {s['divergencias_passos']} |")
    lines += ['',f"Com reserva: {sum(t['corretas'] for t in protected)}/884 janelas, {sum(t['corretas']==17 for t in protected)}/52 trajetórias inteiramente corretas. Nos testes saudáveis: {sum(t['corretas'] for t in healthy)}/272 janelas. Alarmes anteriores à falha ou em condição saudável: {sum(t['alarme_indevido'] for t in protected)} de 52 trajetórias protegidas.", '',
              '## Comparação pareada com a reserva desligada', '',
              'Esta comparação usa somente 1,25 µs e os mesmos dois estados iniciais. Os resultados do passo menor não são misturados à referência.', '',
              '| Perfil | Falha | Sem reserva | Com reserva | Janelas recuperadas | Janelas que pioraram |',
              '|---|---|---:|---:|---:|---:|']
    comparisons=[]
    for p in [1,3]:
        for f in [4,2,3]:
            originals=[bykey[p,f,0,1.25e-6,x] for x in [-.37,.37]]
            replacements=[bykey[p,f,1,1.25e-6,x] for x in [-.37,.37]]
            gained=lost=0
            for a,b in zip(originals,replacements):
                a_fail,b_fail=set(a['janelas_falhas']),set(b['janelas_falhas'])
                gained+=len(a_fail-b_fail);lost+=len(b_fail-a_fail)
            a,b=sum(t['corretas'] for t in originals),sum(t['corretas'] for t in replacements)
            lines.append(f'| {PROFILES[p]} | {FAULTS[f]} | {a}/34 | {b}/34 | {gained} | {lost} |')
            comparisons.append(dict(perfil=p,falha=f,sem_reserva=a,com_reserva=b,recuperadas=gained,pioraram=lost))
    (ROOT/'comparacoes.json').write_text(json.dumps(comparisons,indent=2),encoding='utf-8')
    lines += ['', '## Corrente e consistência da medição', '',
              'A corrente principal é calculada externamente como a soma dos módulos das quedas de tensão diretamente nos dois shunts, divididas por 1 kΩ. Foram salvas também correntes dos resistores, sondas de 0 V e monitores comportamentais. O critério permanece 100,005 µA, incluindo partida e transientes; 90 µA é o alvo operacional.', '',
              '| Método | Maior pico no lote (µA) | Trajetórias acima de 100,005 µA |',
              '|---|---:|---:|']
    for label,field,flag in [('Tensões diretas nos shunts','pico_tensoes_uA','corrente_falha_tensoes'),('Correntes dos resistores','pico_resistores_uA','corrente_falha_resistores'),('Sondas de 0 V','pico_sondas_uA','corrente_falha_sondas')]:
        lines.append(f"| {label} | {max(t[field] for t in ts):.6f} | {sum(t[flag] for t in ts)} |")
    lines += ['', f"Maior diferença pontual entre soma por tensões e soma por resistores: {max(t['diferenca_resistores_uA'] for t in ts):.6f} µA; entre tensões e sondas: {max(t['diferenca_sondas_uA'] for t in ts):.6f} µA; entre tensões e monitores: {max(t['diferenca_medidor_uA'] for t in ts):.6f} µA. Essas diferenças pontuais não são a diferença entre os picos. Os valores em RAW usam armazenamento de 32 bits. Um excesso indicado por apenas um método deve ser auditado; nenhuma linha original é apagada.", '',
              '## Detecção', '',
              '| Perfil | Falha | Primeiro alarme: mínimo–máximo (µs) |', '|---|---|---:|']
    for s in ss:
        if s['detector'] and s['falha']:
            a,b=s['latencia_min_us'],s['latencia_max_us']
            label=f'{a:.3f}–{b:.3f}' if a is not None else 'Não detectada'
            lines.append(f"| {PROFILES[s['perfil']]} | {FAULTS[s['falha']]} | {label} |")
    lines += ['', 'Para as falhas temporárias, o intervalo acima é medido a partir de 343,35 ms. Para o atraso permanente, é o instante desde o início, incluindo a inibição inicial de 2 ms; não equivale à latência de cada mudança de comando. Alarme não significa recuperação lógica. O estado de reserva permanece retido e não há rearme automático.', '',
              '## Janelas que falharam com reserva', '',
              '| Arquivo | Caso | Passo (µs) | x inicial | Janelas (índice 0–16) | Menor margem de x (V) |',
              '|---|---:|---:|---:|---|---:|']
    failures=[t for t in protected if t['corretas']<17]
    for t in failures:
        lines.append(f"| {t['arquivo']} | {t['caso']} | {t['passo']*1e6:g} | {t['x_inicial']} | {', '.join(map(str,t['janelas_falhas']))} | {t['margem_minima']:.6g} |")
    if not failures:lines.append('| Nenhuma neste lote | — | — | — | — | — |')
    lines += ['', 'Cada janela corresponde ao bloco de 50 ms indicado pelo índice, com leitura de 30 a 49 ms dentro do bloco. Um único valor com sinal errado reprova a janela. O CSV preserva a margem de cada janela, inclusive quando os passos discordam.', '',
              '## Alcance da evidência e placa virtual', '',
              'A falha é aplicada ao comando do topo. O cálculo local, a alimentação e os sensores permanecem disponíveis. A reserva compartilha sensores e atuadores e não representa redundância física completa. As guardas ideais de sinal e capacidade continuam antes da atuação; a inversão pode ser bloqueada por essa guarda. Portanto, o ensaio não atribui toda proteção ao limitador não ideal.', '',
              'Os amplificadores são UniversalOpAmp2 genéricos. Medição diferencial, soma de módulos, multiplicação, cálculo local, alimentação e chave ainda têm idealizações. O lote não inclui chips selecionados, térmica, acoplamentos de trilhas, ruído estatístico, falha da reserva ou do próprio atuador. A pirâmide completa de sensores adaptativos não foi integrada.', '',
              'A concordância entre duas classificações lógicas não demonstra convergência ponto a ponto. Falhas e divergências devem guiar o próximo experimento. A passagem à placa virtual dependerá da realização dos blocos, análise de estabilidade e alimentação, tolerâncias e modelos de interconexão e térmica.', '',
              '## Evidências e reprodução', '',
              'preparar_etapa15.py gera a matriz; executar.ps1 executa os decks listados em lotes.json (Slot/Slots distribuem decks entre processos). analisar_etapa15.py valida logs e RAW completos e produz trajetorias.json, resultados.csv e resumo.json; gerar_relatorio.py produz este documento e comparacoes.json. Os RAW e logs permanecem junto dos circuitos.', '',
              'Modelos copiados sem alteração da Etapa 14 (SHA-256):', '']
    for file in ['MLC_circuito_reserva.inc','atuadores_etapa14.inc','UniversalOpAmp2.lib']:
        data=(ROOT/file).read_bytes()
        assert data==(ROOT.parent/'etapa14'/file).read_bytes()
        lines.append(f'- {file}: `{hashlib.sha256(data).hexdigest()}`')
    (ROOT/'ETAPA15_RESULTADOS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Relatorio gerado para 64 trajetorias verificadas.')

if __name__=='__main__':main()
