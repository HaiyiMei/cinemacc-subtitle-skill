# Source acquisition

Use this reference when a task begins without an eligible local source, when the supplied file fails the source-eligibility gate, or when the user explicitly asks for source comparison.

## Establish the target

Record the title, year, requested source language, runtime, country or cut, and release name when known. Do not search for a replacement when the user already supplied an eligible source unless they requested comparison.

## Compare candidates before downloading

Treat filenames, site filters, uploader descriptions, and language labels as unverified claims. Compare candidates using:

- observed language from actual cue samples;
- beginning, middle, and end coverage plus final-cue time against a reliable runtime;
- release and timing compatibility;
- textual provenance and machine-translation, OCR, or ASR indicators;
- provider page, uploader or translator attribution, and access date.

Read [release-provenance-and-trust.md](release-provenance-and-trust.md) when release labels, uploader identity, or textual independence affects the choice. Prefer a complete track in the requested source language that matches the user's release over a cleaner-looking but incompatible track.

## Download normally or stop

Use ordinary browser or documented API access available to the agent. Preserve each downloaded original before extraction or conversion. Never defeat authentication, CAPTCHAs, paywalls, quotas, disabled downloads, or takedowns.

If access is blocked, return the best candidate page links and ask the user to download and attach the file. A page URL is not a direct SRT URL. A provider ZIP may need local extraction before inspection.

## Output

Record:

- selected provider page and direct file URL when available;
- claimed and observed language;
- release and timing evidence;
- coverage as `full`, `partial`, or `unverified`;
- provenance limits and access date;
- the untouched local source path and hash.

For a download-only request, inspect the file and pass the source-eligibility gate, then deliver it unchanged with this record. Do not refine or translate it.
