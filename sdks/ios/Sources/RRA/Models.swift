// SPDX-License-Identifier: FSL-1.1-ALv2
// Copyright 2025 Kase Branham

import Foundation

// MARK: - Agent Models

/// Represents an RRA agent in the marketplace.
public struct Agent: Codable, Identifiable, Sendable {
    public let id: String
    public let name: String
    public let description: String?
    public let repoUrl: String
    public let ownerAddress: String
    public let licenseType: LicenseType
    public let basePrice: Double
    public let currency: String
    public let tags: [String]
    public let createdAt: Date
    public let updatedAt: Date
    public let stats: AgentStats?
}

/// Statistics for an agent.
public struct AgentStats: Codable, Sendable {
    public let totalViews: Int
    public let totalNegotiations: Int
    public let totalLicenses: Int
    public let totalRevenue: Double
    public let avgRating: Double?
}

/// License types available.
public enum LicenseType: String, Codable, Sendable {
    case commercial = "commercial"
    case nonCommercial = "non_commercial"
    case derivative = "derivative"
    case streaming = "streaming"
    case custom = "custom"
}

// MARK: - Marketplace Models

/// Response for listing agents.
public struct AgentListResponse: Codable, Sendable {
    public let agents: [Agent]
    public let total: Int
    public let page: Int
    public let pageSize: Int
    public let hasMore: Bool
}

/// Search parameters for marketplace.
public struct MarketplaceSearchParams: Encodable {
    public var query: String?
    public var tags: [String]?
    public var minPrice: Double?
    public var maxPrice: Double?
    public var licenseType: LicenseType?
    public var sortBy: SortOption?
    public var page: Int?
    public var pageSize: Int?

    public init() {}

    public enum SortOption: String, Encodable {
        case newest = "newest"
        case popular = "popular"
        case priceAsc = "price_asc"
        case priceDesc = "price_desc"
        case rating = "rating"
    }
}

// MARK: - Negotiation Models

/// Represents a negotiation session.
public struct NegotiationSession: Codable, Identifiable, Sendable {
    public let id: String
    public let agentId: String
    public let buyerAddress: String?
    public let status: NegotiationStatus
    public let messages: [NegotiationMessage]
    public let currentOffer: Offer?
    public let createdAt: Date
    public let updatedAt: Date
}

/// Status of a negotiation.
public enum NegotiationStatus: String, Codable, Sendable {
    case pending = "pending"
    case active = "active"
    case offerMade = "offer_made"
    case accepted = "accepted"
    case rejected = "rejected"
    case expired = "expired"
    case completed = "completed"
}

/// A message in a negotiation.
public struct NegotiationMessage: Codable, Identifiable, Sendable {
    public let id: String
    public let role: MessageRole
    public let content: String
    public let timestamp: Date
    public let metadata: [String: String]?
}

/// Role of message sender.
public enum MessageRole: String, Codable, Sendable {
    case user = "user"
    case agent = "agent"
    case system = "system"
}

/// An offer in a negotiation.
public struct Offer: Codable, Sendable {
    public let price: Double
    public let currency: String
    public let licenseType: LicenseType
    public let terms: [String: String]?
    public let expiresAt: Date?
}

/// Request to start a negotiation.
public struct StartNegotiationRequest: Encodable {
    public let agentId: String
    public let buyerAddress: String?
    public let initialMessage: String?
    public let preferences: NegotiationPreferences?

    public init(
        agentId: String,
        buyerAddress: String? = nil,
        initialMessage: String? = nil,
        preferences: NegotiationPreferences? = nil
    ) {
        self.agentId = agentId
        self.buyerAddress = buyerAddress
        self.initialMessage = initialMessage
        self.preferences = preferences
    }
}

/// Preferences for negotiation.
public struct NegotiationPreferences: Codable, Sendable {
    public var maxBudget: Double?
    public var preferredLicenseType: LicenseType?
    public var useCase: String?

    public init() {}
}

