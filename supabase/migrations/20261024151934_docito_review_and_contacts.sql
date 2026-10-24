alter table private.quote_outbox add column waiting_review boolean not null default false;
do $patch$ declare b text:=pg_get_functiondef('private.dispatch_quotes()'::regprocedure);needle text:=$n$     update private.quote_outbox set status='integrated',acknowledged_order=$n$;begin
 if position(needle in b)=0 then raise exception 'Confirmação de integração não reconhecida.';end if;
 b:=replace(b,needle,$r$     if response->'pending_review'='true'::jsonb then
      update private.quote_outbox set status='pending',waiting_review=true,attempts=0,request_id=null,next_attempt=now()+interval '5 minutes',last_error='Edição recebida; aguarda conferência operacional na Gestão.',acknowledged_order=(response->>'order_id')::uuid,updated_at=now() where id=o.id;continue;
     end if;
     update private.quote_outbox set waiting_review=false,status='integrated',acknowledged_order=$r$);execute b;
 b:=pg_get_functiondef('private.approve_quote(uuid,bigint,text)'::regprocedure);
 b:=replace(b,$n$'quote',jsonb_build_object('numero',q.numero,$n$,$r$'quote',jsonb_build_object('contato',coalesce(q.dados->'contato','{}'::jsonb),'numero',q.numero,$r$);execute b;
 b:=pg_get_functiondef('private.quote_status(uuid,boolean)'::regprocedure);
 b:=replace(b,$n$'attempts',o.attempts)$n$,$r$'attempts',o.attempts,'waiting_review',o.waiting_review,'updated_at',o.updated_at)$r$);execute b;
end $patch$;
notify pgrst,'reload schema';
-- Server-side sealing prevents integration capabilities from appearing in the app's plaintext export.
create function private.quote_backup(p_actor text,p_passphrase text) returns jsonb language plpgsql security definer set search_path='' as $$
declare state jsonb;sealed text;tables jsonb;
begin
 if p_actor is distinct from 'julio.goiano@gmail.com' then raise insufficient_privilege using message='Somente o proprietário pode exportar a recuperação completa.';end if;
 if length(p_passphrase) not between 16 and 200 then raise exception 'Use senha de recuperação de 16 a 200 caracteres.';end if;
 perform pg_advisory_xact_lock(hashtext('docito-quotes-dispatch'));
 lock table public.orcamentos,public.docito_configuracoes in share mode;
 select jsonb_build_object('orcamentos',(select coalesce(jsonb_agg(to_jsonb(x)),'[]')::text from public.orcamentos x),'docito_configuracoes',(select coalesce(jsonb_agg(to_jsonb(x)),'[]')::text from public.docito_configuracoes x)) into tables;
 select jsonb_build_object('quote_outbox',(select coalesce(jsonb_agg(to_jsonb(x)),'[]') from private.quote_outbox x),'vault',(select coalesce(jsonb_agg(jsonb_build_object('id',v.id,'name',v.name,'decrypted_secret',v.decrypted_secret)),'[]') from vault.decrypted_secrets v where v.name='docito_quote_delivery_token')) into state;
 sealed:=encode(extensions.pgp_sym_encrypt(state::text,p_passphrase,'cipher-algo=aes256,compress-algo=1'),'base64');
 return jsonb_build_object('format','docito-orcamento-recovery','version',1,'generated_at',now(),'tables_json',tables,'objects','[]'::jsonb,'private_sealed',sealed,'private_cipher','pgp-aes256','auth_recovery','Acesso Google e chaves de plataforma são administrados separadamente; mantenha os emails autorizados do repositório.');
end $$;
revoke all on function private.quote_backup(text,text) from public,anon,authenticated,service_role;grant execute on function private.quote_backup(text,text) to service_role;
create function public.docito_quote_backup(p_actor text,p_passphrase text) returns jsonb language sql security invoker set search_path='' as $$select private.quote_backup(p_actor,p_passphrase)$$;
revoke all on function public.docito_quote_backup(text,text) from public,anon,authenticated;grant execute on function public.docito_quote_backup(text,text) to service_role;
notify pgrst,'reload schema';
