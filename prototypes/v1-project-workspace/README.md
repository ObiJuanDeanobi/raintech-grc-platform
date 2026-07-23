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

Open `http://127.0.0.1:5173/`.

The original three alternatives were narrowed to the selected Project Command
Center direction. Dashboard shows the Unified Queue across all clients. Select
a synthetic client in the left sidebar to open its Overview, Client Queue, and
objective-by-objective Assessments workspace.

All data is in memory; there is no backend, persistence, authentication, or
real client data.
