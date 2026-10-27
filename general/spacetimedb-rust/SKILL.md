---
name: spacetimedb-rust
description: Develop SpacetimeDB server modules in Rust. Use when writing reducers, tables, or module logic.
license: Apache-2.0
metadata:
  author: clockworklabs
  version: "2.1"
  upstream_source: "github.com/clockworklabs/SpacetimeDB/blob/master/skills/rust-server/SKILL.md  (upstream RENAMED spacetimedb-rust -> rust-server since our sync)"
  upstream_synced: "2026-04-25 (base); re-checked 2026-08-03; MERGED upstream skills commits through 2026-10-24 (524b4487d rust-server +98: defaults, owned-String keys, view primary keys, Filter::Sql, procedures/HTTP; checked against crates 2.1.0 vs 2.13.0)"
  upstream_divergence: "2026-08-03: upstream REWROTE this skill into a terse ~291-line 'SDK Reference' — now a SUBSET of our richer copy (which retains the older upstream's HALLUCINATED-APIs warnings, Common Mistakes table, detailed Views/Procedures/Event-Tables). Deliberately NOT replaced (would lose depth). Harvested the only real delta: try_insert()/? note. We are AHEAD of upstream on 2.6/2.7 (upstream still v2.0-stamped)."
  release_notes: "https://github.com/clockworklabs/SpacetimeDB/releases/tag/v2.13.0"
  version_reality: "2026-10-27: UPGRADE COMPLETE 10-26 — crate 2.13.0 in ALL 8 modules (Rust 1.97.1 via STDB_RUST_TOOLCHAIN); CLI 2.13.0 launcher-delegated (the banner 'current: v2.1.0' is the launcher's self-version — `spacetime version list` is the truth); TS SDK ^2.13.0; scripts/stdb-backup.sh reads the 2.13 describe shape (sections[].Tables[].source_name). CLI 2.13 codegen = camelCase handles even with CaseConversionPolicy::None; CLI 2.1 still generates identical snake bindings from a 2.13-built module. See stdb-version-gap-2026-08 memory."
  local_additions: "What's new in 2.1.0 callout; Nexus Terminal Build & Deploy section; 2.6 :sender-Identity migration note; [2026-08-03] finalized VIEW-BASED per-user security model + version-gap + stale-landmine corrections (see stdb-finalized-security-model memory + recovery/RLS_*.md)"
---


# SpacetimeDB Rust Module Development

SpacetimeDB modules are WebAssembly applications that run inside the database. They define tables to store data and reducers to modify data. Clients connect directly to the database and execute application logic inside it.

> **Tested with:** SpacetimeDB 2.0+ APIs


## What's new in 2.1.0 (relative to 2.0.2) — HISTORY: all modules, CLI and SDK are on 2.13.0 since 2026-10-26

Non-breaking. Notable for module authors:

- **View table accessors gained `count`** — call `.count()` on a view's query result for cheap cardinality checks without materializing rows.
- **One-shot schedule cleanup** now refreshes views correctly (no manual workaround needed).
- **Sealed commitlog resumption** — internal durability fix; no module-author impact.
- **C++ + Unreal SDK** brought up to 2.0 parity (irrelevant for Rust modules but unblocks downstream consumers).

The 2.0 → 2.1 upgrade requires no Rust source changes. Cargo's `"2.0"` constraint resolves to 2.1.x; run `cargo update -p spacetimedb` if you want the lockfile bump.

## HALLUCINATED APIs — DO NOT USE

**These APIs/patterns are incorrect. LLMs frequently hallucinate them.**

Both macro forms are valid in 2.0: `#[spacetimedb::table(...)]` / `#[table(...)]` and `#[spacetimedb::reducer]` / `#[reducer]`.

```rust
#[derive(Table)]                // Tables use #[table] attribute, not derive
#[derive(Reducer)]              // Reducers use #[reducer] attribute

// WRONG — SpacetimeType on tables
#[derive(SpacetimeType)]        // DO NOT use on #[table] structs!
#[table(accessor = my_table)]
pub struct MyTable { ... }

// WRONG — mutable context
pub fn my_reducer(ctx: &mut ReducerContext, ...) { }  // Should be &ReducerContext

// WRONG — table access without parentheses
ctx.db.player                   // Should be ctx.db.player()
ctx.db.player.find(id)          // Should be ctx.db.player().id().find(&id)

// WRONG — old 1.0 patterns
ctx.sender                      // Use ctx.sender() — method, not field (2.0)
.with_module_name("db")         // Use .with_database_name() (2.0)
ctx.db.user().name().update(..) // Update only via primary key (2.0)
```

### CORRECT PATTERNS:

```rust
use spacetimedb::{table, reducer, Table, ReducerContext, Identity, Timestamp};
use spacetimedb::SpacetimeType;  // Only for custom types, NOT tables

// CORRECT TABLE — accessor, not name; no SpacetimeType derive!
#[table(accessor = player, public)]
pub struct Player {
    #[primary_key]
    pub id: u64,
    pub name: String,
}

// CORRECT REDUCER — immutable context, sender() is a method
#[reducer]
pub fn create_player(ctx: &ReducerContext, name: String) {
    ctx.db.player().insert(Player { id: 0, name });
}

// CORRECT TABLE ACCESS — methods with parentheses, sender() method
let player = ctx.db.player().id().find(&player_id);
let caller = ctx.sender();
```

### DO NOT:
- **Derive `SpacetimeType` on `#[table]` structs** — the macro handles this
- **Use mutable context** — `&ReducerContext`, not `&mut ReducerContext`
- **Forget `Table` trait import** — required for table operations
- **Use field access for tables** — `ctx.db.player()` not `ctx.db.player`
- **Use `ctx.sender`** — it's `ctx.sender()` (method) in 2.0


