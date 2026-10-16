"""Interactive workbenches. Simulation workers contain no Streamlit calls."""
from __future__ import annotations

from dataclasses import asdict
import copy
import json
from pathlib import Path
import threading
import time
import uuid

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from chaoslab.engine import Config
from chaoslab.workbenches import convergence_plan, equivalent_plan, robustness_plan, run_plan, replay_window, ROBUST_RANGES
from chaoslab.storage import ROOT, list_runs, load_result, save_result

TOOLS=['Convergência','Condições equivalentes','Ponte LTspice','Investigar falhas','Robustez','Caderno']


def launch_plan(cases,kind,hypothesis):
    job=dict(state='running',snapshot={},report=None,error=None,saved=[],notebook=None,
             hypothesis=hypothesis,kind=kind,lock=threading.Lock(),cancel=threading.Event())
    def update(snapshot):
        with job['lock']: job['snapshot']=copy.deepcopy(snapshot)
    def worker():
        try:
            report=run_plan(cases,kind,progress=update,cancelled=job['cancel'].is_set)
            job['report']=report
            for case,result in zip(report['cases'],report['results']):
                if result['status']=='complete':
                    job['saved'].append(dict(name=case['name'],path=save_result(result)))
            job['notebook']=record_report(report,hypothesis,job['saved'])
            job['state']=report['status']
        except Exception as exc:
            job['error']=str(exc);job['state']='failed'
    job['thread']=threading.Thread(target=worker,daemon=True,name='chaoslab-workbench')
    job['thread'].start()
    return job


def record_report(report,hypothesis,saved):
    # Adapter to the independently implemented notebook module.
    from chaoslab.notebook import record_experiment
    return record_experiment(hypothesis=hypothesis,configuration=report['plan'],
        result_references=[r['path'] for r in saved],
        conclusion='Execução '+report['status']+'. Comparações descritivas; não certifica convergência nem hardware.',
        status=report['status'],evidence=dict(kind=report['kind'],plan_sha256=report['plan_sha256'],
            cases=report['cases'],comparisons=[{k:v for k,v in c.items() if k!='window_pairs'} for c in report['comparisons']]))


def curve(trace,title,key):
    if not trace.get('t_s'): return
    fig=go.Figure()
    for name in ('x','y'):
        if name in trace: fig.add_trace(go.Scatter(x=np.asarray(trace['t_s'])*1000,y=trace[name],name=name.upper()))
    fig.update_layout(title=title,xaxis_title='Tempo (ms)',yaxis_title='Estado',height=290,
                      margin=dict(l=20,r=20,t=45,b=20),legend=dict(orientation='h'))
    st.plotly_chart(fig,width='stretch',key=key)


@st.fragment(run_every=1)
def job_panel():
    job=st.session_state.get('tools_job')
    if not job: return
    with job['lock']: snapshot=copy.deepcopy(job['snapshot'])
    if job['state']=='running':
        st.progress(float(snapshot.get('overall_fraction',0)),text=snapshot.get('case','Preparando execução…'))
        if st.button('Cancelar bancada',key='cancel_tools'): job['cancel'].set()
        curve(snapshot.get('trace',{}),'Acompanhamento do caso atual','tools_live')
        st.caption('Cancelar preserva os casos concluídos; um caso parcial não é contado como concluído.')
    if job['state']!='running' and not job.get('announced'):
        job['announced']=True
        st.rerun()
    if job['state']=='failed': st.error(job['error'])
    if job.get('report') and job['state']!='running':
        report=job['report']
        if job['state']=='complete':st.success('Bancada concluída e registrada.')
        elif report['status']=='cancelled':st.warning('Bancada cancelada; veja os casos concluídos preservados.')
        else:st.warning('O cálculo retornou resultados, mas houve erro ao registrar. Os dados permanecem em memória e podem ser baixados.')
        show_report(report)
        if job.get('notebook'): st.caption('Caderno: '+str(job['notebook']))


