create schema if not exists private;
revoke all on schema private from public,anon,authenticated;
grant usage on schema private to service_role;
create extension if not exists pg_net with schema extensions;
create extension if not exists pg_cron;
revoke all on schema net from public,anon,authenticated;
-- The delivery token stays encrypted in Vault; only its SHA-256 is configured at the destination.
do $$ begin
 if not exists(select 1 from vault.secrets where name='docito_quote_delivery_token') then
  perform vault.create_secret(encode(extensions.gen_random_bytes(32),'hex'),'docito_quote_delivery_token','Docito approved quotes only');
 end if;
end $$;
alter table public.orcamentos add column revisao bigint not null default 1,
 add column gestao_approved_revision bigint not null default 0,
 add column gestao_synced_revision bigint not null default 0,
 add column gestao_order_id uuid;
create function private.quote_revision() returns trigger language plpgsql security invoker set search_path='' as $$
begin
 if (to_jsonb(new)-array['revisao','gestao_approved_revision','gestao_synced_revision','gestao_order_id','atualizado_em'])
 is distinct from (to_jsonb(old)-array['revisao','gestao_approved_revision','gestao_synced_revision','gestao_order_id','atualizado_em']) then
  new.revisao:=old.revisao+1;
 else new.revisao:=old.revisao;end if;
 return new;
end $$;
revoke all on function private.quote_revision() from public,anon,authenticated,service_role;
create trigger docito_quote_revision before update on public.orcamentos for each row execute function private.quote_revision();
create table private.quote_outbox (
 id uuid primary key, quote_id uuid not null references public.orcamentos(id) on delete restrict,
 revision bigint not null, payload jsonb not null, status text not null default 'pending' check(status in ('pending','sending','integrated','blocked')),
 attempts integer not null default 0, request_id bigint, next_attempt timestamptz not null default now(),
 last_error text, acknowledged_order uuid, created_at timestamptz not null default now(),updated_at timestamptz not null default now(),
 unique(quote_id,revision)
);
alter table private.quote_outbox enable row level security;
revoke all on private.quote_outbox from public,anon,authenticated,service_role;
create index quote_outbox_due on private.quote_outbox(next_attempt) where status in ('pending','sending');

create function private.dispatch_quotes() returns integer language plpgsql security definer set search_path='' as $$
declare o private.quote_outbox;r record;response jsonb;token text;v_request bigint;v_count integer:=0;
begin
 if not pg_try_advisory_xact_lock(hashtext('docito-quotes-dispatch')) then return 0;end if;
 for o in select * from private.quote_outbox where status in ('pending','sending') and next_attempt<=now() order by created_at limit 20 for update skip locked loop
  if o.status='sending' then
   select * into r from net._http_response where id=o.request_id;
   if found then
    begin response:=r.content::jsonb;exception when others then response:='{}';end;
    if r.status_code=200 and response->>'event_id'=o.id::text and response->>'revision'=o.revision::text and coalesce(response->>'order_id','') ~ '^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$' then
     update private.quote_outbox set status='integrated',acknowledged_order=(response->>'order_id')::uuid,last_error=null,updated_at=now() where id=o.id;
     update public.orcamentos set gestao_synced_revision=greatest(gestao_synced_revision,o.revision),gestao_order_id=(response->>'order_id')::uuid where id=o.quote_id;
     continue;
    end if;
    update private.quote_outbox set status=case when r.status_code=409 then 'blocked' else 'pending' end,last_error=case when r.status_code=409 then left(coalesce(response->>'error','Revisão recusada pela Gestão.'),250) else 'Falha temporária na comunicação com a Gestão.' end,updated_at=now() where id=o.id;
    if r.status_code=409 then continue;end if;
   elsif o.updated_at>now()-interval '2 minutes' then continue;
   end if;
  end if;
  if o.attempts>=10 then
   update private.quote_outbox set status='blocked',last_error='Tentativas automáticas esgotadas. Revise e tente novamente.',updated_at=now() where id=o.id;continue;
  end if;
  select decrypted_secret into strict token from vault.decrypted_secrets where name='docito_quote_delivery_token';
  v_request:=net.http_post(url:='https://ownzvyokbljywgqxnijw.supabase.co/functions/v1/docito-quotes',headers:=jsonb_build_object('Content-Type','application/json','Authorization','Bearer '||token),body:=o.payload,timeout_milliseconds:=20000);
  update private.quote_outbox set request_id=v_request,status='sending',attempts=attempts+1,next_attempt=now()+least(300,15*power(2,least(attempts,4))) * interval '1 second',updated_at=now() where id=o.id;
  v_count:=v_count+1;
 end loop;
 return v_count;
end $$;
revoke all on function private.dispatch_quotes() from public,anon,authenticated,service_role;

