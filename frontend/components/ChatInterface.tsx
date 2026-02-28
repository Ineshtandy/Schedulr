'use client';

import { useState, useRef, useEffect } from 'react';
import { generatePlan, updatePlan } from '@/lib/api';
import { Message, Plan } from '@/lib/types';

interface ChatInterfaceProps {
  messages: Message[];
  setMessages: (messages: Message[]) => void;
  currentPlanId: string | null;
  isGenerating: boolean;
  setIsGenerating: (value: boolean) => void;
  onNewPlan: (plan: Plan, planId: string) => void;
}

export default function ChatInterface({
  messages,
  setMessages,
  currentPlanId,
  isGenerating,
  setIsGenerating,
  onNewPlan,
}: ChatInterfaceProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  function scrollToBottom() {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isGenerating) return;

    const userMessage: Message = {
      role: 'user',
      content: input.trim(),
    };

    setMessages([...messages, userMessage]);
    setInput('');
    setIsGenerating(true);

    try {
      if (!currentPlanId) {
        // Generate initial plan
        const response = await generatePlan({
          goal: userMessage.content,
          num_days: 14,
          minutes_per_day: 90,
        });

        const assistantMessage: Message = {
          role: 'assistant',
          content: `I've created a ${response.plan.num_days}-day plan for "${response.plan.goal}". Check out the plan viewer to see the details!`,
          planId: response.plan_id,
        };

        setMessages([...messages, userMessage, assistantMessage]);
        onNewPlan(response.plan, response.plan_id);
      } else {
        // Update existing plan
        const response = await updatePlan({
          plan_id: currentPlanId,
          user_message: userMessage.content,
        });

        const assistantMessage: Message = {
          role: 'assistant',
          content: `I've updated your plan based on your feedback. The plan now reflects your changes!`,
          planId: response.plan_id,
        };

        setMessages([...messages, userMessage, assistantMessage]);
        onNewPlan(response.plan, response.plan_id);
      }
    } catch (error: any) {
      const errorMessage: Message = {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error.message}. Please try again.`,
      };
      setMessages([...messages, userMessage, errorMessage]);
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-20">
            <h2 className="text-2xl font-semibold mb-4">Start Planning!</h2>
            <p className="text-lg">Tell me what you'd like to accomplish.</p>
            <p className="text-sm mt-2">
              Example: "Train for a marathon in 14 days, 60 minutes per day"
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-900'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {isGenerating && (
          <div className="flex justify-start">
            <div className="bg-gray-200 text-gray-900 rounded-lg px-4 py-2">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce delay-200"></div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4 bg-white">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              currentPlanId
                ? 'Tell me how to adjust the plan...'
                : 'What would you like to plan?'
            }
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isGenerating}
          />
          <button
            type="submit"
            disabled={!input.trim() || isGenerating}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