def show_report(report):
    rows=[]
    for case in report['cases']:
        s=case['summary']
        rows.append({'Caso':case['name'],'Estado':case['status'],'Corretas':s['correct_windows'],
            'Janelas':s['total_windows'],'Pico (µA)':s['peak_current_uA'],
            'RMS Y (µA)':s['residual_y_rms_uA'],'RMS D (µA)':s['residual_d_rms_uA'],
            'Alarmes indevidos':s['false_alarm_trajectories']})
    st.dataframe(pd.DataFrame(rows),width='stretch',hide_index=True)
    paired=[]
    for p in report['comparisons']:
        paired.append({'Comparação':p['baseline']+' → '+p['candidate'],'Recuperadas':p['recovered'],
            'Regrediram':p['regressed'],'Saldo':p['net'],'Discordantes':p['discordant'],'Janelas':p['windows']})
    if paired:
        st.dataframe(pd.DataFrame(paired),width='stretch',hide_index=True)
        st.caption('Totais iguais podem esconder discordâncias. Ausência de janelas completas em um horizonte curto não significa 100% de acerto.')
        with st.expander('Margens, pares de janelas e erros no horizonte curto'):
            for p in report['comparisons']:
                st.write(p['baseline']+' → '+p['candidate'])
                st.json(p['short_trace'])
                st.dataframe(pd.DataFrame(p['window_pairs']),width='stretch',hide_index=True)
    if report['results']:
        fig=go.Figure()
        for c,r in zip(report['cases'],report['results']):
            fig.add_trace(go.Scatter(x=np.asarray(r['trace']['t_s'])*1000,y=r['trace']['x'],name=c['name']))
        fig.update_layout(title='Estados X sobrepostos · traçados amostrados',xaxis_title='Tempo (ms)',height=350)
        st.plotly_chart(fig,width='stretch',key='tools_compare_x')
    compact={k:v for k,v in report.items() if k!='results'}
    st.download_button('Baixar plano e comparações',json.dumps(compact,ensure_ascii=False,indent=2).encode(),
                       file_name='chaoslab-bancada.json',mime='application/json',key='tools_download')


def configuration_form(kind,active):
    with st.form('workbench_form'):
        hypothesis=st.text_input('Hipótese do experimento',value='Verificar estabilidade numérica e comparar condições equivalentes.')
        a,b,c=st.columns(3)
        trajectories=int(a.number_input('Trajetórias',1,64,2))
        windows=int(b.number_input('Janelas por trajetória',1,100,1))
        h=float(c.selectbox('Passo inicial (µs)',[5.,2.5,1.25,10.]))
        short=st.checkbox('Somente horizonte curto (sem classificar janelas incompletas)',value=kind=='convergence')
        duration_ms=float(st.number_input('Horizonte curto (ms)',.1,20.,1.,.1)) if short else None
        a,b=st.columns(2)
        profile=a.selectbox('Camadas', ['coordinator','actuator','ideal','nominal','unlimited_sampled'])
        detector=b.selectbox('Fiscal',['effective','quota','off'])
        a,b,c=st.columns(3)
        latency=float(a.number_input('Atraso do coordenador (µs)',0.,1000.,5.))
        tau=float(b.number_input('Filtro do coordenador (µs)',0.,1000.,10.))
        sample=float(c.number_input('Amostragem dos pedidos (µs)',h,1000.,max(h,10.),h))
        a,b,c=st.columns(3)
        budget=float(a.number_input('Orçamento de atuação (µA)',1.,1000.,90.))
        reserve=float(b.number_input('Reserva E (µA)',0.,1000.,5.))
        seed=int(c.number_input('Semente',0,2**31-1,20191))
        mode='policy';scenarios=3;fault='healthy';combined=();fault_start=fault_end=None;ranges_text=None
        if kind=='equivalent':
            mode=st.selectbox('Comparação',['policy','budget'],format_func=lambda x:
                'L2 × comum com tempos iguais' if x=='policy' else 'Teto × ilimitado com a mesma amostragem')
            if mode=='budget': st.caption('Esta ablação usa medição ideal e fiscal desligado nos dois controles; a única diferença pretendida é a restrição de atuação.')
        if kind=='robustness':
            scenarios=int(st.number_input('Cenários pareados',1,12,3))
            fault=st.selectbox('Falha principal',['healthy','bias','dropout','double','starve','replay','stale'])
            combined=tuple(st.multiselect('Falhas simultâneas adicionais',['bias','dropout','double','starve','replay','stale']))
            if fault!='healthy' or combined:
                a,b=st.columns(2)
                fault_start=float(a.number_input('Início da falha (ms)',0.,5000.,12.))/1000
                fault_end=float(b.number_input('Fim da falha (ms)',0.,5000.,30.))/1000
            st.caption('Cada cenário sorteia tempos, tolerâncias, fase de ruído, relógios, entradas e estados iniciais. Cotas/efetiva recebem exatamente o mesmo cenário.')
            with st.expander('Faixas de robustez · mínimo e máximo'):
                ranges_text=st.text_area('Faixas em JSON',json.dumps(ROBUST_RANGES,indent=2),height=240)
                st.caption('Unidades nos nomes: µs, µA, ppm; tolerância relativa e fase em radianos. Distribuição uniforme exploratória, sem probabilidade de fabricação presumida.')
        submit=st.form_submit_button('Executar bancada',type='primary',disabled=active)
    if not submit: return
    try:
        base=Config(dt_us=h,trajectories=trajectories,windows=windows,profile=profile,detector=detector,
            coordinator_delay_us=latency,coordinator_tau_us=tau,sample_period_us=sample,
            budget_uA=budget,reserve_uA=reserve,seed=seed,duration_s=duration_ms/1000 if short else None,
            metrics_warmup_s=0 if short else .03,fault=fault,additional_faults=combined,
            fault_start_s=fault_start,fault_end_s=fault_end,trace_points=1500)
        cases=(convergence_plan(base,(h,h/2,h/4)) if kind=='convergence' else
               equivalent_plan(base,mode) if kind=='equivalent' else
               robustness_plan(base,scenarios,seed,ranges=json.loads(ranges_text),combined_faults=combined))
        st.session_state['tools_job']=launch_plan(cases,kind,hypothesis.strip() or 'Experimento exploratório')
        st.rerun()
    except (ValueError,TypeError) as exc: st.error(str(exc))