/// Request to send a message.
public struct SendMessageRequest: Encodable {
    public let sessionId: String
    public let content: String

    public init(sessionId: String, content: String) {
        self.sessionId = sessionId
        self.content = content
    }
}

// MARK: - Streaming Payment Models

/// A streaming license.
public struct StreamingLicense: Codable, Identifiable, Sendable {
    public let id: String
    public let repoId: String
    public let buyerAddress: String
    public let sellerAddress: String
    public let monthlyPriceUsd: Double
    public let flowRateWei: String
    public let status: StreamStatus
    public let gracePeriodHours: Int
    public let startedAt: Date
    public let lastPaymentAt: Date?
    public let accessGranted: Bool
}

/// Status of a stream.
public enum StreamStatus: String, Codable, Sendable {
    case pending = "pending"
    case active = "active"
    case paused = "paused"
    case gracePeriod = "grace_period"
    case terminated = "terminated"
}

/// Request to create a stream.
public struct CreateStreamRequest: Encodable {
    public let repoId: String
    public let buyerAddress: String
    public let sellerAddress: String
    public let monthlyPriceUsd: Double
    public let gracePeriodHours: Int

    public init(
        repoId: String,
        buyerAddress: String,
        sellerAddress: String,
        monthlyPriceUsd: Double,
        gracePeriodHours: Int = 24
    ) {
        self.repoId = repoId
        self.buyerAddress = buyerAddress
        self.sellerAddress = sellerAddress
        self.monthlyPriceUsd = monthlyPriceUsd
        self.gracePeriodHours = gracePeriodHours
    }
}

// MARK: - Analytics Models

/// Analytics overview.
public struct AnalyticsOverview: Codable, Sendable {
    public let period: String
    public let startTime: Date
    public let endTime: Date
    public let totalEvents: Int
    public let uniqueAgents: Int
    public let uniqueSessions: Int
    public let metrics: AnalyticsMetrics
    public let revenue: RevenueMetrics
}

/// Metrics data.
public struct AnalyticsMetrics: Codable, Sendable {
    public let pageViews: Int
    public let negotiationsStarted: Int
    public let negotiationsCompleted: Int
    public let licensesPurchased: Int
    public let widgetOpens: Int
    public let webhookTriggers: Int
    public let forksDetected: Int
    public let derivativesRegistered: Int
}

/// Revenue metrics.
public struct RevenueMetrics: Codable, Sendable {
    public let totalEth: Double
    public let licenseCount: Int
    public let avgPriceEth: Double
}

/// Time range for analytics.
public enum TimeRange: String, Sendable {
    case hour = "hour"
    case day = "day"
    case week = "week"
    case month = "month"
    case quarter = "quarter"
    case year = "year"
    case all = "all"
}

// MARK: - Widget Models

/// Widget configuration.
public struct WidgetConfig: Codable, Sendable {
    public let widgetId: String
    public let agentId: String
    public let sessionToken: String
    public let websocketUrl: String
    public let apiBaseUrl: String
    public let config: WidgetSettings
}

/// Widget settings.
public struct WidgetSettings: Codable, Sendable {
    public let theme: String
    public let position: String
    public let primaryColor: String
    public let language: String
    public let autoOpen: Bool
    public let showBranding: Bool
}

/// Request to initialize widget.
public struct WidgetInitRequest: Encodable {
    public let agentId: String
    public let theme: String
    public let position: String
    public let primaryColor: String
    public let language: String
    public let autoOpen: Bool
    public let showBranding: Bool

    public init(
        agentId: String,
        theme: String = "default",
        position: String = "bottom-right",
        primaryColor: String = "#0066ff",
        language: String = "en",
        autoOpen: Bool = false,
        showBranding: Bool = true
    ) {
        self.agentId = agentId
        self.theme = theme
        self.position = position
        self.primaryColor = primaryColor
        self.language = language
        self.autoOpen = autoOpen
        self.showBranding = showBranding
    }
}
