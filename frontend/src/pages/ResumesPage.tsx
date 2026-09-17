import React, { useEffect, useState } from 'react';
import { resumeApi } from '../api/resumes';
import { Resume } from '../types/resume';
import { ResumeUpload } from '../components/resume/ResumeUpload';
import { ResumeCard } from '../components/resume/ResumeCard';
import { FileText, Loader2, FolderOpen } from 'lucide-react';

export const ResumesPage: React.FC = () => {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchResumes = async () => {
    try {
      setLoading(true);
      const data = await resumeApi.getResumes();
      setResumes(data.items);
    } catch {
      setError('Failed to load candidate resumes.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResumes();
  }, []);

  const handleUploadSuccess = () => {
    fetchResumes();
  };

  const handleDelete = () => {
    fetchResumes();
  };

  const handleSetPrimary = () => {
    fetchResumes();
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight text-white font-display">
          Resume Documents
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Upload, manage, and store candidate resume versions ready for AI analysis and ATS evaluation
        </p>
      </div>

      {/* Upload Zone */}
      <ResumeUpload onUploadSuccess={handleUploadSuccess} />

      {/* Resumes Grid */}
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <FileText className="h-5 w-5 text-brand-400" />
          <span>My Uploaded Resumes ({resumes.length})</span>
        </h2>
      </div>

      {loading ? (
        <div className="py-16 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-brand-500 mx-auto mb-2" />
          <p className="text-xs text-slate-400">Loading stored resumes...</p>
        </div>
      ) : error ? (
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-center text-sm">
          {error}
        </div>
      ) : resumes.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl border border-slate-800 text-center">
          <div className="h-16 w-16 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mx-auto mb-4">
            <FolderOpen className="h-8 w-8" />
          </div>
          <h3 className="text-base font-bold text-white mb-1">No resumes uploaded yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Use the upload dropzone above to ingest your first PDF, DOCX, or TXT resume document.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {resumes.map((resume) => (
            <ResumeCard
              key={resume.id}
              resume={resume}
              onDelete={handleDelete}
              onSetPrimary={handleSetPrimary}
            />
          ))}
        </div>
      )}
    </div>
  );
};