## Common Mistakes Table

| Wrong | Right | Error |
|-------|-------|-------|
| `#[table(accessor = "my_table")]` | `#[table(accessor = my_table)]` | String literals not allowed |
| Missing `public` on table | Add `public` flag | Clients can't subscribe |
| Network/filesystem in reducer | Use procedures instead | Sandbox violation |
| Panic for expected errors | Return `Result<(), String>` | WASM instance destroyed |


## Hard Requirements

1. **DO NOT derive `SpacetimeType` on `#[table]` structs** — the macro handles this
2. **Import `Table` trait** — required for all table operations
3. **Use `&ReducerContext`** — not `&mut ReducerContext`
4. **Tables are methods** — `ctx.db.table()` not `ctx.db.table`
5. **Use `ctx.sender()`** — method call, not field access (2.0)
6. **Use `accessor =` for API handles** — `name = "..."` is optional canonical naming in table/index attributes
7. **Reducers must be deterministic** — no filesystem, network, timers, or external RNG
8. **Use `ctx.rng()`** — not `rand` crate for random numbers
9. **Add `public` flag** — if clients need to subscribe to a table
10. **Update only via primary key** — use delete+insert for non-PK changes (2.0)


## Project Setup

```toml
[package]
name = "my-module"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib"]

[dependencies]
spacetimedb = { workspace = true }
log = "0.4"
```

### Essential Imports

```rust
use spacetimedb::{ReducerContext, Table};
use spacetimedb::{Identity, Timestamp, ConnectionId, ScheduleAt};
```

## Table Definitions

```rust
#[spacetimedb::table(accessor = player, public)]
pub struct Player {
    #[primary_key]
    #[auto_inc]
    id: u64,
    name: String,
    score: u32,
}
```

### Table Attributes

| Attribute | Description |
|-----------|-------------|
| `accessor = identifier` | Required. The API name used in `ctx.db.{accessor}()` |
| `public` | Makes table visible to clients via subscriptions |
| `scheduled(function_name)` | Creates a schedule table that triggers the named reducer or procedure |
| `index(accessor = idx, btree(columns = [a, b]))` | Multi-column index |

### Column Attributes

| Attribute | Description |
|-----------|-------------|
| `#[primary_key]` | Unique identifier for the row (one per table max) |
| `#[unique]` | Enforces uniqueness, enables `find()` method |
| `#[auto_inc]` | Auto-generates unique integer values when inserting 0 |
| `#[index(btree)]` | Creates a B-tree index for efficient lookups |

### Supported Column Types

**Primitives**: `u8`-`u256`, `i8`-`i256`, `f32`, `f64`, `bool`, `String`

**SpacetimeDB Types**: `Identity`, `ConnectionId`, `Timestamp`, `Uuid`, `ScheduleAt`

**Collections**: `Vec<T>`, `Option<T>`, `Result<T, E>`

**Custom Types**: Any struct/enum with `#[derive(SpacetimeType)]`


## Reducers

```rust
#[spacetimedb::reducer]
pub fn create_player(ctx: &ReducerContext, name: String) -> Result<(), String> {
    if name.is_empty() {
        return Err("Name cannot be empty".to_string());
    }
    ctx.db.player().insert(Player { id: 0, name, score: 0 });
    Ok(())
}
```

### Reducer Rules

1. First parameter must be `&ReducerContext`
2. Return `()`, `Result<(), String>`, or `Result<(), E>` where `E: Display`
3. All changes roll back on panic or `Err` return
4. Must import `Table` trait: `use spacetimedb::Table;`

### ReducerContext

```rust
ctx.db              // Database access
ctx.sender()        // Identity of the caller (method, not field!)
ctx.connection_id() // Option<ConnectionId> (None for scheduled/system reducers)
ctx.timestamp       // Invocation timestamp
ctx.database_identity() // Module's own identity — added in crate 2.3 (identity() deprecated there); on crate 2.1 ONLY ctx.identity() exists
ctx.rng()            // Deterministic RNG (method, not field!)
```


## Table Operations

### Insert

```rust
// Insert returns the row with auto_inc values populated
let player = ctx.db.player().insert(Player { id: 0, name: "Alice".into(), score: 100 });
log::info!("Created player with id: {}", player.id);
```

**`insert()` PANICS on a constraint violation** (unique/PK collision) — and a panic destroys the WASM instance (expensive). In a reducer that returns `Result`, use **`try_insert()` with `?`** instead (upstream 2026-08 addition):
```rust
ctx.db.player().try_insert(Player { id: 0, name, score: 0 })?;  // Err on violation, no panic
```

### Find and Filter

```rust
// Find by unique/primary key — returns Option
if let Some(player) = ctx.db.player().id().find(&123) {
    log::info!("Found: {}", player.name);
}

// Optional clarity: typed literals can avoid inference ambiguity
if let Some(player) = ctx.db.player().id().find(&123u64) {
    log::info!("Found: {}", player.name);
}

// Filter by indexed column — returns iterator
for player in ctx.db.player().name().filter(&"Alice".to_string()) {
    log::info!("Player: {}", player.name);
}

// Full table scan
for player in ctx.db.player().iter() { }
let total = ctx.db.player().count();
```

### Update

```rust
// Update via primary key (2.0: only primary key has update)
if let Some(player) = ctx.db.player().id().find(&123) {
    ctx.db.player().id().update(Player { score: player.score + 10, ..player });
}

// For non-PK changes: delete + insert
if let Some(old) = ctx.db.player().id().find(&id) {
    ctx.db.player().id().delete(&id);
    ctx.db.player().insert(Player { name: new_name, ..old });
}
```

