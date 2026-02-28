'use client';

import { useState, useEffect } from 'react';

export default function LandingPage() {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const words = ['adventure', 'project', 'trip', 'hobby', 'resolution'];
  const [currentWordIndex, setCurrentWordIndex] = useState(0);
  const [isVisible, setIsVisible] = useState(true);
  
  useEffect(() => {
    const wordInterval = setInterval(() => {
      setIsVisible(false);
      setTimeout(() => {
        setCurrentWordIndex((prev) => (prev + 1) % words.length);
        setIsVisible(true);
      }, 300);
    }, 2800); // 2.5s pause + 0.3s transition
    
    return () => clearInterval(wordInterval);
  }, []);
  
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

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4">
      <div className="text-center">
        {/* Animated Heading */}
        <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-8">
          Ready to plan your next{' '}
          <div 
            className={`inline-block min-w-[250px] transition-opacity duration-300 ${
              isVisible ? 'opacity-100' : 'opacity-0'
            } ${getColorClass(words[currentWordIndex])}`}
            key={currentWordIndex}
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
