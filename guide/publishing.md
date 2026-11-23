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
- **Thumbnail:** if `<video>.png` exists (the [cover](pipeline.md#7-cover)), `upload_existing.py` sets it with `thumbnails().set` after the upload. A failure is reported, never fatal. The thumbnail is the vertical cover as it is (JPEG, 9:16): Studio crops a 16:9 image to its centre, so never convert it.
- The API cannot delete videos with the stored scopes (403). Delete in YouTube Studio: the video's menu, Delete, tick the box, confirm.
- Uploads can be refused for a daily limit (`uploadLimitExceeded`): `scripts/retry_youtube_uploads.py <manifest>` resends the missing ones.

### YouTube OAuth

The Google Cloud app "Silicon Verdict Uploader" (project `silicon-verdict-bot`) was published to **Production** on 2026-11-23, so its refresh token no longer dies every 7 days (that limit applies only to apps in Testing; the app stays "unverified", which only shows a warning at login).
The token of 2026-11-23 is the first one issued in Production: if it still fails with `invalid_grant: Token has been expired or revoked` after a week, Production did not take effect: check the status in Google Cloud Console > Google Auth Platform > Público.
A token also stops working if the Google account password changes or the access is revoked in the Google account settings; then renew it:

```bash
BROWSER=true .venv/bin/python scripts/authenticate_yt.py      # prints the Google URL and listens on localhost:8080
```

Open the printed URL in a browser signed in to Google, choose the Google account **NotChego** (the owner), then the brand account **Silicon Verdict · YouTube** (that is the SiliconVerdictHQ channel),
press Continuar past "Google no ha verificado esta aplicación" (it is your own app), tick *Seleccionar todo* (manage videos, view account, view Analytics) and press Continuar.
The script writes `data/token.json`, `token.json` and `tokens/token.json` (and keeps the old one in `data/token_backups/`). Check with
`.venv/bin/python -c "from services.yt_analytics import channel; print(channel())"`.

To publish an app again (or for a new project): Google Auth Platform > Información de la marca needs the app name, support email, homepage, privacy and terms URLs (`https://adrlopech.github.io/Silicon-Verdict/`, `privacy.html`, `terms.html`) and that domain as an authorized domain; then Público > Publicar app.
A refresh must keep the stored scopes: `services/youtube.py` loads the token without passing scopes for that reason.

## TikTok

There is no posting API in use.
Videos are scheduled by hand in **TikTok Studio** (`https://www.tiktok.com/tiktokstudio/upload`), which the assistant drives with Claude in Chrome. Use the **<10 MB copy**
(`output/tiktok_small/`, the upload tool caps one call at 10 MB) and the cover PNG.

### TikTok Studio step by step

Per entry of `data/batches/latest.json` (`caption`, `hashtags`, `tiktok_copy`, `cover`, `madrid` hour). The page-side work is in `scripts/tiktok_studio.js`, which finds every element by class, role or text: no screen coordinates
(they broke whenever the window size changed). Paste that file's body into the page once per load (`javascript_tool`); it defines `tt`.

1. Open `/tiktokstudio/upload`, `find` "file input" and `file_upload` the `tiktok_copy`. Wait about 10 seconds for the form.
2. **Description:** `tt.focusCaption()`, then real keystrokes (`computer`): `cmd+a`, `Delete`, type the `caption`. The editor ignores programmatic edits and **crashes the page** on `execCommand`, so never edit it from JavaScript.
   For **every hashtag**: type ` #tag` with `computer`, wait about 3 s, then `await tt.pickHashtag('#tag')` (it clicks the exact option; it returns `{ok, suggestions}`).
   A hashtag typed but not picked stays plain text: `tt.state().hashtags` must list all of them. If `ok` is false the exact tag is not offered (for example `#steamdeck`); delete it and use one of the `suggestions`.
3. **Cover:** `find` "Editar portada", click it, `find` "Cargar portada file input" and `file_upload` the cover PNG, then press **Guardar** (`await tt.press('Guardar')`).
4. **Schedule:** `await tt.schedule({date: '2026-11-24', time: '20:00'})` (minutes in steps of 5). It selects "Programación", walks the calendar to the right month, picks the day and the hour and returns `{ok, value}`: check `ok`.
   The time zone shows **Hora local**, the computer's zone: **(GMT+1)** in Madrid, so use the Madrid hour of the plan; if the computer is elsewhere (it showed GMT+0 in Lisbon) convert from the UTC hour.
5. `await tt.press('Programar')`. If the dialog "¿Seguir con la publicación?" appears (TikTok is still reviewing the content), `await tt.confirmReview()` ("Publicar ahora" continues the *scheduled* post).
   For a video that must go out right now, leave the radio on "Ahora" and `await tt.press('Publicar')`.
6. Check `/tiktokstudio/content`: the new posts show "16 nov, 20:00 (GMT+1) Madrid" style times (the list can take a few seconds to show the new post: reload).

To throw an upload away: `await tt.press('Descartar')` and confirm the red "Descartar" of the dialog. Delete a published post: the "..." menu of its row, Eliminar, confirm.
If TikTok changes its page, the selectors to fix are the ones at the top of `tiktok_studio.js` (`.Picker__*`, `.TimePicker__*`, `.DatePicker__*`, `.mention`, `[role=option]`); `tt.state()` shows what the page offers.

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

## Comments

`python scripts/comments.py` lists the comments of the last days that the channel has not answered, with a suggested reply each (written to `notes/comments_<date>.md`); `--post` asks y / n / your own text for every one and posts only the approved ones. It needs the `youtube.force-ssl` scope, which also allows deleting a video: re-run `scripts/authenticate_yt.py` once (NotChego account, Silicon Verdict channel) and approve it. Without it the script says so and does nothing.