### Delete

```rust
// Delete by primary key
ctx.db.player().id().delete(&123);

// Delete by indexed column (collect first to avoid iterator invalidation)
let to_remove: Vec<u64> = ctx.db.player().name().filter(&"Alice".to_string())
    .map(|p| p.id)
    .collect();
for id in to_remove {
    ctx.db.player().id().delete(&id);
}
```


## Indexes

```rust
// Single-column index
#[spacetimedb::table(accessor = player, public)]
pub struct Player {
    #[primary_key]
    id: u64,
    #[index(btree)]
    level: u32,
    name: String,
}

// Multi-column index
#[spacetimedb::table(
    accessor = score, public,
    index(accessor = by_player_level, btree(columns = [player_id, level]))
)]
pub struct Score {
    player_id: u32,
    level: u32,
    points: i64,
}

// Multi-column index querying: prefix match (first column only)
for s in ctx.db.score().by_player_level().filter(&(42,)) {
    log::info!("Player 42, any level: {} pts", s.points);
}

// Full match (both columns)
for s in ctx.db.score().by_player_level().filter(&(42, 5)) {
    log::info!("Player 42, level 5: {} pts", s.points);
}
```


## Event Tables (2.0)

Reducer callbacks are removed in 2.0. Use event tables + `on_insert` instead.

```rust
#[table(accessor = damage_event, public, event)]
pub struct DamageEvent {
    pub target: Identity,
    pub amount: u32,
}

#[reducer]
fn deal_damage(ctx: &ReducerContext, target: Identity, amount: u32) {
    ctx.db.damage_event().insert(DamageEvent { target, amount });
}
```

Client subscribes and uses `on_insert`:
```rust
conn.db.damage_event().on_insert(|ctx, event| {
    play_damage_animation(event.target, event.amount);
});
```

Event tables must be subscribed explicitly — they are excluded from `subscribe_to_all_tables()`.


## Views

Views are read-only server-side queries that clients subscribe to like tables. Useful for filtering, joining, or aggregating before sending data to clients.

Two return shapes with very different update semantics:

| Shape | Update model | Output type | Iteration |
|---|---|---|---|
| `impl Query<T>` (query-builder) | **Incremental** — engine analyzes and updates only affected rows | Source row type only (T must be a `#[table]` type) | Engine handles scanning |
| `Vec<T>` / `Option<T>` (procedural) | **Full re-evaluation** when read-set changes (black box) | Any `#[derive(SpacetimeType)]` struct (custom shape) | **Indexed lookups only** — `.iter()` is forbidden |

### Query-builder views (incremental, source row type)

```rust
use spacetimedb::{view, AnonymousViewContext, ViewContext, Query};

// Anonymous: same result for everyone — materialized once, shared.
#[view(accessor = high_scorers, public)]
fn high_scorers(ctx: &AnonymousViewContext) -> impl Query<Player> {
    ctx.from.player()
        .r#where(|p| p.score.gte(1000u64))
        .filter(|p| p.name.ne("BOT"))
}

// Per-user: ctx.sender filter; materialized separately for each subscriber.
#[view(accessor = my_player, public)]
fn my_player(ctx: &ViewContext) -> Option<Player> {
    ctx.db.player().identity().find(&ctx.sender())
}

// Semijoin: keep left rows that have a match on the right (or vice versa).
#[view(accessor = players_with_levels, public)]
fn players_with_levels(ctx: &AnonymousViewContext) -> impl Query<Player> {
    ctx.from.player()
        .left_semijoin(ctx.from.player_level(), |p, pl| p.id.eq(pl.player_id))
}
```

**Operators on query-builder views** — much richer than subscription `WHERE` (which only supports `=`):

| Operation | Method |
|---|---|
| Equal / not equal | `eq`, `ne` |
| Less / less or eq | `lt`, `lte` |
| Greater / greater or eq | `gt`, `gte` |
| Boolean | `.and(...)`, `.or(...)`, `.not()` |
| Filter | `.r#where(\|row\| ...)` or `.filter(\|row\| ...)` (alias) |
| Join | `.left_semijoin(other, \|l, r\| ...)`, `.right_semijoin(other, \|l, r\| ...)` |

Join predicates **must use indexed columns**. Multi-column indexes not supported in semijoin predicates yet.

### Procedural views (full re-eval, custom shape)

```rust
use spacetimedb::{view, AnonymousViewContext, ViewContext, SpacetimeType};

#[derive(SpacetimeType)]
pub struct PlayerCountRow { count: u64 }

#[view(accessor = player_count, public)]
fn player_count(ctx: &AnonymousViewContext) -> Vec<PlayerCountRow> {
    vec![PlayerCountRow { count: ctx.db.player().count() }]
}

// Procedural views CAN'T use .iter(). They must drive iteration through indexed
// lookups (.find / .filter on indexed columns) or .count(). For "give me all
// rows of table X" use a query-builder view instead.
#[view(accessor = players_at_level_2, public)]
fn players_at_level_2(ctx: &AnonymousViewContext) -> Vec<Player> {
    ctx.db.player().level().filter(&2u64).collect()
}
```

**Why `.iter()` is forbidden in procedural views:** procedural views are Turing-complete black boxes. The engine tracks which rows the function reads (the "read set") and re-runs the entire function when any row in that set changes. A `.iter()` call would put every row of the table in the read set, triggering re-evaluation on every write — prohibitively expensive at scale. Index lookups give the engine a precise read-set so re-evaluation only fires when a relevant row changes.

