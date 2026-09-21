"""Permissões administradas separadamente do perfil biométrico."""
from configuracoes import carregar_configuracoes, salvar_configuracoes
from perfil_store import normalizar_nome


def definir_autorizacao(nome, autorizado):
    config = carregar_configuracoes()
    nomes = set(config['pessoas_autorizadas'])
    nome = normalizar_nome(nome)
    if autorizado:
        nomes.add(nome)
    else:
        nomes.discard(nome)
    config['pessoas_autorizadas'] = sorted(nomes)
    if not salvar_configuracoes(config):
        raise OSError('Não foi possível salvar a autorização. Confira as permissões de config.json.')
