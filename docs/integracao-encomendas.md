# Orçamentos aprovados → encomendas

No Histórico, abra o orçamento salvo, confira cliente, entrega, itens e total, marque **O cliente autorizou esta versão do orçamento** e clique **Aprovar e agendar na Gestão**. Somente o orçamento aprovado é enviado; não há importação em massa dos registros antigos.

O banco guarda a revisão e uma cópia imutável da aprovação em uma fila privada. O envio é tentado automaticamente, com limite de dez tentativas. **Integrado** só aparece após o reconhecimento do Gestão. Atualizar situação/tentar novamente consulta a confirmação ou repete a mesma versão aprovada, sem aprovar um rascunho. Pode levar aproximadamente um minuto; indisponibilidade pode prolongar o prazo.

Para alterar: edite e salve normalmente, gere a imagem e envie ao cliente como já faz. A Gestão continua com a versão aprovada anterior. Após a nova autorização, volte ao Histórico e use **Aprovar edição e atualizar Gestão**. A encomenda conserva seu identificador e recebe nova revisão. O sistema não envia imagens ou mensagens ao cliente por conta própria.

Na Gestão, o menu **Encomendas** mostra cliente, data, itens, total e revisões. Produtos sem vínculo ficam sinalizados; a associação é explícita por cadastro, sem tentar adivinhar nomes. Quantidades por cento já são contagens de unidades no carrinho; massa em gramas é convertida em kg. Embalagens, adicionais e descontos ficam preservados na composição comercial, sem gerar movimentações.

Agendar não significa vender, receber pagamento ou consumir estoque. Revisões de pedidos iniciados, pagos ou encerrados são recusadas e ficam pendentes para ajuste explícito. Cancelar/reabrir agendamento na Gestão preserva orçamento e revisões. A situação de integração na origem confirma o recebimento da versão, não acompanha estados posteriores da produção.

## Operação técnica

A origem usa Supabase pg_net + pg_cron e Vault, sem nova credencial nos Secrets do Streamlit. A capacidade de 256 bits é gerada no banco, criptografada no Vault e enviada em Authorization pelo backend. Somente o hash é configurado no destino. O endpoint Edge valida método, tamanho e autenticação via RPC privado, permitido apenas a service_role. Nem a capacidade nem chaves administrativas entram no cliente ou no repositório.

O agendamento executa a fila a cada minuto, até 20 eventos por execução, com backoff limitado. A fila é persistente; a perda de tabelas temporárias do pg_net é recuperada por reenvio idempotente. Falhas de validação ficam bloqueadas para revisão humana; não sobrescrever eventos aprovados para consertá-las: salvar uma edição e aprovar nova revisão. Segredos e cabeçalhos não devem ser impressos nos logs.

Referências: https://supabase.com/docs/guides/database/extensions/pg_net e https://supabase.com/docs/guides/database/vault.