`count()` is exempt — it's a constant-time metadata lookup.

### When to use which

| Use case | Recommended | Why |
|---|---|---|
| Filtering / joining many rows | Query-builder | Incremental updates, engine optimizes plan |
| Custom output shape (collapse Option, compute fields) | Procedural | Only procedural can return `SpacetimeType` structs distinct from source rows |
| Aggregation / counts | Procedural | `count()` + return a `Vec<CountRow>` |
| Per-user materialization | Either with `ViewContext` | Pays per-client compute cost |
| Cross-client shared materialization | Either with `AnonymousViewContext` | Materialized once, shared — much cheaper at scale |

**Strongly prefer `AnonymousViewContext` when the result is the same for all clients.** Per-user views (using `ctx.sender()`) require separate computation and change-tracking per subscriber — at 1k clients, that's 1k materializations.

### Subscribing to views from clients

Same SQL as tables:

```sql
SELECT * FROM high_scorers
SELECT * FROM player_and_level WHERE id = 2
```

But subscription-side `WHERE` retains the standard subscription limitations (only `=`, can't filter `Option<T>` fields). View-internal `where` clauses use the richer query-builder operators above.

### Workaround pattern: shadow-index table for `Option<T>` subscription filtering

STDB 2.0/2.1 subscriptions cannot filter on `Option<T>` columns (only `=` on non-null primitives). If you have a denormalized `Option<String> room_id` column added for scoping that turned out to be unfilterable, **a shadow-index table is the canonical workaround**:

1. Define a parallel public table whose `room_id: String` is non-null from creation:

```rust
#[spacetimedb::table(accessor = reaction_room_index, public)]
pub struct ReactionRoomIndex {
    #[primary_key]
    pub reaction_id: String,        // FK into source table
    #[index(btree)]
    pub room_id: String,            // non-null, filterable
    pub message_id: String,
    pub user_id: String,
    pub emoji: String,
    pub created_at: u64,
}
```

2. In the source-table reducer (`add_reaction`, `edit_message`, etc.), dual-write to the index inside the same transaction. If the source's `room_id` is `None`, skip the index insert and log a warning (don't fail the source write).
3. In cascade-delete paths (message delete, etc.), delete the index row alongside the source row.
4. Provide an idempotent `backfill_*_index` admin reducer that walks the source table and populates missing index rows.
5. Clients subscribe to `SELECT * FROM reaction_room_index WHERE room_id = '...'` instead of the source table. The index carries enough fields to render UI without joining back.

**Why not views for this:** query-builder views can't transform `Option<String>` to `String` (output is the source row type). Procedural views can transform shape but require full re-eval on every write and can't use `.iter()` to drive iteration over the source table. Index tables give incremental updates AND non-null projection in one move — the right tool for this specific limitation.

This pattern was developed in the Nexus Terminal workspace's `shadowing-stork` plan; documenting here so other modules hitting the same wall don't have to rediscover it.


## Lifecycle Reducers

```rust
#[spacetimedb::reducer(init)]
pub fn init(ctx: &ReducerContext) -> Result<(), String> {
    log::info!("Database initializing...");
    ctx.db.config().insert(Config {
        id: 0,
        max_players: 100,
        game_mode: "default".to_string(),
    });
    Ok(())
}

#[spacetimedb::reducer(client_connected)]
pub fn on_connect(ctx: &ReducerContext) -> Result<(), String> {
    let caller = ctx.sender();
    log::info!("Client connected: {}", caller);

    if let Some(user) = ctx.db.user().identity().find(&caller) {
        ctx.db.user().identity().update(User { online: true, ..user });
    } else {
        ctx.db.user().insert(User {
            identity: caller,
            name: format!("User-{}", &caller.to_hex()[..8]),
            online: true,
        });
    }
    Ok(())
}

#[spacetimedb::reducer(client_disconnected)]
pub fn on_disconnect(ctx: &ReducerContext) -> Result<(), String> {
    let caller = ctx.sender();
    if let Some(user) = ctx.db.user().identity().find(&caller) {
        ctx.db.user().identity().update(User { online: false, ..user });
    }
    Ok(())
}
```


## Scheduled Reducers

```rust
use spacetimedb::ScheduleAt;
use std::time::Duration;

#[spacetimedb::table(accessor = game_tick_schedule, scheduled(game_tick))]
pub struct GameTickSchedule {
    #[primary_key]
    #[auto_inc]
    scheduled_id: u64,
    scheduled_at: ScheduleAt,
}

#[spacetimedb::reducer]
fn game_tick(ctx: &ReducerContext, schedule: GameTickSchedule) {
    if !ctx.sender_auth().is_internal() { return; }
    log::info!("Game tick at {:?}", ctx.timestamp);
}

// Schedule at interval (e.g., in init reducer)
ctx.db.game_tick_schedule().insert(GameTickSchedule {
    scheduled_id: 0,
    scheduled_at: ScheduleAt::Interval(Duration::from_millis(100).into()),
});

// Schedule at specific time
let run_at = ctx.timestamp + Duration::from_secs(delay_secs);
ctx.db.reminder_schedule().insert(ReminderSchedule {
    scheduled_id: 0,
    scheduled_at: ScheduleAt::Time(run_at),
});
```


## Identity and Authentication

```rust
#[spacetimedb::table(accessor = user, public)]
pub struct User {
    #[primary_key]
    identity: Identity,
    name: String,
    online: bool,
}

#[spacetimedb::reducer]
pub fn set_name(ctx: &ReducerContext, new_name: String) -> Result<(), String> {
    let caller = ctx.sender();
    let user = ctx.db.user().identity().find(&caller)
        .ok_or("User not found — connect first")?;
    ctx.db.user().identity().update(User { name: new_name, ..user });
    Ok(())
}
```

