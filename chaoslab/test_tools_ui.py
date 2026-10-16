"""Opt-in real Streamlit worker smoke, isolated from research persistence.

Run: python -m chaoslab.test_tools_ui
Requires the normal host on Windows (AppTest uses localhost sockets).
"""
from unittest.mock import patch
import json

from streamlit.testing.v1 import AppTest


def main():
    wrapper='''
import streamlit as st
from chaoslab.tools_ui import render_tools
render_tools()
'''
    with patch('chaoslab.tools_ui.save_result',return_value='test-memory-only'), \
         patch('chaoslab.tools_ui.record_report',return_value='test-notebook-memory-only'):
        app=AppTest.from_string(wrapper,default_timeout=60).run()
        assert not app.exception,[e.value for e in app.exception]
        button=next(b for b in app.button if b.label=='Executar bancada')
        button.click().run()
        assert not app.exception,[e.value for e in app.exception]
        job=app.session_state['tools_job']
        job['thread'].join(timeout=60)
        assert not job['thread'].is_alive()
        app.run()
        assert not app.exception,[e.value for e in app.exception]
        assert job['state']=='complete',job['error']
        assert len(job['report']['cases'])==3
        assert len(app.get('plotly_chart'))>=1
        assert len(job['saved'])==3
        assert job['notebook']=='test-notebook-memory-only'
        for selection in ('Condições equivalentes','Ponte LTspice','Investigar falhas','Robustez','Caderno'):
            app.selectbox(key='tools_selection').select(selection).run()
            assert not app.exception,(selection,[e.value for e in app.exception])
    print(json.dumps(dict(status='passed',checks=['convergence form','real fixed-step worker',
          'three step sizes','paired tables','plot rendering','mocked persistence'],scientific_results_saved=0)))


if __name__=='__main__':main()
