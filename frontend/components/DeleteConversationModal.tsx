'use client';

interface DeleteConversationModalProps {
  isOpen: boolean;
  conversationTitle: string;
  onConfirm: () => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
}

export default function DeleteConversationModal({
  isOpen,
  conversationTitle,
  onConfirm,
  onCancel,
  isLoading = false,
}: DeleteConversationModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Delete Conversation?</h3>
        <p className="text-sm text-gray-700 mb-1">
          This conversation will be permanently deleted. This includes:
        </p>
        <ul className="text-sm text-gray-700 mb-4 list-disc list-inside space-y-1">
          <li>All messages in this chat</li>
          <li>All generated plans</li>
          <li>Any deployed plans to Google Tasks</li>
        </ul>
        <p className="text-sm font-medium text-gray-800 mb-4">
          <strong>"{conversationTitle}"</strong> cannot be recovered.
        </p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="flex-1 px-4 py-2 bg-gray-100 border border-gray-400 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed text-gray-800"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isLoading && <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />}
            {isLoading ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}
