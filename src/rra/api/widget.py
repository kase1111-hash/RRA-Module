# SPDX-License-Identifier: FSL-1.1-ALv2
# Copyright 2025 Kase Branham
"""
Embeddable Widget API for RRA Module.

Provides REST API endpoints for:
- Widget initialization and configuration
- Cross-origin widget communication
- Widget analytics and tracking
"""

import json
import secrets
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field


router = APIRouter(prefix="/api/widget", tags=["widget"])


# =============================================================================
# Widget Configuration Models
# =============================================================================

class WidgetConfig(BaseModel):
    """Configuration for embeddable widget."""
    agent_id: str
    theme: str = Field(default="default", pattern="^(default|minimal|dark|light)$")
    position: str = Field(default="bottom-right", pattern="^(inline|bottom-right|bottom-left|top-right|top-left)$")
    primary_color: str = Field(default="#0066ff", pattern="^#[a-fA-F0-9]{6}$")
    language: str = Field(default="en", pattern="^(en|es|zh|ja|de|fr)$")
    auto_open: bool = False
    show_branding: bool = True
    enable_analytics: bool = True


class WidgetInitResponse(BaseModel):
    """Response for widget initialization."""
    widget_id: str
    agent_id: str
    config: Dict[str, Any]
    websocket_url: str
    api_base_url: str
    session_token: str


class WidgetEventRequest(BaseModel):
    """Widget analytics event."""
    widget_id: str
    event_type: str
    event_data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


# =============================================================================
# Widget Session Storage (use Redis in production)
# =============================================================================

_widget_sessions: Dict[str, Dict[str, Any]] = {}
_widget_analytics: List[Dict[str, Any]] = []


# =============================================================================
# Widget Endpoints
# =============================================================================

@router.post("/init", response_model=WidgetInitResponse)
async def initialize_widget(
    config: WidgetConfig,
    request: Request,
) -> WidgetInitResponse:
    """
    Initialize an embeddable widget instance.

    Creates a new widget session and returns configuration
    for the client-side widget to use.
    """
    # Generate unique widget session
    widget_id = f"wgt_{secrets.token_hex(12)}"
    session_token = secrets.token_urlsafe(32)

    # Get base URLs from request
    host = request.headers.get("host", "localhost:8000")
    scheme = "wss" if request.url.scheme == "https" else "ws"

    # Store session
    _widget_sessions[widget_id] = {
        "agent_id": config.agent_id,
        "config": config.model_dump(),
        "session_token": session_token,
        "created_at": datetime.utcnow().isoformat(),
        "origin": request.headers.get("origin", ""),
        "events": [],
    }

    return WidgetInitResponse(
        widget_id=widget_id,
        agent_id=config.agent_id,
        config=config.model_dump(),
        websocket_url=f"{scheme}://{host}/ws/widget/{widget_id}",
        api_base_url=f"{request.url.scheme}://{host}/api",
        session_token=session_token,
    )


@router.get("/config/{widget_id}")
async def get_widget_config(widget_id: str) -> Dict[str, Any]:
    """Get widget configuration."""
    session = _widget_sessions.get(widget_id)
    if not session:
        raise HTTPException(404, "Widget session not found")

    return {
        "agent_id": session["agent_id"],
        "config": session["config"],
    }


@router.post("/event")
async def record_widget_event(event: WidgetEventRequest) -> Dict[str, str]:
    """Record analytics event from widget."""
    session = _widget_sessions.get(event.widget_id)
    if not session:
        raise HTTPException(404, "Widget session not found")

    event_record = {
        "widget_id": event.widget_id,
        "agent_id": session["agent_id"],
        "event_type": event.event_type,
        "event_data": event.event_data,
        "timestamp": event.timestamp or datetime.utcnow().isoformat(),
        "origin": session.get("origin", ""),
    }

    # Store event
    _widget_analytics.append(event_record)
    session["events"].append(event_record)

    return {"status": "recorded"}


