'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  createConversation,
  generatePlan,
  getConversation,
  getMe,
  listConversations,
  updatePlan,
} from '@/lib/api';
import { Conversation, Message, Plan, UserInfo } from '@/lib/types';
import Sidebar from '@/components/Sidebar';
import ChatPanel from '@/components/ChatPanel';
import PlanPanel from '@/components/PlanPanel';

export default function AppPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null);
  const [currentPlanId, setCurrentPlanId] = useState<string | null>(null);
  const [conversationState, setConversationState] = useState<'idle' | 'awaiting_info' | 'generating'>('idle');
  const [isLoading, setIsLoading] = useState(false);
  const [planUpdating, setPlanUpdating] = useState(false);

  const activeConversation = useMemo(
    () => conversations.find((c) => c.conversation_id === activeConversationId) || null,
    [conversations, activeConversationId]
  );

  useEffect(() => {
    // Only run on client side
    if (typeof window === 'undefined') return;

    async function initialize() {
      let me: UserInfo;

      try {
        me = await getMe();
        if (!me.authenticated) {
          router.push('/');
          return;
        }
        setUser(me);
      } catch (error) {
        console.error('Authentication check failed:', error);
        router.push('/');
        return;
      }

      try {
        const items = await listConversations();
        setConversations(items);

        if (items.length > 0) {
          const firstId = items[0].conversation_id;
          const detail = await getConversation(firstId);
          setActiveConversationId(firstId);
          setMessages(detail.messages);
          setCurrentPlan(detail.latest_plan);
          setCurrentPlanId(detail.latest_plan?.plan_id || null);
          setConversationState((detail.conversation.state as 'idle' | 'awaiting_info' | 'generating') || 'idle');
        }
      } catch (error) {
        console.error('Initial conversation load failed:', error);
        setConversations([]);
      }
    }

    void initialize();
  }, [router]);

  async function refreshConversations(preferredId?: string) {
    const items = await listConversations();
    setConversations(items);
    if (preferredId) {
      setActiveConversationId(preferredId);
    } else if (!activeConversationId && items.length > 0) {
      setActiveConversationId(items[0].conversation_id);
    }
  }

  async function selectConversation(conversationId: string, source?: Conversation[]) {
    setIsLoading(true);
    try {
      const detail = await getConversation(conversationId);
      setActiveConversationId(conversationId);
      setMessages(detail.messages);
      setCurrentPlan(detail.latest_plan);
      setCurrentPlanId(detail.latest_plan?.plan_id || null);
      setConversationState((detail.conversation.state as 'idle' | 'awaiting_info' | 'generating') || 'idle');

      if (!source) {
        await refreshConversations(conversationId);
      }
    } finally {
      setIsLoading(false);
    }
  }

  async function handleNewConversation() {
    setIsLoading(true);
    try {
      const created = await createConversation();
      setActiveConversationId(created.conversation_id);
      setMessages([]);
      setCurrentPlan(null);
      setCurrentPlanId(null);
      setConversationState('idle');
      await refreshConversations(created.conversation_id);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSendMessage(content: string) {
    if (!activeConversationId || isLoading) {
      return;
    }

    // Optimistic: append user message immediately so the UI feels instant
    const optimisticMsg: Message = {
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticMsg]);
    setIsLoading(true);
    setPlanUpdating(true);

    try {
      if (!currentPlanId) {
        setConversationState('generating');
        const response = await generatePlan(activeConversationId, {
          user_message: content,
        });

        if (response.state === 'awaiting_info') {
          setConversationState('awaiting_info');
          // Append assistant questions optimistically
          if (response.questions) {
            const questionText = response.questions.map((q: string, i: number) => `${i + 1}. ${q}`).join('\n');
            setMessages((prev) => [
              ...prev,
              { role: 'assistant', content: `Before I build your first plan, please answer:\n${questionText}`, created_at: new Date().toISOString() },
            ]);
          }
        } else {
          setConversationState('idle');
          setCurrentPlan(response.plan || null);
          setCurrentPlanId(response.plan_id || null);
          // Append "Plan generated." assistant message
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: 'Plan generated.', created_at: new Date().toISOString() },
          ]);
        }
      } else {
        const response = await updatePlan(activeConversationId, {
          user_message: content,
        });
        setConversationState('idle');
        setCurrentPlan(response.plan || null);
        setCurrentPlanId(response.plan_id || null);
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: 'Plan updated.', created_at: new Date().toISOString() },
        ]);
      }

      // Only refresh sidebar (lightweight) — no need to re-fetch messages/plan
      refreshConversations(activeConversationId);
    } catch (error) {
      console.error('Failed to send message:', error);
      setConversationState(currentPlanId ? 'idle' : conversationState);
    } finally {
      setIsLoading(false);
      setPlanUpdating(false);
    }
  }

  // Show loading state during initial load
  if (!user) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-800">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Schedulr</h1>
        <div className="text-sm text-gray-800">{user?.email}</div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        <aside className="w-80 bg-white border-r border-gray-200 overflow-y-auto">
          <Sidebar
            conversations={conversations}
            activeConversationId={activeConversationId}
            onSelectConversation={selectConversation}
            onNewConversation={handleNewConversation}
          />
        </aside>

        <main className="flex-1 flex flex-col overflow-hidden">
          <ChatPanel
            messages={messages}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            hasPlan={Boolean(currentPlanId)}
            conversationState={conversationState}
            conversationTitle={activeConversation?.title || 'New chat'}
          />
        </main>

        <aside className="hidden xl:block w-[30rem] bg-white border-l border-gray-200 overflow-y-auto">
          <PlanPanel plan={currentPlan} planId={currentPlanId} isLoading={isLoading} planUpdating={planUpdating} />
        </aside>
      </div>
    </div>
  );
}