def pick_result(key):
    runs=list_runs()
    if not runs: st.info('Execute primeiro um ensaio ou uma bancada.');return None
    by_path={str(r['path']):r for r in runs}
    def label(p):
        r=by_path[p];c=r.get('config',{});s=r.get('summary',{})
        return f"{Path(p).stem} · {c.get('profile')} · {c.get('detector')} · {s.get('correct_windows')}/{s.get('total_windows')}"
    selected=st.selectbox('Execução de origem',list(by_path),format_func=label,key=key)
    return load_result(selected)


def investigator_panel(active):
    from chaoslab.diagnostics import investigate_window
    st.caption('Selecione uma janela. Para inspecionar outra trajetória, o replay refaz a evolução original e verifica os resultados antes de mostrar o recorte.')
    result=pick_result('investigation_source')
    if result is None:return
    if not result['windows']:st.info('Esta execução curta não contém janelas lógicas completas.');return
    a,b=st.columns(2)
    trajectory=int(a.selectbox('Trajetória',sorted({r['trajectory'] for r in result['windows']})))
    window=int(b.selectbox('Janela',sorted({r['window'] for r in result['windows'] if r['trajectory']==trajectory})))
    identity=(result['validation']['final_state_sha256'],trajectory,window)
    replay=st.session_state.get('tools_replay')
    if replay and replay['identity']==identity and replay.get('result'):result=replay['result']
    diagnosis=investigate_window(result,trajectory,window)
    with st.expander('Métricas, eventos e cobertura da janela'):
        st.json({k:v for k,v in diagnosis.items() if k not in ('trace','channels')})
    if st.button('Reproduzir janela com traçado detalhado',disabled=active,key='replay_window'):
        job=dict(identity=identity,result=None,error=None,state='running',cancel=threading.Event())
        def worker():
            try:
                job['result']=replay_window(result,trajectory,window,cancelled=job['cancel'].is_set)
                job['state']=job['result']['status']
            except Exception as exc:job['error']=str(exc);job['state']='failed'
        job['thread']=threading.Thread(target=worker,daemon=True);job['thread'].start()
        st.session_state['tools_replay']=job;st.rerun()
    replay_panel(identity)
    if result['validation'].get('trace_trajectory',0)==trajectory:
        trace=result['trace'];t=np.asarray(trace.get('t_s',[])); mask=(t>=window*.05)&(t<=(window+1)*.05)
        groups=[('Pedidos, cotas e concessões (µA)', ['request_y_uA','request_d_uA','quota_y_uA','quota_d_uA','grant_y_uA','grant_d_uA']),
                ('Correntes aplicadas (µA)',['current_y_uA','current_d_uA','current_e_uA']),
                ('Estado',['x','y']),('Fiscal e reserva',['timer','trip','alarm','reserve'])]
        fig=make_subplots(rows=4,cols=1,shared_xaxes=True,subplot_titles=[x[0] for x in groups])
        for row,(_,channels) in enumerate(groups,1):
            for key in channels:
                if key in trace:fig.add_trace(go.Scatter(x=t[mask]*1000,y=np.asarray(trace[key])[mask],name=key),row=row,col=1)
        fig.update_layout(height=900,legend=dict(orientation='h'));fig.update_xaxes(title_text='Tempo (ms)',row=4,col=1)
        st.plotly_chart(fig,width='stretch',key='investigation_chain')
        st.caption('Pedido → cota → concessão → corrente → estado → alarme → reserva. Sobreposição temporal auxilia o diagnóstico; não demonstra causalidade sozinha.')


