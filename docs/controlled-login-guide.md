# Controlled Login Guide — Boris / Reviewer Access

**Status:** Open signup is blocked until Resend is operational.
Controlled manual accounts are used instead.

---

## How a reviewer logs in

1. **Get a pre-provisioned sign-in link from Andy.**
   Andy generates a magic-link URL using the admin sign-in tool and
   sends it directly to the reviewer (email, Slack, etc.).

2. **Open the link in a browser.**
   The link looks like: `https://inventionindex8.com/auth/magic?token=...`
   It authenticates you and redirects to Today.

3. **Complete onboarding (first-time users only).**
   - Select your role, industry, interests
   - Review suggested companies and themes (remove any you don't want)
   - Confirm → redirected to Today

4. **You're logged in.** The session persists via cookie.

## Known limitations

- Magic-link expiry: 15 minutes after generation. If your link is
  stale, ask Andy for a new one.
- Resend (email delivery) is not operational yet. Magic links must
  be shared directly — they are NOT sent via email.
- "Sign in" on the landing page (`/login`) accepts email addresses
  but will NOT send an email while Resend is down. Direct links work.
- No password-based login. No social login. Magic-link only.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Link says "expired" | Ask Andy for a fresh link |
| Link says "invalid" | Copy the full URL — tokens are case-sensitive |
| White screen after login | Hard refresh (Cmd+Shift+R). If persists, check JavaScript console |
| Today shows generic stats | Complete onboarding or follow topics on /themes |
| Can't find a feature | Use the left nav: Today, Search, Companies, Expiry Radar, Watchlist |

## Success criteria for reviewer

- [ ] Lands on Today after login
- [ ] Sees "For You" section (after onboarding/topic setup)
- [ ] Can search for a patent by keyword
- [ ] Can open a patent detail page
- [ ] Can save a patent to watchlist
- [ ] Can navigate to Companies, Expiry Radar, Watchlist
- [ ] Theme toggle shows System/Light/Dark
- [ ] No broken pages, 404s, or debug labels
