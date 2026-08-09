# Registry snapshot provenance audit

Audit date: 2026-08-09

Release: `registry-2026.08.05`

Fixture: `tests/fixtures/registry_snapshot_provenance_audit.json`

This is a provenance audit and validator-fixture proposal. It does not implement a
snapshot downloader or validator, publish a release, grant a data license, or make
the live website a source of snapshot identity. The database was downloaded only to
`/tmp/gft-registry-2026.08.05-audit`; it was not copied into this package or its
wheel.

## Executive findings

1. The four public release assets download successfully and all hashes agree across
   the GitHub API digests, `SHA256SUMS`, and local downloads. The compressed asset
   decompresses to the manifest's 24,961,024-byte SQLite file, whose `quick_check`
   and `integrity_check` both return `ok`.
2. The release manifest is internally consistent with the released compressed
   database, raw database, and schema asset. It declares 25 application tables and
   10,120 rows.
3. The matching source bytes named by the manifest are not the current live
   `data/registry.db`. The current live database has the same size, SQLite metadata,
   table populations, and integrity results, but a different file hash and 335
   changed `papers.structured_json` rows. A preserved source sidecar has the
   manifest's declared source hash and is logically equal to the released database.
4. `registry-schema.sql` is not replayable as a standalone fresh SQLite schema: its
   indexes precede the tables they reference, and it declares SQLite-reserved
   internal tables. This does not invalidate the released database, but it is a
   validator/schema-fixture defect that must remain explicit.
5. The public repository is MIT-licensed, but no separate database/data license was
   found. The release body calls the asset a private development snapshot and says
   it is not the public archival/DOI release. Redistribution of the database is
   therefore unresolved, not implied by the software license.
6. The release is a historical package-base association, not an association with the
   current renamed RC package. The manifest names the old `gft-registry-python`
   repository and commit `473bf6a`; the current package is
   `geometric-function-atlas` after commit `e504452`. The manifest does not carry a
   package version.
7. The live website stats endpoint reports matching headline populations, but that
   is not a snapshot identity check. Website-only counts would miss the current
   source's row-level `papers` divergence.

The complete machine-readable record, including exact URLs, bytes, hashes, table
populations, source comparison, license status, and deterministic negative-fixture
descriptors, is in the JSON fixture named above.

## Release and asset audit

The audited public release is:

- repository: <https://github.com/Prasanna28Devadiga/geometric-function-atlas>
- release: <https://github.com/Prasanna28Devadiga/geometric-function-atlas/releases/tag/registry-2026.08.05>
- API release id: `365295986`
- tag target: `473bf6a1cc63648b0b6b999ea7428cbc6b455611`
- created: `2026-08-04T18:15:30Z`
- published: `2026-08-05T05:02:49Z`
- GitHub visibility at audit: public
- repository license reported by GitHub: MIT

| Asset | Exact download URL suffix | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| `gft-registry-2026.08.05.sqlite.zst` | `.../gft-registry-2026.08.05.sqlite.zst` | 2,254,015 | `4fea49b741e57964f411cebfa388881a64d81f3aefd2a08d3940c296dc2acef6` |
| `registry-manifest.json` | `.../registry-manifest.json` | 2,792 | `0a42493e1d0812cb0cff96112c7279bbfac3adefe2a536efbb0373153555fdec` |
| `registry-schema.sql` | `.../registry-schema.sql` | 15,166 | `5298e3885a922d2207e3d0e5aa54b5569854674ce2297ffd0ad3b5ff77359f47` |
| `SHA256SUMS` | `.../SHA256SUMS` | 373 | `de5909187c698e5953e298fa1cd81a565e25c0d0355c80244e19380a9f67a569` |
| decompressed `gft-registry-2026.08.05.sqlite` | not a release asset; listed by `SHA256SUMS` | 24,961,024 | `e20ab91171cbe7515fbb8ad116311e98cf09054407140fbb93746d1c6608f82e` |

