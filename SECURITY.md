# Security Policy

blockchainkit is **teaching software**. Its cryptography is deliberately
unhardened so the mathematics stays visible: tiny RSA and Diffie-Hellman
parameters, variable-time elliptic-curve arithmetic, a Schnorr scheme that
is not BIP-340, and wire formats that are not Bitcoin's or Ethereum's.
These are documented model boundaries, not vulnerabilities. Never use
blockchainkit to protect real secrets or real value.

What does count as a vulnerability here:

- A bug that makes an experiment teach something false, for example a
  verifier that accepts an invalid signature, Merkle proof, or block.
- Code execution or resource exhaustion from loading data the package
  claims to validate.

Vulnerabilities in real blockchains, wallets, or cryptographic libraries
should be reported to those projects, not here.

## Reporting a Vulnerability

Please **do not open a public GitHub issue**. Instead, use GitHub's private
vulnerability reporting:

1. Go to the repository's **Security** tab.
2. Click **Report a vulnerability**.

If that's not available, open an issue asking a maintainer to contact you
privately, without describing the vulnerability itself.

We'll acknowledge reports within a few days and aim to release a fix
promptly once a report is confirmed.

## Supported Versions

Only the latest released version on PyPI is supported with fixes.
