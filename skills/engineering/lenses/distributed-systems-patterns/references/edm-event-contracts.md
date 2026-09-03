# Event contracts

Read this when designing or reviewing a stream, schema, or writer boundary.

## Contents

1. [Event shapes](#event-shapes)
2. [Data contract](#data-contract)
3. [Design rules](#design-rules)
4. [Breaking changes](#breaking-changes)
5. [Single writer](#single-writer)

## Event shapes

| Shape | Key | Meaning | Typical stream |
| --- | --- | --- | --- |
| Unkeyed | none | one-off fact | clicks, sensors |
| Entity | unique id of the thing | state of that thing at a time; latest value is current | `books`, `customers` |
| Keyed non-entity | partition key only | locality without being the entity | "user X viewed book Y", keyed on book |

**Table–stream duality:** upsert entity events in order → table. Record table changes → stream. A tombstone is a keyed event with `null` value; it deletes that key. Compaction keeps the latest per key.

If a consumer needs "current X", the stream must be an entity stream (or a compacted changelog), not an unkeyed firehose.

## Data contract

Two parts, both required:

1. **Data definition** — fields, types, nullability, defaults
2. **Triggering logic** — _why_ this event is emitted (header comment on the schema)

Implicit JSON/maps become tribal knowledge. Require an explicit schema (Avro, Protobuf, or Thrift) with documented compatibility. JSON without a compatibility framework is not a contract.

Compatibility (pick one per stream; default **full**):

- **Forward** — new schema data readable as old (producer moves first)
- **Backward** — old schema data readable as new (consumer can upgrade first; needed for replay)
- **Full** — both. Loosen later if you must; tightening later is expensive.

Comments belong _in_ the schema: trigger in the header, units/timezones on fields.

Code generation is part of the contract: producers cannot omit required fields; consumers get typed objects. A shared "interpret any event" library across languages is a defect.

## Design rules

Apply all of these. A stream that fails one is a finding.

1. **Whole truth.** The event _is_ the fact. Do not emit a semaphore that says "look in system Y." Two sources of truth will diverge.
2. **One definition per stream.** Do not mix incompatible types. Topics are cheap; ambiguous streams are not.
3. **Narrowest types.** Numbers as numbers, booleans as booleans, closed sets as enums — not strings.
4. **Single purpose.** A `type` field that overloads one schema (book click + movie preview + bookmark) is a smell. Split when a new field applies to only one variant.
5. **Small.** If the payload is a pointer to a blob, say so and accept the mutability risk. Do not stuff unrelated context "just in case."
6. **Consumers in the room.** Design the first version with at least one real consumer.
7. **No signal-only events** for business facts. "JobDone" without the result is not **event-first**.

Entity events that other contexts materialize are the most expensive to get wrong. Spend the design time there.

## Breaking changes

A breaking change is a domain redefinition, not a deploy tactic. Tell consumers first.

**Entities:** the producer rebuilds every entity under the new schema and writes a _new_ stream. Leave the old stream for forensics. Do not push "support both shapes" onto every consumer — the producer is in the better position to resolve meaning.

**Non-entity events:** new stream, new definition. Consumers subscribe. Old stream ages out with retention, then delete.

Two-stream eventual migration is allowed only when a 1:1 mapping still makes sense _and_ running both will not create business inconsistency. Tag the old stream `deprecated`. If new services keep attaching to it, the migration has failed.

Never write two incompatible schemas into one stream.

## Single writer

One producing service per public stream. Enforce with ACLs (`WRITE` only for that service). Lineage is then mechanical: stream → writer → team.

Internal streams (repartitions, changelogs) are private to that service. Another service reading a sibling's changelog is coupling on an implementation.

If two writers are already publishing to one topic, that is a blocking `review-fix`. Split the stream or merge the writers into one bounded context — do not "coordinate harder."
