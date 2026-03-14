---
name: Decisive layer and layered architecture
overview: "Consolidated plan: (1) Checklist of all items from v1–v3 and detailed/decisive plans so nothing is missed; (2) Single decisive layer, risk layer, goals (min trades, max profit, brokerage-aware, carry only on very high prob); (3) Layered architecture (Data, Technical, Information, Knowledge, Risk, Decisive); (4) Code structure and repository layout—single codebase recommendation, module boundaries, folder structure, dependency direction, config, and maintainability."
todos: []
isProject: false
---

# Decisive Layer + Layered Architecture – Consolidated Plan (with Checklist and Code Structure)

This plan (1) **reconciles all prior plan versions** via a checklist so no key information is dropped, (2) keeps the **single decisive layer + risk layer + goals**, (3) keeps the **layered architecture**, and (4) adds **code structure and repository layout** (single codebase vs services, module layout, dependencies, config, maintainability).

---

## Part A – Consolidated checklist (from v1, v2, v3, detailed, decisive)

Use this to verify nothing is missing when implementing.

**Data (v1, detailed)**  

- DataProvider interface: `get_quote(symbol, is_fno)`, `get_ohlc_bars(symbol, interval, from_ts, to_ts)`, `get_current_time()`  
- Live implementation: wrap existing Quotes + broker historical API (Kite/Breeze) for bars; cache by symbol/interval/day  
- Backtest/historical implementation: bars from CSV or pre-fetched; get_quote = bar at current replay time  
- Bar buffer: in-memory (or small store) per (symbol, interval), last N bars; updated on bar close (and tick for forming bar in live)  
- Multi-timeframe config: e.g. 1m, 5m, 15m, 30m, 1h, 1d  
- Phase 1: futures + spot only; Phase 2: options (expiry, DTE, premium, greeks)

**Technical (v1, v2, detailed)**  

- Indicator module: RSI, EMA, ATR, BB, MACD etc. per timeframe; input = list of bars, output = latest values into technical cache  
- Support/resistance: auto (swing high/low) + manual (user levels); per symbol per timeframe; in technical cache  
- Candlestick patterns: doji, engulfing, hammer, pin bar, inside bar; last 1–3 bars per TF; in technical cache  
- Spot: same OHLC/indicators/S/R/patterns for underlying spot symbol(s)  
- Global/sentiment: optional symbols (e.g. US indices, commodities); quote or 1–2 bars in context  
- Technical cache: updated on bar close (or at interval); decision loop only reads it (no heavy compute in 30s/1m/5m path)

**Information layer (v2, v3, detailed)**  

- Input types: user views, news, scraped data, sector view, market direction view  
- No user-assigned weightage; LLM decides relevance and adapts when view/news is wrong  
- Storage: type, content, optional source/timestamp; short-term (session/day) for daily inputs  
- APIs: add view, add news, trigger scrape, add sector/market view; list active items  
- Context builder: format all with labels for LLM

**Knowledge layer (v3, detailed, decisive)**  

- Gyan: long-term store (rules, examples, e.g. double-bottom, “when to carry”, “when not to trade”)  
- Outcomes/corrections: user corrections and optional “recent outcomes” summary for learning  
- Loader + formatter for prompt; no model training in v1, prompt-time injection only  
- Editable via chatbot/admin UI; versioning or “active” flag for rules

**Probability and order choice (v2, v3, detailed)**  

- Broker limit: only one of target or SL active at a time  
- Probability of candle close (for active TF): LLM or heuristic; used to choose “place SL first” vs “place target first”  
- Order logic: from LLM output (suggested_active_order: SL | target), place/cancel accordingly; re-evaluate each decision cycle and switch when justified

**LLM (v1, v2, v3, detailed)**  

- Input: information + technical + knowledge + risk context  
- Output (structured JSON): action (TRADE | NO_TRADE), direction, symbol, quantity, entry_type, limit_price (brokerage-aware), sl, target, active_order (SL | target), carry_to_next_day, probability_win/loss, reason, optional regime  
- Local: Ollama + Mistral 7B or Qwen 2.5 7B; lighter option Qwen 2.5 3B / Phi-3  
- Prompt: min trades, max profit, adapt if view wrong, only carry when very high probability; use gyan for tops/bottoms, mean reversion, momentum  
- Caching: backtest = cache per (symbol, decision_time); live = optional cache 1–5 min

**Latency and scheduling (detailed)**  

- Decision interval configurable: 30s / 1m / 5m  
- Heavy work (indicators, S/R, patterns) in bar/cache update; decision path only reads cache + one LLM call per interval  
- Scheduler: sleep(interval) → read cache + info + knowledge + risk → build context → LLM → order logic → TradeManager

**Risk (decisive)**  

- Risk layer: inputs = positions, PnL, drawdown, config limits (max exposure, max loss/day, max positions)  
- Outputs: risk context for prompt + hard constraints  
- Risk gate: before sending order, check signal vs constraints; block or reduce size and log

