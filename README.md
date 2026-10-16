# Violeta · ChaosLab

Laboratório local de pesquisa da pirâmide de controle caótico: Python/NumPy para
cálculo em passos fixos e Streamlit para acompanhar curvas e janelas lógicas.

Neste computador, o ambiente Python já está instalado. Dê dois cliques em
`Abrir-ChaosLab.cmd`: o navegador abrirá quando o servidor estiver pronto.
Também é possível executar `./Iniciar-ChaosLab.ps1` no PowerShell e abrir
<http://127.0.0.1:8501>.

Se iniciar o servidor manualmente, mantenha a janela do terminal aberta.
Para encerrá-lo, use `Ctrl+C` nesse terminal. Fechar a aba do navegador não
apaga os resultados. Para consultar os ensaios, abra **Resultados** e clique
em **Atualizar execuções salvas**.

Instalação em outro ambiente, metodologia e reprodução estão em
[chaoslab/GUIA.txt](chaoslab/GUIA.txt).

- [Motor matemático](chaoslab/core.py) — RK4 da planta, controles amostrados e RC exato sob ZOH.
- [Painel](chaoslab/app.py) — execução em memória, gráficos ao vivo e comparação de resultados.
- [Lote da Etapa 19](chaoslab/stage19.py) — protocolo registrado, retomada e proveniência.
- [Novas bancadas](chaoslab/TOOLS.txt) — convergência, condições equivalentes, ponte LTspice, investigação de falhas, robustez e caderno automático; disponíveis na aba **Ferramentas**.
- [Pesquisa LTspice](experiments/ltspice-caos) — fontes, parâmetros, logs e métricas das etapas anteriores.
- [Retenção de dados](experiments/ltspice-caos/manutencao_armazenamento/NOTA_RETENCAO.txt) — limpeza autorizada e limites dos extratos.

10.000 janelas significam 500 trajetórias × 20 blocos de 50 ms, com estado contínuo
entre blocos de cada trajetória. O modo personalizado também aceita uma trajetória
longa; seu custo é diferente. Passos fixos eliminam a adaptação da malha pelo
observador, mas ainda exigem estudo de convergência. O modelo não valida uma PCB
nem substitui modelos físicos de componentes no LTspice.

O armazenamento de novas execuções é limitado a 512 MB, com reserva de 10 GB
livres. Formas de onda completas e ambientes de dependências não entram no Git.
