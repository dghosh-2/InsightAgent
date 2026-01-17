import { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { FileUpload } from './components/FileUpload';
import { DocumentList } from './components/DocumentList';
import { QuestionInput } from './components/QuestionInput';
import { AnswerDisplay } from './components/AnswerDisplay';
import { listDocuments, queryDocuments, getErrorMessage } from './services/api';
import type { DocumentInfo, QueryResponse } from './types';

function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [isQuerying, setIsQuerying] = useState(false);
  const [queryResponse, setQueryResponse] = useState<QueryResponse | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);

  // Load documents on mount
  useEffect(() => {
    const loadDocuments = async () => {
      try {
        const response = await listDocuments();
        setDocuments(response.documents);
      } catch (err) {
        console.error('Failed to load documents:', err);
      } finally {
        setIsLoadingDocs(false);
      }
    };

    loadDocuments();
  }, []);

  const handleUploadSuccess = useCallback((doc: DocumentInfo) => {
    setDocuments((prev) => [...prev, doc]);
  }, []);

  const handleDocumentDeleted = useCallback((documentId: string) => {
    setDocuments((prev) => prev.filter((d) => d.document_id !== documentId));
  }, []);

  const handleQuestion = useCallback(async (question: string) => {
    setIsQuerying(true);
    setQueryError(null);
    setQueryResponse(null);

    try {
      const response = await queryDocuments(question);
      setQueryResponse(response);
    } catch (err) {
      setQueryError(getErrorMessage(err));
    } finally {
      setIsQuerying(false);
    }
  }, []);

  return (
    <div className="min-h-screen bg-white pattern-dots">
      <Header />

      <main className="max-w-5xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Sidebar - Documents */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm">
              <h2 className="font-display font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <svg
                  className="w-5 h-5 text-primary-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                  />
                </svg>
                Upload PDF
              </h2>
              <FileUpload onUploadSuccess={handleUploadSuccess} />
            </div>

            <div className="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm">
              <h2 className="font-display font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <svg
                  className="w-5 h-5 text-primary-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                  />
                </svg>
                Documents
                {documents.length > 0 && (
                  <span className="ml-auto text-xs bg-primary-100 text-primary-700 px-2 py-0.5 rounded-full font-medium">
                    {documents.length}
                  </span>
                )}
              </h2>

              {isLoadingDocs ? (
                <div className="flex items-center justify-center py-8">
                  <div className="w-6 h-6 border-2 border-gray-200 border-t-primary-600 rounded-full animate-spin" />
                </div>
              ) : (
                <DocumentList
                  documents={documents}
                  onDocumentDeleted={handleDocumentDeleted}
                />
              )}
            </div>
          </div>

          {/* Main Content - Q&A */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white border border-gray-200 rounded-2xl p-5 shadow-sm">
              <h2 className="font-display font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <svg
                  className="w-5 h-5 text-primary-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                Ask a Question
              </h2>
              <QuestionInput
                onSubmit={handleQuestion}
                isLoading={isQuerying}
                disabled={documents.length === 0}
              />
            </div>

            <AnswerDisplay
              response={queryResponse}
              isLoading={isQuerying}
              error={queryError}
            />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-100 mt-16">
        <div className="max-w-5xl mx-auto px-6 py-6">
          <p className="text-center text-sm text-gray-400">
            InsightAgent · Powered by FAISS, BGE Embeddings, and OpenAI
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
