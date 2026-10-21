# Zetaris adapter — not implemented yet

Our verified installation uses the **Zetaris Cloud local platform Docker bundle** and `http://localhost:3000`; it is NOT the separate Zetaris Freemium `:9001` compose layout.

During the official build: register fabricated TB-v1 CSVs under an authorized local namespace, implement authenticated **read-only** source queries, preserve record IDs and timestamps, and distinguish timeout/denied from no matching record. Do not guess API paths. Credentials live only in gitignored local configuration. Never query official SITB/SATUSEHAT patient data.

See `docs/zetaris-setup.md`.
