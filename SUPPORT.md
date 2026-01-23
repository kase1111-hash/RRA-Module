# Support

This document explains how to get help with the RRA Module (Revenant Repo Agent).

## Documentation

Before seeking support, please check the available documentation:

- **[Quick Start Guide](QUICKSTART.md)** - Installation and basic usage
- **[Usage Guide](docs/USAGE-GUIDE.md)** - Comprehensive how-to guide
- **[FAQ](FAQ.md)** - Frequently asked questions
- **[Specification](SPECIFICATION.md)** - Technical specification

### Integration Guides

- **[Selling Licenses](docs/SELLING-LICENSES.md)** - Monetize your repository with Story Protocol
- **[Blockchain Licensing](docs/BLOCKCHAIN-LICENSING.md)** - Automated license management
- **[DeFi Integration](docs/DEFI-INTEGRATION.md)** - Yield tokens, IPFi lending
- **[Mobile SDK](docs/MOBILE_SDK.md)** - iOS and Android integration

### Security Documentation

- **[Security Policy](SECURITY.md)** - Reporting vulnerabilities
- **[Hardware Authentication](docs/HARDWARE-AUTHENTICATION.md)** - FIDO2/WebAuthn setup
- **[Transaction Security](docs/TRANSACTION-SECURITY.md)** - Two-step verification

## Getting Help

### GitHub Issues

For bugs and feature requests, please use the GitHub issue tracker:

- **[Bug Reports](https://github.com/kase1111-hash/RRA-Module/issues/new?template=bug_report.yml)** - Report unexpected behavior
- **[Feature Requests](https://github.com/kase1111-hash/RRA-Module/issues/new?template=feature_request.yml)** - Suggest improvements

Before opening an issue:
1. Search [existing issues](https://github.com/kase1111-hash/RRA-Module/issues) to avoid duplicates
2. Check the [FAQ](FAQ.md) for common questions
3. Read the relevant documentation

### GitHub Discussions

For questions, ideas, and community discussions:

- **[GitHub Discussions](https://github.com/kase1111-hash/RRA-Module/discussions)** - Ask questions and share ideas

### Security Vulnerabilities

**Do NOT report security vulnerabilities in public issues.**

Please follow the [Security Policy](SECURITY.md) to report vulnerabilities responsibly.

## Common Issues

### Installation Problems

If you encounter installation issues:

```bash
# Ensure Python 3.9+ is installed
python --version

# Install with all dependencies
pip install -e ".[dev]"

# For crypto performance optimizations
pip install gmpy2 py_ecc
```

### Configuration Issues

Check your `.market.yaml` configuration:

```yaml
# Minimum required configuration
license_model: "Perpetual"
target_price: "0.05 ETH"
floor_price: "0.02 ETH"
```

### Blockchain Connection

For blockchain-related issues:

1. Verify your RPC endpoint is accessible
2. Check that your wallet has sufficient funds for gas
3. Ensure you're connected to the correct network

## Response Times

- **Bug reports**: Initial response within 48-72 hours
- **Security vulnerabilities**: Acknowledged within 48 hours
- **Feature requests**: Reviewed during regular triage

## Contributing

Interested in contributing? See the [Contributing Guide](CONTRIBUTING.md).

## License

This project is licensed under FSL-1.1-ALv2. See [LICENSE.md](LICENSE.md) for details.
