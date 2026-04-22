# RUNBOOK: <operation name>

> **Template.** Copy this file, rename to `runbook_<operation>.md`, fill in all fields. Delete the italic guidance lines before committing.

---

| Field | Value |
|---|---|
| **Operation** | *(one-line description, e.g. "Rotate the Dhan access token used by all local and AWS runners")* |
| **Frequency** | *(Daily / Weekly / Monthly / Quarterly / As-needed / On-failure)* |
| **Environment** | *(Local only / AWS only / Both)* |
| **Prerequisites** | *(what must be true before starting — e.g. Dhan account credentials available, .env file writable)* |
| **Expected duration** | *(e.g. 2 minutes)* |
| **Who can do this** | *(Navin only / Navin or on-call / automated via task N)* |
| **Last verified** | *(YYYY-MM-DD — update after a successful run)* |

---

## When to use this runbook

*One paragraph. What trigger brings someone here? A scheduled refresh? An error? A setup task?*

---

## Steps

> Every step is a concrete action. No interpretation at runtime. If a step requires judgment, flag it explicitly.

### 1. *(short step title)*

```bash
# exact command or action
```

*What to expect:* *(stdout, log line, DB row — whatever tells you it worked)*

### 2. *(short step title)*

```bash
# exact command or action
```

*What to expect:* *(...)*

### 3. *(short step title)*

*(...)*

---

## Verification

How do you confirm this worked?

```bash
# verification query or command
```

Expected output: *(specific string, row count, status code)*

---

## Failure modes

| If you see… | It probably means… | Do this |
|---|---|---|
| *(specific error)* | *(root cause)* | *(recovery action)* |
| *(specific error)* | *(root cause)* | *(recovery action)* |

---

## Related

- Related runbooks: *(links)*
- Related tech debt: *(TD-N if any)*
- Related code files: *(paths)*
- Related tables: *(names)*

---

## Change history

| Date | Change | Commit |
|---|---|---|
| YYYY-MM-DD | Created | `<hash>` |

---

*Runbook — commit with `MERDIAN: [OPS] runbook_<op> — created/updated`.*
