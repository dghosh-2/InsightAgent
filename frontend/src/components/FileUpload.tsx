import { useState, useCallback } from 'react';
import { uploadDocument, getErrorMessage } from '../services/api';
import type { DocumentInfo } from '../types';

interface FileUploadProps {
  onUploadSuccess: (doc: DocumentInfo) => void;
}

export function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setError('Please upload a PDF file');
        return;
      }

      setIsUploading(true);
      setError(null);
      setSuccess(false);
      setUploadProgress('Uploading...');

      try {
        // Simulate progress stages
        setTimeout(() => setUploadProgress('Extracting text...'), 500);
        setTimeout(() => setUploadProgress('Creating embeddings...'), 1500);
        setTimeout(() => setUploadProgress('Indexing document...'), 3000);

        const response = await uploadDocument(file);
        
        setSuccess(true);
        setUploadProgress('Complete!');
        
        setTimeout(() => {
          onUploadSuccess({
            document_id: response.document_id,
            filename: response.filename,
            upload_time: new Date().toISOString(),
            page_count: response.page_count,
            chunk_count: response.chunk_count,
            file_size: file.size,
          });
          setSuccess(false);
          setUploadProgress('');
        }, 1000);
      } catch (err) {
        setError(getErrorMessage(err));
        setUploadProgress('');
      } finally {
        setIsUploading(false);
      }
    },
    [onUploadSuccess]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const file = e.dataTransfer.files[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile]
  );

  return (
    <div className="space-y-3">
      <label
        className={`
          relative flex flex-col items-center justify-center
          w-full h-44 border-2 border-dashed rounded-2xl
          cursor-pointer transition-all duration-300
          ${isDragging
            ? 'border-primary-500 bg-primary-50 scale-[1.02]'
            : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
          }
          ${isUploading || success ? 'pointer-events-none' : ''}
          ${success ? 'border-green-400 bg-green-50' : ''}
        `}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <input
          type="file"
          accept=".pdf"
          onChange={handleInputChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={isUploading}
        />

        {isUploading ? (
          <div className="flex flex-col items-center gap-4 animate-fade-in-up">
            {/* Animated loader */}
            <div className="relative">
              {/* Outer pulse ring */}
              <div className="absolute inset-0 w-16 h-16 rounded-full bg-gradient-to-r from-primary-400 to-accent-400 pulse-ring" />
              {/* Inner spinning circle */}
              <div className="relative w-16 h-16 rounded-full bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center glow-pulse">
                <div className="w-12 h-12 rounded-full bg-white flex items-center justify-center">
                  <svg className="w-6 h-6 text-primary-600 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                </div>
              </div>
            </div>
            
            {/* Progress text */}
            <div className="text-center">
              <p className="font-semibold text-gray-700">{uploadProgress}</p>
              {/* Progress bar */}
              <div className="mt-2 w-48 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full w-1/4 bg-gradient-to-r from-primary-500 to-accent-500 rounded-full progress-bar" />
              </div>
            </div>
          </div>
        ) : success ? (
          <div className="flex flex-col items-center gap-3 animate-scale-in">
            {/* Success checkmark */}
            <div className="w-16 h-16 rounded-full bg-green-500 flex items-center justify-center">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path className="checkmark-path" strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="font-semibold text-green-700">Upload Complete!</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3 transition-all duration-300">
            <div className={`
              w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-100 to-accent-100 
              flex items-center justify-center transition-transform duration-300
              ${isDragging ? 'scale-110' : 'group-hover:scale-105'}
            `}>
              <svg
                className={`w-7 h-7 text-primary-600 transition-transform duration-300 ${isDragging ? '-translate-y-1' : ''}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
            </div>
            <div className="text-center">
              <span className="text-sm font-semibold text-gray-700">
                {isDragging ? 'Drop to upload' : 'Drop your PDF here'}
              </span>
              {!isDragging && (
                <span className="text-sm text-gray-500"> or click to browse</span>
              )}
            </div>
            <span className="text-xs text-gray-400">PDF files up to 50MB</span>
          </div>
        )}
      </label>

      {error && (
        <div className="flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-100 rounded-xl text-sm text-red-600 animate-fade-in-up">
          <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
          {error}
        </div>
      )}
    </div>
  );
}
