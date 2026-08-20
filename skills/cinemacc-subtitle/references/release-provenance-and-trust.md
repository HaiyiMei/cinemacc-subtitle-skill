# Release Provenance and Source Trust

Use this reference to choose a subtitle base, interpret release filenames, and evaluate uploader or translator credibility. Recheck time-sensitive facts live; never treat a filename or reputation note as permanent proof.

## Parse release names by role

For `Title.2026.1080p.TELESYNC.x264-DKS`:

- `1080p` states output dimensions, not captured detail or source fidelity.
- `TELESYNC` claims the acquisition source and is the most relevant quality clue.
- `x264` states the video encoder, not the source quality.
- `DKS` is a release tag. It may identify a Scene/P2P group, small team, individual, bot, site, or repacker; do not call it an organization or expand the name without direct evidence.

Treat site-like suffixes such as `OnlyFlix` as provider or repackaging labels unless evidence proves otherwise. Separate these roles:

1. video capture or release group;
2. encoder, repacker, or streaming site;
3. subtitle author, transcriber, or translator;
4. subtitle uploader.

An uploader matching an SRT to `DKS` or `NGP` does not establish membership in that release group. Require an NFO, signed release notes, a verified public profile, or consistent first-party history before attributing identity.

## Interpret source labels cautiously

| Label | Usual claim | Practical expectation |
| --- | --- | --- |
| `CAM`, `HDCAM` | Cinema screen filmed with camera audio | Lowest image and audio quality; audience noise and obstructions are common |
| `TS`, `TELESYNC`, `HDTS` | Cinema-screen video with a separate or direct audio source | Video remains camera-derived; audio may be much cleaner than CAM |
| `PreDVD`, `PDVD`, `PreDVDRip` | Early copy packaged or re-ripped as a disc | Commonly CAM/TS-derived; not evidence of retail DVD quality |
| `TC`, `TELECINE`, `HDTC` | Direct transfer from a film print | Potentially better than TS but rare and frequently mislabeled |
| `SCR`, `DVDSCR`, `WEBSCREENER` | Leaked review, awards, or internal screener | Potentially clean but may contain watermarks, warnings, or altered sections |
| `WEBRip` | Captured or re-encoded streaming source | Usually clean, but quality and generation loss vary |
| `WEB-DL` | Direct digital-service stream extraction | Usually high quality and preferable to theatrical captures |
| `BluRay`, `BDRip`, `Remux` | Blu-ray-derived source | Usually the strongest consumer source; `Remux` normally avoids video re-encoding |

These labels are community claims, not authenticated metadata. `1080p`, `4K`, `x264`, and `x265` cannot rescue a poor capture and must not outweigh visible defects, audio evidence, timing compatibility, or textual quality.

For subtitle selection, prefer exact timing and edit compatibility over the video label's presumed image rank. CAM/TS variants may differ in intros, ads, cuts, missing scenes, playback speed, and intermission placement.

## Infer how an early subtitle was made

Consider, in order of ordinary likelihood:

- automatic speech recognition from CAM/TS audio;
- manual listening and transcription;
- OCR from hard-coded captions;
- machine translation of another subtitle;
- copying and time-shifting a derivative SRT;
- a fake, recycled, or incorrectly matched upload;
- a leaked official caption or screener file, only with strong supporting evidence.

Availability before a local premiere does not prove a studio leak. Verify official release dates and advance screenings by territory. Treat repeated OCR artifacts, improbable dialogue, language leakage, identical errors, timing offsets, uploader credits, and machine-translation badges as provenance evidence.

## Assess subtitle accounts

Do not equate upload count, membership tier, download count, early availability, or a familiar handle with subtitle quality.

Check:

- `Trusted` or `Sub Translator` quality badges separately from quantity tiers such as Gold;
- account age, language concentration, upload bursts, and repeated external credits;
- explicit machine-translation flags and whether the claimed language matches the text;
- ratings, corrections, comments, duplicate families, and synchronization quality;
- whether the uploader claims authorship or merely supplies another translator's work.

High download counts often measure scarcity, popularity, API traffic, or being first, not accuracy. Record the profile URL and `checked_on` date. Re-verify before relying on any account in a later job.

Keep account-specific findings in the current job's context pack rather than this reusable reference. Include direct source links and a check date so later jobs do not inherit stale reputation claims.

## Record the decision

For each job, record:

- selected base release and why;
- parsed source, resolution, codec, and release-tag claims;
- timing-family and textual-dependence evidence;
- uploader/translator evidence with a check date;
- machine-translation, OCR, ASR, or official-source indicators;
- unresolved provenance and confidence.

Never convert an inference about a group, uploader, or acquisition method into an asserted fact.