**Goals (decisive)**  

- Minimum trades, maximum profit (brokerage-aware)  
- Probability of win vs loss in output; only trade when expected value positive after costs  
- Carry to next day only when probability very high (config/gyan)  
- Buy low, sell high; re-enter when justified; identify tops/bottoms, mean reversion, momentum via gyan

**Backtest (v1, detailed)**  

- Historical DataProvider; bars from broker API or CSV  
- Replay: bar-by-bar or step every 30s; update bar buffer and technical cache; no look-ahead  
- SimulationOrderManager: same interface as BaseOrderManager; fill by rule (e.g. next bar open)  
- At each decision time: run full decision pipeline (context → LLM or cached → order logic); TradeManager uses SimOrderManager  
- RUN_MODE = live | backtest in config

**Integration with existing codebase**  

- Keep: Trade, TradeManager, OrderManager (Zerodha/ICICI), Controller, Instruments, login, REST (home, login, start algo, positions, holdings)  
- Algo/start flow: in live mode start ticker + decision scheduler; in backtest mode start replay + decision at interval  
- New: decisive entry point (replaces strategy.run) that runs context → LLM → order logic and feeds TradeManager

**Fundamentals and options (v3, detailed)**  

- Fundamentals: optional for spot/equity in Phase 1 (P/E, sector, etc.); add to context  
- Phase 2 options: expiry, time to expiry (DTE), premium, greeks; extend context and order logic

**UI / chatbot (decisive)**  

- One interface to add gyan (long-term) and daily inputs (views, news, etc.) (short-term)  
- Optional: “what’s in context today”, “last decision reason”  
- Backend: APIs for add/list/expire; storage split by type and scope (long-term vs short-term)

---

## Part B – Code structure and repository layout

**Recommendation: single codebase (monolith) first.**

- One repo, one deployable app: simpler to run, debug, and deploy; shared types and config; no network boundaries between layers.  
- Splitting into separate services (e.g. “data service”, “LLM service”) later is possible **only if** you hit scaling or team boundaries; for one developer and “improve each layer over time”, a single codebase with clear **module boundaries** is easier to maintain and test.

**When to consider multiple services later:**  

- You need to scale data or LLM independently, or  
- A separate team owns one part (e.g. ML models).  
Then extract one or more layers into separate services with clear APIs; the checklist and layer boundaries still apply.

---

### Suggested folder structure (single codebase)

Keep existing packages and add new ones so that **layers map to packages** and dependencies flow one way (upper layers depend on lower, not the reverse).

```
intrade-backend/
├── config/                    # existing
│   ├── Config.py
│   ├── server.json
│   ├── system.json
│   ├── brokerapp.json
│   ├── holidays.json
│   └── decision.json         # new: interval_sec, timeframes, risk_limits, etc.
├── core/                     # existing + thin orchestration
│   ├── Controller.py
│   ├── Quotes.py             # keep; DataProvider live impl can wrap this
│   └── Algo.py               # adapt: start scheduler + (ticker or backtest runner)
├── data/                     # NEW – Layer 1
│   ├── __init__.py
│   ├── provider.py           # DataProvider interface + get_quote, get_ohlc_bars, get_current_time
│   ├── live_provider.py      # wraps Quotes + broker historical
│   ├── historical_provider.py # for backtest; bars from CSV or pre-fetched
│   ├── bar_buffer.py         # in-memory bar buffer per (symbol, interval)
│   └── bar.py                # Bar dataclass or simple class (o,h,l,c,v,ts)
├── technical/                # NEW – Layer 2
│   ├── __init__.py
│   ├── cache.py              # TechnicalCache: read/write indicator, S/R, pattern summary per (symbol, tf)
│   ├── indicators.py         # compute RSI, EMA, ATR, BB, MACD from bars
│   ├── support_resistance.py # auto + manual S/R from bars
│   └── patterns.py           # candlestick pattern detection
├── information/              # NEW – Layer 3
│   ├── __init__.py
│   ├── store.py              # add/list/expire items (views, news, scraped, sector, market)
│   └── context_builder.py    # format for LLM (labels, no weightage)
├── knowledge/                # NEW – Layer 4
│   ├── __init__.py
│   ├── store.py              # gyan rules + examples; outcomes/corrections
│   └── context_builder.py    # format for prompt
├── risk/                     # NEW – Layer 5
│   ├── __init__.py
│   ├── manager.py            # RiskManager: positions + PnL + limits → risk context + constraints
│   └── gate.py               # check order vs constraints; block or reduce
├── decisive/                 # NEW – Layer 6
│   ├── __init__.py
│   ├── context_builder.py    # assemble tech + info + knowledge + risk
│   ├── llm_client.py         # Ollama client, prompt template, JSON parse
│   ├── order_logic.py        # from signal: place SL or target, size, price; single-order constraint
│   └── scheduler.py          # loop: sleep(interval) → build context → LLM → order_logic → TradeManager
├── backtest/                 # NEW
│   ├── __init__.py
│   ├── runner.py             # replay loop; advance time; update bar buffer + technical cache
│   ├── sim_order_manager.py  # implements BaseOrderManager; simulated fills
│   └── data_loader.py        # load bars from CSV or broker historical for date range
├── instruments/              # existing
├── loginmgmt/                # existing
├── models/                   # existing + optional new (e.g. RiskLimitConfig)
├── ordermgmt/                # existing; SimOrderManager in backtest/
├── restapis/                 # existing + new
│   ├── ...
│   ├── InformationAPI.py     # add view, add news, list (for chatbot)
│   └── KnowledgeAPI.py       # add gyan, list, outcomes (for chatbot)
├── ticker/                   # existing
├── trademgmt/                # existing (TradeManager, Trade, etc.)
├── utils/                    # existing
├── templates/                # existing; optional chatbot UI later
├── main.py
└── requirements.txt          # add: requests (for Ollama), optional pandas/ta for indicators
```

