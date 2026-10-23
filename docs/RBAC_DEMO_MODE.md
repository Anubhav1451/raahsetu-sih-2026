# RBAC and local demo mode

Production authentication always uses Supabase Auth and profile-based roles. Local jury demonstrations may opt in to `ALLOW_DEMO_AUTH=true` and `APP_ENV=development`; the backend then accepts only `Bearer demo:<role>` tokens. The demo branch is rejected when `APP_ENV=production`.

The frontend quick-role buttons are rendered only when `VITE_DEMO_MODE=true`. They are visibly labelled Local Demo Mode and must never be enabled in a deployed build. This is a local test identity, not a CAPTCHA bypass and not a production authentication path. The service-role key is never sent to the browser.

For real authority accounts, use `scripts/provision_authority_accounts.py` after Supabase signup rate limits reset. The script is idempotent, skips existing users and reports failures without printing passwords.
