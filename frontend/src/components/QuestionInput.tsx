import { useState, FormEvent } from 'react';

interface QuestionInputProps {
  onSubmit: (question: string) => void;
  isLoading: boolean;
  disabled: boolean;
}

export function QuestionInput({ onSubmit, isLoading, disabled }: QuestionInputProps) {
  const [question, setQuestion] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (question.trim() && !isLoading && !disabled) {
      onSubmit(question.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative">
      <div className={`
        relative rounded-2xl transition-all duration-300
        ${isFocused ? 'ring-4 ring-primary-100' : ''}
        ${isLoading ? 'ring-4 ring-primary-100' : ''}
      `}>
        {/* Gradient border effect when focused */}
        {isFocused && (
          <div className="absolute -inset-[2px] bg-gradient-to-r from-primary-500 to-accent-500 rounded-2xl opacity-20 blur-sm" />
        )}
        
        <div className="relative">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={disabled ? "Upload a PDF first..." : "Ask anything about your documents..."}
            disabled={isLoading || disabled}
            className={`
              w-full px-5 py-4 pr-14
              bg-white border-2 rounded-2xl
              text-gray-900 placeholder-gray-400
              font-medium text-base
              transition-all duration-200
              ${isFocused ? 'border-primary-500' : 'border-gray-200'}
              ${disabled ? 'bg-gray-50 cursor-not-allowed' : 'hover:border-gray-300'}
              ${isLoading ? 'bg-gray-50' : ''}
            `}
          />

          <button
            type="submit"
            disabled={!question.trim() || isLoading || disabled}
            className={`
              absolute right-2 top-1/2 -translate-y-1/2
              w-10 h-10 rounded-xl
              flex items-center justify-center
              transition-all duration-300
              ${
                question.trim() && !isLoading && !disabled
                  ? 'bg-gradient-to-r from-primary-500 to-accent-500 text-white shadow-lg shadow-primary-500/30 hover:shadow-xl hover:shadow-primary-500/40 hover:scale-105 active:scale-95'
                  : 'bg-gray-100 text-gray-400'
              }
            `}
          >
            {isLoading ? (
              <div className="flex items-center justify-center">
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              </div>
            ) : (
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M14 5l7 7m0 0l-7 7m7-7H3"
                />
              </svg>
            )}
          </button>
        </div>
      </div>

      {disabled && (
        <p className="mt-3 text-sm text-gray-500 text-center flex items-center justify-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Upload at least one PDF document to start asking questions
        </p>
      )}
      
      {isLoading && (
        <p className="mt-3 text-sm text-primary-600 text-center flex items-center justify-center gap-2 animate-pulse">
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Searching documents and generating answer...
        </p>
      )}
    </form>
  );
}
