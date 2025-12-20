// SPDX-License-Identifier: FSL-1.1-ALv2
// Copyright 2025 Kase Branham

package io.natlangchain.rra

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.encodeToString
import kotlinx.serialization.decodeFromString
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

/**
 * Main client for interacting with the RRA (Revenant Repo Agent) API.
 *
 * Example usage:
 * ```kotlin
 * val client = RRAClient(
 *     baseUrl = "https://api.natlangchain.io",
 *     apiKey = "your-api-key"
 * )
 * val agents = client.marketplace.listAgents()
 * ```
 */
class RRAClient(
    private val baseUrl: String,
    private val apiKey: String? = null,
    private val httpClient: OkHttpClient = defaultHttpClient()
) {
    companion object {
        private val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()

        private fun defaultHttpClient(): OkHttpClient = OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()
    }

    internal val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        encodeDefaults = true
        prettyPrint = false
    }

    /** Marketplace API client */
    val marketplace: MarketplaceClient by lazy { MarketplaceClient(this) }

    /** Negotiation API client */
    val negotiation: NegotiationClient by lazy { NegotiationClient(this) }

    /** Streaming payments API client */
    val streaming: StreamingClient by lazy { StreamingClient(this) }

    /** Analytics API client */
    val analytics: AnalyticsClient by lazy { AnalyticsClient(this) }

    /** Widget API client */
    val widget: WidgetClient by lazy { WidgetClient(this) }

    /**
     * Perform a GET request.
     */
    internal suspend inline fun <reified T> get(
        path: String,
        queryParams: Map<String, String>? = null
    ): T = withContext(Dispatchers.IO) {
        val urlBuilder = StringBuilder("$baseUrl$path")
        queryParams?.let { params ->
            if (params.isNotEmpty()) {
                urlBuilder.append("?")
                urlBuilder.append(params.entries.joinToString("&") { "${it.key}=${it.value}" })
            }
        }

        val request = Request.Builder()
            .url(urlBuilder.toString())
            .get()
            .apply { addHeaders(this) }
            .build()

        executeRequest(request)
    }

    /**
     * Perform a POST request with a body.
     */
    internal suspend inline fun <reified B, reified T> post(
        path: String,
        body: B
    ): T = withContext(Dispatchers.IO) {
        val jsonBody = json.encodeToString(body)
        val requestBody = jsonBody.toRequestBody(JSON_MEDIA_TYPE)

        val request = Request.Builder()
            .url("$baseUrl$path")
            .post(requestBody)
            .apply { addHeaders(this) }
            .build()

        executeRequest(request)
    }

    /**
     * Perform a DELETE request.
     */
    internal suspend fun delete(path: String): Unit = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("$baseUrl$path")
            .delete()
            .apply { addHeaders(this) }
            .build()

        httpClient.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                throw handleError(response.code, response.body?.string())
            }
        }
    }

    private fun addHeaders(builder: Request.Builder) {
        builder.addHeader("User-Agent", "RRA-Android-SDK/1.0.0")
        apiKey?.let { builder.addHeader("X-API-Key", it) }
    }

    private inline fun <reified T> executeRequest(request: Request): T {
        httpClient.newCall(request).execute().use { response ->
            val body = response.body?.string() ?: ""

            if (!response.isSuccessful) {
                throw handleError(response.code, body)
            }

            return try {
                json.decodeFromString(body)
            } catch (e: Exception) {
                throw RRAException.DecodingError(e)
            }
        }
    }

    private fun handleError(code: Int, body: String?): RRAException {
        return when (code) {
            401 -> RRAException.Unauthorized
            403 -> RRAException.Forbidden
            404 -> RRAException.NotFound
            429 -> RRAException.RateLimited
            in 500..599 -> RRAException.ServerError(code)
            else -> RRAException.HttpError(code, body)
        }
    }
}

/**
 * Exceptions that can occur when using the RRA SDK.
 */
sealed class RRAException(message: String, cause: Throwable? = null) : Exception(message, cause) {
    object Unauthorized : RRAException("Authentication required")
    object Forbidden : RRAException("Access forbidden")
    object NotFound : RRAException("Resource not found")
    object RateLimited : RRAException("Rate limit exceeded")
    class ServerError(code: Int) : RRAException("Server error: $code")
    class HttpError(code: Int, body: String?) : RRAException("HTTP error $code: $body")
    class DecodingError(cause: Throwable) : RRAException("Failed to decode response", cause)
    class EncodingError(cause: Throwable) : RRAException("Failed to encode request", cause)
    class WebSocketError(message: String) : RRAException("WebSocket error: $message")
}