The local verification commands returned `OK` for the three downloaded assets,
then `OK` for the decompressed database:

```text
gft-registry-2026.08.05.sqlite.zst: OK
registry-manifest.json: OK
registry-schema.sql: OK
gft-registry-2026.08.05.sqlite: OK
```

Zstandard inspection found one frame, a 4 MiB window, compressed size 2,254,015,
decompressed size 24,961,024, and check `XXH64 b8c6312f`. Decompression used the
installed Zstandard CLI 1.5.7; the manifest declares `zstd -15 -T0` and tool version
1.5.7.

## Manifest and database populations

The downloaded `registry-manifest.json` has `manifest_schema_version: 1`, dataset
version `2026.08.05`, and reports:

- SQLite library `3.53.1`;
- page size 4,096, page count 6,094, freelist count 2,869;
- `PRAGMA user_version: 0`;
- `PRAGMA quick_check: ok`;
- `PRAGMA integrity_check: ok`;
- 25 application tables and 10,120 total rows.

The declared row populations are:

```text
daily_stats 398                 dlmf_catalog 0
 evidence 961                  facts 1040
function_aliases 0             function_families 151
function_instances 543         function_relations 0
function_tags 281              functions 137
gft_properties 18               merge_candidates 49
page_views 0                    paper_claims 1039
paper_class_tags 186            paper_family_links 2606
paper_queue 0                   paper_tags 126
papers 1088                     properties 137
property_implications 15        tags 54
verification_queue 4            verification_runs 1287
verify_queue 0
```

A read-only SQLite audit of the decompressed database reproduced every declared
count and every declared SQLite/integrity value. `sqlite_master` contains 27 table
entries: the 25 application tables plus SQLite's `sqlite_sequence` and
`sqlite_stat1` internal tables. The release's application-table count of 25 is
therefore not a contradiction.

## Schema asset finding

The schema asset has the expected downloaded hash and declares all 25 application
table names plus two internal table names and 39 named indexes. It cannot, however,
be used as a clean standalone schema replay:

```text
sqlite3 < registry-schema.sql
exit=1
parse errors=41
first error: no such table: main.function_aliases
```

The first statements are `CREATE INDEX` statements, before their referenced tables
are created. Later, `CREATE TABLE sqlite_sequence` and `CREATE TABLE sqlite_stat1`
are rejected as reserved internal objects. The released database itself passes both
integrity pragmas; this is a schema-asset usability problem, not evidence of raw
SQLite corruption. A future validator should either require a corrected ordered
schema asset or treat this release schema as descriptive metadata only.

## Research-source comparison

The matching research artifact is
<https://github.com/Prasanna28Devadiga/gft-registry> at commit
`acee553e03f9ca2bdcb55977e18ff7d9deb57e40`. The source database is explicitly
untracked by Git and the source worktree was already dirty; the repository commit
alone cannot identify database bytes.

The manifest declares this source identity:

```text
relative path: data/registry.db
bytes: 24961024
SHA-256: 5dfd7060c232bcfeb61b4118d667b59127cb5142a91eee9d030c633789de5634
modified_at: 2026-07-18T20:07:58.660655+00:00
```

A preserved source sidecar,
`data/registry.db.bak.ocr_apply_batch.20260806-120044`, has exactly that declared
hash and size. A row/schema comparison found it logically equal to the released
SQLite database, even though a transactionally consistent SQLite copy can have a
different file-level hash.

The current live `data/registry.db` is different:

```text
bytes: 24961024
SHA-256: 51e0e7cbbef124c761cf31b784140f1f2e7f79589377e1fdbf76601417782e51
modified_at: 2026-08-06T12:54:53.197416+00:00
quick_check: ok
integrity_check: ok
application tables: 25
total rows: 10120
```

Its only logical table mismatch against the released database is `papers`: 335
existing rows have changed `structured_json` values; no rows were added or removed.
The canonical table hashes are:

