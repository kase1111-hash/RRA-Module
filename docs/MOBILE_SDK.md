# RRA Module - Mobile SDK Integration Guide

This guide covers integrating the RRA Module with mobile applications on iOS and Android.

## Overview

The RRA Module exposes a REST API and WebSocket interface that mobile applications can use to:

- Negotiate and purchase licenses
- Verify license ownership
- Manage DID-based identity
- Interact with Story Protocol IP assets
- Stream payments via Superfluid

## Quick Start

### Base URLs

| Environment | API URL |
|-------------|---------|
| Development | `http://localhost:8000/api/v1` |
| Staging | `https://staging-api.rra.dev/api/v1` |
| Production | `https://api.rra.io/api/v1` |

### Authentication

All API requests require authentication via JWT tokens or API keys:

```http
Authorization: Bearer <jwt_token>
# or
X-API-Key: <api_key>
```

---

## iOS SDK Integration

### Requirements

- iOS 15.0+
- Swift 5.5+
- Xcode 14+

### Installation

#### Swift Package Manager

Add to your `Package.swift`:

```swift
dependencies: [
    .package(url: "https://github.com/natlangchain/rra-ios-sdk", from: "1.0.0")
]
```

#### CocoaPods

```ruby
pod 'RRAModule', '~> 1.0'
```

### Basic Usage

```swift
import RRAModule

// Initialize the SDK
let rra = RRAClient(
    baseURL: "https://api.rra.io",
    apiKey: "your-api-key"
)

// Get repository info
Task {
    let repo = try await rra.repositories.get(url: "https://github.com/user/repo")
    print("License price: \(repo.targetPrice)")
}

// Purchase a license
Task {
    let license = try await rra.licenses.purchase(
        repositoryId: "repo-123",
        tier: .standard,
        paymentMethod: .ethereum(wallet: userWallet)
    )
    print("License NFT: \(license.tokenId)")
}
```

### DID Authentication

```swift
import RRAModule

// Create or restore DID
let didManager = DIDManager()
let did = try await didManager.createDID(method: .nlc)

// Authenticate with the RRA API
let authResult = try await rra.auth.authenticate(
    did: did.identifier,
    challenge: challenge,
    signature: try did.sign(challenge)
)

// Use the session token
rra.setSessionToken(authResult.token)
```

### WebSocket for Real-time Updates

```swift
import RRAModule

let ws = RRAWebSocket(url: "wss://api.rra.io/ws")

ws.onLicenseUpdate = { update in
    print("License \(update.licenseId) status: \(update.status)")
}

ws.onNegotiationMessage = { message in
    print("Agent: \(message.content)")
}

try await ws.connect(authToken: authToken)
```

### Wallet Integration

```swift
import RRAModule
import WalletConnect

// Connect via WalletConnect
let wcSession = try await WalletConnect.connect()

// Use for license purchases
let payment = try await rra.payments.create(
    amount: "0.05",
    currency: .eth,
    walletSession: wcSession
)
```

---

## Android SDK Integration

### Requirements

- Android API 26+
- Kotlin 1.8+
- Gradle 8+

### Installation

#### Gradle

```kotlin
dependencies {
    implementation("io.rra:rra-android-sdk:1.0.0")
}
```

### Basic Usage

```kotlin
import io.rra.sdk.RRAClient
import io.rra.sdk.models.*

// Initialize the SDK
val rra = RRAClient.Builder()
    .baseUrl("https://api.rra.io")
    .apiKey("your-api-key")
    .build()

// Get repository info
lifecycleScope.launch {
    val repo = rra.repositories.get("https://github.com/user/repo")
    Log.d("RRA", "License price: ${repo.targetPrice}")
}

// Purchase a license
lifecycleScope.launch {
    val license = rra.licenses.purchase(
        repositoryId = "repo-123",
        tier = LicenseTier.STANDARD,
        paymentMethod = PaymentMethod.Ethereum(userWallet)
    )
    Log.d("RRA", "License NFT: ${license.tokenId}")
}
```

