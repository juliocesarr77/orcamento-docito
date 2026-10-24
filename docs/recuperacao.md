# Recuperação do Orçamento

Exporte em Configurações → Backup criptografado e recuperação como proprietário. Guarde também o backup da Gestão, com a senha separada do arquivo. O download não cria URL pública de mídia.

O arquivo usa o mesmo envelope AES-256-GCM/PBKDF2-SHA256 da Gestão e conserva os números em `tables_json`. O pacote privado da fila/token de integração sai do banco selado por PGP/AES-256. O verificador da tela confere senha e estrutura sem escrever dados.

O teste `npm run test:db` verifica aprovação, ACK, espera de revisão operacional, aplicação, retry, permissões e recuperação do banco em PostgreSQL/PGlite isolado. Os testes Python verificam criptografia, contato e IDs estáveis de linhas. Para recuperação real, use ambiente isolado, preserve os UUIDs/revisões e a fila, restaure `orcamentos` e `docito_configuracoes`, confira quantidades/totais e só depois reative a entrega. O pacote privado deve ser decifrado apenas em cliente administrativo com parâmetros vinculados e restaurado no Vault, sem imprimir tokens. Mantenha fila/agendadores desativados durante o ensaio.

Credenciais Google, Secrets do Streamlit, permissões GitHub e chaves do Supabase são administradas separadamente. Não exponha o backup decifrado nem grave suas senhas no repositório. O runbook completo de dados/anexos/integração está em `docito-gestao/docs/recuperacao.md`.
