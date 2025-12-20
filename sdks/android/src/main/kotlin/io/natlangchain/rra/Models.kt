// SPDX-License-Identifier: FSL-1.1-ALv2
// Copyright 2025 Kase Branham

package io.natlangchain.rra

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// MARK: - Agent Models

/**
 * Represents an RRA agent in the marketplace.
 */
@Serializable
data class Agent(
    val id: String,
    val name: String,
    val description: String? = null,
    @SerialName("repo_url") val repoUrl: String,
    @SerialName("owner_address") val ownerAddress: String,
    @SerialName("license_type") val licenseType: LicenseType,
    @SerialName("base_price") val basePrice: Double,
    val currency: String,
    val tags: List<String> = emptyList(),
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
    val stats: AgentStats? = null
)

/**
 * Statistics for an agent.
 */
@Serializable
data class AgentStats(
    @SerialName("total_views") val totalViews: Int,
    @SerialName("total_negotiations") val totalNegotiations: Int,
    @SerialName("total_licenses") val totalLicenses: Int,
    @SerialName("total_revenue") val totalRevenue: Double,
    @SerialName("avg_rating") val avgRating: Double? = null
)

/**
 * License types available.
 */
@Serializable
enum class LicenseType {
    @SerialName("commercial") COMMERCIAL,
    @SerialName("non_commercial") NON_COMMERCIAL,
    @SerialName("derivative") DERIVATIVE,
    @SerialName("streaming") STREAMING,
    @SerialName("custom") CUSTOM
}

// MARK: - Marketplace Models

/**
 * Response for listing agents.
 */
@Serializable
data class AgentListResponse(
    val agents: List<Agent>,
    val total: Int,
    val page: Int,
    @SerialName("page_size") val pageSize: Int,
    @SerialName("has_more") val hasMore: Boolean
)

/**
 * Search parameters for marketplace.
 */
@Serializable
data class MarketplaceSearchParams(
    val query: String? = null,
    val tags: List<String>? = null,
    @SerialName("min_price") val minPrice: Double? = null,
    @SerialName("max_price") val maxPrice: Double? = null,
    @SerialName("license_type") val licenseType: LicenseType? = null,
    @SerialName("sort_by") val sortBy: SortOption? = null,
    val page: Int? = null,
    @SerialName("page_size") val pageSize: Int? = null
)

@Serializable
enum class SortOption {
    @SerialName("newest") NEWEST,
    @SerialName("popular") POPULAR,
    @SerialName("price_asc") PRICE_ASC,
    @SerialName("price_desc") PRICE_DESC,
    @SerialName("rating") RATING
}

// MARK: - Negotiation Models

/**
 * Represents a negotiation session.
 */
@Serializable
data class NegotiationSession(
    val id: String,
    @SerialName("agent_id") val agentId: String,
    @SerialName("buyer_address") val buyerAddress: String? = null,
    val status: NegotiationStatus,
    val messages: List<NegotiationMessage> = emptyList(),
    @SerialName("current_offer") val currentOffer: Offer? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String
)

/**
 * Status of a negotiation.
 */
@Serializable
enum class NegotiationStatus {
    @SerialName("pending") PENDING,
    @SerialName("active") ACTIVE,
    @SerialName("offer_made") OFFER_MADE,
    @SerialName("accepted") ACCEPTED,
    @SerialName("rejected") REJECTED,
    @SerialName("expired") EXPIRED,
    @SerialName("completed") COMPLETED
}

/**
 * A message in a negotiation.
 */
@Serializable
data class NegotiationMessage(
    val id: String,
    val role: MessageRole,
    val content: String,
    val timestamp: String,
    val metadata: Map<String, String>? = null
)

/**
 * Role of message sender.
 */
@Serializable
enum class MessageRole {
    @SerialName("user") USER,
    @SerialName("agent") AGENT,
    @SerialName("system") SYSTEM
}

/**
 * An offer in a negotiation.
 */
@Serializable
data class Offer(
    val price: Double,
    val currency: String,
    @SerialName("license_type") val licenseType: LicenseType,
    val terms: Map<String, String>? = null,
    @SerialName("expires_at") val expiresAt: String? = null
)

/**
 * Request to start a negotiation.
 */
@Serializable
data class StartNegotiationRequest(
    @SerialName("agent_id") val agentId: String,
    @SerialName("buyer_address") val buyerAddress: String? = null,
    @SerialName("initial_message") val initialMessage: String? = null,
    val preferences: NegotiationPreferences? = null
)

/**
 * Preferences for negotiation.
 */
@Serializable
data class NegotiationPreferences(
    @SerialName("max_budget") val maxBudget: Double? = null,
    @SerialName("preferred_license_type") val preferredLicenseType: LicenseType? = null,
    @SerialName("use_case") val useCase: String? = null
)