### Owner-Only Reducer Pattern

```rust
fn require_owner(ctx: &ReducerContext, entity_owner: &Identity) -> Result<(), String> {
    if ctx.sender() != *entity_owner {
        Err("Not authorized: you don't own this entity".to_string())
    } else {
        Ok(())
    }
}

#[spacetimedb::reducer]
pub fn rename_character(ctx: &ReducerContext, char_id: u64, new_name: String) -> Result<(), String> {
    let character = ctx.db.character().id().find(&char_id)
        .ok_or("Character not found")?;
    require_owner(ctx, &character.owner)?;
    ctx.db.character().id().update(Character { name: new_name, ..character });
    Ok(())
}
```


## Error Handling

```rust
// Sender error — return Err (user sees message, transaction rolls back cleanly)
#[spacetimedb::reducer]
pub fn transfer(ctx: &ReducerContext, to: Identity, amount: u64) -> Result<(), String> {
    let sender = ctx.db.wallet().identity().find(&ctx.sender())
        .ok_or("Wallet not found")?;
    if sender.balance < amount {
        return Err("Insufficient balance".to_string());
    }
    // ... proceed with transfer
    Ok(())
}

// Programmer error — panic (destroys the WASM instance, expensive!)
// Only use for truly impossible states
#[spacetimedb::reducer]
pub fn process(ctx: &ReducerContext, id: u64) {
    let item = ctx.db.item().id().find(&id)
        .expect("BUG: item should exist at this point");
    // ...
}
```

Prefer `Result<(), String>` for all expected failure cases. Panics destroy and recreate the WASM instance.


## Procedures (Beta)

> Procedures are STABLE from crate 2.5 (no `unstable` needed); on crate ≤2.4 (our modules until 2026-10-26; all are 2.13 now) they are behind `unstable`. We keep
> `features = ["unstable"]` everywhere anyway — RLS (`client_visibility_filter`), views and HTTP handlers are still gated in 2.13.
> In `Cargo.toml`: `spacetimedb = { version = "...", features = ["unstable"] }`

```rust
use spacetimedb::{procedure, ProcedureContext};

#[procedure]
fn save_external_data(ctx: &mut ProcedureContext, url: String) -> Result<(), String> {
    let data = fetch_from_url(&url)?;
    ctx.try_with_tx(|tx| {
        tx.db.external_data().insert(ExternalData { id: 0, content: data });
        Ok(())
    })?;
    Ok(())
}
```

| Reducers | Procedures |
|----------|------------|
| `&ReducerContext` (immutable) | `&mut ProcedureContext` (mutable) |
| Direct `ctx.db` access | Must use `ctx.with_tx()` |
| No HTTP/network | HTTP allowed |
| No return values | Can return data |


## Upstream additions merged 2026-10-24 (version-gated — check the module's locked crate before using)

| Topic | API (upstream skill, verified in crate source) | crate 2.1.0 | crate 2.13.0 |
|---|---|---|---|
| Migration-safe new column | `#[default(true)]` / `#[default(None::<T>)]` on an appended field | ✅ | ✅ (`&'static str` defaults ≥2.8.1) |
| Owned `String` index keys | `find`/`delete` on a `String` column take `String`/`&String`, not `&str` (`.delete("Alice".to_string())`) | ✅ | ✅ |
| Connection id | `ctx.connection_id()` — a method, `None` outside connection-scoped calls | ✅ | ✅ |
| Module identity | `ctx.database_identity()` | ❌ (use `ctx.identity()`) | ✅ (`identity()` deprecated) |
| Visibility filter | `#[client_visibility_filter] const F: Filter = Filter::Sql("SELECT * FROM t WHERE owner = :sender");` (`:sender` is a typed Identity — column must be `Identity`) | ✅ unstable | ✅ unstable |
| View primary key | `#[view(accessor = x, public, primary_key = sku)]` — explicit, NOT inherited from the source table | ❌ | ✅ (≥2.6) |
| Procedural view access | indexed `find`/`filter` only, never `iter()` — start from an index (`ctx.db.entity().active().filter(true)`) | ✅ | ✅ |
| Query-builder `String` compare | `row.label.eq("active".to_string())` (owned `String`) | ✅ | ✅ |
| Procedures | `#[procedure] fn f(ctx: &mut ProcedureContext, …) -> T` returning typed values | unstable | stable (≥2.5) |
| Short transactions | `ctx.with_tx(\|tx\| …)` — tables via `tx.db`, returns the closure's value directly (no `unwrap`) | ✅ | ✅ |
| Outbound HTTP | `ctx.http.get(url)`; else `Request::builder().method("POST").uri(url).body(Body::from_bytes(data))` + `ctx.http.send(req)` | ✅ unstable | ✅ (gzip/br decoded for you ≥2.10.2 — drop manual decompression) |
| Scheduled procedure | ordinary scheduled table; the target is `#[procedure]` taking `&mut ProcedureContext` + the row | ✅ unstable | ✅ |
| Inbound HTTP | `use spacetimedb::http::{handler, router, Body, HandlerContext, Request, Response, Router};` `#[handler] fn health(_ctx: &mut HandlerContext, _r: Request) -> Response`, one `#[router] fn routes() -> Router { Router::new().get("/health", health) }`; `HandlerContext` has no `db` — use `ctx.with_tx`; bodies must own their data | ❌ | ✅ unstable |
| Module env values | `#[env]` declared typed config/secrets, read via the context | ❌ | ✅ (2.12) |
| Misc | `spacetimedb::sats::{u256, i256}`; `ConnectionId::from_u128(v)` | ✅ | ✅ |

