# File-based body (proven working form)

- When the cycle-log content is long or contains quotes/backticks, write the body to a /tmp JSON
  file (heredoc or file tool) and POST it with `curl --data-binary @/tmp/<file>.json`:
  `-d @file` never re-quotes the content, so shell-escaping problems disappear. Write+verify in
  ONE call with `-w "HTTP %{http_code}"` and truncate the 201-echo DISPLAY only.
- Do NOT leave a stray `python3 - "$TOK" <<'PYEOF' || curl …` prefix in front of the curl: the
  python side reads an empty program from stdin (an interactive hang, not a fast failure) and the
  curl only fires if python fails. Use the one-call curl form above, or a /tmp script file per
  the hardline-filter rule in SKILL.md — never an inline heredoc wrapper around the write.