/**
 * Request to send a message.
 */
@Serializable
data class SendMessageRequest(
    @SerialName("session_id") val sessionId: String,
    val content: String
)

// MARK: - Streaming Payment Models

/**
 * A streaming license.
 */
@Serializable
data class StreamingLicense(
    val id: String,
    @SerialName("repo_id") val repoId: String,
    @SerialName("buyer_address") val buyerAddress: String,
    @SerialName("seller_address") val sellerAddress: String,
    @SerialName("monthly_price_usd") val monthlyPriceUsd: Double,
    @SerialName("flow_rate_wei") val flowRateWei: String,
    val status: StreamStatus,
    @SerialName("grace_period_hours") val gracePeriodHours: Int,
    @SerialName("started_at") val startedAt: String,
    @SerialName("last_payment_at") val lastPaymentAt: String? = null,
    @SerialName("access_granted") val accessGranted: Boolean
)

/**
 * Status of a stream.
 */
@Serializable
enum class StreamStatus {
    @SerialName("pending") PENDING,
    @SerialName("active") ACTIVE,
    @SerialName("paused") PAUSED,
    @SerialName("grace_period") GRACE_PERIOD,
    @SerialName("terminated") TERMINATED
}

/**
 * Request to create a stream.
 */
@Serializable
data class CreateStreamRequest(
    @SerialName("repo_id") val repoId: String,
    @SerialName("buyer_address") val buyerAddress: String,
    @SerialName("seller_address") val sellerAddress: String,
    @SerialName("monthly_price_usd") val monthlyPriceUsd: Double,
    @SerialName("grace_period_hours") val gracePeriodHours: Int = 24
)

// MARK: - Analytics Models

/**
 * Analytics overview.
 */
@Serializable
data class AnalyticsOverview(
    val period: String,
    @SerialName("start_time") val startTime: String,
    @SerialName("end_time") val endTime: String,
    @SerialName("total_events") val totalEvents: Int,
    @SerialName("unique_agents") val uniqueAgents: Int,
    @SerialName("unique_sessions") val uniqueSessions: Int,
    val metrics: AnalyticsMetrics,
    val revenue: RevenueMetrics
)

/**
 * Metrics data.
 */
@Serializable
data class AnalyticsMetrics(
    @SerialName("page_views") val pageViews: Int,
    @SerialName("negotiations_started") val negotiationsStarted: Int,
    @SerialName("negotiations_completed") val negotiationsCompleted: Int,
    @SerialName("licenses_purchased") val licensesPurchased: Int,
    @SerialName("widget_opens") val widgetOpens: Int,
    @SerialName("webhook_triggers") val webhookTriggers: Int,
    @SerialName("forks_detected") val forksDetected: Int,
    @SerialName("derivatives_registered") val derivativesRegistered: Int
)

/**
 * Revenue metrics.
 */
@Serializable
data class RevenueMetrics(
    @SerialName("total_eth") val totalEth: Double,
    @SerialName("license_count") val licenseCount: Int,
    @SerialName("avg_price_eth") val avgPriceEth: Double
)

/**
 * Time range for analytics.
 */
enum class TimeRange(val value: String) {
    HOUR("hour"),
    DAY("day"),
    WEEK("week"),
    MONTH("month"),
    QUARTER("quarter"),
    YEAR("year"),
    ALL("all")
}

// MARK: - Widget Models

/**
 * Widget configuration.
 */
@Serializable
data class WidgetConfig(
    @SerialName("widget_id") val widgetId: String,
    @SerialName("agent_id") val agentId: String,
    @SerialName("session_token") val sessionToken: String,
    @SerialName("websocket_url") val websocketUrl: String,
    @SerialName("api_base_url") val apiBaseUrl: String,
    val config: WidgetSettings
)

/**
 * Widget settings.
 */
@Serializable
data class WidgetSettings(
    val theme: String,
    val position: String,
    @SerialName("primary_color") val primaryColor: String,
    val language: String,
    @SerialName("auto_open") val autoOpen: Boolean,
    @SerialName("show_branding") val showBranding: Boolean
)

/**
 * Request to initialize widget.
 */
@Serializable
data class WidgetInitRequest(
    @SerialName("agent_id") val agentId: String,
    val theme: String = "default",
    val position: String = "bottom-right",
    @SerialName("primary_color") val primaryColor: String = "#0066ff",
    val language: String = "en",
    @SerialName("auto_open") val autoOpen: Boolean = false,
    @SerialName("show_branding") val showBranding: Boolean = true
)

// MARK: - Internal Types

@Serializable
internal class EmptyBody

@Serializable
internal data class AccessResponse(
    @SerialName("access_granted") val accessGranted: Boolean
)
