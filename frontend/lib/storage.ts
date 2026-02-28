// LocalStorage utilities for chat message persistence
import { Message } from './types';

const CHAT_STORAGE_KEY = 'schedulr_chat_messages';

export function saveChatMessages(messages: Message[]): void {
  try {
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
  } catch (error) {
    console.error('Failed to save chat messages:', error);
  }
}

export function loadChatMessages(): Message[] {
  try {
    const stored = localStorage.getItem(CHAT_STORAGE_KEY);
    if (!stored) return [];
    
    const messages = JSON.parse(stored);
    return Array.isArray(messages) ? messages : [];
  } catch (error) {
    console.error('Failed to load chat messages:', error);
    return [];
  }
}

export function clearChatMessages(): void {
  try {
    localStorage.removeItem(CHAT_STORAGE_KEY);
  } catch (error) {
    console.error('Failed to clear chat messages:', error);
  }
}