### DID Authentication

```kotlin
import io.rra.sdk.identity.DIDManager
import io.rra.sdk.auth.AuthManager

// Create or restore DID
val didManager = DIDManager(context)
val did = didManager.createDID(DIDMethod.NLC)

// Authenticate
val auth = AuthManager(rra)
val result = auth.authenticate(
    did = did.identifier,
    challenge = challenge,
    signature = did.sign(challenge)
)

// Use session
rra.setSessionToken(result.token)
```

### WebSocket for Real-time Updates

```kotlin
import io.rra.sdk.websocket.RRAWebSocket

val webSocket = RRAWebSocket("wss://api.rra.io/ws")

webSocket.onLicenseUpdate { update ->
    Log.d("RRA", "License ${update.licenseId}: ${update.status}")
}

webSocket.onNegotiationMessage { message ->
    Log.d("RRA", "Agent: ${message.content}")
}

webSocket.connect(authToken)
```

### Wallet Integration

```kotlin
import io.rra.sdk.wallet.WalletConnector
import com.walletconnect.android.Web3Modal

// Connect wallet
val wcSession = Web3Modal.connect(context)

// Use for payments
val payment = rra.payments.create(
    amount = "0.05",
    currency = Currency.ETH,
    walletSession = wcSession
)
```

---

## Other Platforms

React Native and Flutter SDKs are planned for future releases. See [FUTURE.md](../FUTURE.md) for the roadmap.

Currently supported:
- **iOS** (Swift) - Full feature support
- **Android** (Kotlin) - Full feature support

---

## API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/repositories` | GET | List available repositories |
| `/repositories/{id}` | GET | Get repository details |
| `/licenses/purchase` | POST | Purchase a license |
| `/licenses/{id}` | GET | Get license details |
| `/licenses/verify` | POST | Verify license ownership |
| `/negotiations/start` | POST | Start AI negotiation |
| `/negotiations/{id}/message` | POST | Send negotiation message |

### WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `license:update` | Server → Client | License status changed |
| `negotiation:message` | Server → Client | Agent message |
| `negotiation:offer` | Server → Client | New price offer |
| `payment:confirmed` | Server → Client | Payment confirmed |

### Error Codes

| Code | Description |
|------|-------------|
| `AUTH_REQUIRED` | Authentication required |
| `INVALID_TOKEN` | Invalid or expired token |
| `LICENSE_NOT_FOUND` | License doesn't exist |
| `INSUFFICIENT_FUNDS` | Wallet balance too low |
| `RATE_LIMITED` | Too many requests |

---

## Security Best Practices

### API Key Storage

- **Never** hardcode API keys in source code
- Use secure storage (Keychain on iOS, EncryptedSharedPreferences on Android)
- Consider using environment-specific keys

### DID Private Key Management

```swift
// iOS - Store in Keychain
let keychain = Keychain(service: "io.rra.app")
keychain["did_private_key"] = privateKeyHex
```

```kotlin
// Android - Store in EncryptedSharedPreferences
val prefs = EncryptedSharedPreferences.create(...)
prefs.edit().putString("did_private_key", privateKeyHex).apply()
```

### Certificate Pinning

Implement SSL certificate pinning for production:

```swift
// iOS
let session = URLSession(configuration: .default, delegate: PinningDelegate(), delegateQueue: nil)
```

```kotlin
// Android
val certificatePinner = CertificatePinner.Builder()
    .add("api.rra.io", "sha256/AAAA...")
    .build()
```

---

## Offline Support

The SDK supports offline caching for:

- License verification (cached for 24 hours)
- Repository metadata
- User preferences

```swift
// iOS
rra.cachePolicy = .returnCacheDataElseLoad

// Android
rra.setCachePolicy(CachePolicy.CACHE_FIRST)
```

---

## Support

- Documentation: https://docs.rra.io/mobile
- GitHub Issues: https://github.com/natlangchain/rra-module/issues
- Discord: https://discord.gg/rra
