# Europeana discovery metadata

Europeana is connected for the local unified-discovery demo. On 2026-10-09 a
small authenticated Search API request for the exact phrase `"Burma Road"`
returned HTTP 200, `success: true`, 28 matches and three requested records.
These are candidate matches, not 28 verified historical sources.

The repository includes the resulting metadata sample, not the key used to
retrieve it. Previewing the demo needs no credentials. To refresh Europeana,
configure your own key: from `step1/`, copy `.env.example` to `.env.europeana`,
run `chmod 600 .env.europeana`, and fill in `EUROPEANA_API_KEY` in a local editor.
The `.env.*` ignore rule excludes the credential file. Never include it in Git,
documentation, publication screenshots, browser code or exported metadata.
The fetching utility also accepts `EUROPEANA_API_KEY` from the process environment.

## Fetch a small sample

Run from `step1/`:

```sh
python3 tools/fetch_europeana_metadata.py \
  --env-file .env.europeana \
  --query '"Burma Road"' \
  --rows 3 \
  --output data/europeana-discovery-candidates.json
```

The utility makes one request to the official Search API, normalizes selected
metadata and writes the output only after a successful response. It does not
fetch images or full text. HTTP errors, timeouts and missing credentials fail
explicitly without overwriting an existing sample. Credentials and raw
credential-bearing response URLs are not included in output or error logs.

## Review candidates before using them

The first live query returned an INA record titled “The discussion of the three
friends: The Pacific; Rommel offensive; Burma road; Japanese to Java.” Another
record, “Old pictures,” explicitly describes the Burma road to Jerusalem, so
it does not belong to the China–Burma topic. “Spring 1944 : spring on Burma Road”
has insufficient descriptive metadata to establish relevance. Do not include
these two records as China–Burma historical evidence merely because of the name.

Keep original titles, source identifiers, supplying institutions and links.
`year` is supplied catalogue metadata; it is not automatically an event date.
An external object URL does not prove unrestricted full-text access, so
`access_status` remains `unverified` until checked. Use metadata as text in any
future page, not as executable HTML.

Europeana descriptive metadata are provided under CC0. Source attribution and
links are retained. The `rights` statements for the underlying objects remain
separate; CC0 metadata do not make images or recordings freely reusable.
[Europeana metadata policy](https://www.europeana.eu/en/rights/europeana-data-sources)

Personal keys are for individual exploration and development testing. Before
operating a public service, follow the project-key process and applicable
limits. [Key types and registration](https://www.europeana.eu/en/how-to-register-for-and-manage-an-api-key)

See the [demo steps](demo-steps.md) for LoC, NDL, NARA and the completed search
page, or the [README](../README.md) for current capabilities and planned work.
