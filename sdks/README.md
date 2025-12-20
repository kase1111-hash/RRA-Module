# RRA Mobile SDKs

Official mobile SDKs for the Revenant Repo Agent (RRA) API.

## Available SDKs

### iOS (Swift)

Native Swift SDK with full async/await support.

**Installation via Swift Package Manager:**

```swift
dependencies: [
    .package(url: "https://github.com/natlangchain/rra-ios-sdk.git", from: "1.0.0")
]
```

**Usage:**

```swift
import RRA

// Initialize client
let client = RRAClient(
    baseURL: "https://api.natlangchain.io",
    apiKey: "your-api-key"
)

// List marketplace agents
let agents = try await client.marketplace.listAgents()

// Start a negotiation
let session = try await client.negotiation.start(
    StartNegotiationRequest(
        agentId: "agent-123",
        initialMessage: "I'd like to license this repository"
    )
)

// Create a streaming license
let license = try await client.streaming.createStream(
    CreateStreamRequest(
        repoId: "my-repo",
        buyerAddress: "0x...",
        sellerAddress: "0x...",
        monthlyPriceUsd: 99.0
    )
)

// Get analytics
let overview = try await client.analytics.getOverview(timeRange: .week)
```

### Android (Kotlin)

Native Kotlin SDK with coroutines support.

**Installation via Gradle:**

```kotlin
dependencies {
    implementation("io.natlangchain:rra-sdk:1.0.0")
}
```

**Usage:**

```kotlin
import io.natlangchain.rra.*

// Initialize client
val client = RRAClient(
    baseUrl = "https://api.natlangchain.io",
    apiKey = "your-api-key"
)

// List marketplace agents
val agents = client.marketplace.listAgents()

// Start a negotiation
val session = client.negotiation.start(
    StartNegotiationRequest(
        agentId = "agent-123",
        initialMessage = "I'd like to license this repository"
    )
)

// Create a streaming license
val license = client.streaming.createStream(
    CreateStreamRequest(
        repoId = "my-repo",
        buyerAddress = "0x...",
        sellerAddress = "0x...",
        monthlyPriceUsd = 99.0
    )
)

// Get analytics
val overview = client.analytics.getOverview(TimeRange.WEEK)
```

## Features

Both SDKs provide:

- **Marketplace API**: List, search, and browse agents
- **Negotiation API**: Start negotiations, send messages, accept/reject offers
- **Streaming API**: Create and manage streaming licenses
- **Analytics API**: Track events and view metrics
- **Widget API**: Initialize and configure embedded widgets

## Authentication

Pass your API key when initializing the client:

```swift
// iOS
let client = RRAClient(baseURL: "...", apiKey: "your-api-key")

// Android
val client = RRAClient(baseUrl = "...", apiKey = "your-api-key")
```

## Error Handling

Both SDKs throw typed exceptions for common error cases:

- `Unauthorized` - API key missing or invalid
- `Forbidden` - Access denied
- `NotFound` - Resource not found
- `RateLimited` - Too many requests
- `ServerError` - Server-side error

## Requirements

### iOS
- iOS 14.0+
- macOS 12.0+
- Swift 5.7+

### Android
- minSdk 24 (Android 7.0)
- Kotlin 1.9+
- kotlinx-serialization
- OkHttp 4.12+

## License

FSL-1.1-ALv2 - Copyright 2025 Kase Branham
