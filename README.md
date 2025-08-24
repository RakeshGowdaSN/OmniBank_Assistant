---

## Security & privacy notes

- Do not commit `.env` or secrets to source control.
- Treat recorded audio as sensitive user data; ensure TLS for network transport in production.
- Add authentication and RBAC before connecting to real banking APIs.

---

## Contributing

- Read and run unit tests (if any) before submitting PRs.
- Keep changes modular: update banking_agent tools for new features; keep frontend audio logic in static/js.
- Open issues for new feature requests (multi-language, JWT auth, external bank connectors).

---

## License

MIT — see LICENSE file.

---
