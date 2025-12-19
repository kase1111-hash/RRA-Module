'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { NegotiationMessage, NegotiationPhase } from '@/types';

interface NegotiationChatProps {
  messages: NegotiationMessage[];
  phase: NegotiationPhase;
  isLoading?: boolean;
  onSendMessage: (message: string) => void;
  onAcceptOffer?: () => void;
}

export function NegotiationChat({
  messages,
  phase,
  isLoading,
  onSendMessage,
  onAcceptOffer,
}: NegotiationChatProps) {
  const [input, setInput] = useState('');
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
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-700">
        <div className="flex items-center space-x-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900">
            <Bot className="h-4 w-4 text-primary-600 dark:text-primary-400" />
          </div>
          <div>
            <h3 className="font-medium text-gray-900 dark:text-white">
              Negotiator Agent
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              AI-powered licensing negotiation
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
              <div
                className={cn(
                  'rounded-2xl px-4 py-2',
                  message.role === 'agent'
                    ? 'bg-gray-100 text-gray-900 dark:bg-gray-700 dark:text-white'
                    : 'bg-primary-600 text-white'
                )}
              >
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                <p
                  className={cn(
                    'mt-1 text-xs',
                    message.role === 'agent'
                      ? 'text-gray-500 dark:text-gray-400'
                      : 'text-primary-200'
                  )}
                >
                  {new Date(message.timestamp).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
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

      {/* Accept Offer Button (if in closing phase) */}
      {phase === 'closing' && onAcceptOffer && (
        <div className="border-t border-gray-200 px-4 py-3 dark:border-gray-700">
          <button
            onClick={onAcceptOffer}
            className="w-full rounded-lg bg-green-600 px-4 py-2 font-medium text-white hover:bg-green-700 transition-colors"
          >
            Accept Offer & Purchase License
          </button>
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
            placeholder="Type your message..."
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
