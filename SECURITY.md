# Segurança da Docito

Revisão em 9 de outubro de 2026 do repositório `juliocesarr77/orcamento-docito` e do projeto Supabase `orcamentos-docito`.

## Correções aplicadas

- O aplicativo anteriormente abria sem autenticação. Agora existe um bloqueio antes de conectar ao banco ou renderizar orçamento, histórico e editor. A única entrada é Google, limitada aos dois e-mails definidos no código. Falta de configuração, identidade inválida ou token expirado bloqueiam o acesso.
- Callbacks, diálogo de configurações e cada operação de banco revalidam a identidade. Cookies e identidade são tratados pela autenticação nativa do Streamlit/Authlib; e-mail em query string, formulário ou session state não concede acesso.
- As imagens privadas de orçamento usam dados inline na sessão autorizada, sem criar endereços públicos de mídia ou download do Streamlit. Os nomes de arquivo são sanitizados. O logo continua sendo um recurso público.
- Erros de banco e infraestrutura não exibem credenciais, respostas técnicas ou traceback no navegador. CORS e proteção XSRF estão habilitados; headers não concedem identidade e não há serviço de arquivos estáticos.
- `orcamentos` e `docito_configuracoes` têm RLS habilitado e forçado. Não existem políticas para visitantes: o aplicativo usa uma chave de backend somente nos Secrets. `anon` e `authenticated` não possuem permissões nessas tabelas ou na RPC de numeração. `service_role` tem apenas SELECT/INSERT/UPDATE em orçamentos e SELECT/UPDATE no catálogo; não pode excluir ou truncar essas tabelas por seus privilégios de tabela.
- O catálogo valida nomes, duplicatas, tipos de cobrança, preços finitos e faixas consistentes; salvamentos usam revisão para evitar perdas. A sequência de orçamentos elimina a disputa por MAX + 1 entre as duas contas.
- Credenciais e arquivos `.env` são ignorados pelo Git; existe apenas um exemplo sem valores reais. Dependências diretas e transitivas foram fixadas. As verificações de acesso e dos projetos JSON são executadas no GitHub Actions com permissão somente de leitura.

## Evidência e limites

- 15 testes Python verificaram as duas contas, rejeição de outros e-mails, aliases, e-mails não confirmados, emissor/audiência incorretos, tokens vencidos, configurações incompletas, proteção de callbacks, catálogo preenchido, CRUD, conflito e preservação de preços. 12 testes Node verificaram importação/exportação e recuperação dos projetos JSON.
- A varredura de credenciais em 89 commits não encontrou padrões de tokens Google/GitHub/Supabase, JWTs completos ou chaves privadas nos arquivos de texto revisados. Isso não confirma ausência absoluta de segredos ou vazamentos externos.
- `pip-audit` não encontrou vulnerabilidades conhecidas nas versões fixadas em `requirements.txt` na data da revisão.
- O Security Advisor do Supabase retornou apenas os avisos informativos **RLS Enabled No Policy**, coerentes com o acesso exclusivo pelo backend. [Explicação do aviso](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy).

## Pendências de infraestrutura

O proprietário precisa configurar o cliente OAuth Google nos Secrets do Streamlit para concluir o login real. Até isso ocorrer, o site permanece fechado para os dados privados, inclusive para as duas contas. A configuração e o roteiro de verificação estão no README.

O motor PostgreSQL do projeto ainda reporta **17.6**. O Supabase anunciou a atualização para **17.11** com correções de segurança em 25/09/2026. A integração disponível permite SQL e migrações, mas não atualiza o motor gerenciado. A atualização deve ser concluída no painel do Supabase, com backup e janela apropriada. O projeto não possui extensões `ltree` ou `btree_gist`; `pgcrypto` está instalado. Os dados de orçamentos e catálogo usam JSONB e não foram regravados. [Comunicado oficial](https://supabase.com/changelog).

Esta revisão cobre o código e os privilégios observados. Não inclui auditoria das contas Google/GitHub/Streamlit, acessos de administradores, backups externos ou dispositivos das duas usuárias. Downloads e cópias já feitos por uma conta autorizada continuam sob o controle dessa pessoa.