@router.get("/embed.js", response_class=Response)
async def get_widget_script() -> Response:
    """
    Serve the embeddable widget JavaScript.

    This is a minimal loader that loads the full widget from CDN.
    """
    script = '''
(function() {
    'use strict';

    // RRA Widget Loader
    window.RRAWidget = window.RRAWidget || {};

    // Default configuration
    var defaults = {
        theme: 'default',
        position: 'bottom-right',
        primaryColor: '#0066ff',
        language: 'en',
        autoOpen: false,
        showBranding: true
    };

    // Widget state
    var state = {
        initialized: false,
        widgetId: null,
        sessionToken: null,
        websocket: null,
        container: null,
        messages: []
    };

    // Initialize widget
    RRAWidget.init = function(config) {
        if (state.initialized) {
            console.warn('RRAWidget already initialized');
            return;
        }

        config = Object.assign({}, defaults, config);

        if (!config.agentId) {
            console.error('RRAWidget: agentId is required');
            return;
        }

        // Create widget container
        createWidgetContainer(config);

        // Initialize session with backend
        initializeSession(config);

        state.initialized = true;
    };

    // Create widget container
    function createWidgetContainer(config) {
        var container = document.createElement('div');
        container.id = 'rra-widget-container';
        container.className = 'rra-widget rra-widget-' + config.position;

        // Apply theme
        container.setAttribute('data-theme', config.theme);

        // Inject styles
        injectStyles(config);

        // Create widget HTML
        container.innerHTML = getWidgetHTML(config);

        document.body.appendChild(container);
        state.container = container;

        // Attach event listeners
        attachEventListeners(config);
    }

    // Inject widget styles
    function injectStyles(config) {
        var style = document.createElement('style');
        style.id = 'rra-widget-styles';
        style.textContent = `
            .rra-widget {
                --rra-primary: ${config.primaryColor};
                --rra-background: #ffffff;
                --rra-text: #333333;
                --rra-border: #e0e0e0;
                --rra-radius: 12px;
                --rra-shadow: 0 4px 20px rgba(0,0,0,0.15);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                position: fixed;
                z-index: 999999;
            }
            .rra-widget[data-theme="dark"] {
                --rra-background: #1a1a1a;
                --rra-text: #ffffff;
                --rra-border: #333333;
            }
            .rra-widget-bottom-right { bottom: 20px; right: 20px; }
            .rra-widget-bottom-left { bottom: 20px; left: 20px; }
            .rra-widget-top-right { top: 20px; right: 20px; }
            .rra-widget-top-left { top: 20px; left: 20px; }

            .rra-widget-bubble {
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: var(--rra-primary);
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: var(--rra-shadow);
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .rra-widget-bubble:hover {
                transform: scale(1.05);
                box-shadow: 0 6px 25px rgba(0,0,0,0.2);
            }
            .rra-widget-bubble svg {
                width: 28px;
                height: 28px;
                fill: white;
            }

            .rra-widget-panel {
                display: none;
                width: 380px;
                height: 520px;
                background: var(--rra-background);
                border-radius: var(--rra-radius);
                box-shadow: var(--rra-shadow);
                overflow: hidden;
                flex-direction: column;
            }
            .rra-widget-panel.open { display: flex; }

            .rra-widget-header {
                background: var(--rra-primary);
                color: white;
                padding: 16px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .rra-widget-header h3 {
                margin: 0;
                font-size: 16px;
                font-weight: 600;
            }
            .rra-widget-close {
                background: none;
                border: none;
                color: white;
                cursor: pointer;
                font-size: 20px;
                opacity: 0.8;
            }
            .rra-widget-close:hover { opacity: 1; }

            .rra-widget-messages {
                flex: 1;
                overflow-y: auto;
                padding: 16px;
            }
            .rra-widget-message {
                margin-bottom: 12px;
                max-width: 85%;
            }
            .rra-widget-message.agent {
                background: #f0f0f0;
                padding: 10px 14px;
                border-radius: 12px 12px 12px 4px;
            }
            .rra-widget-message.user {
                background: var(--rra-primary);
                color: white;
                padding: 10px 14px;
                border-radius: 12px 12px 4px 12px;
                margin-left: auto;
            }
            [data-theme="dark"] .rra-widget-message.agent {
                background: #2a2a2a;
                color: #ffffff;
            }

            .rra-widget-input-area {
                padding: 12px;
                border-top: 1px solid var(--rra-border);
                display: flex;
                gap: 8px;
            }
            .rra-widget-input {
                flex: 1;
                padding: 10px 14px;
                border: 1px solid var(--rra-border);
                border-radius: 20px;
                font-size: 14px;
                outline: none;
                background: var(--rra-background);
                color: var(--rra-text);
            }
            .rra-widget-input:focus {
                border-color: var(--rra-primary);
            }
            .rra-widget-send {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: var(--rra-primary);
                border: none;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .rra-widget-send svg {
                width: 18px;
                height: 18px;
                fill: white;
            }

            .rra-widget-branding {
                text-align: center;
                padding: 8px;
                font-size: 11px;
                color: #999;
                border-top: 1px solid var(--rra-border);
            }
            .rra-widget-branding a {
                color: var(--rra-primary);
                text-decoration: none;
            }
        `;
        document.head.appendChild(style);
    }

    // Get widget HTML
    function getWidgetHTML(config) {
        var brandingHTML = config.showBranding ?
            '<div class="rra-widget-branding">Powered by <a href="https://natlangchain.io" target="_blank">NatLangChain</a></div>' : '';

        return `
            <div class="rra-widget-bubble" id="rra-bubble">
                <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>
            </div>
            <div class="rra-widget-panel" id="rra-panel">
                <div class="rra-widget-header">
                    <h3>License This Repository</h3>
                    <button class="rra-widget-close" id="rra-close">&times;</button>
                </div>
                <div class="rra-widget-messages" id="rra-messages">
                    <div class="rra-widget-message agent">
                        Hi! I'm the licensing agent for this repository. How can I help you today?
                    </div>
                </div>
                <div class="rra-widget-input-area">
                    <input type="text" class="rra-widget-input" id="rra-input" placeholder="Type a message...">
                    <button class="rra-widget-send" id="rra-send">
                        <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                    </button>
                </div>
                ${brandingHTML}
            </div>
        `;
    }

    // Attach event listeners
    function attachEventListeners(config) {
        var bubble = document.getElementById('rra-bubble');
        var panel = document.getElementById('rra-panel');
        var closeBtn = document.getElementById('rra-close');
        var input = document.getElementById('rra-input');
        var sendBtn = document.getElementById('rra-send');

        bubble.addEventListener('click', function() {
            panel.classList.add('open');
            bubble.style.display = 'none';
            trackEvent('widget_opened');
        });

        closeBtn.addEventListener('click', function() {
            panel.classList.remove('open');
            bubble.style.display = 'flex';
            trackEvent('widget_closed');
        });

        sendBtn.addEventListener('click', sendMessage);
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });

        if (config.autoOpen) {
            setTimeout(function() {
                bubble.click();
            }, 1000);
        }
    }

    // Send message
    function sendMessage() {
        var input = document.getElementById('rra-input');
        var message = input.value.trim();

        if (!message) return;

        // Add user message to UI
        addMessage(message, 'user');
        input.value = '';

        // Send via WebSocket or fallback to REST
        if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
            state.websocket.send(JSON.stringify({
                type: 'message',
                content: message
            }));
        } else {
            sendMessageREST(message);
        }

        trackEvent('message_sent', { length: message.length });
    }

    // Send message via REST fallback
    function sendMessageREST(message) {
        // Show typing indicator
        var typingId = addMessage('...', 'agent');

        fetch('/api/widget/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Widget-Session': state.sessionToken
            },
            body: JSON.stringify({
                widget_id: state.widgetId,
                message: message
            })
        })
        .then(function(response) { return response.json(); })
        .then(function(data) {
            // Remove typing indicator
            var typingEl = document.getElementById(typingId);
            if (typingEl) typingEl.remove();

            // Add agent response
            addMessage(data.response, 'agent');
        })
        .catch(function(error) {
            console.error('RRAWidget error:', error);
            var typingEl = document.getElementById(typingId);
            if (typingEl) typingEl.textContent = 'Sorry, something went wrong. Please try again.';
        });
    }

    // Add message to UI
    function addMessage(content, sender) {
        var messages = document.getElementById('rra-messages');
        var messageEl = document.createElement('div');
        var id = 'msg-' + Date.now();
        messageEl.id = id;
        messageEl.className = 'rra-widget-message ' + sender;
        messageEl.textContent = content;
        messages.appendChild(messageEl);
        messages.scrollTop = messages.scrollHeight;
        return id;
    }

    // Initialize session
    function initializeSession(config) {
        fetch('/api/widget/init', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                agent_id: config.agentId,
                theme: config.theme,
                position: config.position,
                primary_color: config.primaryColor,
                language: config.language,
                auto_open: config.autoOpen,
                show_branding: config.showBranding,
                enable_analytics: true
            })
        })
        .then(function(response) { return response.json(); })
        .then(function(data) {
            state.widgetId = data.widget_id;
            state.sessionToken = data.session_token;

            // Connect WebSocket
            connectWebSocket(data.websocket_url);

            trackEvent('widget_initialized');
        })
        .catch(function(error) {
            console.error('RRAWidget init error:', error);
        });
    }

    // Connect WebSocket
    function connectWebSocket(url) {
        try {
            state.websocket = new WebSocket(url);

            state.websocket.onmessage = function(event) {
                var data = JSON.parse(event.data);
                if (data.type === 'message') {
                    addMessage(data.content, 'agent');
                }
            };

            state.websocket.onerror = function(error) {
                console.warn('RRAWidget WebSocket error, falling back to REST');
            };
        } catch (e) {
            console.warn('RRAWidget WebSocket not available');
        }
    }

    // Track analytics event
    function trackEvent(eventType, eventData) {
        if (!state.widgetId) return;

        fetch('/api/widget/event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                widget_id: state.widgetId,
                event_type: eventType,
                event_data: eventData,
                timestamp: new Date().toISOString()
            })
        }).catch(function() {});
    }

    // Expose public API
    RRAWidget.open = function() {
        var panel = document.getElementById('rra-panel');
        var bubble = document.getElementById('rra-bubble');
        if (panel && bubble) {
            panel.classList.add('open');
            bubble.style.display = 'none';
        }
    };

    RRAWidget.close = function() {
        var panel = document.getElementById('rra-panel');
        var bubble = document.getElementById('rra-bubble');
        if (panel && bubble) {
            panel.classList.remove('open');
            bubble.style.display = 'flex';
        }
    };

    RRAWidget.destroy = function() {
        var container = document.getElementById('rra-widget-container');
        var styles = document.getElementById('rra-widget-styles');
        if (container) container.remove();
        if (styles) styles.remove();
        if (state.websocket) state.websocket.close();
        state.initialized = false;
    };

})();
'''
    return Response(
        content=script,
        media_type="application/javascript",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
        }
    )


