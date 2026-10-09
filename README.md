# Docito — orçamentos e projetos de doces

Aplicativo em https://docito.streamlit.app/. O acesso exige Google e é autorizado no servidor somente para `gerusa041188@gmail.com` e `julio.goiano@gmail.com`. A lista fica em `docito_auth.py`; não existe cadastro, senha local ou recuperação de senha.

## Ativar o login Google

O código bloqueia todos os dados enquanto o OAuth não estiver configurado. O botão de login permanece desabilitado até haver credenciais válidas nos Secrets. Não publique credenciais no GitHub nem compartilhe o segredo em conversas.

1. No Google Cloud Console, configure a tela de consentimento e crie um cliente OAuth **Aplicativo da Web**. Use apenas os escopos `openid`, `email` e `profile`. Se o aplicativo estiver no modo de teste, adicione os dois e-mails como usuários de teste.
2. Cadastre o URI de redirecionamento exatamente como `https://docito.streamlit.app/oauth2callback`.
3. No Streamlit Community Cloud, abra as configurações do aplicativo, em **Settings > Secrets**. Preserve `SUPABASE_URL` e `SUPABASE_KEY` existentes e acrescente os blocos `[auth]` e `[auth.google]` conforme `.streamlit/secrets.example.toml`. Preencha o `client_id` e `client_secret` do Google. Gere um `cookie_secret` privado e aleatório, por exemplo com `python -c 'import secrets; print(secrets.token_urlsafe(48))'` em seu computador. Não use o texto do exemplo.
4. Salve os Secrets e reinicie o aplicativo. Teste o login com cada conta autorizada e com uma conta diferente. Uma conta diferente deve ver apenas a tela de boas-vindas e a opção de trocar a conta.

Referências oficiais: [autenticação Streamlit](https://docs.streamlit.io/develop/concepts/connections/authentication), [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect).

O Streamlit/Authlib valida o token Google e o fluxo OAuth. A aplicação também verifica e-mail confirmado, emissor, público do token, sujeito e validade antes das telas privadas, callbacks e operações no banco. Ao sair ou trocar de identidade, o estado da sessão é limpo. A validade do token é verificada novamente a cada execução; sessões expiradas não leem nem salvam dados.

## Doces e preços

A engrenagem no topo abre o catálogo preenchido com os 20 produtos e as quatro faixas de preços originais. Permite adicionar, renomear, excluir e alterar preços por cento, unidade ou kg. A seção **Preços por quantidade** permite alterar as faixas progressivas. Produtos sem faixa usam cálculo proporcional.

As configurações são persistidas no Supabase e valem para as duas contas. Salvamentos simultâneos usam revisão para evitar sobrescrever alterações de outra sessão. Cada item novo guarda sua regra de preço; itens antigos mantêm a tabela original. Excluir ou renomear um doce não altera orçamentos salvos.

A migração em `supabase/migrations/20261009153118_private_access_and_catalogue.sql` foi aplicada ao projeto `orcamentos-docito`. Ela cria o catálogo, habilita RLS, restringe permissões e gera números de orçamento com uma sequência atômica. Orçamentos antigos são mantidos.

## Instalação e verificação

Use Python 3.12 ou 3.13 (a hospedagem usa 3.13). `requirements.in` declara as dependências diretas e as restrições de compatibilidade; `requirements.txt` fixa também as versões transitivas utilizadas no deploy. A biblioteca Authlib está incluída para o login Google. `multidict` usa a versão 7.0.0 compatível com os dois ambientes; `pyarrow` usa 24.0.0, pois o Community Cloud bloqueia 25.0.1 por falha de segmentação.

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/project-files.test.cjs
streamlit run app.py
```

Sem credenciais OAuth, a execução local também permanece na tela pública de boas-vindas. O URI de produção não deve ser alterado nos Secrets do aplicativo publicado. Para desenvolvimento do login em localhost, use um cliente OAuth separado e ajuste o URI no código da cópia local; não flexibilize o controle do aplicativo publicado.

Projetos `.json` antigos continuam aceitos. O formato novo guarda cada imagem uma vez e reduz o tamanho do arquivo. A biblioteca de artes permanece neste navegador e também pode ser exportada.
