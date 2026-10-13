from preparar_etapa17 import make,manifest

if __name__=='__main__':
    manifest('lotes_topo.json',[make(f'{label}_f{fault}',arch,fault)
        for fault in [4,2,3] for label,arch in [('C_comum',0),('G_emprestimo',2)]])
    manifest('lotes_falhas_recursos.json',[
        make('G_super_queda',2,steps=(.625e-6,),falha_super=1),
        make('G_super_duplo',2,steps=(.625e-6,),falha_super=3),
        make('G_super_enviesado',2,steps=(.625e-6,),falha_super=4),
        make('G_super_atraso',2,steps=(.625e-6,),falha_super=2),
        make('G_grupo_ABC_queda',2,4,steps=(.625e-6,),alvo_topo=1),
        make('G_grupo_D_queda',2,4,steps=(.625e-6,),alvo_topo=2)])
    manifest('lotes_refinamento.json',[
        make('R_C_comum',0,steps=(.3125e-6,)),
        make('R_G_emprestimo',2,steps=(.3125e-6,))])
    print('Expansao: 24 topo + 12 recursos/grupos + 4 terceiro passo = 40 trajetorias.')
