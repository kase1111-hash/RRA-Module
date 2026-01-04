'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2, MessageSquare, Sparkles, Check, Copy, ThumbsUp, ThumbsDown } from 'lucide-react';
import { cn, copyToClipboard } from '@/lib/utils';
import { StepProgress } from '@/components/ui/Progress';
import { Badge } from '@/components/ui/Badge';
import type { NegotiationMessage, NegotiationPhase } from '@/types';

interface NegotiationChatProps {
  messages: NegotiationMessage[];
  phase: NegotiationPhase;
  isLoading?: boolean;
  onSendMessage: (message: string) => void;
  onAcceptOffer?: () => void;
  floorPrice?: string;
  currentOffer?: string;
}

const NEGOTIATION_PHASES: NegotiationPhase[] = ['greeting', 'discovery', 'proposal', 'negotiation', 'closing', 'completed'];

const PHASE_LABELS: Record<NegotiationPhase, string> = {
  greeting: 'Hello',
  discovery: 'Discovery',
  proposal: 'Proposal',
  negotiation: 'Discuss',
  closing: 'Closing',
  completed: 'Complete',
};

const SUGGESTED_RESPONSES: Record<NegotiationPhase, string[]> = {
  greeting: ['Hello! I\'m interested in licensing this repo.', 'Hi, can you tell me about licensing options?'],
  discovery: ['I\'m building a commercial SaaS product.', 'It\'s for an open-source project.', 'Internal company use only.'],
  proposal: ['What\'s included in the standard license?', 'Can you explain the premium tier?', 'Are there volume discounts?'],
  negotiation: ['Which license fits my use case best?', 'What are the differences between tiers?', 'Do you have startup-friendly options?'],
  closing: ['I\'d like to proceed with this license.', 'Can I get the terms in writing first?'],
  completed: [],
};