@router.post("/message")
async def widget_message(
    request: Request,
) -> Dict[str, Any]:
    """
    Handle message from widget (REST fallback for WebSocket).
    """
    data = await request.json()
    widget_id = data.get("widget_id")
    message = data.get("message", "")

    session = _widget_sessions.get(widget_id)
    if not session:
        raise HTTPException(404, "Widget session not found")

    # Load the negotiator agent and get response
    from rra.services.deep_links import DeepLinkService
    from rra.ingestion.knowledge_base import KnowledgeBase
    from rra.agents.negotiator import NegotiatorAgent
    from pathlib import Path

    agent_id = session["agent_id"]
    link_service = DeepLinkService()

    # Try to find knowledge base
    kb_dir = Path("agent_knowledge_bases")
    kb = None

    # Check registered mappings first
    mapping = link_service.resolve_repo_id(agent_id)
    if mapping:
        repo_url = mapping["repo_url"]
        # Extract repo name from URL
        import re
        match = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
        if match:
            repo_name = f"{match.group(1)}_{match.group(2)}"
            kb_path = kb_dir / f"{repo_name}_kb.json"
            if kb_path.exists():
                kb = KnowledgeBase.load(kb_path)

    # Fallback: search for any matching KB
    if not kb and kb_dir.exists():
        for kb_file in kb_dir.glob("*_kb.json"):
            try:
                temp_kb = KnowledgeBase.load(kb_file)
                if agent_id in str(kb_file) or agent_id == link_service.generate_repo_id(temp_kb.repo_url):
                    kb = temp_kb
                    break
            except Exception:
                continue

    if not kb:
        return {
            "response": "I'm sorry, I couldn't find information about this repository. Please try again later.",
            "phase": "error",
        }

    # Get or create negotiator
    negotiator = NegotiatorAgent(kb)

    # Start or continue negotiation
    if not session.get("negotiation_started"):
        negotiator.start_negotiation()
        session["negotiation_started"] = True

    # Get response
    response = negotiator.respond(message)

    # Track message
    session["events"].append({
        "type": "message",
        "user_message": message,
        "agent_response": response,
        "timestamp": datetime.utcnow().isoformat(),
    })

    return {
        "response": response,
        "phase": negotiator.current_phase.value,
    }


