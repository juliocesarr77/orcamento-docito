-- Catálogo privado: somente o backend autenticado da Docito usa service_role.
-- Os orçamentos existentes não são alterados.
create table public.docito_configuracoes (
  id text primary key check (id = 'catalogo'),
  configuracao jsonb not null check (
    configuracao->>'versao' = '1'
    and jsonb_typeof(configuracao->'doces') = 'array'
    and jsonb_typeof(configuracao->'faixas') = 'array'
  ),
  revisao bigint not null default 1 check (revisao > 0),
  atualizado_em timestamptz not null default now(),
  atualizado_por text check (char_length(atualizado_por) <= 254)
);
alter table public.docito_configuracoes enable row level security;
alter table public.docito_configuracoes force row level security;
revoke all on public.docito_configuracoes from public, anon, authenticated, service_role;
grant select, update on public.docito_configuracoes to service_role;

insert into public.docito_configuracoes (id, configuracao)
values ('catalogo', $catalogo${"versao":1,"doces":[{"id":"c438e7bd-661b-5343-9779-154fbb6961d2","nome":"Brigadeiro de Chocolate","cobranca":"Cento","preco":125.0,"conta_como_doce":true,"tematico":false},{"id":"4de43d1c-79ae-5523-b650-71c20b81bf27","nome":"Brigadeiro de Ninho","cobranca":"Cento","preco":125.0,"conta_como_doce":true,"tematico":false},{"id":"f10dfa41-d41d-55de-a40d-f5450d036b87","nome":"Beijinho","cobranca":"Cento","preco":130.0,"conta_como_doce":true,"tematico":false},{"id":"26e44df2-b44f-5916-b5ca-0ca30b3fc7bf","nome":"Meio a Meio","cobranca":"Cento","preco":130.0,"conta_como_doce":true,"tematico":false},{"id":"918b20c2-e794-5f06-be8d-1b928f4e3e8f","nome":"Bicho de Pé","cobranca":"Cento","preco":125.0,"conta_como_doce":true,"tematico":false},{"id":"236dcfef-1e0f-53d2-a400-1f9e488088e5","nome":"Moranguinho","cobranca":"Cento","preco":125.0,"conta_como_doce":true,"tematico":false},{"id":"d65e2b48-dc14-5a23-9b1d-37dab6d288bf","nome":"Cajuzinho","cobranca":"Cento","preco":130.0,"conta_como_doce":true,"tematico":false},{"id":"84d5008f-c5f2-5499-9be1-d258943043be","nome":"Ninho com Nutella","cobranca":"Cento","preco":150.0,"conta_como_doce":true,"tematico":false},{"id":"47eec44d-edd3-5b46-aab6-7b5f96800f59","nome":"Churros","cobranca":"Cento","preco":150.0,"conta_como_doce":true,"tematico":false},{"id":"194d685b-e4ce-50eb-8610-486d09a046bd","nome":"Ferrero Rocher","cobranca":"Cento","preco":150.0,"conta_como_doce":true,"tematico":false},{"id":"d6926720-4b62-5d26-a797-b1429c1874b4","nome":"Maracujá","cobranca":"Cento","preco":150.0,"conta_como_doce":true,"tematico":false},{"id":"55e81de1-c229-5a88-b801-7ac5be13e001","nome":"Limão","cobranca":"Cento","preco":150.0,"conta_como_doce":true,"tematico":false},{"id":"ec563a6c-97fa-53e3-811b-9a4768e12ead","nome":"Maçãzinha","cobranca":"Cento","preco":150.0,"conta_como_doce":true,"tematico":false},{"id":"5ac3245c-418d-5a16-92b5-69fd3a12aeed","nome":"Olho de Sogra","cobranca":"Cento","preco":150.0,"conta_como_doce":true,"tematico":false},{"id":"503f7bb1-651d-58e3-b6c0-0dd52063b791","nome":"Oreo","cobranca":"Cento","preco":150.0,"conta_como_doce":true,"tematico":false},{"id":"4717c194-1935-57bc-bf79-62f136b073bf","nome":"Ninho Temático","cobranca":"Cento","preco":160.0,"conta_como_doce":true,"tematico":true},{"id":"a76a798f-6260-5bdc-9b6a-062d8cd3f0f9","nome":"Aplique","cobranca":"Unidade","preco":1.5,"conta_como_doce":false,"tematico":false},{"id":"84d04309-1c3f-5c8a-a30d-81fb9a47e590","nome":"Brigadeiro de Chocolate em massa","cobranca":"kg","preco":84.9,"conta_como_doce":false,"tematico":false},{"id":"1afb32fa-5348-5bb0-afde-30913158f825","nome":"Brigadeiro de Chocolate Branco","cobranca":"Cento","preco":150.0,"conta_como_doce":true,"tematico":false},{"id":"28042f61-c114-53e4-b47c-2e75026ac8c9","nome":"Brigadeiro de Ninho com Rosetas Coloridas e Apliques de Pasta Americana","cobranca":"Cento","preco":160.0,"conta_como_doce":true,"tematico":false}],"faixas":[{"preco_cento":125.0,"unitario_ate_25":1.5,"40":58.9,"50":68.9,"75":98.9,"90":116.9,"100":125.0},{"preco_cento":130.0,"unitario_ate_25":1.5,"40":59.9,"50":71.9,"75":104.9,"90":123.9,"100":130.0},{"preco_cento":150.0,"unitario_ate_25":2.0,"40":77.9,"50":82.9,"75":117.9,"90":140.9,"100":150.0},{"preco_cento":160.0,"unitario_ate_25":2.0,"40":78.9,"50":85.0,"75":124.9,"90":148.9,"100":160.0}]}$catalogo$::jsonb);

create function public.docito_atualizar_configuracao()
returns trigger
language plpgsql
security invoker
set search_path = pg_catalog
as $function$
begin
  if new.revisao <> old.revisao + 1 then
    raise exception 'Invalid catalogue revision';
  end if;
  new.atualizado_em := pg_catalog.now();
  return new;
end;
$function$;
revoke all on function public.docito_atualizar_configuracao() from public, anon, authenticated;
create trigger docito_configuracao_atualizada before update on public.docito_configuracoes
for each row execute function public.docito_atualizar_configuracao();

-- Numeração atômica: dois usuários não recebem o mesmo número.
create sequence public.docito_orcamento_numero_seq as bigint start with 234;
select pg_catalog.setval('public.docito_orcamento_numero_seq'::regclass,
  greatest(234, coalesce((select max(numero) + 1 from public.orcamentos), 234)), false);
revoke all on sequence public.docito_orcamento_numero_seq from public, anon, authenticated;
grant usage on sequence public.docito_orcamento_numero_seq to service_role;
create function public.docito_proximo_numero()
returns bigint
language sql
volatile
security invoker
set search_path = pg_catalog
as $function$
  select pg_catalog.nextval('public.docito_orcamento_numero_seq'::regclass);
$function$;
revoke all on function public.docito_proximo_numero() from public, anon, authenticated;
grant execute on function public.docito_proximo_numero() to service_role;

-- O aplicativo precisa apenas consultar, criar e atualizar orçamentos.
alter table public.orcamentos force row level security;
revoke all on public.orcamentos from public, anon, authenticated, service_role;
grant select, insert, update on public.orcamentos to service_role;
revoke all on function public.atualizar_data_orcamento() from public, anon, authenticated;
notify pgrst, 'reload schema';
