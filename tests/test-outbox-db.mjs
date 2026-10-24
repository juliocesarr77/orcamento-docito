// Test the other database in isolation. pg_net/Vault/Cron are explicit test doubles.
import { PGlite } from "@electric-sql/pglite";
import fs from "node:fs/promises";
import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
const db = new PGlite();
await db.exec(`create role anon;create role authenticated;create role service_role;create schema extensions;create schema vault;create schema net;create schema cron;
 create table vault.secrets(id uuid default gen_random_uuid(),name text,decrypted_secret text);insert into vault.secrets(name,decrypted_secret) values('docito_quote_delivery_token',repeat('f',64));create view vault.decrypted_secrets as select * from vault.secrets;
 create table net.sent(id bigserial,body jsonb);create table net._http_response(id bigint,status_code integer,content text);
 create function net.http_post(url text,headers jsonb,body jsonb,timeout_milliseconds integer) returns bigint language sql as $$insert into net.sent(body) values(body) returning id$$;
 create function cron.schedule(text,text,text) returns bigint language sql as $$select 1::bigint$$;
 create table public.docito_configuracoes(id text primary key,configuracao jsonb,revisao bigint);
 create table public.orcamentos(id uuid primary key default gen_random_uuid(),numero bigint,cliente text,data_entrega date,dados jsonb,itens jsonb,observacao text,total numeric,desconto_geral text,embalagem_pedido jsonb,embalagens_especiais jsonb,adicionais jsonb,criado_em timestamptz default now(),atualizado_em timestamptz default now());`);
const path = new URL(
  "../supabase/migrations/",
  import.meta.url,
);
const file = (await fs.readdir(path)).find((x) =>
  x.endsWith("_docito_quote_outbox.sql"),
);
const migration = (await fs.readFile(new URL(file, path), "utf8")).replace(
  /^create extension .*;$/gm,
  "",
);
await db.exec(migration);
for(const file of (await fs.readdir(path)).filter(f=>f.endsWith('_docito_review_and_contacts.sql')))await db.exec(await fs.readFile(new URL(file,path),'utf8'));

const sql = async (q, a = []) => (await db.query(q, a)).rows;
const rpc = async (name, args) => {
  await db.exec("set role service_role");
  try {
    return (
      await sql(
        `select public.${name}(${args.map((_, n) => "$" + (n + 1)).join(",")}) result`,
        args,
      )
    )[0].result;
  } finally {
    await db.exec("reset role");
  }
};
const id = randomUUID();
await sql(
  `insert into public.orcamentos(id,numero,cliente,data_entrega,itens,total,dados) values($1,100,'Cliente isolada','2026-11-01','[{"produto":"Doce","tipo":"unitario","qtd":27}]',189,'{"contato":{"telefone":"11999990000","modalidade":"delivery"}}')`,
  [id],
);
assert.equal((await sql("select * from private.quote_outbox")).length, 0);
await assert.rejects(
  () => rpc("docito_approve_quote", [id, 1, "intruso@docito.invalid"]),
  /não autorizado/,
);
await rpc("docito_approve_quote", [id, 1, "julio.goiano@gmail.com"]);
await rpc("docito_approve_quote", [id, 1, "julio.goiano@gmail.com"]);
assert.equal((await sql("select * from private.quote_outbox")).length, 1);
assert.equal((await sql("select * from net.sent")).length, 1);
let event = (await sql("select * from private.quote_outbox"))[0];
assert.equal(event.payload.quote.total, "189.00");
assert.equal(event.payload.quote.contato.telefone,"11999990000");
assert.equal((await rpc("docito_quote_status", [id, false])).status, "sending");
const order = randomUUID();
await sql("insert into net._http_response values($1,200,$2)", [
  event.request_id,
  JSON.stringify({ order_id: order, revision: 1, event_id: event.id }),
]);
await sql("update private.quote_outbox set next_attempt=now()");
let state = await rpc("docito_quote_status", [id, false]);
assert.equal(state.status, "integrated");
assert.equal(state.order_id, order);
assert.equal(state.synced_revision, 1);
assert.equal(state.revision, 1);
await sql(
  "update public.orcamentos set cliente='Cliente editada' where id=$1",
  [id],
);
assert.equal(
  (await sql("select revisao from public.orcamentos where id=$1", [id]))[0]
    .revisao,
  2,
);
assert.equal((await sql("select * from private.quote_outbox")).length, 1);
await assert.rejects(
  () => rpc("docito_approve_quote", [id, 1, "julio.goiano@gmail.com"]),
  /alterado/,
);
await rpc("docito_approve_quote", [id, 2, "gerusa041188@gmail.com"]);
assert.equal((await sql("select * from private.quote_outbox")).length, 2);
event = (await sql("select * from private.quote_outbox where revision=2"))[0];
await sql("insert into net._http_response values($1,409,$2)", [
  event.request_id,
  JSON.stringify({ error: "Pedido iniciado exige ajuste explícito." }),
]);
await sql("update private.quote_outbox set next_attempt=now()");
state = await rpc("docito_quote_status", [id, false]);
assert.equal(state.status, "blocked");
assert.match(state.error, /ajuste explícito/);
await rpc("docito_quote_status", [id, true]);
event = (await sql("select * from private.quote_outbox where revision=2"))[0];
assert.equal(event.status, "sending");
assert.equal(event.attempts, 1);
await sql("insert into net._http_response values($1,200,$2)",[event.request_id,JSON.stringify({order_id:order,revision:2,event_id:event.id,pending_review:true})]);
await sql("update private.quote_outbox set next_attempt=now() where revision=2");
state=await rpc('docito_quote_status',[id,false]);assert.equal(state.waiting_review,true);assert.equal(state.synced_revision,1);assert.notEqual(state.status,'integrated');
await sql("update private.quote_outbox set next_attempt=now() where revision=2");await rpc('docito_quote_status',[id,false]);event=(await sql("select * from private.quote_outbox where revision=2"))[0];
await sql("insert into net._http_response values($1,200,$2)",[event.request_id,JSON.stringify({order_id:order,revision:2,event_id:event.id,pending_review:false})]);await sql("update private.quote_outbox set next_attempt=now() where revision=2");state=await rpc('docito_quote_status',[id,false]);assert.equal(state.waiting_review,false);assert.equal(state.synced_revision,2);assert.equal(state.status,'integrated');
await assert.rejects(()=>rpc('docito_quote_backup',['gerusa041188@gmail.com','senha-sintetica-grande']),/proprietário/);
await db.exec("set role anon");
await assert.rejects(
  () =>
    sql("select public.docito_approve_quote($1,2,$2)", [
      id,
      "julio.goiano@gmail.com",
    ]),
  /permission denied/,
);
await db.exec("reset role;set role service_role");
await assert.rejects(
  () => sql("select * from private.quote_outbox"),
  /permission denied/,
);
await db.exec("reset role");
const beforeRestore=(await sql("select jsonb_agg(to_jsonb(t) order by id) data from public.orcamentos t"))[0].data;
const archive=await db.dumpDataDir();const restored=new PGlite({loadDataDir:archive});assert.deepEqual((await restored.query("select jsonb_agg(to_jsonb(t) order by id) data from public.orcamentos t")).rows[0].data,beforeRestore);await restored.close();
await db.close();
console.log(
  "PASS: aprovação explícita, fila durável, edição isolada, ACK obrigatório, retry, revisão e permissões da origem",
);