@st.fragment(run_every=1)
def replay_panel(identity):
    job=st.session_state.get('tools_replay')
    if not job or job['identity']!=identity:return
    if job['state']=='running':
        st.info('Replay em andamento, preservando condições e evolução originais.')
        if st.button('Cancelar replay'):job['cancel'].set()
    elif job['error']:st.error(job['error'])
    elif st.button('Mostrar replay verificado'):st.rerun()


def bridge_panel():
    from chaoslab import bridge
    st.info('A ponte exporta a referência matemática nominal. Outros perfis só podem ser comparados quando o modelo correspondente estiver explicitamente representado.')
    st.caption('Importe um CSV/TSV exportado pelo LTspice para sobrepor estados no intervalo comum. Sem extrapolar ou equiparar modelos diferentes.')
    result=pick_result('bridge_source')
    if result is None:return
    bridge_controls(bridge,result)


def bridge_controls(bridge,result):
    if st.button('Gerar referência nominal curta',key='bridge_nominal'):
        from chaoslab.engine import run
        reference=run(Config(profile='nominal',detector='off',trajectories=1,windows=1,
                             dt_us=1.25,duration_s=.001,metrics_warmup_s=0,trace_points=1000))
        st.session_state['bridge_reference']=reference
        st.session_state['bridge_reference_path']=save_result(reference)
    if st.session_state.get('bridge_reference') and st.checkbox('Usar referência nominal curta gerada',value=True):
        result=st.session_state['bridge_reference']
    st.write({'Perfil':result['config']['profile'],'Passo Python (µs)':result['config']['dt_us'],
              'Duração simulada (s)':result['timing']['simulated_seconds_per_trajectory']})
    trajectory=result['validation'].get('trace_trajectory',0)
    try:
        manifest=bridge.make_manifest(result,trajectory)
        st.download_button('Baixar contrato e netlist · ZIP',bridge.bundle_zip(manifest),
                           file_name='chaoslab-ltspice.zip',mime='application/zip',key='bridge_zip')
        if st.button('Salvar pacote para abrir no LTspice',key='bridge_export'):
            export=bridge.export_bundle(manifest,ROOT/'chaoslab/bridge_exports'/uuid.uuid4().hex[:12])
            st.session_state['bridge_export']=export
        if st.session_state.get('bridge_export'):st.code(st.session_state['bridge_export']['netlist'])
        with st.expander('Contrato compartilhado e limites do modelo'):st.json(manifest)
    except ValueError as exc:st.warning(str(exc))
    upload=st.file_uploader('Resultado do LTspice · CSV, TSV ou RAW',type=['csv','tsv','txt','raw'],key='bridge_upload')
    if upload:
        try:
            if upload.size>bridge.MAX_BYTES:raise ValueError('Importação limitada a 32 MiB.')
            imported=bridge.import_raw(upload.getvalue()) if upload.name.lower().endswith('.raw') else bridge.import_csv(upload.getvalue())
            comparison=bridge.compare({k:result['trace'][k] for k in ('t_s','x','y')},imported['trace'])
            st.caption('Trajetória Python '+str(trajectory)+'. Parâmetros do arquivo importado não foram verificados automaticamente; confira o contrato da execução LTspice.')
            st.dataframe(pd.DataFrame(comparison['channels']).T,width='stretch')
            over=comparison['overlay'];fig=go.Figure()
            for name in ('x_python','x_ltspice','y_python','y_ltspice'):
                if name in over:fig.add_trace(go.Scatter(x=np.asarray(over['t_s'])*1000,y=over[name],name=name))
            fig.update_layout(title='Python e LTspice · intervalo comum',xaxis_title='Tempo (ms)',yaxis_title='Estado (V)',height=400)
            st.plotly_chart(fig,width='stretch',key='bridge_overlay')
            st.caption(comparison['limitation'])
            logical=bridge.logical_comparison(result,imported['trace'],trajectory)
            st.write('Janelas comparáveis:',logical['compared'],'· Discordâncias:',logical['discordant'])
            if logical['windows']:st.dataframe(pd.DataFrame(logical['windows']),width='stretch',hide_index=True)
            st.caption(logical['assumption'])
            st.download_button('Baixar comparação importada',json.dumps(dict(comparison,source_sha256=imported['source_sha256']),indent=2).encode(),
                               file_name='comparacao-ltspice.json',mime='application/json',key='bridge_comparison')
        except (ValueError,OSError,UnicodeError) as exc:st.error(str(exc))


