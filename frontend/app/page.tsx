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
      <style>{`
        @keyframes blink {
          0%, 49% { opacity: 1; }
          50%, 100% { opacity: 0; }
        }
        .cursor {
          animation: blink 1s infinite;
          display: inline;
          margin: 0 2px;
        }
      `}</style>
      <div className="text-center">
        {/* Schedulr Title */}
        <h2 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">Schedulr</h2>

        {/* Animated Heading */}
        <h1 className="text-2xl md:text-3xl font-semibold text-gray-900 mb-8 leading-tight">
          Ready to plan your next<span className="cursor -mr-5">_</span>
          <div 
            className={`inline-flex items-center justify-center overflow-hidden w-[240px] h-[1.2em] transition-colors duration-200 drop-shadow-sm ${getColorClass(words[currentWordIndex])} ${getAnimationClass()}`}
          >
            {words[currentWordIndex]}?
          </div>
        </h1>

        {/* Sign in button */}
        <button
          onClick={handleSignIn}
          className="px-8 py-4 bg-white text-gray-700 text-lg font-semibold rounded-full hover:bg-gray-100 transition-colors shadow-lg hover:shadow-xl inline-flex items-center gap-3 border border-gray-300"
        >
          <img 
            src="https://www.gstatic.com/images/branding/product/1x/googleg_48dp.png" 
            alt="Google" 
            className="w-5 h-5"
          />
          Sign in with Google
        </button>
      </div>
    </div>
  );
}
