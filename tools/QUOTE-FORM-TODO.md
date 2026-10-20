# Quote form: parked, not live yet

Branch `quote-form` holds the finished quote request page (/offert/, /fi/tarjous/, /en/quote/)
and the Worker that emails each request with photos inline. `main` (the live site) is unchanged.

## To finish (Cloudflare dashboard)
1. xpressbygg.com > Email > Email Routing > Enable (accept the DNS records).
2. Email Routing > Destination addresses > add the inbox, click the verify link it sends.
3. Workers & Pages > xpressbygg-site (Worker) > Settings > Variables and Secrets > Add,
   type Secret: `QUOTE_TO` = the inbox address. Deploy.
4. Optional "I'm human" check: Turnstile > Add widget (hostnames xpressbygg.com and
   franzsnickeri.workers.dev, mode Managed). Add two Secrets to the Worker:
   `TURNSTILE_SITEKEY` and `TURNSTILE_SECRET`. Deploy.
5. Test on the preview link for this branch, then merge `quote-form` into `main` to go live.

## Editing the quote pages
The three pages are generated: edit `tools/build_quote.py`, then run
`python3 tools/build_quote.py .` from the repo root.