export function NegotiationChat({
  messages,
  phase,
  isLoading,
  onSendMessage,
  onAcceptOffer,
  floorPrice,
  currentOffer,
}: NegotiationChatProps) {
  const [input, setInput] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    onSendMessage(input.trim());
    setInput('');
  };

  const handleSuggestedResponse = (response: string) => {
    if (isLoading) return;
    onSendMessage(response);
  };

  const handleCopyMessage = async (id: string, content: string) => {
    const success = await copyToClipboard(content);
    if (success) {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  const currentPhaseIndex = NEGOTIATION_PHASES.indexOf(phase);
  const suggestedResponses = SUGGESTED_RESPONSES[phase] || [];

  const phaseColors: Record<NegotiationPhase, string> = {
    greeting: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    discovery: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
    proposal: 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300',
    negotiation: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
    closing: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300',
  };

  return (
    <div className="flex h-full flex-col rounded-xl border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
      {/* Header with Progress */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center space-x-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900">
              <Bot className="h-4 w-4 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h3 className="font-medium text-gray-900 dark:text-white">
                License Advisor
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                AI-powered license selection
              </p>
            </div>
          </div>

          {/* Phase Badge */}
          <span
            className={cn(
              'rounded-full px-2.5 py-0.5 text-xs font-medium capitalize',
              phaseColors[phase]
            )}
          >
            {phase}
          </span>
        </div>

        {/* Step Progress Bar */}
        <div className="px-4 pb-3">
          <StepProgress
            steps={NEGOTIATION_PHASES.slice(0, -1).map(p => PHASE_LABELS[p])}
            currentStep={Math.min(currentPhaseIndex, 4)}
            size="sm"
          />
        </div>

        {/* Price Comparison (if available) */}
        {(floorPrice || currentOffer) && (
          <div className="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-900/50 text-xs">
            {floorPrice && (
              <div className="flex items-center gap-1.5">
                <span className="text-gray-500 dark:text-gray-400">Floor:</span>
                <span className="font-medium text-gray-700 dark:text-gray-300">{floorPrice}</span>
              </div>
            )}
            {currentOffer && (
              <div className="flex items-center gap-1.5">
                <span className="text-gray-500 dark:text-gray-400">Selected:</span>
                <Badge variant="success" size="sm">{currentOffer}</Badge>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={cn(
              'flex message-animate',
              message.role === 'buyer' ? 'justify-end' : 'justify-start'
            )}
          >
            <div
              className={cn(
                'flex max-w-[80%] items-start space-x-2',
                message.role === 'buyer' && 'flex-row-reverse space-x-reverse'
              )}
            >
              {/* Avatar */}
              <div
                className={cn(
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
                  message.role === 'agent'
                    ? 'bg-primary-100 dark:bg-primary-900'
                    : 'bg-gray-100 dark:bg-gray-700'
                )}
              >
                {message.role === 'agent' ? (
                  <Bot className="h-4 w-4 text-primary-600 dark:text-primary-400" />
                ) : (
                  <User className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                )}
              </div>

              {/* Message Content */}
              <div className="group/msg">
                <div
                  className={cn(
                    'rounded-2xl px-4 py-2',
                    message.role === 'agent'
                      ? 'bg-gray-100 text-gray-900 dark:bg-gray-700 dark:text-white'
                      : 'bg-primary-600 text-white'
                  )}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  <div
                    className={cn(
                      'mt-1 flex items-center justify-between gap-2 text-xs',
                      message.role === 'agent'
                        ? 'text-gray-500 dark:text-gray-400'
                        : 'text-primary-200'
                    )}
                  >
                    <span>
                      {new Date(message.timestamp).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                    {/* Message Actions */}
                    <div className="flex items-center gap-1 opacity-0 group-hover/msg:opacity-100 transition-opacity">
                      <button
                        onClick={() => handleCopyMessage(message.id, message.content)}
                        className="p-1 hover:bg-black/10 rounded transition-colors"
                        title="Copy message"
                      >
                        {copiedId === message.id ? (
                          <Check className="h-3 w-3" />
                        ) : (
                          <Copy className="h-3 w-3" />
                        )}
                      </button>
                      {message.role === 'agent' && (
                        <>
                          <button
                            className="p-1 hover:bg-black/10 rounded transition-colors"
                            title="Helpful"
                          >
                            <ThumbsUp className="h-3 w-3" />
                          </button>
                          <button
                            className="p-1 hover:bg-black/10 rounded transition-colors"
                            title="Not helpful"
                          >
                            <ThumbsDown className="h-3 w-3" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="flex items-center space-x-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900">
                <Bot className="h-4 w-4 text-primary-600 dark:text-primary-400" />
              </div>
              <div className="rounded-2xl bg-gray-100 px-4 py-3 dark:bg-gray-700">
                <div className="flex space-x-1">
                  <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: '0ms' }} />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: '150ms' }} />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Purchase Button (if in closing phase) */}
      {phase === 'closing' && onAcceptOffer && (
        <div className="border-t border-gray-200 px-4 py-3 dark:border-gray-700">
          <button
            onClick={onAcceptOffer}
            className="w-full rounded-lg bg-green-600 px-4 py-2 font-medium text-white hover:bg-green-700 transition-colors"
          >
            Accept & Purchase License
          </button>
        </div>
      )}

      {/* Suggested Responses */}
      {suggestedResponses.length > 0 && !isLoading && phase !== 'completed' && (
        <div className="border-t border-gray-200 px-4 py-3 dark:border-gray-700">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="h-3.5 w-3.5 text-amber-500" />
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
              Suggested responses
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {suggestedResponses.map((response, index) => (
              <button
                key={index}
                onClick={() => handleSuggestedResponse(response)}
                className="inline-flex items-center gap-1 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-colors dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                <MessageSquare className="h-3 w-3" />
                {response}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-gray-200 p-4 dark:border-gray-700"
      >
        <div className="flex items-center space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={phase === 'completed' ? 'Chat completed' : 'Type your message...'}
            disabled={isLoading || phase === 'completed'}
            className="flex-1 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 disabled:bg-gray-100 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 dark:disabled:bg-gray-800"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading || phase === 'completed'}
            className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors dark:disabled:bg-gray-600"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
