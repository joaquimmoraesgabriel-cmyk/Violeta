"""Ensaio definido apos fixar a revisao 2; nao muda seus parametros."""
from pathlib import Path
import preparar_mlc as generator

ROOT=Path(__file__).resolve().parent
generator.SEQUENCE=list(reversed(generator.SEQUENCE))
steps=generator.PILLAR+[
    '.param caso=0',
    '.param x_inicial=if(mod(caso,2),0.37,-0.37) y_inicial=-0.2',
    '.param desvio=if(mod(floor(caso/2),2),0.0037,-0.0037)',
    '.param erro_sensor=if(floor(caso/4),0.000137,-0.000137)',
    '.param passo=1.25u',
    '.step param caso 0 7 1',
]
source=generator.make_deck('* Revisao 2: verificacao nova; ordem reversa e parametros nao usados no ajuste.',steps)
source=source.replace('MLC_base.inc','MLC_base_v2.inc')
(ROOT/'MLC_AND_verificacao_nova_v2.cir').write_text(source,encoding='utf-8')
print('8 novas trajetorias: sequencia reversa, novos estados/desvios/erros de referencia, passo de 1.25 us.')
