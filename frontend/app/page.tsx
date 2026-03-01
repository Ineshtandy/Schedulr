'use client';

import { useState, useEffect } from 'react';

type AnimationPhase = 'idle' | 'exit' | 'enter';

export default function LandingPage() {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  const words = ['adventure', 'project', 'trip', 'hobby', 'resolution'];
  const [currentWordIndex, setCurrentWordIndex] = useState(0);
  const [animationPhase, setAnimationPhase] = useState<AnimationPhase>('idle');
  
  useEffect(() => {
    // Only run animation on client side
    if (typeof window === 'undefined') return;

    const phaseTimings = {
      idle: 1800,
      exit: 350,
      enter: 350,
    };
    const totalCycle = phaseTimings.idle + phaseTimings.exit + phaseTimings.enter; // 2500ms

    const runCycle = () => {
      setAnimationPhase('idle');
      
      setTimeout(() => {
        setAnimationPhase('exit');
      }, phaseTimings.idle);
      
      setTimeout(() => {
        setCurrentWordIndex((prev) => (prev + 1) % words.length);
        setAnimationPhase('enter');
      }, phaseTimings.idle + 300); // 300ms into exit, creates 50ms overlap
      
      setTimeout(() => {
        setAnimationPhase('idle');
      }, totalCycle);
    };

    runCycle();
    const interval = setInterval(runCycle, totalCycle);
    
    return () => clearInterval(interval);
  }, [words.length]);
  
  const handleSignIn = () => {
    window.location.href = `${API_URL}/api/auth/login`;
  };

  const getColorClass = (word: string) => {
    const colors: Record<string, string> = {
      adventure: 'text-blue-600',
      project: 'text-green-600',
      trip: 'text-purple-600',
      hobby: 'text-orange-600',
      resolution: 'text-pink-600',
    };
    return colors[word] || 'text-blue-600';
  };

  const getAnimationClass = () => {
    if (animationPhase === 'exit') {
      return 'animate-slideDown';
    }
    if (animationPhase === 'enter') {
      return 'animate-slideUp';
    }
    return '';
  };

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4">
      <div className="text-center">
        {/* Animated Heading */}
        <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-8 leading-tight">
          Ready to plan your next{' '}
          <div 
            className={`inline-flex items-center justify-center overflow-hidden w-[320px] h-[1.2em] transition-colors duration-200 drop-shadow-sm ${getColorClass(words[currentWordIndex])} ${getAnimationClass()}`}
          >
            {words[currentWordIndex]}
          </div>
        </h1>

        {/* Sign in button */}
        <button
          onClick={handleSignIn}
          className="px-8 py-4 bg-blue-600 text-white text-lg font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-lg hover:shadow-xl"
        >
          Sign in with Google
        </button>
      </div>
    </div>
  );
}
