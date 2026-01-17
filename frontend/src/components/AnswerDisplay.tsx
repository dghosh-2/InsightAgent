import type { QueryResponse } from '../types';

interface AnswerDisplayProps {
  response: QueryResponse | null;
  isLoading: boolean;
  error: string | null;
}

export function AnswerDisplay({ response, isLoading, error }: AnswerDisplayProps) {
  if (isLoading) {
    return (
      <div className="bg-gradient-to-br from-gray-50 to-white border border-gray-100 rounded-2xl p-8 animate-fade-in-up">
        <div className="flex flex-col items-center gap-6">
          {/* AI thinking animation */}
          <div className="relative">
            {/* Outer glow */}
            <div className="absolute inset-0 w-20 h-20 rounded-full bg-gradient-to-r from-primary-400 to-accent-400 blur-xl opacity-40 animate-pulse" />
            
            {/* Main circle with gradient border */}
            <div className="relative w-20 h-20 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 p-1 glow-pulse">
              <div className="w-full h-full rounded-full bg-white flex items-center justify-center">
                {/* Brain/AI icon */}
                <svg className="w-8 h-8 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
            </div>
            
            {/* Orbiting dots */}
            <div className="absolute inset-0 animate-spin" style={{ animationDuration: '3s' }}>
              <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1 w-2 h-2 rounded-full bg-primary-500" />
            </div>
            <div className="absolute inset-0 animate-spin" style={{ animationDuration: '3s', animationDelay: '-1s' }}>
              <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1 w-2 h-2 rounded-full bg-accent-500" />
            </div>
          </div>
          
          {/* Text with typing indicator */}
          <div className="text-center space-y-3">
            <p className="font-display font-semibold text-gray-800 text-lg">Analyzing your documents</p>
            
            {/* Typing dots */}
            <div className="flex items-center justify-center gap-1">
              <div className="w-2 h-2 rounded-full bg-primary-500 typing-dot" />
              <div className="w-2 h-2 rounded-full bg-primary-400 typing-dot" />
              <div className="w-2 h-2 rounded-full bg-primary-300 typing-dot" />
            </div>
            
            <p className="text-sm text-gray-500">Searching through content and generating answer...</p>
          </div>
          
          {/* Shimmer skeleton preview */}
          <div className="w-full max-w-md space-y-3 mt-2">
            <div className="h-4 rounded-full shimmer-gradient" />
            <div className="h-4 rounded-full shimmer-gradient w-5/6" />
            <div className="h-4 rounded-full shimmer-gradient w-4/6" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-100 rounded-2xl p-6 animate-fade-in-up">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-red-100 flex items-center justify-center flex-shrink-0">
            <svg className="w-6 h-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-red-800 text-lg">Something went wrong</h3>
            <p className="text-sm text-red-600 mt-1">{error}</p>
            <p className="text-xs text-red-400 mt-2">Please try again or rephrase your question</p>
          </div>
        </div>
      </div>
    );
  }

  if (!response) {
    return (
      <div className="bg-gradient-to-br from-primary-50/50 to-accent-50/50 border border-primary-100 rounded-2xl p-10 text-center">
        <div className="w-20 h-20 mx-auto mb-5 rounded-2xl bg-gradient-to-br from-primary-100 to-accent-100 flex items-center justify-center">
          <svg
            className="w-10 h-10 text-primary-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <h3 className="font-display font-semibold text-gray-800 text-xl">Ask a Question</h3>
        <p className="text-gray-500 mt-3 max-w-sm mx-auto leading-relaxed">
          Type your question above and I'll search through your documents to find the answer with citations
        </p>
        
        {/* Example questions */}
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <span className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-xs text-gray-600">
            "What is the main topic?"
          </span>
          <span className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-xs text-gray-600">
            "Summarize chapter 1"
          </span>
          <span className="px-3 py-1.5 bg-white border border-gray-200 rounded-full text-xs text-gray-600">
            "Key findings?"
          </span>
        </div>
      </div>
    );
  }

  const confidenceColor =
    response.confidence >= 0.8
      ? 'text-green-600 bg-green-50 border-green-200'
      : response.confidence >= 0.5
      ? 'text-yellow-600 bg-yellow-50 border-yellow-200'
      : 'text-red-600 bg-red-50 border-red-200';

  const confidenceIcon = response.confidence >= 0.8 ? (
    <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
    </svg>
  ) : response.confidence >= 0.5 ? (
    <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
    </svg>
  ) : (
    <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
    </svg>
  );

  return (
    <div className="space-y-6 stagger-children">
      {/* Answer Section */}
      <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow duration-300">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h3 className="font-display font-semibold text-gray-900">Answer</h3>
          </div>
          <div className="flex items-center gap-3">
            <span className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${confidenceColor}`}>
              {confidenceIcon}
              {Math.round(response.confidence * 100)}% confidence
            </span>
            <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">
              {response.processing_time_ms}ms
            </span>
          </div>
        </div>
        <p className="text-gray-700 leading-relaxed whitespace-pre-wrap text-[15px]">
          {response.answer}
        </p>
      </div>

      {/* Citations Section */}
      {response.citations.length > 0 && (
        <div className="bg-gray-50 border border-gray-100 rounded-2xl p-6">
          <h3 className="font-display font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gray-200 flex items-center justify-center">
              <svg
                className="w-4 h-4 text-gray-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            Sources
            <span className="ml-1 text-sm font-normal text-gray-500">
              ({response.citations.length} found)
            </span>
          </h3>

          <div className="space-y-3">
            {response.citations.map((citation, index) => (
              <div
                key={index}
                className="bg-white border border-gray-200 rounded-xl p-4 hover:border-primary-300 hover:shadow-sm transition-all duration-200 group"
              >
                <div className="flex items-center gap-2 mb-3">
                  <span className="w-7 h-7 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 text-white text-xs font-bold flex items-center justify-center shadow-sm">
                    {index + 1}
                  </span>
                  <span className="font-semibold text-sm text-gray-900 truncate flex-1">
                    {citation.document_name}
                  </span>
                  <span className="text-xs text-gray-500 bg-gray-100 px-2.5 py-1 rounded-full flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                    </svg>
                    Page {citation.page_number}
                  </span>
                  <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-primary-50 text-primary-600">
                    {Math.round(citation.relevance_score * 100)}%
                  </span>
                </div>
                <div className="relative">
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-primary-400 to-accent-400 rounded-full" />
                  <p className="text-sm text-gray-600 leading-relaxed pl-4 italic">
                    "{citation.text_excerpt}"
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
