# Engine note — the parity target as observed on Thu 2026-11-12 (from retail session MR-S9)

For the engine lane, which owns the parity documents (`MERDIAN_Parity_Target_Spec.md`, `ADR-025-parity-acceptance-criterion.md`, `claude/parity_eval/`). Sent at the operator's word (11-12 17:54 IST: "Record and send to MerdianEngine which maintains a parity doc").

**This note rules nothing and reopens nothing.** ADR-025 closed parity on 2026-10-09 and says a layer outside the fourteen does not count toward parity. Whether anything below gets a disposition, an ENH entry or no action is the engine lane's and the operator's call.

## How this was read

- `<parity-target site>/signup/` step 1: page text read through the operator's browser, 11-12 about 17:30 IST.
- Steps 2 and 3, the broker settings and the AI assistant page: the operator's screenshots and pasted page text from a fresh trial sign-up, 11-12 17:38 to 17:54 IST.
- Nothing was read from inside the workspace (no board, tab or number was seen). Feature names below are the marketing panel's own words, not verified against a working screen.
- Lines marked **[inference]** are my reading, not something the page states.

## 1. Coverage and features named on the sign-up page

Not checked against the fourteen layers here; the mapping is left to the engine lane.

- **Underlyings:** NIFTY, BANKNIFTY, SENSEX, FINNIFTY, MIDCPNIFTY, F&O stocks. MERIDIAN covers NIFTY and SENSEX.
- **Gamma and levels:** net gamma, pin and its conviction, flip, call and put walls, GEX by strike.
- **Concentration:** HHI by session and expiry, each strike's share of exposure.
- **Delta and flows:** delta positioning by strike, aggressor balance, hedge ladder, charm and vanna.
- **OI and volatility:** OI change and rotation, IV surface, term and skew, unusual volume by strike.
- **Replay:** any session minute by minute from the 09:15 open, past sessions kept.
- **Workspace:** user-built layout, compare two indices, F&O stock screener.

`claude/target_read_Mar-Oct2026.md` already records the tabs as of September. Items I did not find named there: BANKNIFTY / FINNIFTY / MIDCPNIFTY / F&O stock coverage, aggressor balance, hedge ladder, unusual volume by strike, the two-index compare, the stock screener. I searched by retrieval, not by reading that document end to end, so treat "not found" as unconfirmed.

## 2. AI assistant (MCP connector)

`target_read_Mar-Oct2026.md` already notes a read-only Claude MCP connector. The settings page adds detail:

- Heading: "Ask Claude or ChatGPT about your own positioning." Works with Claude and ChatGPT.
- One address for both: `<parity-target API>/mcp`. Added in Claude as a custom connector, in ChatGPT as a custom MCP server. Setup guide at `<parity-target site>/ask-claude` (Claude app, phone, Claude Code, ChatGPT).
- Authorisation: the assistant opens a the parity target page; the user signs in and presses Allow; the password is entered on the parity target's site only. A manual token is offered as an alternative. Connected assistants are listed on the page.
- Stated limits. It can: read the same numbers the workspace shows and nothing else; answer questions about them in plain language. It cannot: place an order; change a setting; see any account but the user's.
- Tied to the subscription: it stops answering when the subscription lapses and resumes on renewal.
- Suggested first prompt is a product tour ("too many tabs. Help me navigate through the parity target step by step").
- Footer: analytics for education and research; not investment advice; not a recommendation to buy or sell.

Relevance to the engine: MERIDIAN has no equivalent surface. `agentic_layer_roadmap_S90.md` is the nearest register. **[inference]** The connector is a per-user, read-only view over the same API the board uses, gated by entitlement, so the retail platform (auth, entitlements) and the engine's read views would both be involved if it were ever built.

## 3. Data stance stated on the broker pages

- Dhan and Firstock pages both say the broker "supplies live prices only; everything else on your dashboard comes from the parity target."
- Dhan page: market data needs Dhan's Data API subscription (Rs 499 a month, paid to Dhan by the user).
- Zerodha page: the user's own Kite Connect app with an active subscription; a browser login with Kite every morning before 09:15 "or the dashboard gets no data that day".
- **[inference]** Their exchange-data position is: the subscriber's own broker feed for prices, the parity target's own computation for everything else. Which inputs (OI, IV) come from which side is not stated.

## 4. Sign-up and broker connect (retail detail, summarised)

Full record in `claude/retail/rulings_mr_s9.md`, "Findings recorded 2026-11-12". In short: 7-day trial with no card; email verified by code, phone collected but no SMS OTP step seen; 14 brokers, none on an app held by the parity target; 3 need a daily login by the user (Zerodha, Fyers, ICICI Direct), 11 are logged into by the parity target using credentials the user stores with it (for Dhan: client id, PIN and TOTP secret).

## 5. Not known from this read

- Prices of the paid plans (only the Diwali offer: 3 months +15 days, 6 months +1 month, start by 16 Nov).
- What the MCP tools are called and what they return.
- Anything inside the workspace after a broker is active.
