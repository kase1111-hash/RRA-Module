// SPDX-License-Identifier: FSL-1.1-ALv2
// Copyright 2025 Kase Branham

import Foundation

// MARK: - Marketplace Client

/// Client for marketplace API operations.
public class MarketplaceClient {
    private weak var client: RRAClient?

    init(client: RRAClient) {
        self.client = client
    }

    /// List agents in the marketplace.
    public func listAgents(
        page: Int = 1,
        pageSize: Int = 20
    ) async throws -> AgentListResponse {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.get(
            path: "/api/marketplace/agents",
            queryItems: [
                URLQueryItem(name: "page", value: String(page)),
                URLQueryItem(name: "page_size", value: String(pageSize))
            ]
        )
    }

    /// Search for agents.
    public func search(_ params: MarketplaceSearchParams) async throws -> AgentListResponse {
        guard let client = client else { throw RRAError.invalidResponse }

        var queryItems: [URLQueryItem] = []
        if let query = params.query {
            queryItems.append(URLQueryItem(name: "q", value: query))
        }
        if let tags = params.tags {
            queryItems.append(URLQueryItem(name: "tags", value: tags.joined(separator: ",")))
        }
        if let minPrice = params.minPrice {
            queryItems.append(URLQueryItem(name: "min_price", value: String(minPrice)))
        }
        if let maxPrice = params.maxPrice {
            queryItems.append(URLQueryItem(name: "max_price", value: String(maxPrice)))
        }
        if let sortBy = params.sortBy {
            queryItems.append(URLQueryItem(name: "sort", value: sortBy.rawValue))
        }
        if let page = params.page {
            queryItems.append(URLQueryItem(name: "page", value: String(page)))
        }
        if let pageSize = params.pageSize {
            queryItems.append(URLQueryItem(name: "page_size", value: String(pageSize)))
        }

        return try await client.get(path: "/api/marketplace/search", queryItems: queryItems)
    }

    /// Get a specific agent by ID.
    public func getAgent(id: String) async throws -> Agent {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.get(path: "/api/marketplace/agents/\(id)")
    }

    /// Get featured agents.
    public func getFeatured() async throws -> [Agent] {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.get(path: "/api/marketplace/featured")
    }

    /// Get trending agents.
    public func getTrending(limit: Int = 10) async throws -> [Agent] {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.get(
            path: "/api/marketplace/trending",
            queryItems: [URLQueryItem(name: "limit", value: String(limit))]
        )
    }
}

// MARK: - Negotiation Client

/// Client for negotiation API operations.
public class NegotiationClient {
    private weak var client: RRAClient?

    init(client: RRAClient) {
        self.client = client
    }

    /// Start a new negotiation.
    public func start(_ request: StartNegotiationRequest) async throws -> NegotiationSession {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.post(path: "/api/negotiate/start", body: request)
    }

    /// Send a message in a negotiation.
    public func sendMessage(_ request: SendMessageRequest) async throws -> NegotiationMessage {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.post(path: "/api/negotiate/message", body: request)
    }

    /// Get negotiation session by ID.
    public func getSession(id: String) async throws -> NegotiationSession {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.get(path: "/api/negotiate/session/\(id)")
    }

    /// Accept the current offer.
    public func acceptOffer(sessionId: String) async throws -> NegotiationSession {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.post(
            path: "/api/negotiate/accept",
            body: ["session_id": sessionId]
        )
    }

    /// Reject the current offer.
    public func rejectOffer(sessionId: String, reason: String? = nil) async throws -> NegotiationSession {
        guard let client = client else { throw RRAError.invalidResponse }
        var body: [String: String] = ["session_id": sessionId]
        if let reason = reason {
            body["reason"] = reason
        }
        return try await client.post(path: "/api/negotiate/reject", body: body)
    }

