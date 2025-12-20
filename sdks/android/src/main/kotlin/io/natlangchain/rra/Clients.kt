// SPDX-License-Identifier: FSL-1.1-ALv2
// Copyright 2025 Kase Branham

package io.natlangchain.rra

/**
 * Client for marketplace API operations.
 */
class MarketplaceClient internal constructor(private val client: RRAClient) {

    /**
     * List agents in the marketplace.
     */
    suspend fun listAgents(
        page: Int = 1,
        pageSize: Int = 20
    ): AgentListResponse = client.get(
        path = "/api/marketplace/agents",
        queryParams = mapOf(
            "page" to page.toString(),
            "page_size" to pageSize.toString()
        )
    )

    /**
     * Search for agents.
     */
    suspend fun search(params: MarketplaceSearchParams): AgentListResponse {
        val queryParams = mutableMapOf<String, String>()
        params.query?.let { queryParams["q"] = it }
        params.tags?.let { queryParams["tags"] = it.joinToString(",") }
        params.minPrice?.let { queryParams["min_price"] = it.toString() }
        params.maxPrice?.let { queryParams["max_price"] = it.toString() }
        params.sortBy?.let { queryParams["sort"] = it.name.lowercase() }
        params.page?.let { queryParams["page"] = it.toString() }
        params.pageSize?.let { queryParams["page_size"] = it.toString() }

        return client.get(path = "/api/marketplace/search", queryParams = queryParams)
    }

    /**
     * Get a specific agent by ID.
     */
    suspend fun getAgent(id: String): Agent = client.get(path = "/api/marketplace/agents/$id")

    /**
     * Get featured agents.
     */
    suspend fun getFeatured(): List<Agent> = client.get(path = "/api/marketplace/featured")

    /**
     * Get trending agents.
     */
    suspend fun getTrending(limit: Int = 10): List<Agent> = client.get(
        path = "/api/marketplace/trending",
        queryParams = mapOf("limit" to limit.toString())
    )
}

/**
 * Client for negotiation API operations.
 */
class NegotiationClient internal constructor(private val client: RRAClient) {

    /**
     * Start a new negotiation.
     */
    suspend fun start(request: StartNegotiationRequest): NegotiationSession =
        client.post(path = "/api/negotiate/start", body = request)

    /**
     * Send a message in a negotiation.
     */
    suspend fun sendMessage(request: SendMessageRequest): NegotiationMessage =
        client.post(path = "/api/negotiate/message", body = request)

    /**
     * Get negotiation session by ID.
     */
    suspend fun getSession(id: String): NegotiationSession =
        client.get(path = "/api/negotiate/session/$id")

    /**
     * Accept the current offer.
     */
    suspend fun acceptOffer(sessionId: String): NegotiationSession =
        client.post(
            path = "/api/negotiate/accept",
            body = mapOf("session_id" to sessionId)
        )

    /**
     * Reject the current offer.
     */
    suspend fun rejectOffer(sessionId: String, reason: String? = null): NegotiationSession {
        val body = mutableMapOf("session_id" to sessionId)
        reason?.let { body["reason"] = it }
        return client.post(path = "/api/negotiate/reject", body = body)
    }

    /**
     * Make a counter-offer.
     */
    suspend fun counterOffer(sessionId: String, offer: Offer): NegotiationSession =
        client.post(
            path = "/api/negotiate/counter",
            body = mapOf("session_id" to sessionId, "offer" to offer)
        )
}

/**
 * Client for streaming payment operations.
 */
class StreamingClient internal constructor(private val client: RRAClient) {

    /**
     * Create a new streaming license.
     */
    suspend fun createStream(request: CreateStreamRequest): StreamingLicense =
        client.post(path = "/api/streaming/create", body = request)

    /**
     * Activate a stream.
     */
    suspend fun activate(licenseId: String): StreamingLicense =
        client.post(path = "/api/streaming/activate/$licenseId", body = EmptyBody())

    /**
     * Stop a stream.
     */
    suspend fun stop(licenseId: String): StreamingLicense =
        client.post(path = "/api/streaming/stop/$licenseId", body = EmptyBody())

    /**
     * Get stream status.
     */
    suspend fun getStatus(licenseId: String): StreamingLicense =
        client.get(path = "/api/streaming/status/$licenseId")

    /**
     * Check access for a license.
     */
    suspend fun checkAccess(licenseId: String): Boolean {
        val response: AccessResponse = client.get(path = "/api/streaming/access/$licenseId")
        return response.accessGranted
    }

    /**
     * Get all licenses for a buyer.
     */
    suspend fun getLicenses(buyerAddress: String): List<StreamingLicense> = client.get(
        path = "/api/streaming/tokens",
        queryParams = mapOf("buyer" to buyerAddress)
    )
}

/**
 * Client for analytics operations.
 */
class AnalyticsClient internal constructor(private val client: RRAClient) {

    /**
     * Get analytics overview.
     */
    suspend fun getOverview(timeRange: TimeRange = TimeRange.WEEK): AnalyticsOverview = client.get(
        path = "/api/analytics/overview",
        queryParams = mapOf("time_range" to timeRange.value)
    )

    /**
     * Get analytics for a specific agent.
     */
    suspend fun getAgentAnalytics(
        agentId: String,
        timeRange: TimeRange = TimeRange.WEEK
    ): AnalyticsOverview = client.get(
        path = "/api/analytics/agent/$agentId",
        queryParams = mapOf("time_range" to timeRange.value)
    )

    /**
     * Record an analytics event.
     */
    suspend fun recordEvent(
        eventType: String,
        agentId: String,
        metadata: Map<String, String>? = null
    ) {
        @kotlinx.serialization.Serializable
        data class EventRequest(
            @kotlinx.serialization.SerialName("event_type") val eventType: String,
            @kotlinx.serialization.SerialName("agent_id") val agentId: String,
            val metadata: Map<String, String>? = null
        )
        client.post<EventRequest, Unit>(
            path = "/api/analytics/event",
            body = EventRequest(eventType, agentId, metadata)
        )
    }
}

/**
 * Client for widget operations.
 */
class WidgetClient internal constructor(private val client: RRAClient) {

    /**
     * Initialize a widget.
     */
    suspend fun initialize(request: WidgetInitRequest): WidgetConfig =
        client.post(path = "/api/widget/init", body = request)

    /**
     * Get widget configuration.
     */
    suspend fun getConfig(widgetId: String): WidgetConfig =
        client.get(path = "/api/widget/config/$widgetId")
}
