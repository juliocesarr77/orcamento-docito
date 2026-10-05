-- Verificação de disponibilidade do Supabase para o Docito.
-- Execute uma vez no SQL Editor do projeto orcamentos-docito.
-- A função só devolve a data/hora do banco, sem ler ou alterar tabelas.
begin;

create or replace function public.docito_keep_alive()
returns timestamptz
language sql
stable
security invoker
set search_path = pg_catalog
as $function$
  select pg_catalog.now();
$function$;

revoke execute on function public.docito_keep_alive()
  from public, anon, authenticated;
grant execute on function public.docito_keep_alive() to anon;

notify pgrst, 'reload schema';
commit;
