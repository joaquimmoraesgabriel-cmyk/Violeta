# Controle de capacidade e dinâmica — alta demanda saudável

O filtro de comando de 2 µs, a partida, a lógica e o detector são mantidos. O atuador ideal substitui o amplificador e o limitador realimentado por uma fonte de corrente; sua capacidade é imposta pela guarda de comando. Este controle não valida um limitador físico.

| Realização | Acertos 1,25 µs | Acertos 0,625 µs | Corretas nos dois passos | Classificações diferentes | Pico shunts (µA) |
|---|---:|---:|---:|---:|---:|
| Circuito não ideal, 90 µA | 26/34 | 21/34 | 16/34 | 15 | 90.015769 |
| Atuador ideal com RC, 90 µA | 25/34 | 25/34 | 20/34 | 10 | 90.000153 |
| Atuador ideal com RC, 100 µA | 28/34 | 28/34 | 23/34 | 10 | 100.000203 |

As diferenças entre os passos são de classificação de janelas, não uma estimativa de erro ponto a ponto. Mudar a capacidade também muda a trajetória do sistema; estes controles não sustentam extrapolação monotônica de acertos para outros limites ou perfis.

A comparação circuito/ideal em 90 µA avalia conjuntamente a dinâmica dos amplificadores e do limitador. A comparação ideal 90/100 µA altera a capacidade. O cálculo local, os sensores favoráveis, as guardas e o RC de comando permanecem presentes. Os resultados não isolam erros de sensores nem testam outra lei de controle.

Evidências: ABL_ideal_90/100.cir, respectivos logs e RAW, ablacao_trajetorias.json e ablacao_janelas.csv. As oito trajetórias (136 janelas) não fazem parte das 64 trajetórias da matriz principal.
