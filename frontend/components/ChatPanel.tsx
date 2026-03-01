'use client';

import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { Message } from '@/lib/types';

interface ChatPanelProps {
  messages: Message[];
  onSendMessage: (message: string) => Promise<void>;
  isLoading: boolean;
  hasPlan: boolean;
  conversationState: 'idle' | 'awaiting_info' | 'generating';
  conversationTitle: string;
}

const STARTER_PILLS = [
  'Train for a marathon',
  'Learn a new language',
  'Manage patient intake workflow optimization',
  'Construction on Baltimore Ave for the next two weeks',
];

export default function ChatPanel({
  messages,
  onSendMessage,
  isLoading,
  hasPlan,
  conversationState,
  conversationTitle,
}: ChatPanelProps) {
  const [input, setInput] = useState('');
  const scrollAnchorRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change or loading state changes
  useEffect(() => {
    scrollAnchorRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const placeholder = useMemo(() => {
    if (conversationState === 'awaiting_info') {
      return 'Answer the two questions so I can build your first plan...';
    }
    if (hasPlan) {
      return 'Describe changes to update your plan...';
    }
    return 'Describe your goal to start planning...';
  }, [conversationState, hasPlan]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const message = input.trim();
    if (!message || isLoading) return;
    setInput('');
    await onSendMessage(message);
  }

  async function sendStarter(text: string) {
    if (isLoading) return;
    setInput('');
    await onSendMessage(text);
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-6 py-4 border-b border-gray-200 bg-white">
        <h2 className="text-lg font-semibold text-gray-900 truncate">{conversationTitle}</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="space-y-4">
            <div>
              <p className="text-xl font-semibold text-gray-900">Start a new conversation</p>
              {/* <p className="text-sm mt-1 text-gray-800">The first message asks two clarifying questions before initial plan generation.</p> */}
            </div>
            <div className="flex flex-wrap gap-2">
              {STARTER_PILLS.map((pill) => (
                <button
                  key={pill}
                  onClick={() => sendStarter(pill)}
                  className="px-3 py-1.5 rounded-full border border-gray-300 bg-white text-sm text-gray-900 hover:bg-gray-50"
                >
                  {pill}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message, idx) => (
          <div key={`${message.created_at || idx}-${idx}`} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] rounded-xl px-4 py-2 whitespace-pre-wrap ${
                message.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-900'
              }`}
            >
              {message.content}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="text-sm text-gray-700">Working on your request…</div>
        )}

        {/* Invisible anchor for auto-scroll */}
        <div ref={scrollAnchorRef} />
      </div>

      <div className="border-t border-gray-200 p-4 bg-white">
        <form onSubmit={submit} className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={placeholder}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-5 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