In-memory module unit tests (reducers, procedures with `with_tx`, env values, views) arrive in 2.12/2.13 — a reason to upgrade the module crate.

## Custom Types

```rust
use spacetimedb::SpacetimeType;

#[derive(SpacetimeType)]
pub enum PlayerStatus { Active, Idle, Away }

#[derive(SpacetimeType)]
pub struct Position { x: f32, y: f32, z: f32 }

// Use in table (DO NOT derive SpacetimeType on the table!)
#[spacetimedb::table(accessor = player, public)]
pub struct Player {
    #[primary_key]
    id: u64,
    status: PlayerStatus,
    position: Position,
}
```


## Commands

```bash
spacetime build
spacetime publish my_database --module-path .
spacetime publish my_database --clear-database --module-path .
spacetime logs my_database
spacetime call my_database create_player "Alice"
spacetime sql my_database "SELECT * FROM player"
spacetime generate --lang rust --out-dir <client>/src/module_bindings --module-path <backend-dir>
```

## Important Constraints

1. **No Global State**: Static/global variables are undefined behavior across reducer calls
2. **No Side Effects**: Reducers cannot make network requests or file I/O
3. **Deterministic Execution**: Use `ctx.rng()` and `ctx.new_uuid_*()` for randomness
4. **Transactional**: All reducer changes roll back on failure
5. **Isolated**: Reducers don't see concurrent changes until commit

---

## Nexus Terminal — Build & Deploy (Workspace-Specific)

This section documents the non-standard Rust/SpacetimeDB toolchain setup in the Nexus Terminal workspace on Replit. **Always use the npm wrapper scripts** — never run `spacetime build` or `spacetime publish` directly.

### Why Custom Scripts?

The workspace has a non-standard Rust installation that requires specific environment variables. The deploy scripts (`scripts/spacetimedb-publish-core.sh`) handle all of this automatically:

1. **GLIBC_TUNABLES workaround** — Replit's `LD_AUDIT` runtime loader consumes static TLS space. Rust 1.92+ crashes with "cannot allocate memory in static TLS block" without:
   ```bash
   export GLIBC_TUNABLES=glibc.rtld.optional_static_tls=65536
   ```

2. **Custom tool paths** — Rustup, Cargo, and the SpacetimeDB CLI are in non-standard locations:
   ```bash
   SPACETIME_CLI="$WORKSPACE/.local/bin/spacetime"
   CARGO="$WORKSPACE/.cargo/bin/cargo"
   RUSTUP_HOME="$WORKSPACE/.rustup/"
   ```

3. **Pinned Rust version** — Rust 1.97.1 matches the SpacetimeDB 2.13 MSRV (the publish wrappers pin it via STDB_RUST_TOOLCHAIN):
   ```bash
   export RUSTUP_TOOLCHAIN="1.97.1"
   ```

4. **Nix linker** — A Nix-provided `clang` wrapper must be on PATH for proc-macro compilation:
   ```bash
   export PATH="/nix/store/.../clang-wrapper-.../bin:$PATH"
   ```

5. **Pre-built WASM** — Scripts run `cargo build --target wasm32-unknown-unknown --release` manually, then pass the `.wasm` binary to `spacetime publish --bin-path`. This avoids `spacetime build` which may use incorrect toolchain settings.

> **Per-module toolchain (2026-10-24):** a wrapper sets `STDB_RUST_TOOLCHAIN="1.97.1"` once its module's crate is ≥2.12 (MSRV 1.97);
> `spacetimedb-publish-core.sh` then puts that rustup toolchain's bin + the runtime `gcc` first on PATH. Unset = the wrapper default (1.97.1 since 2026-10-26).
> First module on crate 2.13: **nexus-blaster-lab** (published 2026-10-24 9:19 PM PT, commit cf5a33841). All 8 modules on 2.13 since 2026-10-26 (scripts/stdb-upgrade-module.sh).

### npm Deploy Commands

```bash
npm run stdb:deploy            # Build + generate types + publish (safe; preserves data)
npm run stdb:deploy:generate   # Generate TypeScript client types only (builds WASM first)
npm run stdb:deploy:publish    # Publish only (safe)
npm run stdb:deploy:clear      # DESTRUCTIVE — wipe data + publish (NEVER without explicit user permission)
npm run stdb:logs              # Tail live module logs
```

### Multi-Module Architecture

The workspace has multiple SpacetimeDB modules, each with its own wrapper script:

| Module | npm Script | Wrapper Script | Module Name |
|--------|-----------|----------------|-------------|
| Platform | `stdb:deploy` | `spacetimedb-publish.sh` | `nexus-terminal` |
| Financial | `stdb:deploy:financial` | `spacetimedb-publish-financial.sh` | `nexus-financial` |
| Lattice | — | `spacetimedb-publish-lattice.sh` | `nexus-lattice` |
| NexusSense | — | `spacetimedb-publish-nexus-sense.sh` | `nexus-nexus-sense` |
| BlasterLab | — | `spacetimedb-publish-blaster-lab.sh` | `nexus-blaster-lab` |
| Chat | — | `spacetimedb-publish-chat.sh` | `nexus-chat` |
| NexusCortex | `stdb:deploy:cortex` | `spacetimedb-publish-nexus-cortex.sh` | `nexus-nexus-cortex` |

All wrapper scripts source `spacetimedb-publish-core.sh` which contains the shared build logic.

### Schema Change Safety Rules

