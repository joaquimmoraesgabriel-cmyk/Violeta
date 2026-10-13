# Conferência independente de corrente da etapa 12

Nos oito ensaios, nenhum pico da soma externa das correntes excedeu o critério de 100,005 µA. O maior foi 100.000095931 µA. O monitor interno chegou a 100.009812741 µA. Assim, o excesso indicado por esse monitor não foi confirmado como corrente aplicada acima do critério nestas execuções. A classificação dos outros casos antigos continua pendente de conferência independente.

Repetimos o coordenador comum no perfil AB exige mais, com falha silenciosa do topo e dois estados iniciais. São oito trajetórias: monitor direto e sondas ideais de 0 V, cada um com vntol de 1e-9 e 1e-11; reltol=1e-6, abstol=1e-12, passo máximo=2,5 µs. A referência é o mesmo caso de COORD_falha4_AB.

A soma abaixo é calculada fora do LTspice a partir das correntes salvas no RAW, no mesmo instante. Ela não depende da fonte B que exibe V(orcamento). Nos arquivos com sondas, também conferimos a soma das correntes das fontes de 0 V contra as fontes de atuação. Todos os logs precisam conter as 17 janelas completas e os RAW chegar a 0,85 s.

| Medicao | vntol | x inicial | Pico monitor (µA) | Soma das correntes (µA) | Diferenca maxima (µA) | Acertos |
|---|---|---|---|---|---|---|
| Direta | 1e-09 | -0.37 | 100.006844150 | 100.000004750 | 0.009411451 | 16/17 |
| Direta | 1e-09 | +0.37 | 100.008590380 | 100.000095931 | 0.009672021 | 16/17 |
| Sondas de 0 V | 1e-09 | -0.37 | 100.009347079 | 100.000004750 | 0.009411451 | 17/17 |
| Sondas de 0 V | 1e-09 | +0.37 | 100.009812741 | 100.000004750 | 0.009810744 | 16/17 |
| Direta | 1e-11 | -0.37 | 99.999997474 | 100.000004750 | 0.009596874 | 16/17 |
| Direta | 1e-11 | +0.37 | 99.999997474 | 100.000004750 | 0.009672021 | 16/17 |
| Sondas de 0 V | 1e-11 | -0.37 | 100.000623206 | 100.000004750 | 0.009898940 | 16/17 |
| Sondas de 0 V | 1e-11 | +0.37 | 99.999997474 | 100.000004750 | 0.010134954 | 16/17 |

As correntes do RAW têm precisão de armazenamento de 32 bits. Os extremos de .meas são registrados separadamente; pequenos resíduos da ordem de 0,00001 µA na soma externa não sustentam uma alegação de ultrapassagem física. A tolerância de verificação continua 0,005 µA e a capacidade nominal continua 100 µA.

Fontes de 0 V são equivalentes elétricos ideais, mas sua inclusão muda as equações resolvidas e pode mudar a trajetória numérica de um sistema sensível. Portanto comparamos os picos e classificações de cada execução; não exigimos identidade ponto a ponto entre execuções distintas.

A documentação da Analog Devices explica as limitações das referências a correntes em fontes comportamentais: [Behavioral Sources, Parameters and Expression Evaluation](https://ez.analog.com/cfs-file/__key/docpreview-s/00-00-01-54-13/todaysslidedeck6141655150841730.pdf). O resultado desta conferência está em conferencia_medidores.json. A conclusão deve distinguir discrepância no monitor, resíduo numérico da solução e uma corrente aplicada acima do critério; não extrapolamos estes oito casos a todas as execuções antigas.
