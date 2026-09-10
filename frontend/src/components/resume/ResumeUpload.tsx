import React, { useState, useRef } from 'react';
import { resumeApi } from '../../api/resumes';
import { Resume } from '../../types/resume';
import { UploadCloud, FileText, AlertCircle, Loader2, CheckCircle2 } from 'lucide-react';

interface ResumeUploadProps {
  onUploadSuccess: (resume: Resume) => void;
}

export const ResumeUpload: React.FC<ResumeUploadProps> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [customName, setCustomName] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const allowedExtensions = ['.pdf', '.docx', '.txt'];
  const maxBytes = 10 * 1024 * 1024; // 10MB

  const handleFile = (file: File) => {
    setError(null);
    setSuccessMsg(null);

    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!allowedExtensions.includes(ext)) {
      setError(`Unsupported file format '${ext}'. Please upload a PDF, DOCX, or TXT document.`);
      return;
    }

    if (file.size === 0) {
      setError('The selected file is empty (0 bytes).');
      return;
    }

    if (file.size > maxBytes) {
      setError('File size exceeds the 10MB maximum limit.');
      return;
    }

    setSelectedFile(file);
    if (!customName) {
      // Auto-populate humanized name
      const base = file.name.replace(/\.[^/.]+$/, '').replace(/[_-]+/g, ' ');
      setCustomName(base.replace(/\b\w/g, (c) => c.toUpperCase()));
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const uploaded = await resumeApi.uploadResume(selectedFile, customName);
      setSuccessMsg(`"${uploaded.name}" uploaded successfully!`);
      setSelectedFile(null);
      setCustomName('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      onUploadSuccess(uploaded);
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      const msg = err.response?.data?.message || 'Failed to upload resume. Please try again.';
      setError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-slate-800 shadow-xl mb-8">
      <div className="text-center mb-6">
        <h2 className="text-xl font-bold text-white font-display">Upload Candidate Resume</h2>
        <p className="text-xs text-slate-400 mt-1">
          Secure document ingestion with magic-byte validation and encrypted server storage
        </p>
      </div>

      {error && (
        <div className="mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-3 text-rose-400 text-sm">
          <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="mb-6 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center gap-3 text-emerald-400 text-sm">
          <CheckCircle2 className="h-5 w-5 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Drag & Drop Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-2xl p-8 sm:p-10 text-center cursor-pointer transition-all ${
          isDragging
            ? 'border-brand-500 bg-brand-500/10 scale-[0.99]'
            : 'border-slate-700/80 hover:border-slate-600 bg-slate-900/40 hover:bg-slate-900/60'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
          onChange={handleInputChange}
          className="hidden"
        />

        <div className="flex flex-col items-center justify-center">
          <div className="h-14 w-14 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400 mb-4 shadow-inner">
            <UploadCloud className="h-7 w-7" />
          </div>

          <h3 className="text-base font-semibold text-white mb-1">
            {selectedFile ? selectedFile.name : 'Drag & Drop Resume Here'}
          </h3>
          <p className="text-xs text-slate-400 mb-3">
            {selectedFile
              ? `${(selectedFile.size / 1024).toFixed(1)} KB • Click to choose another file`
              : 'or browse your computer to select a file'}
          </p>

          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-850 border border-slate-800 text-[11px] font-medium text-slate-400">
            <span>PDF</span>
            <span>•</span>
            <span>DOCX</span>
            <span>•</span>
            <span>TXT</span>
            <span>•</span>
            <span>Max 10MB</span>
          </div>
        </div>
      </div>

      {/* Selected File Details & Custom Name */}
      {selectedFile && (
        <div className="mt-6 p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="h-10 w-10 rounded-lg bg-slate-800 flex items-center justify-center shrink-0 text-brand-400">
              <FileText className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <input
                type="text"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                placeholder="Resume display title"
                className="w-full bg-transparent border-b border-slate-700 text-sm font-semibold text-white focus:outline-none focus:border-brand-500 pb-0.5"
              />
              <span className="text-xs text-slate-400 truncate block">
                {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
              </span>
            </div>
          </div>

          <button
            onClick={handleUpload}
            disabled={isUploading}
            className="px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-slate-950 font-bold text-sm shadow-md shadow-brand-600/20 flex items-center justify-center gap-2 transition-all disabled:opacity-60 cursor-pointer shrink-0"
          >
            {isUploading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Validating & Uploading...</span>
              </>
            ) : (
              <span>Confirm & Upload</span>
            )}
          </button>
        </div>
      )}
    </div>
  );
};
