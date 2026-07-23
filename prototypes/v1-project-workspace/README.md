# V1 Project Workspace UI Prototype

> Experimental throwaway code for GitHub Issue #20. Do not promote directly
> into the production application.

Design question: What navigation and information hierarchy make a dense
CMMC/HIPAA delivery workspace clear enough for one person to operate daily?

## Run

From this folder, install dependencies if needed and start the prototype with
one command:

```powershell
.\run.ps1
```

Open `http://127.0.0.1:5173/?variant=A`. Use the floating switcher or the left
and right arrow keys to move between:

- A — Project Command Center
- B — Guided Engagement Flow
- C — Work Queue First

The project toggle switches between the synthetic CMMC and FQHC HIPAA
engagements. All data is in memory; there is no backend, persistence,
authentication, or real client data.
