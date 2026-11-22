## Context

See proposal.md - Why. The client already builds `GET /stock-movement` from `XANO_STOCK_MOVEMENTS_URL`, omits absent optional filters, validates supplied parameters, and returns a response dictionary after requiring `movements` to be a list. The history form has an explicit submit button and editable page/per-page fields, but does not offer previous/next controls or consume pagination metadata. No live request was made; previous HTTP 400 messages are recorded in mock tests and an audit report, not verified against the currently published endpoint.

## Goals / Non-Goals

**Goals:**
- Normalize the documented paginated response into the records for the requested page without duplicating entries.
- Make page navigation an explicit user action and preserve current filters while changing pages.
- Enforce documented page size limits and keep diagnostic errors sanitized.
- Keep optional filter omission behavior; do not infer mandatory filters from prior HTTP 400 responses.

**Non-Goals:**
- Change the Xano route, endpoint deployment, backend data, authorization, movement business rules, or accepted movement enum.
- Trigger automatic requests on page render or test against the live Xano service.
- Invent or hard-code undocumented pagination metadata fields.

## Decisions

- Keep the base URL selected through `XANO_STOCK_MOVEMENTS_URL` and route `/stock-movement`; preserve the existing endpoint and session-authentication path.
- Build query parameters only from values supplied by the UI. Blank/absent optional filters remain omitted; provided filters retain their documented names. Validate `page >= 1` and `1 <= per_page <= 100`.
- Normalize the records from the documented response lists `movements` and `items`. Prefer the established `movements` list when present and use `items` as a fallback; never concatenate both lists because that could duplicate records. Keep recognized response metadata available to the UI without assuming undocumented key names.
- Retain the explicit query form and add explicit previous/next navigation that reuses the active filters and page size. No pagination metadata field is established in the available contract; therefore keep the next-page action available after any successful response, even if it contains fewer than 100 or zero records, rather than inferring the end of pagination from the returned count.
- Continue surfacing HTTP status and useful backend validation text through the existing redaction helper. Do not treat successful mocked requests as evidence that the published endpoint accepts omitted filters.
- Update mocked client and Streamlit AppTest coverage for both response list shapes, optional parameter omission, page-size bounds, navigation, filter reset, HTTP 400 diagnostics, and token redaction.

## Risks / Trade-offs

- [The currently published endpoint may differ from the previously inspected optional-parameter contract] -> Preserve optional omission and exact parameter names; do not add artificial values, and report endpoint compatibility as unverified until confirmed through an authorized contract source.
- [The response may include both `items` and `movements` with semantics not documented in the repository] -> Prefer the existing `movements` list, use `items` only as fallback, and do not merge arrays. Confirm this interpretation against the provided endpoint contract during implementation.
- [Pagination metadata keys are not established in the inspected code] -> Do not infer field names or infer the final page from the returned count; keep next-page navigation available after every successful response.
