# Crypto in Brief

[Crypto in Brief](https://cryptoinbrief.xyz) explains what happens inside cryptocurrencies for readers with no assumed background. The site covers Bitcoin, proof of stake, Solana, Sui, Monero, Zcash, and zero knowledge proofs through illustrated essays and browser labs in English and Arabic.

The labs use a mix of browser cryptography and deliberately small teaching models. The homepage creates an ephemeral ECDSA P256 key, signs a demonstration payment, verifies the original message, and rejects an altered amount through the Web Crypto API. Its wallet balances, network, and ledger remain a visual model; production networks use different transaction formats and signature schemes. Consensus races, validator selection, privacy constructions, and other systems that would require a network are simulations built to expose one mechanism at a time. They are learning tools, not wallet software, production cryptography, or security advice.

## Reading path

Start with [the illustrated overview](crypto-summary.html), then follow the essays in this order:

1. [Bitcoin from zero](bitcoin-from-zero.html)
2. [The Bitcoin white paper](bitcoin-whitepaper.html)
3. [Proof of stake from zero](proof-of-stake.html)
4. [Solana from zero](solana.html)
5. [Sui from zero](sui.html)
6. [Monero under the hood](monero-under-the-hood.html)
7. [How to get Monero](getting-monero.html)
8. [Bitcoin and Monero white papers compared](bitcoin-vs-monero-whitepapers.html)
9. [Zcash from zero](zcash.html)
10. [Zero knowledge from zero](zero-knowledge-from-zero.html)

Developers can optionally follow a transaction through the verified source references in [Inside the Bitcoin Core codebase](bitcoin-codebase.html).

Arabic editions are available for the [illustrated overview](crypto-summary-ar.html), [Bitcoin](bitcoin-from-zero-ar.html), and [Monero](monero-from-zero-ar.html).

## Run locally

The site has no build step. Serve the repository root so navigation, shared images, and browser security rules behave consistently:

```console
python3 -m http.server 8000
```

Then open `http://localhost:8000/`. The site serves its fonts from `assets/fonts/` and includes the corresponding SIL Open Font License files in that directory.

## Maintainer checks

The published site has no build step or runtime package dependency. The development packages only support browser QA. Install them and the Python QA dependency with:

```console
pnpm install
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r qa/requirements.txt
python3 -m playwright install webkit
```

Run the static audit, labs, and standalone WebKit smoke test with:

```console
pnpm test
pnpm test:labs
pnpm test:webkit
```

The story and responsive UI suites use the local server. Keep this running in one terminal:

```console
pnpm serve
```

Then run these in another:

```console
pnpm test:stories
pnpm test:figures
pnpm test:support
pnpm test:acquisition
pnpm test:monero-figures
pnpm test:summary-figures
pnpm test:zcash-colors
pnpm test:bitcoin-guides
pnpm test:ui
```

`pnpm serve` keeps the local site on `127.0.0.1:8934`. The static audit covers canonical pages, metadata, local links, fragments, JSON LD, discovery files, and JavaScript syntax. The labs, stories, and UI suite expect an installed Google Chrome browser. The WebKit smoke test starts its own server.

## Project layout

The site is static HTML, CSS, SVG, and JavaScript. Shared files under `assets/` provide the site styles, interactions, fonts, and official coin marks; individual essays also contain the code for their illustrations and labs. Coin mark sources and upstream hashes are recorded in [`assets/BRAND-SOURCES.md`](assets/BRAND-SOURCES.md). Root assets provide the favicon and social preview image. `package.json` and `pnpm-lock.yaml` are development only. `robots.txt`, `sitemap.xml`, `rss.xml`, `llms.txt`, `llms-full.txt`, `ai.txt`, and `humans.txt` describe the public site for crawlers and readers.

Facts that may change are dated in the essays. Corrections and translations are welcome through issues and pull requests.

## Credits

Written and maintained by [Moamen Basel](https://moamenbasel.com), security engineer at [Grey Core Labs](https://greycorelabs.com).

## License

Source code and documentation are available under the [MIT License](LICENSE).