@router.get("/analytics/{agent_id}")
async def get_widget_analytics(
    agent_id: str,
    days: int = Query(default=7, ge=1, le=90),
) -> Dict[str, Any]:
    """Get widget analytics for an agent."""
    # Filter analytics for this agent
    agent_events = [
        e for e in _widget_analytics
        if e.get("agent_id") == agent_id
    ]

    # Calculate metrics
    total_opens = sum(1 for e in agent_events if e["event_type"] == "widget_opened")
    total_messages = sum(1 for e in agent_events if e["event_type"] == "message_sent")
    unique_sessions = len(set(e["widget_id"] for e in agent_events))

    return {
        "agent_id": agent_id,
        "period_days": days,
        "metrics": {
            "total_opens": total_opens,
            "total_messages": total_messages,
            "unique_sessions": unique_sessions,
            "avg_messages_per_session": total_messages / unique_sessions if unique_sessions > 0 else 0,
        },
        "recent_events": agent_events[-20:],  # Last 20 events
    }


@router.get("/demo")
async def widget_demo_page() -> HTMLResponse:
    """Demo page showing the widget in action."""
    html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RRA Widget Demo</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            line-height: 1.6;
        }
        h1 { color: #333; }
        pre {
            background: #f5f5f5;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
        }
        code { font-family: 'Monaco', 'Menlo', monospace; }
        .demo-section {
            margin: 40px 0;
            padding: 20px;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
        }
    </style>
</head>
<body>
    <h1>RRA Embeddable Widget Demo</h1>
    <p>This page demonstrates the RRA negotiation widget that can be embedded in any website.</p>

    <div class="demo-section">
        <h2>Quick Start</h2>
        <p>Add this script to your page:</p>
        <pre><code>&lt;script src="/api/widget/embed.js"&gt;&lt;/script&gt;
&lt;script&gt;
    RRAWidget.init({
        agentId: 'your-repo-id',
        theme: 'default',
        position: 'bottom-right',
        primaryColor: '#0066ff'
    });
&lt;/script&gt;</code></pre>
    </div>

    <div class="demo-section">
        <h2>Configuration Options</h2>
        <ul>
            <li><strong>agentId</strong> - Repository ID (required)</li>
            <li><strong>theme</strong> - 'default', 'dark', 'minimal', 'light'</li>
            <li><strong>position</strong> - 'bottom-right', 'bottom-left', 'top-right', 'top-left', 'inline'</li>
            <li><strong>primaryColor</strong> - Hex color code</li>
            <li><strong>language</strong> - 'en', 'es', 'zh', 'ja', 'de', 'fr'</li>
            <li><strong>autoOpen</strong> - Auto-open widget on page load</li>
            <li><strong>showBranding</strong> - Show "Powered by NatLangChain"</li>
        </ul>
    </div>

    <div class="demo-section">
        <h2>Live Demo</h2>
        <p>Click the chat bubble in the bottom-right corner to try the widget!</p>
    </div>

    <script src="/api/widget/embed.js"></script>
    <script>
        RRAWidget.init({
            agentId: 'demo-agent-123',
            theme: 'default',
            position: 'bottom-right',
            primaryColor: '#0066ff',
            showBranding: true
        });
    </script>
</body>
</html>
'''
    return HTMLResponse(content=html)
