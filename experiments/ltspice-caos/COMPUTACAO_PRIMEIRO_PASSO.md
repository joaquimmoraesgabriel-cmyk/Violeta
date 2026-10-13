# Aplicar um bit a um circuito caotico

Abra Chua_entrada_bit.cir no LTspice (filtro All Files) e clique em Run.

O LTspice executa duas simulacoes automaticamente, com a mesma condicao inicial:

- bit=0: nenhuma corrente adicional.
- bit=1: um pulso de corrente de 20 microampere entra em v1 de 10 a 11 milissegundos.

## Ver a entrada e a resposta

Adicione V(v1), V(v2) e V(entrada) ao grafico. V(entrada) e um marcador de 0/1 V para mostrar quando o bit foi aplicado; quem altera o circuito e a fonte de corrente Bentrada.

Ha duas curvas por sinal, uma por execucao. Clique com o botao direito no grafico e procure View > Step Legend para identificar os passos, ou use a opcao Select Steps para mostrar apenas um deles (os menus podem variar entre versoes).

Antes de 10 ms, as respostas devem coincidir, pois as simulacoes possuem o mesmo estado inicial. Depois do pulso, compare as respostas. A separacao das curvas mostra que a entrada afetou a dinamica, mas nao demonstra sozinha caos nem uma computacao confiavel.

## Ler os numeros

Use View > SPICE Error Log (normalmente Ctrl+L). Procure as tabelas media_v1, rms_v1, media_v2 e amostra_v2. Cada medida deve ter duas linhas correspondentes aos dois passos de bit.

- media_v1: tensao media em v1 de 12 a 15 ms.
- rms_v1: valor eficaz de v1 nessa janela.
- media_v2: tensao media em v2 nessa janela.
- amostra_v2: tensao em v2 aos 12 ms.

Esses numeros sao candidatos a uma leitura da resposta. Se uma medida f0 para bit=0 e f1 para bit=1 forem diferentes, podemos experimentar um limiar T=(f0+f1)/2. Se f1>f0, valores acima de T seriam classificados como 1; se f1<f0, a regra se inverte. Duas simulacoes servem para demonstracao e calibracao, nao para provar confiabilidade.

## O que estamos computando

Estamos investigando uma codificacao e leitura de um bit: entrada -> dinamica do circuito -> medida -> classificacao. O circuito transforma a entrada em uma resposta temporal; a regra de leitura ainda precisa ser escolhida a partir dos resultados.

O proximo passo e repetir com pequenas variacoes de estado inicial, amplitude e instante do pulso para verificar se uma mesma regra ainda acerta. Um circuito caotico pode amplificar variacoes indesejadas tambem. Para processar uma sequencia de bits, precisamos definir como reiniciar ou controlar o estado entre entradas; este arquivo usa simulacoes independentes.

Este experimento usa um modelo ideal de Chua. Nao implementa ainda uma porta AND/XOR nem um computador completo. Os resultados ainda precisam ser conferidos na sua instalacao do LTspice.
