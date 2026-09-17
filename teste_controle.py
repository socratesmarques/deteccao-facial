from controle_acesso import ControleAcesso

# Configure a linha GPIO usada pelo seu relé antes do teste.
controle = ControleAcesso(
    gpio_chip="/dev/gpiochip0",
    gpio_linha=-1,
    ativo_alto=False,
    tempo_acionamento=1.0,
)

if not controle.conectar():
    print(controle.ultimo_erro)
    raise SystemExit(1)

input("GPIO pronto. Pressione ENTER para acionar o relé...")

if controle.abrir():
    print("Relé acionado e retornou ao estado inativo.")
else:
    print(controle.ultimo_erro)

controle.desconectar()