create function private.approve_quote(p_id uuid,p_revision bigint,p_actor text) returns jsonb language plpgsql security definer set search_path='' as $$
declare q public.orcamentos;o private.quote_outbox;v_payload jsonb;v_id uuid:=gen_random_uuid();v_items jsonb;v_total numeric;
begin
 if p_actor is null or p_actor not in ('julio.goiano@gmail.com','gerusa041188@gmail.com') then raise exception 'Responsável não autorizado.' using errcode='42501';end if;
 select * into strict q from public.orcamentos where id=p_id for update;
 if p_revision is null or q.revisao<>p_revision then raise exception 'Orçamento alterado. Atualize o histórico e revise novamente.';end if;
 select * into o from private.quote_outbox where quote_id=p_id and revision=p_revision;
 if not found then
  v_items:=case when jsonb_typeof(q.itens)='array' and jsonb_array_length(q.itens)>0 then q.itens else q.dados->'itens' end;
  v_total:=coalesce(q.total,(q.dados->>'total')::numeric);
  if coalesce(jsonb_typeof(v_items),'null')<>'array' or jsonb_array_length(v_items) not between 1 and 100 or coalesce(v_total::text,'') !~ '^[0-9]+(\.[0-9]+)?$' or v_total<>round(v_total,2) then raise exception 'Revise os itens e o total antes de aprovar.';end if;
  v_payload:=jsonb_build_object('version',1,'source','docito-orcamento','kind','approved_quote','event_id',v_id,'quote_id',q.id,'revision',q.revisao,'approved_by',p_actor,
   'quote',jsonb_build_object('numero',q.numero,'cliente',q.cliente,'data_entrega',q.data_entrega,'itens',v_items,'total',round(v_total,2)::text,
    'observacao',coalesce(q.observacao,q.dados->>'observacao',''),'embalagem_pedido',coalesce(q.embalagem_pedido,q.dados->'embalagem_pedido'),'embalagens_especiais',coalesce(q.embalagens_especiais,q.dados->'embalagens_especiais'),'adicionais',coalesce(q.adicionais,q.dados->'adicionais'),'desconto_geral',coalesce(q.desconto_geral,q.dados->>'desconto_geral','')));
  if octet_length(v_payload::text)>131072 then raise exception 'Orçamento muito grande para integração. Reduza os detalhes e revise.';end if;
  insert into private.quote_outbox(id,quote_id,revision,payload) values(v_id,q.id,q.revisao,v_payload);
  update public.orcamentos set gestao_approved_revision=q.revisao where id=q.id;
 end if;
 perform private.dispatch_quotes();
 return jsonb_build_object('revision',q.revisao,'approved',true);
end $$;
revoke all on function private.approve_quote(uuid,bigint,text) from public,anon,authenticated,service_role;
grant execute on function private.approve_quote(uuid,bigint,text) to service_role;
create function public.docito_approve_quote(p_id uuid,p_revision bigint,p_actor text) returns jsonb language sql security invoker set search_path='' as $$select private.approve_quote(p_id,p_revision,p_actor)$$;
revoke all on function public.docito_approve_quote(uuid,bigint,text) from public,anon,authenticated;
grant execute on function public.docito_approve_quote(uuid,bigint,text) to service_role;

create function private.quote_status(p_id uuid,p_retry boolean) returns jsonb language plpgsql security definer set search_path='' as $$
declare q public.orcamentos;o private.quote_outbox;
begin
 select * into strict q from public.orcamentos where id=p_id;
 if p_retry then
  -- Retry the current approved snapshot, never approve a draft implicitly.
  update private.quote_outbox set status='pending',attempts=0,next_attempt=now(),updated_at=now() where quote_id=p_id and revision=q.gestao_approved_revision and status='blocked';
 end if;
 perform private.dispatch_quotes();
 select * into o from private.quote_outbox where quote_id=p_id and revision=q.gestao_approved_revision;
 return jsonb_build_object('status',coalesce(o.status,'draft'),'revision',q.revisao,'approved_revision',q.gestao_approved_revision,'synced_revision',(select gestao_synced_revision from public.orcamentos where id=p_id),'order_id',coalesce(o.acknowledged_order,q.gestao_order_id),'error',o.last_error,'attempts',o.attempts);
end $$;
revoke all on function private.quote_status(uuid,boolean) from public,anon,authenticated,service_role;
grant execute on function private.quote_status(uuid,boolean) to service_role;
create function public.docito_quote_status(p_id uuid,p_retry boolean default false) returns jsonb language sql security invoker set search_path='' as $$select private.quote_status(p_id,p_retry)$$;
revoke all on function public.docito_quote_status(uuid,boolean) from public,anon,authenticated;
grant execute on function public.docito_quote_status(uuid,boolean) to service_role;
select cron.schedule('docito-approved-quotes','* * * * *','select private.dispatch_quotes();');
notify pgrst,'reload schema';