def notebook_panel():
    from chaoslab import notebook
    entries=notebook.list_entries()
    st.caption('Hipóteses, parâmetros, versões, referências e conclusão. Registros compactos; fontes e resultados antigos não são apagados automaticamente.')
    if not entries:st.info('As bancadas registram seus experimentos automaticamente ao terminar.');return
    st.dataframe(pd.DataFrame(entries),width='stretch',hide_index=True)
    valid=[entry['id'] for entry in entries if entry.get('record_ok')]
    if not valid:return
    identifier=st.selectbox('Registro',valid,key='notebook_record')
    try:
        record=notebook.read_entry(identifier)
        if record['verification']['references_ok']:st.success('Integridade do registro e das referências verificada.')
        else:st.warning('Há referências ausentes ou alteradas. Consulte a verificação abaixo.')
        st.write('Hipótese:',record['hypothesis'])
        st.write('Conclusão:',record['conclusion'] or 'Ainda não registrada.')
        with st.expander('Configuração, versões e evidências'):st.json(record)
        st.download_button('Baixar registro',json.dumps(record,ensure_ascii=False,indent=2).encode('utf-8'),
                           file_name=identifier+'.json',mime='application/json')
        with st.form('notebook_annotation'):
            conclusion=st.text_area('Acrescentar conclusão (preserva o registro original)',max_chars=16000)
            submitted=st.form_submit_button('Salvar nova anotação')
        if submitted:
            if not conclusion.strip():st.warning('Escreva uma conclusão antes de salvar.')
            else:
                notebook.append_conclusion(identifier,conclusion)
                st.success('Anotação salva como novo registro.')
    except (ValueError,OSError,KeyError,TypeError) as exc:st.error(str(exc))


def render_tools():
    st.subheader('Bancadas e integração com o LTspice')
    st.caption('Motor ampliado separado da Etapa 19. Testar ferramentas não equivale a validar a arquitetura elétrica.')
    selection=st.selectbox('Ferramenta',TOOLS,key='tools_selection')
    main_job=st.session_state.get('chaoslab_job',{})
    tool_job=st.session_state.get('tools_job',{})
    replay=st.session_state.get('tools_replay',{})
    active=any(j.get('state')=='running' for j in (main_job,tool_job,replay))
    try:
        batch=json.loads((ROOT/'experiments/ltspice-caos/etapa19/progresso.json').read_text(encoding='utf-8'))
        active=active or batch.get('status')=='running'
    except (OSError,ValueError):pass
    if selection in ('Convergência','Condições equivalentes','Robustez'):
        kind={'Convergência':'convergence','Condições equivalentes':'equivalent','Robustez':'robustness'}[selection]
        configuration_form(kind,active);job_panel()
    elif selection=='Ponte LTspice':bridge_panel()
    elif selection=='Investigar falhas':investigator_panel(active)
    else:notebook_panel()