    /// Make a counter-offer.
    public func counterOffer(sessionId: String, offer: Offer) async throws -> NegotiationSession {
        guard let client = client else { throw RRAError.invalidResponse }
        struct CounterOfferRequest: Encodable {
            let sessionId: String
            let offer: Offer
        }
        return try await client.post(
            path: "/api/negotiate/counter",
            body: CounterOfferRequest(sessionId: sessionId, offer: offer)
        )
    }
}

// MARK: - Streaming Client

/// Client for streaming payment operations.
public class StreamingClient {
    private weak var client: RRAClient?

    init(client: RRAClient) {
        self.client = client
    }

    /// Create a new streaming license.
    public func createStream(_ request: CreateStreamRequest) async throws -> StreamingLicense {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.post(path: "/api/streaming/create", body: request)
    }

    /// Activate a stream.
    public func activate(licenseId: String) async throws -> StreamingLicense {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.post(
            path: "/api/streaming/activate/\(licenseId)",
            body: EmptyBody()
        )
    }

    /// Stop a stream.
    public func stop(licenseId: String) async throws -> StreamingLicense {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.post(
            path: "/api/streaming/stop/\(licenseId)",
            body: EmptyBody()
        )
    }

    /// Get stream status.
    public func getStatus(licenseId: String) async throws -> StreamingLicense {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.get(path: "/api/streaming/status/\(licenseId)")
    }

    /// Check access for a license.
    public func checkAccess(licenseId: String) async throws -> Bool {
        guard let client = client else { throw RRAError.invalidResponse }
        struct AccessResponse: Decodable {
            let accessGranted: Bool
        }
        let response: AccessResponse = try await client.get(path: "/api/streaming/access/\(licenseId)")
        return response.accessGranted
    }

    /// Get all licenses for a buyer.
    public func getLicenses(buyerAddress: String) async throws -> [StreamingLicense] {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.get(
            path: "/api/streaming/tokens",
            queryItems: [URLQueryItem(name: "buyer", value: buyerAddress)]
        )
    }
}

// MARK: - Analytics Client

/// Client for analytics operations.
public class AnalyticsClient {
    private weak var client: RRAClient?

    init(client: RRAClient) {
        self.client = client
    }

    /// Get analytics overview.
    public func getOverview(timeRange: TimeRange = .week) async throws -> AnalyticsOverview {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.get(
            path: "/api/analytics/overview",
            queryItems: [URLQueryItem(name: "time_range", value: timeRange.rawValue)]
        )
    }

    /// Get analytics for a specific agent.
    public func getAgentAnalytics(
        agentId: String,
        timeRange: TimeRange = .week
    ) async throws -> AnalyticsOverview {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.get(
            path: "/api/analytics/agent/\(agentId)",
            queryItems: [URLQueryItem(name: "time_range", value: timeRange.rawValue)]
        )
    }

    /// Record an analytics event.
    public func recordEvent(
        eventType: String,
        agentId: String,
        metadata: [String: String]? = nil
    ) async throws {
        guard let client = client else { throw RRAError.invalidResponse }
        struct EventRequest: Encodable {
            let eventType: String
            let agentId: String
            let metadata: [String: String]?
        }
        let _: EmptyResponse = try await client.post(
            path: "/api/analytics/event",
            body: EventRequest(eventType: eventType, agentId: agentId, metadata: metadata)
        )
    }
}

// MARK: - Widget Client

/// Client for widget operations.
public class WidgetClient {
    private weak var client: RRAClient?

    init(client: RRAClient) {
        self.client = client
    }

    /// Initialize a widget.
    public func initialize(_ request: WidgetInitRequest) async throws -> WidgetConfig {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.post(path: "/api/widget/init", body: request)
    }

    /// Get widget configuration.
    public func getConfig(widgetId: String) async throws -> WidgetConfig {
        guard let client = client else { throw RRAError.invalidResponse }
        return try await client.get(path: "/api/widget/config/\(widgetId)")
    }
}

// MARK: - Helper Types

struct EmptyBody: Encodable {}
struct EmptyResponse: Decodable {}
