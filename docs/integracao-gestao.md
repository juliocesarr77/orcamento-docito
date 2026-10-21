# Tabela central de preços do Gestão

A integração implementada é uma importação de JSON com revisão humana. Não adiciona serviços pagos, contas, credenciais ou conexões entre os bancos. Não foi publicada automaticamente.

## Usar

1. No Docito Gestão, exporte a tabela de preços atuais aprovada.
2. No orçamento, entre com sua conta Google já autorizada e abra **Configurações → Preços da Gestão**.
3. Selecione o arquivo JSON. Para cada produto desejado, escolha explicitamente o produto correspondente do orçamento. Confira os nomes, UUIDs e a cobrança; não existe associação automática por nome.
4. Revise a prévia, marque a confirmação e clique em **Aplicar somente os preços associados**.
5. Adicione novos itens ao orçamento. O carrinho já preenchido e os orçamentos salvos ou aceitos mantêm os preços e regras que já possuíam.

A gravação exige a revisão do catálogo que originou a prévia. Se outra sessão salvar antes, o sistema recusa a importação e pede reabertura. Produtos não selecionados, nomes, UUIDs, flags de tema e tabelas de faixas são preservados. Os vínculos por ID são guardados para a próxima importação. Um vínculo existente não pode ser silenciosamente transferido para outro produto.

## Valores e faixas

O Gestão exporta centavos **por unidade**. Para produto cobrado por **Unidade**, 150 centavos viram R$ 1,50; para **Cento**, viram R$ 150,00 por cento. Produto cobrado por kg não aceita esse mapeamento. O limite local é R$ 99.999,99 por preço cadastrado.

Produtos importados passam a usar preço proporcional nos itens novos, mesmo quando o novo valor do cento coincide com uma faixa antiga. O item novo guarda `regra_preco = null`. As faixas antigas permanecem no catálogo para os outros produtos; itens históricos continuam usando sua regra gravada ou a tabela original de compatibilidade. Não há atualização em lote da tabela `orcamentos`.

## Contrato JSON

```json
{
  "version": 1,
  "source": "docito-gestao",
  "policy_version": 1,
  "generated_at": "2026-10-21T19:00:00Z",
  "products": [
    {
      "id": "11111111-1111-4111-8111-111111111111",
      "name": "Brigadeiro",
      "unit": "un",
      "price_cents": 150
    }
  ]
}
```

São aceitos de 1 a 200 produtos e até 256 KB. Preços são inteiros positivos de centavos, como número JSON ou texto de dígitos, até 100000000000; a conversão ainda precisa respeitar o limite menor do orçamento. UUIDs duplicados, destinos repetidos, formato desconhecido, cobrança incompatível e valores inválidos são rejeitados. Nomes iguais na origem são tratados pelos UUIDs, sem correspondência aproximada. O SHA-256 registrado identifica o arquivo importado, mas não constitui assinatura digital ou autenticação da origem; a revisão humana continua necessária. O importador só guarda os campos de preço e identificação previstos, sem custos ou margens.

A configuração JSON existente recebe `gestao_id` e `preco_proporcional` nos produtos selecionados, além da data e SHA-256 da última importação. Não exige migration SQL. As credenciais administrativas existentes permanecem apenas no servidor Streamlit e não integram o arquivo exportado.

## Sincronização automática: pendente

A documentação oficial do Streamlit permite expor explicitamente tokens do provedor em `st.user.tokens`, usando `expose_tokens = "id"` no bloco `[auth]`. Essa opção não foi habilitada por esta implementação. A identidade e a lista de contas autorizadas existentes não foram modificadas.

A API oficial do Supabase aceita ID tokens Google, mas o fluxo documentado com nonce usa o hash no token do Google e o nonce original na chamada ao Supabase. Não há evidência neste projeto de uma interface oficial que forneça o nonce original com essa convenção para o login Streamlit atual. Não foi contornada a verificação de nonce, extraída uma sessão do navegador ou reutilizada uma credencial de outro aplicativo.

Uma futura sincronização precisa de autenticação oficial comprovada e configurada no servidor, vínculo explícito dos IDs e endpoint de leitura que exponha somente os preços aprovados a contas autorizadas. Deve preservar a revisão concorrente e os snapshots históricos e falhar sem alterar o catálogo se a autenticação expirar. Nunca usar a service_role de um aplicativo como credencial cliente do outro.

Fontes oficiais consultadas:

- Streamlit: https://docs.streamlit.io/develop/api-reference/user/st.user
- Supabase Google / nonce: https://supabase.com/docs/guides/auth/social-login/auth-google
- Supabase Python ID token: https://supabase.com/docs/reference/python/auth-signinwithidtoken

## Validação local

`python -m unittest discover -s tests -p 'test_*.py' -v` verifica a integração e as regras existentes, sem tráfego de produção. A suíte cobre centavos/unidade/cento, recusa de kg, validação de formato, associação por ID, revisão concorrente, prévia sem gravação e preservação de preços e faixas históricas.
