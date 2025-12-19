'use client';

import { useParams, useRouter } from 'next/navigation';
import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { ArrowLeft, Send, Loader2, MessageCircle } from 'lucide-react';

interface Message {
  id: string;
  role: 'agent' | 'buyer';
  content: string;
  timestamp: Date;
}

// Mock repository data for now
const mockRepos: Record<string, { name: string; owner: string }> = {
  'rra-module-abc123': { name: 'RRA-Module', owner: 'kase1111-hash' },
  'web3-utils-def456': { name: 'web3-utils', owner: 'example' },
  'ml-pipeline-ghi789': { name: 'ml-pipeline', owner: 'example' },
};

export default function DirectChatPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isConnecting, setIsConnecting] = useState(true);
  const [phase, setPhase] = useState<string>('greeting');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const repo = mockRepos[id] || { name: 'Unknown Repository', owner: 'unknown' };

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Simulate connection and initial greeting
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsConnecting(false);
      setMessages([
        {
          id: '1',
          role: 'agent',
          content: `Welcome! I'm the licensing agent for ${repo.name}. I'm here to help you explore licensing options and find the right package for your needs. What type of project are you working on?`,
          timestamp: new Date(),
        },
      ]);
      setPhase('discovery');
    }, 1500);

    return () => clearTimeout(timer);
  }, [repo.name]);

  const handleSendMessage = useCallback(() => {
    if (!inputValue.trim() || isTyping) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'buyer',
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    // Simulate agent response
    setTimeout(() => {
      const responses = [
        "That's a great use case! Based on what you've shared, I'd recommend our Team License which covers up to 5 developers. Would you like to hear more about the pricing?",
        "I understand your requirements. Our licensing is flexible - we offer individual, team, and enterprise options. Given your project scope, what's your budget range?",
        "Excellent! This repository includes full source access, regular updates, and dedicated support. The starting price is 0.05 ETH for a team license. Would you like to proceed?",
        "I'm happy to negotiate on the terms. What price point would work for your budget? We can also discuss alternative licensing models.",
      ];

      const response: Message = {
        id: (Date.now() + 1).toString(),
        role: 'agent',
        content: responses[Math.floor(Math.random() * responses.length)],
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, response]);
      setIsTyping(false);

      // Progress through phases
      if (messages.length > 2 && phase === 'discovery') {
        setPhase('proposal');
      } else if (messages.length > 4 && phase === 'proposal') {
        setPhase('negotiation');
      }
    }, 1500);
  }, [inputValue, isTyping, messages.length, phase]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  if (isConnecting) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <Loader2 className="mx-auto h-12 w-12 animate-spin text-primary-600" />
          <p className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
            Connecting to agent...
          </p>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Starting negotiation session for {repo.name}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.back()}
              className="rounded-lg p-2 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <ArrowLeft className="h-5 w-5 text-gray-600 dark:text-gray-400" />
            </button>
            <div>
              <h1 className="font-semibold text-gray-900 dark:text-white">
                {repo.name}
              </h1>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {repo.owner}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-primary-100 px-3 py-1 text-xs font-medium text-primary-700 dark:bg-primary-900 dark:text-primary-300">
              {phase.charAt(0).toUpperCase() + phase.slice(1)}
            </span>
            <Link
              href={`/agent/${id}`}
              className="text-sm text-primary-600 hover:underline dark:text-primary-400"
            >
              View Details
            </Link>
          </div>
        </div>
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto max-w-4xl space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'buyer' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  message.role === 'buyer'
                    ? 'bg-primary-600 text-white'
                    : 'bg-white text-gray-900 shadow-sm dark:bg-gray-800 dark:text-white'
                }`}
              >
                <p className="text-sm">{message.content}</p>
                <p
                  className={`mt-1 text-xs ${
                    message.role === 'buyer'
                      ? 'text-primary-200'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}
                >
                  {message.timestamp.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex justify-start">
              <div className="rounded-2xl bg-white px-4 py-3 shadow-sm dark:bg-gray-800">
                <div className="flex gap-1">
                  <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: '0ms' }} />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: '150ms' }} />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <div className="mx-auto flex max-w-4xl gap-3">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            className="flex-1 rounded-xl border border-gray-300 px-4 py-3 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isTyping}
            className="rounded-xl bg-primary-600 px-6 py-3 text-white transition-colors hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
