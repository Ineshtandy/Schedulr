'use client';

import { useEffect, useState } from 'react';
import { Conversation } from '@/lib/types';

interface SidebarProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  onNewConversation: () => void;
  onSelectConversation: (conversationId: string) => void;
}

export default function Sidebar({
  conversations,
  activeConversationId,
  onNewConversation,
  onSelectConversation,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    return localStorage.getItem('schedulr_sidebar_collapsed') === '1';
  });

  useEffect(() => {
    localStorage.setItem('schedulr_sidebar_collapsed', collapsed ? '1' : '0');
  }, [collapsed]);

  if (collapsed) {
    return (
      <div className="h-full p-3 flex flex-col gap-3">
        <button
          onClick={() => setCollapsed(false)}
          className="p-2 border border-gray-300 rounded-lg text-sm"
        >
          →
        </button>
        <button
          onClick={onNewConversation}
          className="p-2 bg-blue-600 text-white rounded-lg text-sm"
        >
          +
        </button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between gap-2">
        <button
          onClick={onNewConversation}
          className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          New plan
        </button>
        <button
          onClick={() => setCollapsed(true)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          ←
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {conversations.map((conversation) => (
          <button
            key={conversation.conversation_id}
            onClick={() => onSelectConversation(conversation.conversation_id)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm border ${
              activeConversationId === conversation.conversation_id
                ? 'bg-blue-50 border-blue-200 text-blue-700'
                : 'bg-white border-transparent hover:bg-gray-50 text-gray-700'
            }`}
          >
            <p className="font-medium truncate">{conversation.title || 'New chat'}</p>
            <p className="text-xs text-gray-500 mt-1 uppercase">{conversation.state}</p>
          </button>
        ))}

        {conversations.length === 0 && (
          <div className="text-sm text-gray-500 p-3">No chats yet. Start a new plan.</div>
        )}
      </div>
    </div>
  );
}