1. **New fields MUST be `Option<T>` at the END with a default annotation** — `#[default(None::<T>)] pub new_field: Option<T>,`. Maincloud ≥2.6
   REJECTS an added column without one ("requires a default value annotation"); crate 2.1 already supports `#[default(CONSTANT)]` (CHAT
   e7dc4dd30, lattice render_json). Never on primary_key/unique/auto_inc columns; non-Option `String` defaults need crate ≥2.8.1
2. **Never remove columns** — mark as deprecated, remove in a future version after migration
3. **Never change column types** — add a new column, migrate data, deprecate old
4. **`npm run stdb:deploy`** is safe by default — preserves all data
5. **`npm run stdb:deploy:clear`** wipes data — NEVER run without asking the user first
6. If publish fails due to schema conflict, **STOP and report the error** — do not automatically retry with `--clear`

### Manual `cargo check` (for IDE / development)

```bash
export GLIBC_TUNABLES=glibc.rtld.optional_static_tls=65536
export RUSTUP_TOOLCHAIN=1.97.1
export PATH="$WORKSPACE/.cargo/bin:/usr/bin:/bin:$PATH"

cargo check --manifest-path spacetimedb-module/Cargo.toml
cargo check --manifest-path modules/financial/spacetimedb-module/Cargo.toml
```

### SpacetimeDB 2.6 RLS `:sender` is a typed `Identity` parameter (BREAKING, learned 2026-06)

Maincloud auto-upgraded to 2.6 (Clockwork-managed; not operator-controlled). **PR #5287 ("Parameterized query plans")** retyped the `#[client_visibility_filter]` `:sender` from a substituted literal into a typed **`Identity` (U256) parameter**. The SQL/RLS type-checker now requires the compared column to be `Identity` or bytes. A filter comparing a **hex `String`** column to `:sender` is rejected:

```
Unexpected type: (expected) (__identity__: U256) != String (inferred)
```

This silently broke RLS on every module that stored the connection identity as a hex `String` (the common AuthBridge `user_identity_links.stdb_identity = :sender` pattern). Grandfathered filters keep working until the next publish; a fresh publish re-validates and **fails atomically** (no data change).

**Fix — migrate the RLS column `String → Identity`:**
```rust
// BEFORE: pub stdb_identity: String,   (hex)     → RLS rejected on 2.6
// AFTER:
use spacetimedb::Identity;
#[primary_key] #[index(btree)]
pub stdb_identity: Identity,            // native → `WHERE stdb_identity = :sender` type-checks
```
Derive it from `ctx.sender()` server-side (never a reducer arg). Update all `.find(&hex)`/`.delete(&hex)` to `.find(&ctx.sender())`. **Composite-key cache tables**: migrate the `requester_id` column to `Identity` but keep the `cache_key: String` PK (built from `sender_hex` via `format!`); the refresh writer uses `let sender = ctx.sender();` for the column + `requester_id().filter(&sender)`.

**`Option<Identity>` does NOT satisfy the filter** (sum type → not `is_identity()`/`is_bytes()`). And a bare `Identity` column added to an existing table is a *required* field = breaking. So the only ways to land the migration: (a) a **new table** with the required `Identity` column (new tables allow required fields), or (b) a one-time **`--clear`** to change the existing column's type. Changing a column type is breaking → needs `--clear` (back up + restore).

**2.6 literal coercion (also learned 2026-06):** a *quoted hex string literal* still coerces to `Identity` in a column comparison (`WHERE id = 'abc…'` type-checks), so existing client subscription filters didn't break — only the fixed-type `:sender` *parameter* can't coerce. Canonical Identity SQL literal is **unquoted `0x<hex>`**; prefer it in new client `WHERE` clauses. Identity `/call` arg encoding = `["0x<hex>"]` (single-element array, 0x-prefixed). `Option` over `/call` = `{"some":v}` (object) or `[0,v]`/`[1,[]]` (tag) — both accepted.

### 🔴 THE finalized per-user SECURITY MODEL is VIEW-BASED, not `client_visibility_filter` (grounded 2026-08-03)

The 2.6 `:sender` migration above was only HALF the DBPEN-driven refactor. The other half — and the one this skill (and upstream) under-documents — is that **`client_visibility_filter` is NOT the mechanism for per-user subscribable data.** DBPEN proved that **client-side `WHERE` is not security**: a malicious client just subscribes `SELECT *`, and maincloud has no JOIN-RLS. Real exploit found: an outside user read a private chat server's messages.

**The mandatory pattern for anything a client subscribes to (3 tiers):**
1. **Identity bridge** — `user_identity_links { stdb_identity: Identity PK, user_id: String }`, one `client_visibility_filter WHERE stdb_identity = :sender`. Written from `ctx.sender()`.
2. **Admin/credential caches** — the ONLY other place `client_visibility_filter` is used; the `:sender`-compared column (`requester_id`/`reader_identity`/`owner_identity`) is native `Identity`.
3. **Per-user data (the bulk)** — the table is **PRIVATE** (omit `public`), carries `owner_user_id: String` (app id), and is exposed ONLY through a `public` `#[view]` `ViewContext` `my_<table>` that resolves `ctx.sender()`→`user_id` and returns owned rows; anonymous → empty:
   ```rust
   fn caller_user_id(ctx: &ViewContext) -> Option<String> {
       ctx.db.user_identity_links().stdb_identity().find(&ctx.sender()).map(|l| l.user_id)
   }
   #[spacetimedb::view(accessor = my_cortex_tasks, public)]
   fn my_cortex_tasks(ctx: &ViewContext) -> Vec<CortexTask> {
       match caller_user_id(ctx) { Some(u) => ctx.db.cortex_tasks().owner_user_id().filter(&u).collect(), None => Vec::new() }
   }
   ```
   Cross-table scoping the filter can't do → a **server-side join INSIDE the view** (indexed lookups only, never `.iter()`); owner-less / `Option`-keyed tables use a **shadow index table** (`agent_owner_index`, `room_server_index`).

