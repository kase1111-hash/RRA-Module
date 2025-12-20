// SPDX-License-Identifier: FSL-1.1-ALv2
// Copyright 2025 Kase Branham

import Foundation

/// Main client for interacting with the RRA (Revenant Repo Agent) API.
///
/// Example usage:
/// ```swift
/// let client = RRAClient(baseURL: "https://api.natlangchain.io", apiKey: "your-api-key")
/// let agents = try await client.marketplace.listAgents()
/// ```
public class RRAClient {

    // MARK: - Properties

    /// Base URL for the RRA API
    public let baseURL: URL

    /// API key for authentication
    private let apiKey: String?

    /// URL session for network requests
    private let session: URLSession

    /// JSON encoder for requests
    private let encoder: JSONEncoder

    /// JSON decoder for responses
    private let decoder: JSONDecoder

    // MARK: - Sub-clients

    /// Marketplace API client
    public lazy var marketplace: MarketplaceClient = {
        MarketplaceClient(client: self)
    }()

    /// Negotiation API client
    public lazy var negotiation: NegotiationClient = {
        NegotiationClient(client: self)
    }()

    /// Streaming payments API client
    public lazy var streaming: StreamingClient = {
        StreamingClient(client: self)
    }()

    /// Analytics API client
    public lazy var analytics: AnalyticsClient = {
        AnalyticsClient(client: self)
    }()

    /// Widget API client
    public lazy var widget: WidgetClient = {
        WidgetClient(client: self)
    }()

    // MARK: - Initialization

    /// Initialize the RRA client.
    ///
    /// - Parameters:
    ///   - baseURL: Base URL for the RRA API
    ///   - apiKey: Optional API key for authentication
    ///   - session: URL session to use (defaults to shared)
    public init(
        baseURL: String,
        apiKey: String? = nil,
        session: URLSession = .shared
    ) {
        self.baseURL = URL(string: baseURL)!
        self.apiKey = apiKey
        self.session = session

        self.encoder = JSONEncoder()
        self.encoder.keyEncodingStrategy = .convertToSnakeCase
        self.encoder.dateEncodingStrategy = .iso8601

        self.decoder = JSONDecoder()
        self.decoder.keyDecodingStrategy = .convertFromSnakeCase
        self.decoder.dateDecodingStrategy = .iso8601
    }

    // MARK: - Request Methods

    /// Perform a GET request.
    internal func get<T: Decodable>(
        path: String,
        queryItems: [URLQueryItem]? = nil
    ) async throws -> T {
        let request = try buildRequest(method: "GET", path: path, queryItems: queryItems)
        return try await perform(request)
    }

    /// Perform a POST request with a body.
    internal func post<Body: Encodable, Response: Decodable>(
        path: String,
        body: Body
    ) async throws -> Response {
        var request = try buildRequest(method: "POST", path: path)
        request.httpBody = try encoder.encode(body)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        return try await perform(request)
    }

    /// Perform a DELETE request.
    internal func delete(path: String) async throws {
        let request = try buildRequest(method: "DELETE", path: path)
        let (_, response) = try await session.data(for: request)
        try validateResponse(response)
    }

    // MARK: - Private Methods

    private func buildRequest(
        method: String,
        path: String,
        queryItems: [URLQueryItem]? = nil
    ) throws -> URLRequest {
        var components = URLComponents(url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: true)!
        components.queryItems = queryItems

        guard let url = components.url else {
            throw RRAError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method

        if let apiKey = apiKey {
            request.setValue(apiKey, forHTTPHeaderField: "X-API-Key")
        }

        request.setValue("RRA-iOS-SDK/1.0.0", forHTTPHeaderField: "User-Agent")

        return request
    }

    private func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await session.data(for: request)
        try validateResponse(response)

        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw RRAError.decodingError(error)
        }
    }

    private func validateResponse(_ response: URLResponse) throws {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw RRAError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200...299:
            return
        case 401:
            throw RRAError.unauthorized
        case 403:
            throw RRAError.forbidden
        case 404:
            throw RRAError.notFound
        case 429:
            throw RRAError.rateLimited
        case 500...599:
            throw RRAError.serverError(httpResponse.statusCode)
        default:
            throw RRAError.httpError(httpResponse.statusCode)
        }
    }
}

// MARK: - Errors

/// Errors that can occur when using the RRA SDK.
public enum RRAError: Error, LocalizedError {
    case invalidURL
    case invalidResponse
    case unauthorized
    case forbidden
    case notFound
    case rateLimited
    case serverError(Int)
    case httpError(Int)
    case decodingError(Error)
    case encodingError(Error)
    case websocketError(String)

    public var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .unauthorized:
            return "Authentication required"
        case .forbidden:
            return "Access forbidden"
        case .notFound:
            return "Resource not found"
        case .rateLimited:
            return "Rate limit exceeded"
        case .serverError(let code):
            return "Server error: \(code)"
        case .httpError(let code):
            return "HTTP error: \(code)"
        case .decodingError(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        case .encodingError(let error):
            return "Failed to encode request: \(error.localizedDescription)"
        case .websocketError(let message):
            return "WebSocket error: \(message)"
        }
    }
}
