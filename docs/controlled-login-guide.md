# Controlled Login Guide — V3.0

**Status:** Open signup blocked until Resend email is operational.
Controlled manual accounts used instead.

---

## How to log in (local dev)

1. **Go to the login page.** http://localhost:3000/login

2. **Enter your email and click "Send magic link."** The UI detects this is a dev environment and shows:
   > Dev mode — check the backend logs
   > This environment does not send real emails. A sign-in link was printed to the backend logs. Look for: `DEV MAGIC LINK:`

3. **Find the dev magic link in backend logs:**
   ```bash
   docker compose logs backend | grep "DEV MAGIC LINK"
   ```
   Example output:
   ```
   DEV MAGIC LINK: http://localhost:3000/login/verify?token=abc123...
   ```

4. **Open the link in a browser.** It authenticates you and redirects to onboarding (first time) or Today (returning user).

5. **Complete onboarding (first-time users only):**
   - Select your role (Founder, VC, Engineer, Researcher, Operator, Other)
   - Pick your industry and interests
   - Confirm → redirected to Today

6. **You're logged in.** Session persists for 30 days via HttpOnly cookie.

---

## How to log in (production)

Same flow, but Resend delivers a real email. The login page shows "Check your email" instead of the dev notice. Click the magic link in the email.

---

## Known limitations

- **Magic-link expiry:** 15 minutes after generation.
- **Resend (email):** Not operational in dev. In production, requires `full_access` API key scope for domain verification. Currently `sending_access` only.
- **No password login. No social login.** Magic-link only.
- **Localhost verify flow:** The verify page uses a 300ms delay + full page navigation to ensure the HttpOnly cookie is committed before the middleware checks it. If you see "Sign-in failed", the token may have expired — request a new one.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Link says "expired" or "invalid" | Request a new magic link. Tokens expire after 15 minutes |
| Link says "Sign-in failed" | Token was already consumed or expired. Request a new one |
| Login page shows "Check your email" in dev | /health resend status is wrong. Check `EMAIL_SEND_MODE=dev` in .env |
| White screen after login | Hard refresh (Cmd+Shift+R). Check browser console |
| Today shows generic stats | Complete onboarding or follow topics on /themes |
| Can't find a feature | Use nav: Today, Patents, Expiry, Opportunities, Trends, Topics, Companies, Search |

---

## Success criteria

- [ ] Lands on onboarding after first magic-link click
- [ ] Onboarding completes → redirected to Today
- [ ] Today shows "Your Topics" with real patent counts
- [ ] Can follow/unfollow topics
- [ ] Can follow/unfollow companies
- [ ] Can save patents to watchlist
- [ ] Theme toggle: System/Light/Dark
- [ ] No broken pages, 404s, or debug labels
- [ ] Freshness banner shows "Ingestion: Last ran X" (not red "Data is not live")