**Existing code stays where it is.** New layers live in new packages (`data`, `technical`, `information`, `knowledge`, `risk`, `decisive`, `backtest`). `core.Algo` is adapted to start either live (ticker + decisive scheduler) or backtest (runner + decisive scheduler). No need to rename `strategies/` immediately; old strategies can stay until you fully switch to the decisive layer; then you can deprecate or remove them.

---

### Dependency direction (maintainability)

- **Lower layers do not import from upper layers.**  
  - `data` → no dependency on technical, information, knowledge, risk, decisive.  
  - `technical` → may depend on `data` (e.g. bars).  
  - `information`, `knowledge` → no dependency on `data` or `technical` (they are just storage + context formatters).  
  - `risk` → may depend on `trademgmt` (positions, PnL) and `config`.  
  - `decisive` → may depend on `data`, `technical`, `information`, `knowledge`, `risk`, `trademgmt`, `ordermgmt` (via TradeManager).  
  - `backtest` → may depend on `data`, `technical`, `decisive`, `trademgmt`, `ordermgmt` (SimOrderManager).
- **Config:** All layers read from `config` (or a single config object passed from main). Add `decision.json` (or equivalent) for: `decision_interval_sec`, `timeframes`, `symbols`, `risk_limits`, `run_mode`, `ollama_url`, etc.
- **Testing:** Each package can have its own tests (e.g. `tests/data/`, `tests/technical/`, `tests/decisive/`). Mock the layer below; e.g. test decisive layer with fake technical/info/knowledge/risk context.

---

### Single codebase vs multiple services (summary)


| Aspect          | Single codebase (recommended now)                                  | Multiple services (later, if needed)                           |
| --------------- | ------------------------------------------------------------------ | -------------------------------------------------------------- |
| Repo            | One repo                                                           | One repo with multiple runnables, or separate repos            |
| Deploy          | One process (Flask + scheduler thread)                             | Data service, LLM service, API service, etc.                   |
| Communication   | In-process function calls                                          | HTTP/gRPC between services                                     |
| When to use     | Current scope; one developer; improve layers incrementally         | Scale, separate teams, or independent scaling of LLM/data      |
| Maintainability | Clear module boundaries and dependency direction; test per package | Same layer boundaries; add API contracts and integration tests |


Start with **single codebase**; introduce services only when the above reasons apply.

---

### Config (centralised)

- **Existing:** `server.json`, `system.json`, `brokerapp.json`, `holidays.json`.  
- **New (e.g. `config/decision.json` or a section in existing):**  
  - `run_mode`: `"live"` | `"backtest"`  
  - `decision_interval_sec`: 30 | 60 | 300  
  - `timeframes`: `["5m", "15m", "1h"]`  
  - `symbols`: list for futures + spot (and later options)  
  - `risk_limits`: max_exposure, max_loss_per_day, max_open_positions  
  - `ollama_url`, `ollama_model`  
  - `backtest`: start_date, end_date, data_source (csv | broker)

One place to change behaviour without touching code; all layers read from config (or a config module that loads these).

---

### Improving layers over time

- **Data:** Swap or add broker, add CSV loader, change bar buffer size or storage (e.g. Redis) without touching technical or decisive.  
- **Technical:** Replace indicator logic or add new patterns; only `technical/cache.py` and callers in decisive need to agree on the cache shape.  
- **Information / Knowledge:** Change storage (DB, files) or add chatbot UI; keep the same “context builder” interface (e.g. `get_information_context()`, `get_knowledge_context()`).  
- **Risk:** Add new limits or risk metrics; decisive layer only consumes “risk context” and “constraints” string/dict.  
- **Decisive:** Replace LLM with another model or add a trained model as an extra input; keep “context in → structured signal out” and “order_logic(signal) → TradeManager”.

Keeping these boundaries and the checklist above will keep the system maintainable and improvable without big rewrites.