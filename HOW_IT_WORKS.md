# How Cloud Cost Guardian Works (Plain English)

You drop a CSV of AWS billing data into the repo (a spreadsheet listing things like "this EC2 instance cost $0.08 yesterday"). That push automatically kicks off a robot (GitHub Actions) that:

1. **Reads the spreadsheet** and looks for rows it hasn't dealt with yet.
2. **Asks an AI (Gemini)**, for each row: "is this cloud resource being wasted, and if so, why?" The AI answers with a category (idle, oversized, orphaned, or misconfigured), who should fix it, and a to-do list for fixing it.
3. **Double-checks the AI's answer** with simple math — if the AI says "this is a Critical emergency!" about something costing 8 cents, the system quietly corrects that down to Low. Anything still genuinely high-priority gets marked "needs a human to confirm" instead of just being auto-opened as urgent.
4. **Saves everything to a database** (Supabase) — the raw billing detail in one private table, and a "here's what to fix" ticket in another table that's readable by the public.
5. **Skips anything it's already done before** — so if you accidentally run it twice on the same file, it won't re-ask the AI or create duplicate tickets.

Separately, there's a **live webpage** (hosted for free on GitHub Pages) that anyone can open — it just reads that ticket table straight from the database and shows a dashboard: total money being wasted, how many tickets are open, and clicking one shows the full "here's how to fix it" instructions.

So: **CSV in → AI reads and judges each line → sanity-checked → saved as a ticket → dashboard shows it live.** Nothing needs a server running 24/7 — GitHub Actions only wakes up when there's new data to process, and the dashboard is just a static page pulling from the database whenever someone visits it.
