# Trust Radar UI Plan

## Findings before implementation

- Frontend: Vite + React 19 + TypeScript + Tailwind CSS v4, `react-router-dom`, Lucide icons and the existing `cyber-*` dark theme. Pages are registered in `web/frontend/src/App.tsx`; navigation is in `src/components/Sidebar.tsx`. API calls live in `src/services/api.ts` and shared interfaces in `src/types/index.ts`.
- Existing view to preserve: `/communication` contains broadcast/unicast forms and broadcast result rows. Trust Radar will be a separate `/trust-radar` page so the current communication and unicast workflows remain available.
- Existing backend: `POST /api/message/broadcast` returns one signed packet, `range_m`, `seed` and per-recipient distance, delivery status, accepted/final verification status, rejection reason, processing/verification latency, safety result and warning. `POST /api/message/send` returns its packet, hash, accepted/reason and full pipeline steps. Existing attack routes cover replay, tampering, impersonation, fake certificate, stale message and false data. `GET /api/vehicles`, `GET /api/simulation/config` and `PATCH /api/vehicles/{vehicle_id}` provide current positions, headings, speed and configuration.
- Gate gap: broadcast currently exposes a final verification status and reason, not six separate gates. The existing unicast and attack `pipeline` reports schema, certificate, identity, signature, replay and timestamp stages. Neither broadcast nor unicast reports a separate relevance stage for rejected/not-delivered recipients. The new broadcast response will add a backward-compatible `verification_gates` array mapped from the actual receiver outcome and authoritative rejection reason; undelivered gates will be `not_reported`. Relevance will use the actual safety result when available, otherwise `not_reported`.
- The API does not report per-stage timings. Timeline steps and pulse/rail sequencing will be labelled visual replay/animation, never as measured durations. Existing `processing_ms` and `verification_ms` remain the only measured recipient latencies.
- Tampering uses the real `POST /api/attack/tampering` flow against the last captured signed packet. Its response currently omits the packet bytes; it will add the modified message with the unchanged original signature as a JSON-safe `packet` field so the anatomy strip can display the real tampered outcome.
- Existing frontend baseline (before Trust Radar changes): `npm test` passed (1 Node test); `npm run build` passed with the existing >500 kB chunk warning; `npm run lint` exited 0 with two existing React effect warnings in Dashboard and EventLogPage.

## Implementation plan

1. Add typed, backward-compatible broadcast gate results and include the actual tamper/false-data packet and verification pipeline needed to visualize existing attacks. Keep `SecureVehicle.receive_packet()` as the authority; do not alter cryptographic primitives or replace verification.
2. Add focused Trust Radar presentation components: controls/state, local-coordinate SVG, six-gate rails, packet strip, timeline, and collapsed recipient drawer. Keep API-derived data authoritative and represent missing fields as not reported.
3. Add `/trust-radar` routing/navigation while retaining the existing communication, certificate, log and attack pages.
4. Implement broadcast/unicast, vehicle positioning via the existing PATCH endpoint, attack calls, state filters, timeline replay, reduced-motion behavior, loading/error/empty states, keyboard labels, and responsive layout.
5. Add backend gate-contract tests and frontend tests for pure state mapping and interaction behavior where the installed test environment permits; run backend and frontend suites, build, lint, `git diff --check`, and real backend scenario checks where local socket permissions allow.

## Known limits

- The radar is a local planar visualization of the API's geographic coordinates, not a map or radio propagation model.
- Certificate and schema gates for broadcast are exposed as stage statuses inferred from the actual verifier's final typed status/reason and its fixed validation order; the API does not provide independent wall-clock timing per gate.
- Browser interaction against a live API may be unavailable in this sandbox because local socket operations can be restricted. If so, tests will exercise the real state/API functions and the limitation will be reported.
