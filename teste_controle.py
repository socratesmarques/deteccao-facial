from controle_acesso import ControleAcesso

controle = ControleAcesso()

if controle.conectar():
    input(
        "ESP32 conectado. "
        "Pressione ENTER para abrir..."
    )

    controle.abrir()

    input(
        "Comando enviado. "
        "Pressione ENTER para sair..."
    )

controle.desconectar()