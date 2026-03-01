'use client';

import { useEffect, useState } from 'react';
import { deleteConversation } from '@/lib/api';
import { Conversation } from '@/lib/types';
import DeleteConversationModal from '@/components/DeleteConversationModal';

interface SidebarProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  onNewConversation: () => void;
  onSelectConversation: (conversationId: string) => void;
  onConversationDeleted?: (conversationId: string) => void;
}

export default function Sidebar({
  conversations,
  activeConversationId,
  onNewConversation,
  onSelectConversation,
  onConversationDeleted,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    return localStorage.getItem('schedulr_sidebar_collapsed') === '1';
  });

  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [conversationToDelete, setConversationToDelete] = useState<string | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [conversationBackup, setConversationBackup] = useState<Conversation | null>(null);
  const [displayedConversations, setDisplayedConversations] = useState<Conversation[]>(conversations);

  useEffect(() => {
    localStorage.setItem('schedulr_sidebar_collapsed', collapsed ? '1' : '0');
  }, [collapsed]);

  useEffect(() => {
    setDisplayedConversations(conversations);
  }, [conversations]);

  async function handleDeleteConversation() {
    if (!conversationToDelete) return;

    const conversation = conversations.find((c) => c.conversation_id === conversationToDelete);
    if (!conversation) return;

    setDeleteLoading(true);
    
    // Optimistic update: remove from displayed list
    const updatedList = displayedConversations.filter((c) => c.conversation_id !== conversationToDelete);
    setDisplayedConversations(updatedList);
    setConversationBackup(conversation);

    try {
      await deleteConversation(conversationToDelete);

      // Success
      setDeleteModalOpen(false);
      setConversationToDelete(null);
      setConversationBackup(null);

      // If deleted conversation was active, switch to another or clear active
      if (activeConversationId === conversationToDelete) {
        if (updatedList.length > 0) {
          onSelectConversation(updatedList[0].conversation_id);
        } else {
          onSelectConversation('');
        }
      }

      // Notify parent if callback provided
      if (onConversationDeleted) {
        onConversationDeleted(conversationToDelete);
      }
    } catch (error: unknown) {
      // Restore conversation on error
      setDisplayedConversations(conversations);
      setConversationBackup(null);
      const message = error instanceof Error ? error.message : 'Failed to delete conversation';
      alert(`Error deleting conversation: ${message}`);
    } finally {
      setDeleteLoading(false);
    }
  }

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
        {/* <button
          onClick={() => setCollapsed(true)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          ←
        </button> */}
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {displayedConversations.map((conversation) => (
          <div key={conversation.conversation_id} className="flex items-center gap-2 group">
            <button
              onClick={() => onSelectConversation(conversation.conversation_id)}
              className={`flex-1 text-left px-3 py-2 rounded-lg text-sm border ${
                activeConversationId === conversation.conversation_id
                  ? 'bg-blue-50 border-blue-200 text-blue-700'
                  : 'bg-white border-transparent hover:bg-gray-50 text-gray-700'
              }`}
            >
              <p className="font-medium truncate">{conversation.title || 'New chat'}</p>
              <p className="text-xs text-gray-700 mt-1 uppercase">{conversation.state}</p>
            </button>
            <button
              onClick={() => {
                setConversationToDelete(conversation.conversation_id);
                setDeleteModalOpen(true);
              }}
              className="p-2 text-gray-400 hover:text-red-600 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
              title="Delete conversation"
            >
              <svg
                className="w-4 h-4"
                fill="currentColor"
                viewBox="0 0 20 20"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  fillRule="evenodd"
                  d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        ))}

        {displayedConversations.length === 0 && (
          <div className="text-sm text-gray-800 p-3">No chats yet. Start a new plan.</div>
        )}
      </div>

      <DeleteConversationModal
        isOpen={deleteModalOpen}
        conversationTitle={
          conversations.find((c) => c.conversation_id === conversationToDelete)?.title || 'Conversation'
        }
        onConfirm={handleDeleteConversation}
        onCancel={() => {
          setDeleteModalOpen(false);
          setConversationToDelete(null);
        }}
        isLoading={deleteLoading}
      />
    </div>
  );
}
