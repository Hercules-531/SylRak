# Jev integration and credit controls

Jev is connected through Vercel AI Gateway using the official TypeSafe-compatible endpoint and model `typesafe-ai/jev`:
https://vercel.com/docs/ai-gateway/sdks-and-apis/typesafe

## What it does

The optional panel in distinctive-appearance search converts an operator's written description into proposed filters: visible colors, a supported model name, body type, roof color, pattern, visible accessories, plate visibility, and occlusion. Clicking “Search with Jev” applies the extracted filters and runs the candidate search immediately. The populated fields remain editable for refinement. Case creation can retain the resulting search criteria. Suggestions do not modify recognition evidence, accept associations, change priorities, mute alerts, or create watchlist records.

The current classifier uses a finite vocabulary, including four model names and two distinctive accessories/damage features. Unsupported attributes remain available through manual fields. Classifier confidence is not displayed as vehicle identity confidence. It cannot see photographs or recover covered features.

## Network and secrets

Only the submitted description (maximum 600 characters) and fixed classification questions leave the laptop. No stored sightings, photographs, registration histories, or API key are sent to the browser. Authentication uses `AI_GATEWAY_API_KEY`, falling back to the existing `API_KEYS/vercelkey.txt`. Both the credential directory and `.env` are ignored by source control.

Calls happen only when the user clicks “Search with Jev.” Opening pages, replaying cameras, searching normally, and alert processing do not call Jev. Failed calls are not retried automatically. Manual search remains usable if the service is unavailable.

## Persistent limits

- Maximum **20 online requests total**, maximum **10 in a rolling 24 hours**, shared across local users.
- Reserve **$0.005 per attempted call**, against an app allowance of **$0.10**. Failed or uncertain requests consume their reservation.
- Successful equivalent descriptions are cached, including across reloads and replay resets. Cached requests consume no new slot.
- SQLite reservations prevent concurrent tabs from overspending the request allowance. The ledger is `runtime/jev-usage.db`; do not delete it to reset usage.
- Provider-reported charges are recorded if available. The reservation is a conservative application guard, not a reading of your Vercel account balance or a provider-enforced spending cap.

One real request was used to verify the integration. Its gateway metadata reported a cost of **$0**, and the application still holds its conservative **$0.005 reservation**. That metadata is not a verification of your account's final bill or remaining balance. All subsequent automated browser checks used that cached result or mocked failures. Your remaining account credit is not queried.

## Verification

Tests cover explicit invocation, cache reuse, limits, failure reservation, no automatic retry, invalid suggestions, hidden roof handling, and sanitized errors. Browser checks cover automatically applying the real cached suggestion and displaying results, finding the multicolor fixture, reload behavior, and manual search after an unavailable response.
