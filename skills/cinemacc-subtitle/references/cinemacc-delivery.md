# Delivery and CinemaCC import

Use this reference to copy generated outputs, package a two-track CinemaCC ZIP, or format a verified public import link.

## Deliver standalone files

Re-resolve the user's destination immediately before writing. Confirm that same-name files are generated outputs rather than sources or user-edited artifacts. For a completed portable job, copy assembled files atomically and write a hash receipt:

```bash
python3 "$TOOL" deliver-job work/subtitle-job /current/output/directory
```

Use `--overwrite` only after confirming the exact existing targets. Never overwrite the original source. Validate copied files again when delivery crosses a filesystem, cloud-sync boundary, or sandbox boundary.

For download-only or refine-only routes without a portable translation job, preserve the original and copy only the named verified output to the resolved destination.

## Package a CinemaCC pair

CinemaCC consumes one dialogue track and one translation track. After both pass structural validation, build a deterministic ZIP:

```bash
python3 "$TOOL" bundle-cinemacc refined.en.srt movie.zh-CN.srt \
  movie.zh-CN.cinemacc.zip \
  --title "Movie" --year 2026 \
  --release "Movie.2026.1080p.WEB-DL" \
  --dialogue-language en --translation-language zh-CN \
  --dialogue-source "OpenSubtitles file 123" \
  --translation-source "CinemaCC Subtitle Skill"
```

The command requires two non-empty SRTs with the same cue-number and timestamp skeleton. It preserves their bytes and writes exactly:

```text
cinemacc.json
dialogue.srt
translation.srt
```

`cinemacc.json` keeps the version 1 core and adds optional, backward-compatible metadata:

```json
{
  "format": "cinemacc-subtitles",
  "version": 1,
  "dialogue": "dialogue.srt",
  "translation": "translation.srt",
  "title": "Movie",
  "year": 2026,
  "release": "Movie.2026.1080p.WEB-DL",
  "dialogueLanguage": "en",
  "translationLanguage": "zh-CN",
  "dialogueSource": "OpenSubtitles file 123",
  "translationSource": "CinemaCC Subtitle Skill"
}
```

Keep both standalone SRTs. A bundle holds one target language. If the job produces `zh-CN` and `zh-TW`, create two bundles rather than a three-track archive.

Add only metadata supported by evidence. `title`, `year`, `release`, track languages, and short source labels appear in CinemaCC's import summary. Do not put signed URLs, credentials, display preferences, guessed offsets, or private job notes in the manifest.

## Create an import link only for a direct URL

An agent attachment, local path, share page, or account-scoped artifact is not automatically a direct URL. Before creating a CinemaCC link, verify that the ZIP URL:

- uses public HTTPS without embedded credentials;
- succeeds with an anonymous `GET` and no cookies or session headers;
- follows only public HTTPS redirects and returns ZIP bytes rather than HTML;
- is no larger than 5 MiB;
- supports browser CORS when the Web player is an intended fallback.

Then format the handoff:

```bash
python3 "$TOOL" cinemacc-link "https://files.example/movie.zh-CN.cinemacc.zip"
```

The source URL stays in the fragment of `https://open.cinemacc.net/import`, so the handoff host does not receive it in the HTTP request. Do not add `role` for a two-track ZIP.

If anonymous access cannot be verified, return the ZIP and tell the user to share or open it with CinemaCC. Hosting or distributing subtitles on a new service requires explicit user authorization and a separate rights, privacy, retention, and deletion decision.
