DISPATCHGRID ROUND 2 INTEGRATION PACKAGE

This package contains two separate, size-optimised source ZIP files:

1. BDSC_Backend_Source.zip - Main FastAPI backend, PostgreSQL persistence, models, schemas, routes, services, migrations, tests, docs and supplied project data.
2. DispatchGrid_Scheduler_Source.zip - Scheduling/assignment optimisation and disruption recovery source, APIs, schemas, tests, documentation and dataset.

Local virtual environments (.venv), Python cache/bytecode, pytest cache, Git metadata, and the real BDSC .env file were excluded. The source projects and requirements files are retained. Recreate virtual environments and install dependencies on your machine. Use .env.example files for local configuration; never share real credentials.

These are source projects, not an already integrated application. Inspect both projects and their API contracts before integration. Preserve BDSC persistence and approval workflow. Resolve the Bengaluru / synthetic scheduler coordinates / Mysuru frontend data differences before map integration.
