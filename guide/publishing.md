# Publishing

Official channels: YouTube [@SiliconVerdictHQ](https://www.youtube.com/@SiliconVerdictHQ) (channel id `UCm0Xb9KY_Hu12j1CijF2KHQ`) and TikTok [@siliconverdict](https://www.tiktok.com/@siliconverdict).
`@siliconverdict` on **YouTube** is an unrelated channel ("Frame Floor"): never use it.

## YouTube

`services/youtube.py` uploads with a resumable chunked upload (retries with backoff) and sets the category (28), `#Shorts` in title or description, `selfDeclaredMadeForKids: false`, and optionally a scheduled time.

```bash
.venv/bin/python scripts/upload_existing.py "<video.mp4>"                       # public now
.venv/bin/python scripts/upload_existing.py "<video.mp4>" --privacy private --publish-at 2026-11-17T13:00:00Z
```

- Title, description and hashtags come from the `.txt` next to the TikTok copy. A scheduled upload is always `private` with `publishAt` (RFC 3339, UTC); YouTube publishes it at that time.
- **Thumbnail:** if `<video>.png` exists (the [cover](pipeline.md#7-cover)), `upload_existing.py` sets it with `thumbnails().set` after the upload. A failure is reported, never fatal.
- The API cannot delete videos with the stored scopes (403). Delete in YouTube Studio: the video's menu, Delete, tick the box, confirm.
- Uploads can be refused for a daily limit (`uploadLimitExceeded`): `scripts/retry_youtube_uploads.py <manifest>` resends the missing ones.

### YouTube OAuth

The Google Cloud app "Silicon Verdict Uploader" is in **Testing** mode, so the refresh token dies **every 7 days** (`invalid_grant: Token has been expired or revoked`). The pipeline then cannot upload or read analytics.

Renew:

```bash
BROWSER=true .venv/bin/python scripts/authenticate_yt.py      # prints the Google URL and listens on localhost:8080
```

Open the printed URL in a browser signed in to Google, choose the Google account **NotChego** (the owner), then the brand account **Silicon Verdict · YouTube** (that is the SiliconVerdictHQ channel),
press Continuar past "Google no ha verificado esta aplicación" (it is your own app), tick *Seleccionar todo* (manage videos, view account, view Analytics) and press Continuar.
The script writes `data/token.json`, `token.json` and `tokens/token.json` (and keeps the old one in `data/token_backups/`). Check with
`.venv/bin/python -c "from services.yt_analytics import channel; print(channel())"`.

The permanent fix is to publish the OAuth consent screen to **Production** in Google Cloud Console (the user's decision).
A refresh must keep the stored scopes: `services/youtube.py` loads the token without passing scopes for that reason.

## TikTok

There is no posting API in use. `services/tiktok.py` and `scripts/auth_tiktok.py` implement the Content Posting API but it is not part of the daily flow (see [Legacy](legacy.md)).
Videos are scheduled by hand in **TikTok Studio** (`https://www.tiktok.com/tiktokstudio/upload`), which the assistant drives with Claude in Chrome. Use the **<10 MB copy**
(`output/tiktok_small/`, the upload tool caps one call at 10 MB) and the cover PNG.

### TikTok Studio step by step

Per entry of `data/batch_latest.json` (`caption`, `hashtags`, `tiktok_copy`, `cover`, `madrid` hour):

1. Open `/tiktokstudio/upload`, `find` "file input" and `file_upload` the `tiktok_copy`. Wait about 10 seconds for the form.
2. **Description:** click the box (about x=700, y=380), `cmd+a`, `Delete`, type the `caption`. Then for **every hashtag**: type ` #tag`, wait about 4 s, click the first row of the dropdown (about x=380, y=556), wait 1 s.
   A hashtag typed but not picked stays plain text. Check with JS: `[...document.querySelectorAll('.mention')].map(e=>e.innerText)` must list all of them.
   If a tag shows no dropdown at all (for example `#pcbuilding`), delete it and use a common one (`#pcbuild`).
3. **Cover:** `find` "Editar portada", scroll to it and click, `find` "Cargar portada file input" and `file_upload` the cover PNG, then **Guardar** (top right of the dialog; its position depends on the window height: take a screenshot).
4. **Schedule:** `find` the radio "Programación" and click it. The date defaults to today. Open the time picker: it starts at the current time. The hour wheel moves about three hours per scroll tick; scroll,
   then click the target hour. For minutes click the `00` row (scroll the minute wheel up if it is out of view). Close the picker by clicking an empty area. The time zone shows **Hora local**, the computer's zone: **(GMT+1)** in Madrid, so use the Madrid hour of the plan; if the computer is elsewhere (it showed GMT+0 in Lisbon) convert from the UTC hour. Verify the date, the hour and the zone before continuing.
5. Press **Programar** (find the button by name and scroll to it). If a dialog "¿Seguir con la publicación?" appears (TikTok is still reviewing the content), press **Publicar ahora**: it continues the *scheduled* post.
6. Check `/tiktokstudio/content`: the new posts show "16 nov, 20:00 (GMT+1) Madrid" style times.

Delete a post: the "..." menu of its row, Eliminar, confirm.

### TikTok rules

- Hashtags are single joined words, and they must be picked from the dropdown.
- In the caption a series number like `#7` would become a hashtag: `tiktok_caption()` writes it as `7`.
- Never publish from the NotChego TikTok account; the official one is `@siliconverdict`.

## Hours

| Slot (UTC) | Madrid | New York |
|---|---|---|
| 13:00 | 14:00 | 8-9 am |
| 16:00 | 17:00 | noon |
| 19:00 | 20:00 | 3 pm |
| 22:00 | 23:00 | 6 pm |

Madrid is UTC+1 in winter (UTC+2 in summer; the plan prints the Madrid hour by adding one, check it when daylight saving changes). If the computer clock is in another zone (for example on a trip), the plan is still in UTC.
Never put two videos on the same hour.

## Hashtags and metadata

- Titles end with joined-word hashtags (`#siliconverdict #pcbuild #gpu`); `joined_hashtag()` removes spaces.
- The description of a game video lists the footage credits.
- `pinned_comment` is the two-option vote of the outro ("A or B? Reply with one word."). It must be posted by hand; the API flow does not post comments.
