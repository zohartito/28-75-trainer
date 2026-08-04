# Local input and output safety boundaries

`trainer2875` remains an offline, local review tool. Selected folders, imported
JSON, XMP sidecars, and all report fields are treated as untrusted data.

## Enforced controls

- Review traversal opens regular files through no-follow descriptors, rejects
  symlinked image leaves, and binds metadata parsing plus SHA-256 hashing to
  the same descriptor.
- A review is limited to 10,000 entries, 4 GiB total recognized bytes, and
  512 MiB per recognized file. An unreadable or oversized photo becomes one
  warning row; it cannot cancel the rest of the review.
- JSON imports are limited to 5 MiB, reject `NaN`/`Infinity`, and validate
  nested report and field-review values before rendering or ranking.
- XMP sidecars are opened below the review root without following links and
  are limited to 1 MiB, 10,000 XML elements, and 1,000 metadata fields.
- Report and contact-sheet outputs use a verified parent descriptor, an
  exclusive temporary leaf, `fsync`, and descriptor-relative atomic replace.
- Field-review preparation accepts only one safe filename-prefix component,
  rejects source image symlinks, applies the same file limits, and copies
  through no-follow source/destination descriptors.
- Lightroom Markdown escapes review-controlled text. CSV cells beginning
  (after whitespace) with `=`, `+`, `-`, or `@` are quoted with an apostrophe.

## Operational boundary

The GitHub workflows are intentionally tombstoned in this offline change. An
owner must restore each workflow only after reviewing current immutable action
commit SHAs, exact permissions, event scope, and bounded job inputs. The
former credentialed PR-review workflow additionally needs a documented
least-privilege tool and token boundary before it is re-enabled.

These controls do not make an arbitrary local filesystem mutually hostile:
the person running the tool still chooses its review folder and output paths.
They do ensure the tool fails closed on links, bounded workloads, malformed
data, and output-leaf replacement races within that chosen local scope.
