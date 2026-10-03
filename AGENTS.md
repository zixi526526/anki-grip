# anki-grip

Windows desktop companion for Xbox controllers and Anki. Keep source, tests,
documentation and original assets in Git. Keep virtual environments, build output,
personal settings and Anki profiles outside the repository. Never commit secrets.
Do not read or edit the user's collection or unrelated add-ons. Install only
`anki_grip_bridge` in Anki's add-ons folder. Tests use fake Anki objects or an
isolated throwaway profile; do not test real reviews against a user's collection.

Ratings are semantic: Again=1, Hard=2, Good=3, Easy=4. Shortcut labels are a
separate configurable presentation setting, standard for new installations.
Preserve existing profiles and migrate
only exact legacy defaults. Load vibration strength from saved settings.

Bridge commands require the current review revision/session. Run Anki operations
on its Qt main thread. Never retry a timed-out rating. Preserve stale-command,
foreground, busy, held-at-startup, center drift, diagonal and input-edge guards.

Space resolves to Show on the question and Good on the answer before sending the
same revision/session. Holding input across a flip must not grade. Feedback uses
the action actually completed, captures neither mouse nor keyboard focus, and
does not report success for rejected or expired commands.

Only scroll actions repeat while held. Stop on centering, directional misalignment,
pause, or review/foreground changes; scrolling must not grade or rumble. Scroll
only the current review WebView with the same guards.

Preserve unsaved settings during language switching. The Controller Test page
pauses Anki actions; leaving it requires input release before actions resume.
Mouse-wheel scrolling must not change focused combos or sliders.

Keep Windows/XInput runtime limits explicit. Linux supports synthetic tests and
offline previews. Verify exported source in isolation; distribute executables
with the complete dependency license bundle and matching SHA-256 manifest.