**Other established rules new code MUST follow:** admin/owner trust is **unforgeable-only** (`is_admin_or_developer` = notary-verified `verified_identity_links` + `admin_user_ids` roster, OR an explicit `admin_identities` allowlist — the legacy forgeable link→admin path is **REMOVED**); never take owner/role from a client param; establish the identity link at **LOGIN** (AuthBridge), never window-gated; before privatizing a table **enumerate all readers** (pollers, cross-module HTTP-SQL, Workers). **DBPEN is the permanent regression gate** — anonymous `SELECT *` on any raw per-user table must return 0 rows.

**Reference impl:** `modules/database-ai/spacetimedb-module/src/views.rs` (~27 `my_*` views). **Coverage VARIES by module:** views shipped in database-ai/CHAT/financial/nexus-sense; platform/blaster-lab/lattice are still legacy client-`WHERE` — new per-user tables THERE must adopt the view pattern, not copy the legacy `owner_stdb_identity: String` neighbor. **Authoritative docs:** `recovery/RLS_SENDER_FIX_PLAN.md`, `recovery/RLS_ROLLOUT_PLAN.md`, `recovery/STDB_POST_MIGRATION_FIXES.md`, `modules/redteam/commands/DBPEN/`. Secure-shape template: `modules/redteam/fixtures/vuln-fixture/src/lib.rs`. Full detail: memory `stdb-finalized-security-model`.

**🔴 STALE LANDMINES (do not trust):** the per-module `utils/auth.rs` header comments still say *"JOIN-based RLS does NOT work — use client-side subscription scoping"* — SUPERSEDED (correct answer = a `ViewContext` view). `commands/standalone/CHAT/CLAUDE.md` claims "only user_identity_links has a filter" — WRONG (CHAT has 3 + a full views.rs). This skill's own Views section (above) documents views generically but does not mark them as THE security mechanism — this subsection is the correction.

### Version gap (grounded 2026-08-03) — our tooling is behind maincloud

> **2026-10-24 update (supersedes the dates below):** latest = v2.13.0 (MSRV Rust 1.97.1; rustup 1.97.1 installed alongside 1.93.0). **2026-10-26: upgrade COMPLETE — all 8 modules + CLI + SDK on 2.13.0.**
> camelCase TS handles landed in **2.7.0** and optional `Option<T>` keys in **2.6.1** (not 2.6). Proven locally: the 2.13 CLI generates camelCase
> handles even with `CaseConversionPolicy::None`, while the 2.1 CLI still generates byte-identical snake bindings from a crate-2.13 module — so
> modules can move to crate 2.13 one at a time WITHOUT touching the SPA. Offline pilot (blaster-lab, local 2.13 standalone): 2.1 → 2.13 publish
> = empty migration plan, data kept. Security: v2.10.0 fixed an identity-impersonation JWT bug (server-side, maincloud's to patch).

Upstream metadata on this skill = synced 2026-04-25 @ v2.1.0-era (and upstream restructured paths: `skills/spacetimedb-rust`→`skills/rust-server`). Installed CLI = **v2.13.0** (since 2026-10-26; the launcher banner 'current: v2.1.0' is its self-version); **maincloud 2.13** — ~5 releases ahead of our tooling. **🔴 A CLI upgrade + type regen triggers BREAKING TS changes** (2.6: generated handles → **camelCase**; `Option<T>` fields → truly optional keys) — upgrade deliberately in a branch, typecheck, fix casing; never bundle into a feature deploy. Also 2.6: **views gained PRIMARY KEYS** (`#[view(..., primary_key = id)]` → views can emit `onUpdate`); adding `#[unique]`/`#[primary_key]` to an existing table is now non-breaking if data satisfies. 2.4: `ReducerContext::identity` deprecated → `database_identity()`. Full list: memory `stdb-version-gap-2026-08`. Get upstream deltas via `gh api .../releases`, NOT a clone (a full SpacetimeDB clone to /tmp stalled the repl).

### `ctx.identity()` is the MODULE identity, NOT the database owner (learned 2026-06)

A frequent misconception: `ctx.sender() == ctx.identity()` ("is_system_caller") is true **only for internal/scheduled calls** (the module calling itself). It is **NOT** true for the database owner calling via `spacetime call` — the owner's CLI `ctx.sender()` is the owner's login identity, which differs from `ctx.identity()`. Consequences:
- An "owner-only" reducer gate **cannot** rely on `is_system_caller` — that rejects the owner CLI too.
- Post-`--clear`, no roster/link data exists, so role-based gates can't authorize the operator's restore. The post-clear-safe options are: (a) **claim-based trust-on-first-use** (a `recovery_owner` singleton + a `claim_*` reducer settable only while unset → the restoring identity becomes the authorized owner), or (b) pin the owner identity as a constant. The Nexus Terminal recovery-import reducers use pattern (a).

### Deploy gotcha: `publish` skips the WASM rebuild if the binary exists

`spacetimedb-publish-*.sh publish` only runs `build_wasm` when the `.wasm` is **missing**. If you edit Rust and run `publish`, it ships the **stale** binary. **Always `cargo build --target wasm32-unknown-unknown --release` first** (or use the full deploy mode), then `publish`. Symptom: your reducer-logic change appears not to take effect on maincloud. Adding a new table/reducer is a **data-preserving** change (safe `publish`, no `--clear`); changing a column type is **breaking** (`--clear`).