- released `papers`: `c5e6727b044df37514470d0ee4a0631875dfab35a2390a180a944a3b841d7797`
- current source `papers`: `f7309b7348fe7ff621986674b169509aeb6085a72e1d031b9cd07cd032ccf853`

Thus “same table count” and “same website headline count” do not establish row-level
snapshot equivalence.

## Software association and package boundary

The release manifest says:

```text
package repository: https://github.com/Prasanna28Devadiga/gft-registry-python
package commit:    473bf6a1cc63648b0b6b999ea7428cbc6b455611
```

The release target is the same historical commit. That commit is the pre-rename
`gft-registry` / `gft_registry` Phase 1 package. The current package branch has
renamed the distribution and import package to `geometric-function-atlas` /
`geometric_function_atlas` at `e504452eb399bf9818fbf79fff078f4104ab94ae`. The old
GitHub repository URL currently canonicalizes to the renamed public repository, but
that does not change the historical package identity recorded by the manifest.

The manifest contains no package version. The snapshot is consequently a historical
base-commit association only. It is not evidence that the current RC package uses
this snapshot, and it must not cause the database to be copied into a wheel. The
fixture records this association and includes a stale-association negative case.

## License and redistribution boundary

The source/package repository reports an MIT software license. No explicit
license for the SQLite contents, extracted literature metadata, paper text, or
schema/data release was found in the release manifest or release body. The release
body calls the release a “Private research snapshot for development,” says it is
not yet the public archival/DOI release, and the manifest records
`visibility_at_creation: private`, although the GitHub release is publicly
readable now.

Conclusion: software MIT licensing is not sufficient evidence that the database
may be redistributed or embedded. The snapshot's redistribution status is
**unresolved** until an explicit data-license/redistribution decision is recorded.
No publication, release mutation, or credential action was performed.

## Website-only divergence

At audit time, `https://gft-registry.fly.dev/api/v2/stats` returned a 308-byte JSON
response with SHA-256
`f499e92939f8d87e18425bd04e9ad6b1a7e98ed7946682329ca0ad25c7056c85`. Its headline
values match the snapshot for evidence (961), facts (1,040), families (151),
instances (543), merge candidates (49), relations (0), and verification runs
(1,287). The endpoint does not expose the released database hash, table hashes,
source commit, or snapshot tag.

The website counts are therefore a useful live observation, not a provenance
anchor. The current source can retain the same headline populations while changing
335 `papers.structured_json` rows. The JSON fixture includes a deterministic
website-only-divergence case that preserves the website counts while substituting
the alternate `papers` table hash; a future validator must reject that as snapshot
identity evidence.

## Deterministic negative-fixture proposal

`tests/fixtures/registry_snapshot_provenance_audit.json` defines, without
implementing them, these rejection cases:

- wrong compressed hash: expected hash replaced with 64 zeroes;
- truncation: remove one trailing compressed byte; any listed size/hash/decompression
  failure is acceptable, but successful acceptance is not;
- wrong schema: set `manifest_schema_version` to 999;
- missing table: remove `papers` from a decompressed temporary database after
  archive/hash verification and recompute only the mutation fixture's database hash,
  so the intended assertion is `required_table_missing` rather than an earlier
  download failure;
- missing field: remove `database.row_counts.papers`;
- stale software association: replace the package commit with current post-rename
  commit `e504452` while leaving the release target unchanged;
- decompression/resource limit: cap decompressed bytes at 24,961,023, one byte below
  the declared output;
- website-only divergence: preserve website headline counts while substituting the
  current-source `papers` table hash.

These are fixture designs for a later validator. No validator or downloader is part
of this handoff.

## Verification boundary

The audit artifact contains metadata and deterministic mutation descriptors only:

- no SQLite database;
- no raw paper corpus;
- no mutable review ledger;
- no credentials;
- no new runtime dependency;
- no validator implementation.

The package tree remains free of a database payload. The next worker may use the
fixture to design a narrow, resource-bounded validator and an explicitly licensed
snapshot contract.
