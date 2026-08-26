# Source acquisition and CinemaCC delivery

Use this reference only when the task begins without an eligible local source, when the user requests a partial workflow, or when the result should enter CinemaCC.

## Acquire without overreaching

If the user supplied a usable source SRT, do not replace it merely because source search is available. Search when no source exists, the supplied file fails the source-eligibility gate, or the user explicitly asks for comparison.

Before downloading, identify the title, year, requested source language, runtime, country or cut, and release name when known. Compare candidates using:

- observed language from actual subtitle cues rather than labels;
- beginning, middle, and end coverage plus final-cue time against a reliable runtime;
- release and timing compatibility;
- textual provenance and machine-translation, OCR, or ASR indicators;
- provider page, uploader or translator attribution, and access date.

Preserve every downloaded original. Use normal browser or documented API access available to the agent. Never defeat authentication, CAPTCHAs, paywalls, quotas, disabled downloads, or takedowns. If access is blocked, provide candidate page links and ask the user to download and attach the file. A page URL is not a direct SRT URL, and a ZIP from a provider may need local extraction before inspection.

For a download-only request, run inspection and the source-eligibility gate, then deliver the unchanged file with the decision record. Do not refine or translate it.

## Package a CinemaCC pair

CinemaCC consumes one dialogue track and one translation track. After both pass structural validation, build a deterministic ZIP:

```bash
python3 "$TOOL" bundle-cinemacc refined.en.srt movie.zh-CN.srt \
  movie.zh-CN.cinemacc.zip --title "Movie (2026)"
```

The command verifies that both files are non-empty and share the same cue-number and timestamp skeleton. It preserves their bytes and writes exactly:

```text
cinemacc.json
dialogue.srt
translation.srt
```

Keep the individual SRT files as normal deliverables. A bundle holds one target language. If the job produces both `zh-CN` and `zh-TW`, produce two bundles rather than a three-track archive.

## Create an import link only for a real direct URL

An agent attachment, local path, share page, or account-scoped artifact is not automatically a direct URL. Before creating a CinemaCC link, verify that the ZIP URL:

- uses public HTTPS and contains no embedded credentials;
- succeeds with an anonymous `GET` without cookies or session headers;
- follows only public HTTPS redirects and returns ZIP bytes rather than HTML;
- is no larger than 5 MiB; and
- supports browser CORS when the Web player is an intended fallback.

Then format the handoff:

```bash
python3 "$TOOL" cinemacc-link "https://files.example/movie.zh-CN.cinemacc.zip"
```

The source URL is placed in the fragment of `https://open.cinemacc.net/import`, so the handoff host does not receive it in the HTTP request. Do not add `role` for a two-track ZIP.

If anonymous access cannot be verified, return the ZIP as a download and tell the user to share or open it with CinemaCC. Hosting or distributing the subtitle on a new service requires explicit user authorization and a separate rights, privacy, retention, and deletion decision; it is not an automatic delivery step.
