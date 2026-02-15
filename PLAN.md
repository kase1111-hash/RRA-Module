# Plan: NFT License Image & Metadata Generation

## Goal
Add dynamic per-license SVG image generation and ERC-721 metadata assembly
with IPFS upload, so each minted license NFT gets a unique, branded visual
and proper on-chain metadata URI — instead of the current static
`nft-metadata.json` pointing to a GitHub-hosted SVG.

## Architecture

```
issue_license(repo_url, license_type, ...)
       │
       ▼
NFTMetadataBuilder.build(license_info, custom_image_path=None)
       │
       ├── 1. generate SVG (or use provided image)
       ├── 2. upload image to IPFS → ipfs://Qm...image
       ├── 3. build ERC-721 metadata JSON (with image URI + attributes)
       └── 4. upload metadata JSON to IPFS → ipfs://Qm...metadata
                │
                ▼
         token_uri = "ipfs://Qm...metadata"
```

## Files to Create

### 1. `src/rra/nft/__init__.py`
Empty package init.

### 2. `src/rra/nft/image_generator.py`
SVG generation module.

- `generate_license_svg(repo_name, license_type, price, licensee_short, token_id, issued_date) -> str`
  - Builds on the existing `assets/license-nft.svg` design (dark gradient, accent colors, license-document icon)
  - Injects dynamic fields: repo name, license type, price, short buyer address, issue date, token ID
  - Returns SVG string (no external dependencies needed — pure string templating)
  - The base SVG is ~42 lines; we template it rather than import it, so the module is self-contained

- `generate_text_logo(text, width=400, height=400) -> str`
  - Fallback: generates a simple text-based logo SVG from a product name
  - Used when no custom image is provided and no repo-specific branding exists

### 3. `src/rra/nft/metadata.py`
Metadata assembly + IPFS upload orchestrator.

- `class NFTMetadataBuilder`
  - `__init__(self, storage: Optional[EncryptedIPFSStorage] = None)`
    - Accepts an existing IPFS storage instance or creates one from env config
    - Reuses `EncryptedIPFSStorage` for upload (supports Pinata, Infura, local, mock)
    - Uses a lightweight wrapper since `EncryptedIPFSStorage.store_evidence()` does encryption + viewing-key work we don't need — we'll call the lower-level `_ipfs_upload` / `_pinata_upload` directly via a new `upload_raw()` method

  - `build(self, license_info: LicenseMetadataInput, custom_image: Optional[bytes] = None) -> str`
    - Main entry point. Returns the `ipfs://` metadata URI ready for `token_uri`
    - Steps:
      1. If `custom_image` provided, use it; otherwise call `generate_license_svg()`
      2. Upload image bytes to IPFS → get `image_uri`
      3. Build ERC-721 metadata dict (name, description, image, external_url, attributes, background_color)
      4. Upload metadata JSON to IPFS → get `metadata_uri`
      5. Return `metadata_uri`

  - `build_metadata_dict(self, license_info, image_uri) -> dict`
    - Pure function that assembles the OpenSea/ERC-721 compatible metadata JSON
    - Attributes include: License Type, Repo URL, Price, Licensee, Issued At, Max Seats, Allow Forks, Royalty %, Token ID

- `@dataclass LicenseMetadataInput`
  - `repo_name: str`
  - `repo_url: str`
  - `license_type: str` (e.g., "Perpetual", "Subscription", "Per-Seat")
  - `price: str` (e.g., "0.05 ETH")
  - `licensee_address: str`
  - `token_id: Optional[int]` (None if not yet known pre-mint)
  - `max_seats: int`
  - `allow_forks: bool`
  - `royalty_basis_points: int`
  - `duration_seconds: int`
  - `issued_at: Optional[str]` (ISO timestamp)

### 4. Add `upload_raw()` to `src/rra/storage/encrypted_ipfs.py`
New public method on `EncryptedIPFSStorage`:

```python
def upload_raw(self, data: bytes, filename: str = "file") -> StorageResult:
```

- Uploads raw bytes (no encryption, no viewing keys) to the configured IPFS provider
- Dispatches to `_ipfs_upload` / `_pinata_upload` / `_arweave_upload` / `_mock_upload` based on provider
- Uses a simplified code path — no dispute_id, no encryption, just upload and return URI
- This is the missing piece that lets NFT metadata use the existing IPFS infra without the evidence-encryption overhead

### 5. `tests/test_nft_metadata.py`
Tests for the new module.

- `test_generate_license_svg` — verify SVG output contains repo name, license type, valid XML
- `test_generate_text_logo` — verify fallback text logo renders
- `test_metadata_dict_structure` — verify ERC-721 JSON schema (name, description, image, attributes)
- `test_metadata_attributes_complete` — all license fields present in attributes array
- `test_build_with_mock_storage` — full integration: SVG gen → IPFS upload → metadata upload → URI returned
- `test_build_with_custom_image` — verify custom image bytes bypass SVG generation
- `test_upload_raw_mock` — verify `upload_raw` on mock provider

## Files to Modify

### 6. `src/rra/contracts/license_nft.py` — wire metadata into `issue_license()`
- Add optional `license_metadata: Optional[LicenseMetadataInput] = None` parameter
- When provided and `token_uri` is empty/not provided:
  - Instantiate `NFTMetadataBuilder`
  - Call `builder.build(license_metadata)`
  - Use returned URI as `token_uri`
- When `token_uri` is explicitly provided, use it as-is (backward compatible)

## What We're NOT Doing
- No PNG/raster generation (SVG is lighter, renders everywhere, no Pillow dependency)
- No on-chain image storage (too expensive; IPFS is standard)
- No changes to the Solidity contract (it already supports arbitrary `tokenURI`)
- No changes to Story Protocol integration (that can adopt this separately)
- Not touching the static `nft-metadata.json` / `assets/license-nft.svg` (they remain as reference/defaults)

## Dependency Impact
- Zero new external dependencies — SVG is string templating, IPFS upload reuses existing `encrypted_ipfs.py`
