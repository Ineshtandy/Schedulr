'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getMe, getPlanHistory } from '@/lib/api';
import { Plan, PlanHistoryItem, Message, UserInfo } from '@/lib/types';
import { loadChatMessages, saveChatMessages } from '@/lib/storage';
import ChatInterface from '@/components/ChatInterface';
import PlanViewer from '@/components/PlanViewer';
import PlanHistory from '@/components/PlanHistory';

export default function AppPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null);
  const [currentPlanId, setCurrentPlanId] = useState<string | null>(null);
  const [planHistory, setPlanHistory] = useState<PlanHistoryItem[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [showHistory, setShowHistory] = useState(true);

  // Check authentication on mount
  useEffect(() => {
    checkAuth();
    loadMessages();
    loadHistory();
  }, []);

  // Save messages whenever they change
  useEffect(() => {
    if (messages.length > 0) {
      saveChatMessages(messages);
    }
  }, [messages]);

  async function checkAuth() {
    try {
      const userInfo = await getMe();
      if (!userInfo.authenticated) {
        router.push('/');
        return;
      }
      setUser(userInfo);
    } catch (error) {
      console.error('Auth check failed:', error);
      router.push('/');
    }
  }

  function loadMessages() {
    const stored = loadChatMessages();
    setMessages(stored);
  }

  async function loadHistory() {
    try {
      const history = await getPlanHistory();
      setPlanHistory(history);
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  }

  function handleNewPlan(plan: Plan, plan_id: string) {
    setCurrentPlan(plan);
    setCurrentPlanId(plan_id);
    loadHistory(); // Refresh history
  }

  function handlePlanSelect(plan: Plan) {
    setCurrentPlan(plan);
    setCurrentPlanId(plan.plan_id);
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="md:hidden p-2 hover:bg-gray-100 rounded"
          >
            ☰
          </button>
          <h1 className="text-2xl font-bold text-gray-900">Schedulr</h1>
        </div>
        <div className="flex items-center gap-4">
          {user && (
            <span className="text-sm text-gray-600">{user.email}</span>
          )}
        </div>
      </header>

      {/* Main Content - 3 Panel Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Plan History */}
        <aside
          className={`${
            showHistory ? 'block' : 'hidden'
          } md:block w-full md:w-64 bg-white border-r border-gray-200 overflow-y-auto`}
        >
          <PlanHistory
            history={planHistory}
            currentPlanId={currentPlanId}
            onPlanSelect={handlePlanSelect}
          />
        </aside>

        {/* Center - Chat Interface */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <ChatInterface
            messages={messages}
            setMessages={setMessages}
            currentPlanId={currentPlanId}
            isGenerating={isGenerating}
            setIsGenerating={setIsGenerating}
            onNewPlan={handleNewPlan}
          />
        </main>

        {/* Right Sidebar - Plan Viewer */}
        <aside className="hidden lg:block w-96 bg-white border-l border-gray-200 overflow-y-auto">
          <PlanViewer
            plan={currentPlan}
            planId={currentPlanId}
            onDeploySuccess={loadHistory}
          />
        </aside>
      </div>
    </div>
  );
}
